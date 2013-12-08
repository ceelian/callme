import callme


def add(a, b):
    return a + b

server = callme.Server(server_id='fooserver',
                       amqp_host='localhost')
server.register_function(add, 'add')
server.start()
