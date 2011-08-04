from kombu import BrokerConnection, Exchange, Queue, Consumer, Producer
import logging


from protocol import RpcRequest
from protocol import RpcResponse

class Server(object):
	
	
	def __init__(self, 
				server_id,
				amqp_host='localhost', 
				amqp_user ='guest',
				amqp_password='guest',
				amqp_vhost='/',
				amqp_port=5672,
				ssl=False):
		self.logger = logging.getLogger('callme.server')
		self.logger.debug('Server ID: %s' % server_id)
		self.server_id = server_id
		self.do_run = True
		self.func_dict={}
		target_exchange = Exchange("callme_target", "direct", durable=False)	
		self.target_queue = Queue(server_id, exchange=target_exchange, 
							routing_key=server_id, auto_delete=True,
							durable=False)
		src_exchange = Exchange("callme_src", "direct", durable=False)
		
		
		self.connection = BrokerConnection(hostname=amqp_host,
                              userid=amqp_user,
                              password=amqp_password,
                              virtual_host=amqp_vhost,
                              port=amqp_port,
                              ssl=ssl)
		channel = self.connection.channel()
		
		# consume
		self.consumer = Consumer(channel, self.target_queue)
		self.consumer.register_callback(self.on_request)
		self.consumer.consume()
		
		
		# producer 
		self.producer = Producer(channel, src_exchange)
		self.logger.debug('Init done')
		
	def on_request(self, body, message):
		self.logger.debug('Got Request')
		rpc_req = body
		
		
		if not isinstance(rpc_req, RpcRequest):
			self.logger.debug('Not an RpcRequest Instance')
			return
		
		self.logger.debug('Call func on Server %s' %self.server_id)
		try:
			self.logger.debug('corr_id: %s' % message.properties['correlation_id'])
			self.logger.debug('Call func with args %s' % repr(rpc_req.func_args))
			result = self.func_dict[rpc_req.func_name](*rpc_req.func_args)
			self.logger.debug('Result: %s' % repr(result))
			self.logger.debug('Build respnse')
			rpc_resp = RpcResponse(result)
		except Exception as e:
			self.logger.debug('exception happened')
			rpc_resp = RpcResponse(e, exception_raised=True)
			
		message.ack()
		
		self.logger.debug('Publish respnse')
		self.producer.publish(rpc_resp, serializer="pickle",
							correlation_id=message.properties['correlation_id'],
							routing_key=message.properties['reply_to'])
		
		self.logger.debug('acknowledge')
		

	
	def register_function(self, func, name):
		self.func_dict[name] = func
	
	def start(self):
		while self.do_run:
			try:
				self.connection.drain_events(timeout=1)
			except:
				self.logger.debug("do_run: %s" % repr(self.do_run))
				pass
		
		self.consumer.cancel()
		self.connection.close()
			
	def stop(self):
		self.do_run = False
		
