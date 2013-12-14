from callme import protocol
import unittest


class TestRpcRequest(unittest.TestCase):

    def test_constructor(self):
        func_args = {'arg1': 3, 'arg2': 7}
        request = protocol.RpcRequest("func_name", func_args)
        self.assertEqual(request.func_name, "func_name")
        self.assertEqual(request.func_args, func_args)


class TestRpcResponse(unittest.TestCase):

    def test_constructor_default(self):
        response = protocol.RpcResponse("result")
        self.assertEqual(response.result, "result")
        self.assertFalse(response.is_exception)

    def test_constructor_exception(self):
        response = protocol.RpcResponse(Exception("test"))
        self.assertIsInstance(response.result, Exception)
        self.assertTrue(response.is_exception)
