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
import time
import uuid

from kombu import utils

from callme import exceptions as exc
from callme import protocol

LOG = logging.getLogger(__name__)


class Proxy(object):
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
    """
    response = None

    def __init__(self,
                 server_id,
                 amqp_host='localhost',
                 amqp_user='guest',
                 amqp_password='guest',
                 amqp_vhost='/',
                 amqp_port=5672,
                 ssl=False,
                 timeout=0):

        self._server_id = server_id
        self._timeout = timeout
        self.is_received = False
        self.connection = kombu.BrokerConnection(hostname=amqp_host,
                                                 userid=amqp_user,
                                                 password=amqp_password,
                                                 virtual_host=amqp_vhost,
                                                 port=amqp_port,
                                                 ssl=ssl)
        self.channel = self.connection.channel()
        my_uuid = utils.gen_unique_id()
        self.reply_id = "client_"+amqp_user+"_ex_"+my_uuid
        self.corr_id = None
        LOG.debug("Queue ID: {0}".format(self.reply_id))
        src_exchange = kombu.Exchange(self.reply_id, durable=False,
                                      auto_delete=True)
        src_queue = kombu.Queue("client_"+amqp_user+"_queue_"+my_uuid,
                                durable=False, exchange=src_exchange,
                                auto_delete=True)

        # must declare in advance so reply message isn't published before
        src_queue(self.channel).declare()

        consumer = kombu.Consumer(channel=self.channel, queues=src_queue,
                                  callbacks=[self._on_response],
                                  accept=['pickle'])
        consumer.consume()

    def _on_response(self, body, message):
        """This method is automatically called when a response is incoming and
        decides if it is the message we are waiting for - the message with the
        result.

        :param body: the body of the amqp message already deserialized by kombu
        :param message: the plain amqp kombu.message with additional
            information
        """

        if self.corr_id == message.properties['correlation_id'] and \
                isinstance(body, protocol.RpcResponse):
            self.response = body
            self.is_received = True
            message.ack()

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

    def __request(self, methodname, params):
        """The remote-method-call execution function.

        :param methodname: name of the method that should be executed
        :param params: parameter for the remote-method
        :type methodname: string
        :type params: list of parameters
        :rtype: result of the method
        """
        LOG.debug("Request: {!r}; Params: {!r}".format(methodname, params))

        target_exchange = kombu.Exchange("server_"+self._server_id+"_ex",
                                         durable=False, auto_delete=True)
        producer = kombu.Producer(channel=self.channel,
                                  exchange=target_exchange,
                                  auto_declare=False)

        rpc_req = protocol.RpcRequest(methodname, params)
        self.corr_id = str(uuid.uuid4())
        LOG.debug("RpcRequest build")
        LOG.debug("Correlation id: {0}".format(self.corr_id))
        producer.publish(rpc_req, serializer='pickle',
                         reply_to=self.reply_id,
                         correlation_id=self.corr_id)
        LOG.debug("Producer published")

        self._wait_for_result()

        LOG.debug("Result: {!r}".format(self.response.result))
        self.is_received = False

        res = self.response.result
        if self.response.is_exception:
            raise res
        return res

    def _wait_for_result(self):
        """Waits for the result from the server, checks every second if
        a timeout occurred. If a timeout occurs a `socket.timeout` exception
        will be raised.
        """
        elapsed = 0
        start_time = time.time()
        while not self.is_received:
            try:
                LOG.debug("Draining events... timeout: {0}, elapsed: {1}"
                          .format(self._timeout, elapsed))
                self.connection.drain_events(timeout=1)
            except socket.timeout:
                if self._timeout > 0:
                    elapsed = time.time() - start_time
                    if elapsed > self._timeout:
                        raise exc.RpcTimeout("RPC Request timeout")

    def __getattr__(self, name):
        """This method is invoked, if a method is being called, which doesn't
        exist on Proxy. It is used for RPC, to get the function which should
        be called on the Server.
        """
        # magic method dispatcher
        LOG.debug("Recursion: {0}".format(name))
        return _Method(self.__request, name)

#===========================================================================


class _Method:
    """This class is used to realize remote-method-calls.

    :param send: name of the function that should be executed on Proxy
    :param name: name of the method which should be called on the Server
    """
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))

    def __call__(self, * args):
        return self.__send(self.__name, args)

#===========================================================================
