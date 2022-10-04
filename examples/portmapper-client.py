#!/usr/bin/env python3

from __future__ import annotations

import sunrpc
import argparse


parser = argparse.ArgumentParser(description='''portmapper-client - a simple portmapper client''')

parser.add_argument('host', help='the target host to connect to')
parser.add_argument('port', type=int, help='the target port to connect to')
parser.add_argument('--protocol', dest='prot', default='udp', choices=['tcp', 'udp'], help='protocol type to use')

subparsers = parser.add_subparsers(dest='action')

parser_set = subparsers.add_parser('set', help='create a new mapping on the server')
parser_set.add_argument('program', type=int, help='programm number to setup')
parser_set.add_argument('version', type=int, help='programm version to setup')
parser_set.add_argument('protocol', choices=['tcp', 'udp'], help='programm protocol to setup')
parser_set.add_argument('pport', type=int, help='the port the programm is listening')

parser_unset = subparsers.add_parser('unset', help='remove a new mapping on the server')
parser_unset.add_argument('program', type=int, help='programm number to remove')
parser_unset.add_argument('version', type=int, help='programm version to remove')
parser_unset.add_argument('protocol', choices=['tcp', 'udp'], help='programm protocol to remove')
parser_unset.add_argument('pport', type=int, help='the port the programm was listening')

parser_get = subparsers.add_parser('get', help='get a mapping from the server')
parser_get.add_argument('program', type=int, help='programm number to lookup')
parser_get.add_argument('version', type=int, help='programm version to lookup')
parser_get.add_argument('protocol', choices=['tcp', 'udp'], help='programm protocol to lookup')

parser_dump = subparsers.add_parser('dump', help='dump available mappings')


def main():
    '''
    Main method :)
    '''
    args = parser.parse_args()
    client = sunrpc.portmapper.get_client(args.host, args.port, args.prot)
    client.connect()

    if args.action == 'set':
        print('[+] Creating a new mapping...')
        proto = sunrpc.portmapper.get_protocol_number(args.protocol)
        worked = client.set(args.program, args.version, proto, args.pport)

        if worked:
            print('[+] Mapping was created successful.')
        else:
            print('[-] Mapping was not created.')

    elif args.action == 'unset':
        print('[+] Creating a new mapping...')
        proto = sunrpc.portmapper.get_protocol_number(args.protocol)
        worked = client.unset(args.program, args.version, proto, args.pport)

        if worked:
            print('[+] Mapping was removed successful.')
        else:
            print('[-] Mapping was not removed.')

    elif args.action == 'get':
        print('[+] Requesting port from the server...')
        proto = sunrpc.portmapper.get_protocol_number(args.protocol)
        port = client.get_port(args.program, args.version, proto, 0)
        print(f'[+] Programm {args.program} is at port: {port}.')

    elif args.action == 'dump':
        print('[+] Dumping mappings from the server...')
        print('[+]')

        mappings = client.dump()
        print('[+]     Prog    Vers    Prot    Port')

        for item in mappings:
            print('[+]', end='')
            print(str(item[0]).rjust(9), end='')
            print(str(item[1]).rjust(8), end='')
            print(str(item[2]).rjust(8), end='')
            print(str(item[3]).rjust(8))

    else:
        print('[-] Unknown action :(')


main()
