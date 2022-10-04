#!/usr/bin/env python3

from __future__ import annotations

import random
import asyncio
import argparse

from sunrpc.types import RpcStr
from sunrpc.client import AsyncTCPClient, rpc_client_send_async, rpc_client_obtain_async


class HelloWorldClient(AsyncTCPClient):
    '''
    '''
    @rpc_client_send_async(1, RpcStr)
    @rpc_client_obtain_async(RpcStr)
    async def hello_world(self, result: str) -> None:
        await asyncio.sleep(random.randint(1, 5))
        print('[+] Response: ' + result)


parser = argparse.ArgumentParser(description='''hello-world-client-async - a simple async RPC client example''')

parser.add_argument('host', help='the target host to connect to')
parser.add_argument('port', type=int, help='the target port to connect to')
parser.add_argument('msg', help='the message to send')
parser.add_argument('count', type=int, help='number of messages to send')


async def main():
    '''
    Main method :)
    '''
    args = parser.parse_args()
    client = HelloWorldClient(args.host, args.port, 1337, 2)

    jobs = []

    for i in range(0, args.count):
        jobs.append(client.hello_world(args.msg))

    await asyncio.gather(*jobs)

asyncio.run(main())
