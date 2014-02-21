#!/bin/bash
rabbitmqctl stop_app
rabbitmqctl reset
rabbitmqctl start_app
rabbitmqctl add_user c1 c1
rabbitmqctl set_permissions c1 "client_c1_.*" "client_c1_.*|server_fooserver_ex" "client_c1_.*"
rabbitmqctl add_user s1 s1
rabbitmqctl set_permissions s1 "server_fooserver_.*" "server_fooserver_.*|client_.*_ex_.*" "server_fooserver_.*"
