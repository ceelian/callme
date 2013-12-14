"""

=======
Classes
=======
"""

from kombu import BrokerConnection, Exchange, Queue, Consumer, Producer
import logging
import Queue as queue

from exceptions import ConnectionError
from protocol import RpcRequest
from protocol import RpcResponse
from threading import Thread
import socket
from time import sleep

LOG = logging.getLogger(__name__)


class Server(object):
    """
    This Server class is used to provide an RPC server

    :keyword server_id: Id of the server
    :keyword amqp_host: The host of where the AMQP Broker is running.
    :keyword amqp_user: The username for the AMQP Broker.
    :keyword amqp_password: The password for the AMQP Broker.
    :keyword amqp_vhost: The virtual host of the AMQP Broker.
    :keyword amqp_port: The port of the AMQP Broker.
    :keyword ssl: Use SSL connection for the AMQP Broker.
    :keyword threaded: Use of multithreading. If set to true RPC call-execution
    will processed parallel (one thread per call) which dramatically improves
    performance.
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
        LOG.debug("Server ID: {0}".format(server_id))
        self.server_id = server_id
        self.threaded = threaded
        self.do_run = True
        self.is_stopped = True
        self.func_dict = {}
        self.result_queue = queue.Queue()
        target_exchange = Exchange("server_"+server_id+"_ex", "direct",
                                   durable=False, auto_delete=True)
        self.target_queue = Queue("server_"+server_id+"_queue",
                                  exchange=target_exchange, auto_delete=True,
                                  durable=False)

        self.connection = BrokerConnection(hostname=amqp_host,
                                           userid=amqp_user,
                                           password=amqp_password,
                                           virtual_host=amqp_vhost,
                                           port=amqp_port,
                                           ssl=ssl)
        try:
            self.connection.connect()
        except IOError:
            LOG.critical("Connection Error: Probably AMQP User has"
                         " not enough permissions")
            raise ConnectionError("Connection Error: Probably AMQP User has"
                                  " not enough permissions")

        self.channel = self.connection.channel()

        self.publish_connection = BrokerConnection(hostname=amqp_host,
                                                   userid=amqp_user,
                                                   password=amqp_password,
                                                   virtual_host=amqp_vhost,
                                                   port=amqp_port,
                                                   ssl=ssl)
        self.publish_channel = self.publish_connection.channel()

        # consume
        self.consumer = Consumer(self.channel, self.target_queue,
                                 accept=['pickle'])
        if self.threaded:
            self.consumer.register_callback(self._on_request_threaded)
        else:
            self.consumer.register_callback(self._on_request)
        self.consumer.consume()

        LOG.debug("Initialization done")

    def _on_request(self, body, message):
        """
        This method is automatically called when a request is incoming. It
        processes the incoming rpc calls in a serial manner (no multi-
        threading)

        :param body: the body of the amqp message already deserialized by kombu
        :param message: the plain amqp kombu.message with additional
        information
        """
        LOG.debug("Got request")
        rpc_req = body

        if not isinstance(rpc_req, RpcRequest):
            LOG.debug("Request is not an RpcRequest instance")
            return

        LOG.debug("Call func on server {0}".format(self.server_id))
        try:
            LOG.debug("Correlation id: {0}".format(
                      message.properties['correlation_id']))
            LOG.debug("Call func with args {!r}".format(rpc_req.func_args))

            result = self.func_dict[rpc_req.func_name](*rpc_req.func_args)

            LOG.debug("Result: {!r}".format(result))
            LOG.debug("Build response")
            rpc_resp = RpcResponse(result)
        except Exception as e:
            LOG.debug("Exception happened: {0}".format(e))
            rpc_resp = RpcResponse(e)

        message.ack()

        LOG.debug("Publish response")
        # producer
        src_exchange = Exchange(message.properties['reply_to'], 'direct',
                                durable=False, auto_delete=True)
        self.producer = Producer(self.publish_channel, src_exchange,
                                 auto_declare=False)

        self.producer.publish(
            rpc_resp, serializer='pickle',
            correlation_id=message.properties['correlation_id'])

        LOG.debug("Acknowledge")

    def _on_request_threaded(self, body, message):
        """
        This method is automatically called when a request is incoming and
        `threaded` set to `True`. It processes the incoming rpc calls in
        a parallel manner (one thread for each request). A separate Publisher
        thread is used to send back the results.

        :param body: the body of the amqp message already deserialized by kombu
        :param message: the plain amqp kombu.message with additional
        information
        """
        LOG.debug("Got request")
        rpc_req = body

        if not isinstance(rpc_req, RpcRequest):
            LOG.debug("Request is not an RpcRequest instance")
            return

        message.ack()
        LOG.debug("Acknowledge")

        def exec_func(body, message, result_queue):
            LOG.debug("Call func on server{0}".format(self.server_id))
            try:
                LOG.debug("Correlation id: {0}".format(
                          message.properties['correlation_id']))
                LOG.debug("Call func with args {!r}".format(rpc_req.func_args))

                result = self.func_dict[rpc_req.func_name](*rpc_req.func_args)

                LOG.debug("Result: {!r}".format(result))
                LOG.debug("Build response")
                rpc_resp = RpcResponse(result)
            except Exception as e:
                LOG.debug("Exception happened: {0}".format(e))
                rpc_resp = RpcResponse(e)

            result_queue.put(ResultSet(rpc_resp,
                                       message.properties['correlation_id'],
                                       message.properties['reply_to']))

        p = Thread(target=exec_func,
                   name=message.properties['correlation_id'],
                   args=(body, message, self.result_queue))
        p.start()

    def register_function(self, func, name):
        """
        Registers a function as rpc function so that is accessible from the
        proxy.

        :param func: The function we want to provide as rpc method
        :param name: The name with which the function is visible to the clients
        """
        self.func_dict[name] = func

    def start(self):
        """
        Starts the server. If `threaded` is `True` also starts the Publisher
        thread.
        """
        self.is_stopped = False
        if self.threaded:
            self.pub_thread = Publisher(self.result_queue,
                                        self.publish_channel)
            self.pub_thread.start()

        while self.do_run:
            try:
                LOG.debug("Draining events: {0}".format(self.do_run))
                self.connection.drain_events(timeout=1)
            except socket.timeout:
                LOG.debug("do_run: {0}".format(self.do_run))
            except Exception as e:
                LOG.debug("Interrupt exception:{0}".format(e))
                if self.threaded:
                    self.pub_thread.stop()
                self.consumer.cancel()
                self.connection.close()
                self.publish_connection.close()
                self.is_stopped = True
                return

        if self.threaded:
            self.pub_thread.stop()
        LOG.debug("Normal exit")
        self.consumer.cancel()
        self.connection.close()
        self.publish_connection.close()
        LOG.debug("Everything closed")
        self.is_stopped = True

    def stop(self):
        """
        Stops the server.
        """
        LOG.debug("Stop server")
        self.do_run = False
        while not self.is_stopped:
            LOG.debug("Wait server stop...")
            sleep(0.1)


class Publisher(Thread):
    """
    This class is a thread class and used internally for sending back
    results to the client

    :param result_queue: a Queue.Queue type queue which is thread-safe and
        holds the results which should be sent back. Item in the queue must
        be of type :class:`ResultSet`.
    :param channel: a kombu.channel
    """

    def __init__(self, result_queue, channel):
        Thread.__init__(self)
        self.result_queue = result_queue
        self.channel = channel
        self.stopp_it = False

    def run(self):
        while not self.stopp_it:
            try:
                result_set = self.result_queue.get(block=True, timeout=1)
                LOG.debug("Publish response: {!r}".format(result_set))

                src_exchange = Exchange(result_set.reply_to, "direct",
                                        durable=False, auto_delete=True)
                producer = Producer(self.channel, src_exchange,
                                    auto_declare=False)

                producer.publish(result_set.rpc_resp, serializer="pickle",
                                 correlation_id=result_set.correlation_id)

            except queue.Empty:
                pass

    def stop(self):
        """
        Stops the Publisher thread
        """
        self.stopp_it = True
        self.join()


class ResultSet(object):
    """
    This class is used as type for the items in the result_queue when used in
    threaded mode. It stores all information needed to send back the result to
    the right client.

    :param rpc_resp: the RPC Response object of type :class:`RpcResponse`.
    :param correlation_id: the correlation_id of the amqp message
    :param reply_to: the reply_to field of the amqp message
    """

    def __init__(self, rpc_resp, correlation_id, reply_to):
        self.rpc_resp = rpc_resp
        self.correlation_id = correlation_id
        self.reply_to = reply_to
