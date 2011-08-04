class RpcRequest(object):
	def __init__(self, func_name, func_args):
		self.func_name = func_name
		self.func_args = func_args
		
		
class RpcResponse(object):
	def __init__(self, result, exception_raised=False):
		self.result = result
		self.exception_raised=exception_raised 
		
