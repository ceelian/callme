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

import unittest

import mock


class TestCase(unittest.TestCase):
    """Base test case class for all unit tests."""


class MockTestCase(TestCase):

    def setUp(self):
        super(MockTestCase, self).setUp()
        self.master_mock = mock.Mock(name='master_mock')

    def _mock_class(self, module, name, autospec=True, attach_as=None):
        """Mock class and its instance."""
        if autospec:
            instance_mock = mock.Mock(spec_set=getattr(module, name))
        else:
            instance_mock = mock.Mock()

        patcher = mock.patch.object(module, name, autospec=autospec)
        class_mock = patcher.start()
        self.addCleanup(patcher.stop)
        class_mock.return_value = instance_mock

        if attach_as is None:
            attach_class_as = name
            attach_instance_as = name.lower()
        else:
            attach_class_as = attach_as + '_class'
            attach_instance_as = attach_as

        self.master_mock.attach_mock(class_mock, attach_class_as)
        self.master_mock.attach_mock(instance_mock, attach_instance_as)

        return class_mock, instance_mock

    def _reset_master_mock(self):
        self.master_mock.reset_mock()
