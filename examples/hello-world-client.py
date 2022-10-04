#!/usr/bin/env python3

from __future__ import annotations

import argparse

from sunrpc.types import RpcStr
from sunrpc.client import TCPClient, rpc_client_send, rpc_client_obtain


class HelloWorldClient(TCPClient):
    '''
    Client class that communicates to the HelloWorldServer.
    '''
    @rpc_client_send(1, RpcStr)
    @rpc_client_obtain(RpcStr)
    def hello_world(self, result: str) -> str:
        '''
        Send a string to the server and print the result.
        '''
        return result


parser = argparse.ArgumentParser(description='''hello-world-client - a simple RPC client example''')

parser.add_argument('host', help='the target host to connect to')
parser.add_argument('port', type=int, help='the target port to connect to')
parser.add_argument('msg', help='the message to send')


def main():
    '''
    Main method :)
    '''
    args = parser.parse_args()
    client = HelloWorldClient(args.host, args.port, 1337, 2)
    client.connect()

    response = client.hello_world(args.msg)
    print(response)


main()
