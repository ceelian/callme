======
Server
======

The Server is used to build a RPC server which provides RPC Method to one or 
more clients. A sample of a simple RPC server is shown here::

    import callme

    def add(a, b):
        return a + b

    server = callme.Server(server_id='fooserver',
                           amqp_host='localhost')
    server.register_function(add, 'add')
    server.start()

.. currentmodule:: callme.server

.. automodule:: callme.server

    .. autoclass:: Server
        :members:
