#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import callme
import threading
import time
import unittest

from callme import exceptions as exc


class ActionsTestCase(unittest.TestCase):

    def test_method_call(self):

        def madd(a, b):
            return a + b

        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest')
        server.register_function(madd, 'madd')
        p = threading.Thread(target=server.start)
        p.start()

        try:
            proxy = callme.Proxy(amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')
            res = proxy.use_server('fooserver', timeout=0).madd(1, 1)
            self.assertEqual(res, 2)
        finally:
            server.stop()
        p.join()

    def test_secured_method_call(self):
        print("IMPORTANT: If this testcase fail you probably haven't setup "
              "your localhost broker with the init_rabbitmq.sh script")

        def madd(a, b):
            return a + b

        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='s1',
                               amqp_password='s1')
        server.register_function(madd, 'madd')
        p = threading.Thread(target=server.start)
        p.start()

        try:
            proxy = callme.Proxy(amqp_host='localhost',
                                 amqp_user='c1',
                                 amqp_password='c1')

            res = proxy.use_server('fooserver', timeout=0).madd(1, 1)
            self.assertEqual(res, 2)
        finally:
            server.stop()
        p.join()

    def test_threaded_method_call(self):

        def madd(a):
            time.sleep(1)
            return a

        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest',
                               threaded=True)
        server.register_function(madd, 'madd')
        p = threading.Thread(target=server.start)
        p.start()

        def threaded_call(i, results):
            proxy = callme.Proxy(amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            results.append((i, proxy.use_server('fooserver',
                                                timeout=0).madd(i)))

        results = []
        threads = []
        try:
            # start 10 threads who call "parallel"
            for i in range(10):
                t = threading.Thread(target=threaded_call, args=(i, results))
                t.start()
                threads.append(t)

            # wait until all threads are finished
            [t.join() for t in threads]
        finally:
            server.stop()
        p.join()

        # check results
        for i, res in results:
            self.assertEqual(i, res)

    def test_half_threaded_method_call(self):

        def madd(a):
            time.sleep(0.1)
            return a

        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest',
                               threaded=False)
        server.register_function(madd, 'madd')
        p = threading.Thread(target=server.start)
        p.start()

        def threaded_call(i, results):
            proxy = callme.Proxy(amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            results.append((i, proxy.use_server('fooserver',
                                                timeout=0).madd(i)))

        results = []
        threads = []
        try:
            #start 3 threads who call "parallel"
            for i in range(3):
                t = threading.Thread(target=threaded_call, args=(i, results))
                t.start()
                threads.append(t)

            #wait until all threads are finished
            [t.join() for t in threads]
        finally:
            server.stop()
        p.join()

        # check results
        for i, res in results:
            self.assertEqual(i, res)

    def test_double_method_call(self):

        def madd(a, b):
            return a + b

        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest')
        server.register_function(madd, 'madd')
        p = threading.Thread(target=server.start)
        p.start()

        try:
            proxy = callme.Proxy(amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            res = proxy.use_server('fooserver', timeout=3).madd(1, 2)
            self.assertEqual(res, 3)

            res = proxy.use_server('fooserver', timeout=1).madd(2, 2)
            self.assertEqual(res, 4)

            res = proxy.use_server('fooserver', timeout=1).madd(2, 3)
            self.assertEqual(res, 5)
        finally:
            server.stop()
        p.join()

    def test_timeout_call(self):

        server = callme.Server(server_id='fooserver',   # noqa
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest')

        proxy = callme.Proxy(amqp_host='localhost',
                             amqp_user='guest',
                             amqp_password='guest')

        self.assertRaises(exc.RpcTimeout,
                          proxy.use_server('fooserver', timeout=1).madd, 1, 2)

    def test_remote_exception(self):

        def madd(a, b):
            return a + b

        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest')
        server.register_function(madd, 'madd')
        p = threading.Thread(target=server.start)
        p.start()

        try:
            proxy = callme.Proxy(amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            self.assertRaises(TypeError, proxy.use_server('fooserver').madd)
        finally:
            server.stop()
        p.join()

    def test_ssl_method_call(self):
        print("IMPORTANT: If this testcase fail you probably haven't setup "
              "your localhost broker with server-side SSL")

        def madd(a, b):
            return a + b

        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest',
                               ssl=True,
                               amqp_port=5671)
        server.register_function(madd, 'madd')
        p = threading.Thread(target=server.start)
        p.start()

        try:
            proxy = callme.Proxy(amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest',
                                 ssl=True,
                                 amqp_port=5671)

            res = proxy.use_server('fooserver', timeout=0).madd(1, 1)
        finally:
            server.stop()
        p.join()
        self.assertEqual(res, 2)

    def test_multiple_server_calls(self):

        def func_a():
            return "a"

        def func_b():
            return "b"

        #Start Server A
        server_a = callme.Server(server_id='server_a',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')
        server_a.register_function(func_a, 'f')
        p_a = threading.Thread(target=server_a.start)
        p_a.start()

        #Start Server B
        server_b = callme.Server(server_id='server_b',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')
        server_b.register_function(func_b, 'f')
        p_b = threading.Thread(target=server_b.start)
        p_b.start()

        try:
            proxy = callme.Proxy(amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            res = proxy.use_server('server_a').f()
            self.assertEqual(res, 'a')

            res = proxy.use_server('server_b').f()
            self.assertEqual(res, 'b')
        finally:
            server_a.stop()
            server_b.stop()
        p_a.join()
        p_b.join()
