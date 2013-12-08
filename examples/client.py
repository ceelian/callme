import callme
proxy = callme.Proxy(amqp_host='localhost')

print proxy.use_server('fooserver').add(1, 1)
