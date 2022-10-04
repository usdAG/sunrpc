#!/usr/bin/env python3

from __future__ import annotations

import argparse
from sunrpc.proxy import UDPProxy


class PortMapperProxy(UDPProxy):
    '''
    Example implementation for a portmapper proxy. Proxies traffic incoming portmapper
    traffic to the targeted portmapper and dumps transmitted data to stdout.
    '''
    def __init__(self, host: str, port: str, target: str, tport: int = 111) -> None:
        '''
        Initialize the proxy
        '''
        UDPProxy.__init__(self, host, port, 100000, 2, target, tport, dump=True)


parser = argparse.ArgumentParser(description='''portmapper-proxy - forwards portmapper requests''')

parser.add_argument('host', help='listening host')
parser.add_argument('port', type=int, help='listening port')
parser.add_argument('target', help='target host')
parser.add_argument('tport', type=int, help='target port')


def main():
    '''
    Main method :)
    '''
    args = parser.parse_args()
    server = PortMapperProxy(args.host, args.port, args.target, args.tport)

    print('[+] Portmapper proxy started :)')
    server.bind()
    server.listen()


main()
