#!/usr/bin/env python3

from __future__ import annotations

import argparse

from sunrpc.types import RpcStr
from sunrpc.server import TCPServer, rpc_server_obtain, rpc_server_return


class HelloWorldServer(TCPServer):
    '''
    RPC server that supports a single method expecting a string. Prints
    the string to stdout and answers with 'Hello World :D'.
    '''
    def __init__(self, host: str, port: str) -> None:
        '''
        Initialize the server and add the available method
        '''
        TCPServer.__init__(self, host, port, 1337, 2)
        self.add_method(1, self.hello_world)

    @rpc_server_obtain(RpcStr)
    @rpc_server_return(RpcStr)
    def hello_world(self, message: str) -> str:
        '''
        Obtain the message from the client, print it and return 'Hello World :D'
        '''
        print(f'[+] The client said: {message}')
        return ['Hello World :D']


parser = argparse.ArgumentParser(description='''hello-world-server - a simple RPC server example.''')

parser.add_argument('host', help='listening host')
parser.add_argument('port', type=int, help='listening port')


def main():
    '''
    Main method :)
    '''
    args = parser.parse_args()
    server = HelloWorldServer(args.host, args.port)
    server.bind()
    server.listen()


main()
