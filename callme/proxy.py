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

import logging
import socket
import time
import uuid

import kombu

from callme import base
from callme import exceptions as exc
from callme import protocol as pr

LOG = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60


class Proxy(base.Base):
    """This Proxy class is used to handle the communication with the rpc
    server.

    :keyword server_id: default id of the Server (can be declared later
        see :func:`use_server`)
    :keyword amqp_host: the host of where the AMQP Broker is running
    :keyword amqp_user: the username for the AMQP Broker
    :keyword amqp_password: the password for the AMQP Broker
    :keyword amqp_vhost: the virtual host of the AMQP Broker
    :keyword amqp_port: the port of the AMQP Broker
    :keyword ssl: use SSL connection for the AMQP Broker
    :keyword timeout: default timeout for calls in seconds
    :keyword durable: make all exchanges and queues durable
    :keyword auto_delete: delete server queues after all connections are closed
        not applicable for client queues
    """

    def __init__(self,
                 server_id,
                 amqp_host='localhost',
                 amqp_user='guest',
                 amqp_password='guest',
                 amqp_vhost='/',
                 amqp_port=5672,
                 ssl=False,
                 timeout=REQUEST_TIMEOUT,
                 durable=False,
                 auto_delete=True):

        super(Proxy, self).__init__(amqp_host, amqp_user, amqp_password,
                                    amqp_vhost, amqp_port, ssl)
        self._uuid = str(uuid.uuid4())
        self._server_id = server_id
        self._timeout = timeout
        self._is_received = False
        self._corr_id = None
        self._response = None
        self._exchange_name = 'client_{0}_ex_{1}'.format(amqp_user, self._uuid)
        self._queue_name = 'client_{0}_queue_{1}'.format(amqp_user, self._uuid)
        self._durable = durable
        self._auto_delete = auto_delete

        # create exchange
        exchange = self._make_exchange(self._exchange_name,
                                       durable=self._durable,
                                       auto_delete=True)

        # create queue
        queue = self._make_queue(self._queue_name, exchange,
                                 durable=self._durable,
                                 auto_delete=True)

        # create consumer
        consumer = kombu.Consumer(channel=self._conn,
                                  queues=queue,
                                  callbacks=[self._on_response],
                                  accept=['pickle'])
        consumer.consume()

    def use_server(self, server_id=None, timeout=None):
        """Use the specified server and set an optional timeout for the method
        call.

        Typical use:

            >> my_proxy.use_server('fooserver').a_remote_func()

        :keyword server_id: the server id where the call will be made
        :keyword timeout: set or overrides the call timeout in seconds
        :rtype: return `self` to cascade further calls
        """
        if server_id is not None:
            self._server_id = server_id
        if timeout is not None:
            self._timeout = timeout
        return self

    def _on_response(self, response, message):
        """This method is automatically called when a response is incoming and
        decides if it is the message we are waiting for - the message with the
        result.

        :param response: the body of the amqp message already deserialized
            by kombu
        :param message: the plain amqp kombu.message with additional
            information
        """
        LOG.debug("Got response: {0}".format(response))
        try:
            message.ack()
        except Exception:
            LOG.exception("Failed to acknowledge AMQP message.")
        else:
            LOG.debug("AMQP message acknowledged.")

            # check response type
            if not isinstance(response, pr.RpcResponse):
                LOG.warning("Response is not a `RpcResponse` instance.")
                return

            # process response
            try:
                if self._corr_id == message.properties['correlation_id']:
                    self._response = response
                    self._is_received = True
            except KeyError:
                LOG.error("Message has no `correlation_id` property.")

    def __request(self, func_name, func_args):
        """The remote-method-call execution function.

        :param func_name: name of the method that should be executed
        :param func_args: parameter for the remote-method
        :type func_name: string
        :type func_args: list of parameters
        :rtype: result of the method
        """
        self._corr_id = str(uuid.uuid4())
        request = pr.RpcRequest(func_name, func_args)
        LOG.debug("Publish request: {0}".format(request))

        # publish request
        with kombu.producers[self._conn].acquire(block=True) as producer:
            exchange = self._make_exchange(
                'server_{0}_ex'.format(self._server_id),
                durable=self._durable,
                auto_delete=self._auto_delete)
            queue = self._make_queue(
                'server_{0}_queue'.format(self._server_id), exchange,
                durable=self._durable,
                auto_delete=self._auto_delete)
            producer.publish(body=request,
                             serializer='pickle',
                             exchange=exchange,
                             reply_to=self._exchange_name,
                             correlation_id=self._corr_id,
                             declare=[queue])

        # start waiting for the response
        self._wait_for_result()
        self._is_received = False

        # handler response
        result = self._response.result
        LOG.debug("Result: {!r}".format(result))
        if self._response.is_exception:
            raise result
        return result

    def _wait_for_result(self):
        """Waits for the result from the server, checks every second if
        a timeout occurred. If a timeout occurred - the `RpcTimeout` exception
        will be raised.
        """
        start_time = time.time()
        while not self._is_received:
            try:
                self._conn.drain_events(timeout=1)
            except socket.timeout:
                if self._timeout > 0:
                    if time.time() - start_time > self._timeout:
                        raise exc.RpcTimeout("RPC Request timeout")

    def __getattr__(self, name):
        """This method is invoked, if a method is being called, which doesn't
        exist on Proxy. It is used for RPC, to get the function which should
        be called on the Server.
        """
        # magic method dispatcher
        LOG.debug("Recursion: {0}".format(name))
        return _Method(self.__request, name)

# ===========================================================================


class _Method:
    """This class is used to realize remote-method-calls.

    :param send: name of the function that should be executed on Proxy
    :param name: name of the method which should be called on the Server
    """
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
        self._send = send
        self._name = name

    def __getattr__(self, name):
        return _Method(self._send, "{0}.{1}".format(self._name, name))

    def __call__(self, *args):
        return self._send(self._name, args)

# ===========================================================================
