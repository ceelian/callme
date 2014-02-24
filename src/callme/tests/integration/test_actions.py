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

import callme
import threading
import time

from callme import exceptions as exc
from callme import test


class ActionsTestCase(test.TestCase):

    @staticmethod
    def _run_server_thread(server):
        t = threading.Thread(target=server.start)
        t.daemon = True
        t.start()
        return t

    def test_method_call(self):
        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest')
        server.register_function(lambda a, b: a + b, 'madd')
        p = self._run_server_thread(server)

        try:
            proxy = callme.Proxy(server_id='fooserver',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')
            res = proxy.madd(1, 1)
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
        p = self._run_server_thread(server)

        def threaded_call(i, results):
            proxy = callme.Proxy(server_id='fooserver',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            results.append((i, proxy.madd(i)))

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
        p = self._run_server_thread(server)

        def threaded_call(i, results):
            proxy = callme.Proxy(server_id='fooserver',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            results.append((i, proxy.madd(i)))

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
        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest')
        server.register_function(lambda a, b: a + b, 'madd')
        p = self._run_server_thread(server)

        try:
            proxy = callme.Proxy(server_id='fooserver',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            res = proxy.use_server(timeout=3).madd(1, 2)
            self.assertEqual(res, 3)

            res = proxy.use_server(timeout=1).madd(2, 2)
            self.assertEqual(res, 4)

            res = proxy.use_server(timeout=1).madd(2, 3)
            self.assertEqual(res, 5)
        finally:
            server.stop()
        p.join()

    def test_timeout_call(self):
        callme.Server(server_id='fooserver',
                      amqp_host='localhost',
                      amqp_user='guest',
                      amqp_password='guest')

        proxy = callme.Proxy(server_id='fooserver',
                             amqp_host='localhost',
                             amqp_user='guest',
                             amqp_password='guest')

        self.assertRaises(exc.RpcTimeout,
                          proxy.use_server(timeout=1).madd, 1, 2)

    def test_remote_exception(self):
        server = callme.Server(server_id='fooserver',
                               amqp_host='localhost',
                               amqp_user='guest',
                               amqp_password='guest')
        server.register_function(lambda a, b: a + b, 'madd')
        p = self._run_server_thread(server)

        try:
            proxy = callme.Proxy(server_id='fooserver',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            self.assertRaises(exc.RemoteException, proxy.madd)
        finally:
            server.stop()
        p.join()

    def test_multiple_server_calls(self):

        # start server A
        server_a = callme.Server(server_id='server_a',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')
        server_a.register_function(lambda: 'a', 'f')
        p_a = self._run_server_thread(server_a)

        # start server B
        server_b = callme.Server(server_id='server_b',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')
        server_b.register_function(lambda: 'b', 'f')
        p_b = self._run_server_thread(server_b)

        try:
            proxy = callme.Proxy(server_id='server_a',
                                 amqp_host='localhost',
                                 amqp_user='guest',
                                 amqp_password='guest')

            res = proxy.f()
            self.assertEqual(res, 'a')

            res = proxy.use_server('server_b').f()
            self.assertEqual(res, 'b')
        finally:
            server_a.stop()
            server_b.stop()
        p_a.join()
        p_b.join()
