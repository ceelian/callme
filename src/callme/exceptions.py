class CallmeException(Exception):
    """Base exception for all callme exceptions"""
    pass


class ConnectionError(CallmeException):
    """Raised when failed to connect to AMQP"""
    pass
