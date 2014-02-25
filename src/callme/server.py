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
        self._exchange_name = 'server_' + server_id + '_ex'
        self._queue_name = 'server_' + server_id + '_queue'

        # create exchange
        exchange = self._make_exchange(self._exchange_name)

        # create queue
        queue = kombu.Queue(name=self._queue_name,
                            exchange=exchange,
                            durable=False,
                            auto_delete=True)

        try:
            self._conn.connect()
        except IOError:
            LOG.critical("Connection Error: Probably AMQP User has"
                         " not enough permissions")
            raise exc.ConnectionError("Connection Error: Probably AMQP User "
                                      "has not enough permissions")

        # create consumer
        self._consumer = kombu.Consumer(self._conn,
                                        queues=queue,
                                        callbacks=[self._on_request],
                                        accept=['pickle'])
        self._consumer.consume()

    def _on_request(self, request, message):
        """This method is automatically called when a request is incoming.

        :param request: the body of the amqp message already deserialized
            by kombu
        :param message: the plain amqp kombu.message with additional
            information
        """
        LOG.info("Got request: {0}".format(request))
        try:
            message.ack()
        except Exception:
            LOG.exception("Failed to acknowledge AMQP message.")
        else:
            LOG.debug("AMQP message acknowledged.")

            # check request type
            if not isinstance(request, pr.RpcRequest):
                LOG.warning("Request is not an `RpcRequest` instance.")
                return

            # process request
            if self._threaded:
                p = threading.Thread(target=self._process_request,
                                     args=(request, message))
                p.daemon = True
                p.start()
                LOG.debug("New thread spawned to process the {0} request."
                          .format(request))
            else:
                self._process_request(request, message)

    def _process_request(self, request, message):
        """Process incoming request."""
        LOG.debug("Call func on server {0}".format(self._server_id))
        corr_id = message.properties['correlation_id']
        reply_to = message.properties['reply_to']
        try:
            LOG.debug("Correlation id: {0}".format(corr_id))
            LOG.debug("Call func with args {!r}".format(request.func_args))
            result = self._func_dict[request.func_name](*request.func_args)
            LOG.debug("Result: {!r}".format(result))
            response = pr.RpcResponse(result)
        except Exception as e:
            LOG.error("Exception happened: {0}".format(e))
            response = pr.RpcResponse(e)

        LOG.debug("Publish response: {0}".format(response))
        with kombu.producers[self._conn].acquire(block=True) as producer:
            exchange = self._make_exchange(reply_to)
            producer.publish(body=response,
                             serializer='pickle',
                             exchange=exchange,
                             correlation_id=corr_id)

    def _cleanup(self):
        """Clean-up all resources."""
        try:
            self._consumer.cancel()
            self._conn.close()
            self._is_stopped = True
        except Exception:
            LOG.exception("Resource clean-up failed.")

    def register_function(self, func, name=None):
        """Registers a function as rpc function so that is accessible from the
        proxy.

        :param func: the function we want to provide as rpc method
        :param name: the name with which the function is visible to the clients
        """
        if not callable(func):
            raise ValueError("The '{0}' is not callable.".format(func))

        self._func_dict[name if name is not None else func.__name__] = func

    def start(self):
        """Start the server."""
        LOG.info("Server with id='{0}' started.".format(self._server_id))
        self._is_stopped = False
        try:
            while self._do_run:
                try:
                    self._conn.drain_events(timeout=1)
                except socket.timeout:
                    pass
                except Exception:
                    LOG.exception("Draining events failed.")
                    return
                except KeyboardInterrupt:
                    LOG.info("Server with id='{0}' stopped.".format(
                        self._server_id))
                    return
        finally:
            self._cleanup()

    def stop(self):
        """Stop the server."""
        LOG.debug("Stopping the '{0}' server.".format(self._server_id))
        self._do_run = False
        while not self._is_stopped:
            LOG.debug("Wait server to stop.")
            time.sleep(0.1)
