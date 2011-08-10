"""Callme - A python RPC module based on AMQP"""
VERSION = (0, 1, 0)
__version__ = ".".join(map(str, VERSION))
__author__ = "Christian Haintz"
__contact__ = "christian.haintz@orangelabs.at"
__homepage__ = "http://packages.python.org/callme"
__docformat__ = "restructuredtext"


from server import Server
from proxy import Proxy