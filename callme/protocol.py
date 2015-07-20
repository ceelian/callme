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


class RpcRequest(object):
    """This class is used to transport the RPC Request to the server.

    :keyword func_name: the rpc function name (= method name)
    :keyword func_args: the arguments for the function
    :keyword func_keywords: keyword arguments for the function
    """
    def __init__(self, func_name, func_args, func_kwargs):
        self.func_name = func_name
        self.func_args = func_args
        self.func_kwargs = func_kwargs

    def __str__(self):
        return ("<RpcRequest(func_name={0}, func_args={1}, func_kwargs={2})>"
                .format(self.func_name, self.func_args, self.func_kwargs))


class RpcResponse(object):
    """This class is used to transport the RPC Response to the client.

    :keyword result: the result of the rpc call on the server
    """
    def __init__(self, result):
        self.result = result

    def __str__(self):
        return "<RpcResponse(result={0})>".format(self.result)

    @property
    def is_exception(self):
        return isinstance(self.result, BaseException)
