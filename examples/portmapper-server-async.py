#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import argparse

from sunrpc.types import RpcBool, RpcInt, RpcList, RpcFArray
from sunrpc.server import AsyncTCPServer, rpc_server_obtain_async, rpc_server_return_async


class PortMapperServer(AsyncTCPServer):
    '''
    Example implementation for an asyncio portmapper server. Do not use this in production,
    it is just an example :D
    '''
    def __init__(self, host: str, port: str) -> None:
        '''
        Initialize the portmapper server and setup the available methods.
        '''
        AsyncTCPServer.__init__(self, host, port, 100000, 2)

        self.add_method(1, self.set)
        self.add_method(2, self.unset)
        self.add_method(3, self.get_port)
        self.add_method(4, self.dump)

        self.mappings = {}

    @rpc_server_obtain_async(RpcInt, RpcInt, RpcInt, RpcInt)
    @rpc_server_return_async(RpcBool)
    async def set(self, prog: int, vers: int, prot: int, port: int) -> bool:
        '''
        Add a new mapping to the internal hashmap.
        '''
        print(f'[+] Adding mapping: [{prog}, {vers}, {prot}] -> {port}')
        ident = (prog, vers, prot)
        self.mappings[ident] = port
        return [True]

    @rpc_server_obtain_async(RpcInt, RpcInt, RpcInt, RpcInt)
    @rpc_server_return_async(RpcBool)
    async def unset(self, prog: int, vers: int, prot: int, port: int) -> bool:
        '''
        Remove a mapping from the internal hashmap.
        '''
        print(f'[+] Removing mapping: [{prog}, {vers}, {prot}] -> {port}')
        port = self.mappings.pop((prog, vers, prot), None)

        if port is None:
            return [False]

        else:
            return [True]

    @rpc_server_obtain_async(RpcInt, RpcInt, RpcInt, RpcInt)
    @rpc_server_return_async(RpcInt)
    async def get_port(self, prog: int, vers: int, prot: int, port: int) -> bool:
        '''
        Return the associated port for the requested prog.
        '''
        print(f'[+] Client requested port for prog: {prog}')
        port = self.mappings.get((prog, vers, prot), None)

        if port is None:
            return [0]

        else:
            return [port]

    @rpc_server_obtain_async()
    @rpc_server_return_async(RpcList(RpcFArray(RpcInt, 4)))
    async def dump(self) -> list:
        '''
        Dump all mappings stored in the internal hashmap to the client.
        '''
        print('[+] Client requested a dump.')
        return_list = []

        for key, value in self.mappings.items():
            prog, vers, prot = key
            return_list.append([prog, vers, prot, value])

        return [return_list]


parser = argparse.ArgumentParser(description='''portmapper-server - a simple portmapper server''')

parser.add_argument('host', help='listening host')
parser.add_argument('port', type=int, help='listening port')


async def main():
    '''
    Main method :)
    '''
    args = parser.parse_args()
    server = PortMapperServer(args.host, args.port)
    await server.bind()
    await server.listen()


asyncio.run(main())
