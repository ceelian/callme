=====
Proxy
=====

The Proxy manages the client part of the RPC system:

Usage example::

    import callme

    proxy = callme.Proxy(amqp_host='localhost')

    print(proxy.use_server('fooserver').add(1, 1))

.. currentmodule:: callme.proxy

.. automodule:: callme.proxy
    :members:
    :undoc-members:
