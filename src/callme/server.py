from kombu import BrokerConnection, Exchange, Queue, Consumer, Producer
import logging
import Queue as queue


from protocol import RpcRequest
from protocol import RpcResponse
from threading import Thread

class Server(object):
	
	
	def __init__(self, 
				server_id,
				amqp_host='localhost', 
				amqp_user ='guest',
				amqp_password='guest',
				amqp_vhost='/',
				amqp_port=5672,
				ssl=False,
				threaded=False):
		self.logger = logging.getLogger('callme.server')
		self.logger.debug('Server ID: %s' % server_id)
		self.server_id = server_id
		self.threaded = threaded
		self.do_run = True
		self.func_dict={}
		self.result_queue = queue.Queue()
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
		
		self.publish_connection = BrokerConnection(hostname=amqp_host,
                              userid=amqp_user,
                              password=amqp_password,
                              virtual_host=amqp_vhost,
                              port=amqp_port,
                              ssl=ssl)
		publish_channel = self.publish_connection.channel()
		
		# consume
		self.consumer = Consumer(channel, self.target_queue)
		if self.threaded == True:
			self.consumer.register_callback(self.on_request_threaded)
		else:
			self.consumer.register_callback(self.on_request)
		self.consumer.consume()
		
		
		# producer 
		self.producer = Producer(publish_channel, src_exchange)
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
		


	def on_request_threaded(self, body, message):
		self.logger.debug('Got Request')
		rpc_req = body
		
		if not isinstance(rpc_req, RpcRequest):
			self.logger.debug('Not an RpcRequest Instance')
			return
		
		message.ack()
		self.logger.debug('acknowledge')
		
		def exec_func(body, message, result_queue):
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
				
			result_queue.put(ResultSet(rpc_resp, 
									message.properties['correlation_id'],
									message.properties['reply_to']))
				
		p = Thread(target=exec_func, 
				name=message.properties['correlation_id'],
				args=(body, message, self.result_queue))
		p.start()
		
	
	def register_function(self, func, name):
		self.func_dict[name] = func
	
	def start(self):
		
		if self.threaded == True:
			self.pub_thread = Publisher(self.result_queue, self.producer)
			self.pub_thread.start()
			
		while self.do_run:
			try:
				self.connection.drain_events(timeout=1)
			except:
				self.logger.debug("do_run: %s" % repr(self.do_run))
				pass
			
		self.consumer.cancel()
		self.connection.close()
		self.publish_connection.close()
			
	def stop(self):
		self.logger.debug('Stop server')
		self.do_run = False
		if self.threaded == True:
			self.pub_thread.stop()
		
class Publisher(Thread):
	
	def __init__(self, result_queue, producer):
		Thread.__init__(self)
		self.logger = logging.getLogger('callme.server')
		self.result_queue = result_queue
		self.producer = producer
		self.stopp_it = False
		
	def run(self):
		while self.stopp_it == False:
			try:
				result_set = self.result_queue.get(block=True, timeout=1)
				self.logger.debug('Publish respnse: %s'%repr(result_set))
				self.producer.publish(result_set.rpc_resp, serializer="pickle",
							correlation_id=result_set.correlation_id,
							routing_key=result_set.reply_to)
			except queue.Empty:
				pass
			
	def stop(self):
		self.stopp_it = True
		self.join()
		
	
class ResultSet(object):
	
	def __init__(self, rpc_resp, correlation_id, reply_to):
		self.rpc_resp = rpc_resp
		self.correlation_id = correlation_id
		self.reply_to = reply_to
		
		
		
