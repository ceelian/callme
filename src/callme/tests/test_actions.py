#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import unittest
import callme
from callme.protocol import MyException
import sys
import logging
#from multiprocessing import Process
import socket
from threading import Thread

class ActionsTestCase(unittest.TestCase):
	
	def setUp(self):
		logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s %(message)s', filename='callme.log',level=logging.DEBUG)
	def tearDown(self):
		pass
	
	def test_method_call(self):
		
		
		
		def madd(a, b):
			return a + b
		
		server = callme.Server(server_id='fooserver',
							amqp_host ='localhost', 
							amqp_user ='guest',
							amqp_password='guest')
		server.register_function(madd, 'madd')
		p = Thread(target=server.start)
		p.start()
		
		proxy = callme.Proxy(amqp_host ='localhost', 
							amqp_user ='guest',
							amqp_password='guest')
		
		res = proxy.use_server('fooserver', timeout=0).madd(1,1)
		self.assertEqual(res, 2)
		server.stop()
		p.join()
		
		
	def test_double_method_call(self):
		
		def madd(a, b):
			return a + b
		
		server = callme.Server(server_id='fooserver',
							amqp_host ='localhost', 
							amqp_user ='guest',
							amqp_password='guest')
		server.register_function(madd, 'madd')
		p = Thread(target=server.start)
		p.start()
		
		proxy = callme.Proxy(amqp_host ='localhost', 
							amqp_user ='guest',
							amqp_password='guest')
		
		res = proxy.use_server('fooserver', timeout=3).madd(1,2)
		self.assertEqual(res, 3)
		
		res = proxy.use_server('fooserver', timeout=1).madd(2,2)
		self.assertEqual(res, 4)
		
		res = proxy.use_server('fooserver', timeout=1).madd(2,3)
		self.assertEqual(res, 5)
		server.stop()
		p.join()
		
	def test_timeout_call(self):
		
		def madd(a, b):
			return a + b
		
		proxy = callme.Proxy(amqp_host ='localhost', 
							amqp_user ='guest',
							amqp_password='guest')
		
		self.assertRaises(socket.timeout,
						proxy.use_server('fooserver', timeout=1).madd, 1, 2)
		
	
	def test_remote_exception(self):
		
		def madd(a, b):
			return a + b
		
		server = callme.Server(server_id='fooserver',
							amqp_host ='localhost', 
							amqp_user ='guest',
							amqp_password='guest')
		server.register_function(madd, 'madd')
		p = Thread(target=server.start)
		p.start()
		
		proxy = callme.Proxy(amqp_host ='localhost', 
							amqp_user ='guest',
							amqp_password='guest')
		
		self.assertRaises(TypeError, 
						proxy.use_server('fooserver').madd)
		server.stop()
		p.join()
		
			
			
def suite():
	suite = unittest.TestSuite()
	if len(sys.argv) > 1 and sys.argv[1][:2] == 't:':
		suite.addTest(ActionsTestCase(sys.argv[1][2:]))
	else:
		suite.addTest(unittest.makeSuite(ActionsTestCase, 'test'))
	return suite


if __name__ == '__main__':
	#call it with 
	#t:<my_testcase>
	#to launch only <my_testcase> test 
	unittest.TextTestRunner(verbosity=3).run(suite())