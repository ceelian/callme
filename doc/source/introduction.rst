================================================================
Callme - A python RPC module based on AMQP
================================================================

Introduction
------------
``Callme`` provides an easy way to do RPC over AMQP (``Callme`` is the
successor of ``QAM`` <http://packages.python.org/qam>).

**Key Features:**

- Easy to use;
- Uses AMQP as transport protocol;
- Support timeouts;
- SSL support;
- Supports remote exceptions;
- OpenSource BSD-licensed;
- Designed to support broker-side permission system.


Getting started with callme
---------------------------
A simple RPC Server which provides an add method::

    import callme

    def add(a, b):
        return a + b

    server = callme.Server(server_id='fooserver',
                           amqp_host='localhost')

    server.register_function(add, 'add')
    server.start()

and a client which uses **fooserver** to add **1 + 1** and finally prints the
result::

    import callme

    proxy = callme.Proxy(server_id='fooserver',
                         amqp_host='localhost')

    print proxy.add(1, 1)

There are optional parameters to fit different needs which are explained in depth
in the Server and Proxy Documentation.

Examples are provided in the *examples* directory in the package.

Multithreading
--------------
The ``Proxy`` is not thread-safe, you must instantiate one Proxy per thread.

The ``Server`` is also not thread-safe as well. Instantiate one Server per
thread.

Even if the Server is not thread-safe itself, it has the capability to use
multi-threading. For each RPC Call a worker thread is started which
significantly improves the call speed if multiple clients are calling
the server simultaneously. To activate multi-threading on the server pass
``threading=True`` to the Server class.


Permissions
-----------
It is possible to control the access to a RPC Server by the Broker. We use
RabbitMQ as example because this is the broker we used for testing and
development. To get the highest security out of the permission system it is
recommended using separate vhost only for callme communication (if you
have other amqp messages on your system on the same broker).  

For a more in depth explanation why these permissions look how they are see 
``Exchange Design``.


Limit Server Permissions
++++++++++++++++++++++++
To limit one server to only accept RPC Calls to its server_id and send result
back to clients we use these permissions. Assumption the RPC server has its own
user called *carl* on the rabbitmq broker.

``rabbitmqctl set_permissions carl "server_fooserver_.*" "server_fooserver_.*|client_.*_ex_.*" "server_fooserver_.*"``


Limit Client (Proxy) Permissions
++++++++++++++++++++++++++++++++
To limit the Proxy to the server with the server_id *fooserver* (no other
server can then be reached with this user) we use these permissions. Assumption
the RPC proxy has its own user called *olivia* on the rabbitmq broker.

``rabbitmqctl set_permissions olivia "client_olivia_.*" "client_olivia_.*|server_fooserver_ex" "client_olivia_.*"``

To give the client access to another RPC server with server_id *barserver* we
set the following permissions:

``rabbitmqctl set_permissions olivia "client_olivia_.*" "client_olivia_.*|server_fooserver_ex|server_barserver_ex" "client_olivia_.*"``

To give the client access to all RPC servers set the permission as follows:

``rabbitmqctl set_permissions olivia "client_olivia_.*" "client_olivia_.*|server_.*_ex" "client_olivia_.*"``


Architecture
------------
Callme uses kombu for communication between Proxy and Server. Callme transfers
instances of the ``RpcResponse`` and ``RpcRequest`` to execute remote procedure
calls (RPC). The instances of these classes are pickled by kombu and then
transferred to the server or proxy.


Exchange Design
---------------
Every Proxy creates a Exchange and a Queue bound to the Exchange which has
the form ``client_<amqp_user>_ex_<uid>`` and ``client_<amqp_user>_queue_<uid>``.
``<uid>`` is generated on creation of the Proxy. All Queues and Exchanges are
auto-deleted and non-durable.

Client Exchange and Queue are declared and bound by the client and server
Exchange and Queue are declared and bound by the server.


The Exchange and Queue Design::

	                                   Time                                   
	                                     |                                  
	------------------------------       |       ----------------------------                           
	|          Proxy             |       v       |          Server          |
	|       User: olivia         |               |        User: carl        |
	|       ------------         |               |        ----------        |
	|                            |               |                          |
	|         --- RPC Call--------------------------> server_fooserver_ex   |                                      
	|                            |               |        (Exchange)        |
	|                            |               |            |             |      
	|                            |               |            |             |
	|                            |               |            |             |
	|                            |               |            v             |
	|                            |               |                          |
	|                            |               |   server_fooserver_queue |                    
	|                            |               |         (Queue)          |                 
	|                            |               |            |             |                 
	|                            |               |            /             |             
	| client_olivia_ex_<uid>  <----- RPC Result --------------              |                                                         
	|        (Exchange)          |               |                          |                 
	|            |               |               |                          |          
	|            |               |               |                          |             
	|            v               |               |                          |                  
	| client_olivia_queue_<uid>  |               |                          |                 
	|         (Queue)            |               |                          |                          
	|____________________________|               |__________________________|      


Logging
-------
At the moment there are two loggers present with the names *callme.proxy*
and *callme.server*. Both are mostly used for debugging at the moment.


Bug Tracker
-----------
If you find any issues please report them on https://github.com/ceelian/callme/issues.


Getting callme
--------------
You can get the python package on the `Python Package Index`_.

.. _`Python Package Index`: http://pypi.python.org/pypi/callme

The git repository is available at `github.com callme`_.

.. _`github.com callme`: https://github.com/ceelian/callme


Installation
------------
``callme`` can be installed via the Python Package Index or from source.

Using ``easy_install`` to install ``callme``::

    $ easy_install callme

Using ``pip`` to install ``callme``::

    $ pip install callme

If you have downloaded a source tarball you can install it as follows::

    $ python setup.py build
    $ python setup.py install


Supported by
------------
Wingware - The Python IDE (http://wingware.com).


Contributing
------------
We are welcome everyone who wants to contribute to ``callme``.
Development of callme happens at https://github.com/ceelian/callme.


Contributors (chronological order)
----------------------------------
- mkisto (https://github.com/mkisto)
- carletes (https://github.com/carletes)
- skudriashev (https://github.com/skudriashev)
- venkat-tenmiles (https://github.com/venkat-tenmiles)
- femtotrader (https://github.com/femtotrader)


License
-------
Callme is released under the BSD License.
The full license text is in the root folder of the callme Package.
