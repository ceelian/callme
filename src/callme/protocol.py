"""

=======
Classes
=======
"""

class RpcRequest(object):
	"""
	This class is used to transport the RPC Request to the server.

	:keyword func_name: the rpc function name (= method name)
	:keyword func_args: the arguments for the function
	"""
	def __init__(self, func_name, func_args):
		self.func_name = func_name
		self.func_args = func_args
		
		
class RpcResponse(object):
	"""
	This class is used to transport the RPC Response from the server
	back to the client

	:keyword result: the result of the rpc call on the server
	:keyword exception_raised: if the result is an exception which was
		raised during the execution of the rpc call on the server
	"""
	def __init__(self, result, exception_raised=False):
		self.result = result
		self.exception_raised=exception_raised 
		


class ConnectionError(Exception):
	pass