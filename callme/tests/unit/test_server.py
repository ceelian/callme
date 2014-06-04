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

# pylint: disable=W0212

from callme import server
from callme import test


class TestServer(test.MockTestCase):

    def setUp(self):
        super(TestServer, self).setUp()

        # mock kombu Exchange
        self.exchange_mock, self.exchange_inst_mock = self._mock_class(
            server.kombu, 'Exchange')

        # mock kombu Queue
        self.queue_mock, self.queue_inst_mock = self._mock_class(
            server.kombu, 'Queue')

        # mock kombu Connection
        self.conn_mock, self.conn_inst_mock = self._mock_class(
            server.kombu, 'BrokerConnection')

        # mock kombu Consumer
        self.consumer_mock, self.consumer_inst_mock = self._mock_class(
            server.kombu, 'Consumer')

    def test_register_function(self):
        def func():
            pass
        s = server.Server('fooserver')
        self.assertEqual(len(s._func_dict), 0)
        s.register_function(func, 'test')
        self.assertEqual(len(s._func_dict), 1)
        self.assertEqual(s._func_dict['test'], func)

    def test_register_function_name_autodetect(self):
        def func():
            pass
        s = server.Server('fooserver')
        self.assertEqual(len(s._func_dict), 0)
        s.register_function(func)
        self.assertEqual(len(s._func_dict), 1)
        self.assertEqual(s._func_dict['func'], func)

    def test_register_function_not_callable(self):
        s = server.Server('fooserver')
        self.assertRaises(ValueError, s.register_function, 1)
