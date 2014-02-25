# Copyright (c) 2009-2014, Christian Haintz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
#     * Neither the name of callme nor the names of its contributors
#       may be used to endorse or promote products derived from this
#       software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import kombu
import logging
import socket
import threading
import time

import six

if six.PY2:
    import Queue as queue
else:
    import queue

from callme import base
from callme import exceptions as exc
from callme import protocol as pr

LOG = logging.getLogger(__name__)


class Server(base.Base):
    """This Server class is used to provide an RPC server.

    :keyword server_id: id of the server
    :keyword amqp_host: the host of where the AMQP Broker is running
    :keyword amqp_user: the username for the AMQP Broker
    :keyword amqp_password: the password for the AMQP Broker
    :keyword amqp_vhost: the virtual host of the AMQP Broker
    :keyword amqp_port: the port of the AMQP Broker
    :keyword ssl: use SSL connection for the AMQP Broker
    :keyword threaded: use of multithreading, if set to true RPC call-execution
        will processed parallel (one thread per call) which dramatically
        improves performance
    """

    def __init__(self,
                 server_id,
                 amqp_host='localhost',
                 amqp_user='guest',
                 amqp_password='guest',
                 amqp_vhost='/',
                 amqp_port=5672,
                 ssl=False,
                 threaded=False):
        super(Server, self).__init__(amqp_host, amqp_user, amqp_password,
                                     amqp_vhost, amqp_port, ssl)
        self._server_id = server_id
        self._threaded = threaded
        self._do_run = True
        self._is_stopped = True
        self._func_dict = {}
        self._result_queue = queue.Queue()
        self._exchange_name = 'server_' + server_id + '_ex'

        # create exchange
        target_exchange = self._make_exchange(self._exchange_name)

        # create queue
        target_queue = kombu.Queue("server_"+server_id+"_queue",
                                   exchange=target_exchange,
                                   durable=False,
                                   auto_delete=True)

        try:
            self._conn.connect()
        except IOError:
            LOG.critical("Connection Error: Probably AMQP User has"
                         " not enough permissions")
            raise exc.ConnectionError("Connection Error: Probably AMQP User "
                                      "has not enough permissions")

        self._publish_connection = kombu.BrokerConnection(
            hostname=amqp_host,
            userid=amqp_user,
            password=amqp_password,
            virtual_host=amqp_vhost,
            port=amqp_port,
            ssl=ssl
        )

        # consume
        self._consumer = kombu.Consumer(self._conn, target_queue,
                                        accept=['pickle'])
        if self._threaded:
            self._consumer.register_callback(self._on_request_threaded)
        else:
            self._consumer.register_callback(self._on_request)
        self._consumer.consume()
        self._pub_thread = None

        LOG.debug("Initialization done")

    def _on_request(self, request, message):
        """This method is automatically called when a request is incoming. It
        processes the incoming rpc calls in a serial manner (no multi-
        threading).

        :param request: the body of the amqp message already deserialized
            by kombu
        :param message: the plain amqp kombu.message with additional
            information
        """
        LOG.info("Got request: {0}".format(request))
        if not isinstance(request, pr.RpcRequest):
            LOG.debug("Request is not an `RpcRequest` instance!")
            return

        LOG.debug("Call func on server {0}".format(self._server_id))
        try:
            LOG.debug("Correlation id: {0}".format(
                      message.properties['correlation_id']))
            LOG.debug("Call func with args {!r}".format(request.func_args))

            result = self._func_dict[request.func_name](*request.func_args)

            LOG.debug("Result: {!r}".format(result))
            LOG.debug("Build response")
            rpc_resp = pr.RpcResponse(result)
        except Exception as e:
            LOG.debug("Exception happened: {0}".format(e))
            rpc_resp = pr.RpcResponse(e)

        message.ack()

        LOG.debug("Publish response")
        # producer
        src_exchange = kombu.Exchange(message.properties['reply_to'],
                                      durable=False, auto_delete=True)
        producer = kombu.Producer(self._publish_connection, src_exchange,
                                  auto_declare=False)

        producer.publish(rpc_resp, serializer='pickle',
                         correlation_id=message.properties['correlation_id'])

        LOG.debug("Acknowledge")

    def _on_request_threaded(self, request, message):
        """This method is automatically called when a request is incoming and
        `threaded` set to `True`. It processes the incoming rpc calls in
        a parallel manner (one thread for each request). A separate Publisher
        thread is used to send back the results.

        :param request: the body of the amqp message already deserialized
            by kombu
        :param message: the plain amqp kombu.message with additional
            information
        """
        LOG.info("Got request: {0}".format(request))
        if not isinstance(request, pr.RpcRequest):
            LOG.debug("Request is not an `RpcRequest` instance!")
            return

        message.ack()
        LOG.debug("Acknowledge")

        def exec_func(message, result_queue):
            LOG.debug("Call func on server{0}".format(self._server_id))
            try:
                LOG.debug("Correlation id: {0}".format(
                          message.properties['correlation_id']))
                LOG.debug("Call func with args {!r}".format(request.func_args))

                result = self._func_dict[request.func_name](*request.func_args)

                LOG.debug("Result: {!r}".format(result))
                LOG.debug("Build response")
                rpc_resp = pr.RpcResponse(result)
            except Exception as e:
                LOG.debug("Exception happened: {0}".format(e))
                rpc_resp = pr.RpcResponse(e)

            result_queue.put(ResultSet(rpc_resp,
                                       message.properties['correlation_id'],
                                       message.properties['reply_to']))

        p = threading.Thread(target=exec_func,
                             name=message.properties['correlation_id'],
                             args=(message, self._result_queue))
        p.start()

    def _cleanup(self):
        """Clean-up all resources."""
        try:
            if self._threaded:
                self._pub_thread.stop()
            self._consumer.cancel()
            self._conn.close()
            self._publish_connection.close()
            self._is_stopped = True
        except Exception as e:
            LOG.error('Resource clean-up failed: {0}'.format(e))

    def register_function(self, func, name=None):
        """Registers a function as rpc function so that is accessible from the
        proxy.

        :param func: the function we want to provide as rpc method
        :param name: the name with which the function is visible to the clients
        """
        if not callable(func):
            raise ValueError("The '%s' is not callable." % func)

        self._func_dict[name if name is not None else func.__name__] = func

    def start(self):
        """Start the server. If `threaded` is `True` also starts the Publisher
        thread.
        """
        self._is_stopped = False
        if self._threaded:
            self._pub_thread = Publisher(self._result_queue,
                                         self._publish_connection)
            self._pub_thread.start()

        LOG.info("Server with id='{0}' started.".format(self._server_id))
        try:
            while self._do_run:
                try:
                    self._conn.drain_events(timeout=1)
                except socket.timeout:
                    pass
                except Exception as e:
                    LOG.error("Draining events failed: {0}".format(e))
                    return
                except KeyboardInterrupt:
                    LOG.info("Server with id='{0}' stopped.".format(
                        self._server_id))
                    return
        finally:
            self._cleanup()

    def stop(self):
        """Stop the server."""
        LOG.debug("Stop server")
        self._do_run = False
        while not self._is_stopped:
            LOG.debug("Wait server stop...")
            time.sleep(0.1)


class Publisher(threading.Thread):
    """This class is a thread class and used internally for sending back
    results to the client.

    :param result_queue: a Queue.Queue type queue which is thread-safe and
        holds the results which should be sent back. Item in the queue must
        be of type :class:`ResultSet`.
    :param channel: a kombu.channel
    """

    def __init__(self, result_queue, channel):
        threading.Thread.__init__(self)
        self.result_queue = result_queue
        self.channel = channel
        self.stop_it = False

    def run(self):
        while not self.stop_it:
            try:
                result_set = self.result_queue.get(block=True, timeout=1)
                LOG.debug("Publish response: {!r}".format(result_set))

                src_exchange = kombu.Exchange(result_set.reply_to,
                                              durable=False, auto_delete=True)
                producer = kombu.Producer(self.channel, src_exchange,
                                          auto_declare=False)

                producer.publish(result_set.rpc_resp, serializer='pickle',
                                 correlation_id=result_set.correlation_id)

            except queue.Empty:
                pass

    def stop(self):
        """Stop the Publisher thread."""
        self.stop_it = True
        self.join()


class ResultSet(object):
    """This class is used as type for the items in the result_queue when used
    in threaded mode. It stores all information needed to send back the result
    to the right client.

    :param rpc_resp: the RPC Response object of type :class:`RpcResponse`
    :param correlation_id: the correlation_id of the amqp message
    :param reply_to: the reply_to field of the amqp message
    """

    def __init__(self, rpc_resp, correlation_id, reply_to):
        self.rpc_resp = rpc_resp
        self.correlation_id = correlation_id
        self.reply_to = reply_to
