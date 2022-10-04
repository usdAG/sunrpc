from __future__ import annotations

import sunrpc

from sunrpc.types import RpcInt, RpcBool, RpcBytes, RpcList, RpcFArray
from sunrpc.client import rpc_client_send, rpc_client_obtain

# Constants
PMAP_PROG = 100000
PMAP_VERS = 2
PMAP_PORT = 111

# Procedure numbers
PMAPPROC_NULL = 0                       # (void) -> void
PMAPPROC_SET = 1                        # (mapping) -> bool
PMAPPROC_UNSET = 2                      # (mapping) -> bool
PMAPPROC_GETPORT = 3                    # (mapping) -> unsigned int
PMAPPROC_DUMP = 4                       # (void) -> pmaplist
PMAPPROC_CALLIT = 5                     # (call_args) -> call_result

# PROTOCOLS
IPPROTO_TCP = 6
IPPROTO_UDP = 17


class PortMapperClient(sunrpc.client.Client):
    '''
    Simple RPC portmapper client.
    '''

    def __init__(self, host: str, port: int = PMAP_PORT):
        '''
        Initialize the client with the well known programm and
        version number used by portmappers.

        Parameters:
            host        host the portmapper is listening on
            port        port the portmapper is listening on

        Returns:
            None
        '''
        sunrpc.client.Client.__init__(self, host, port, PMAP_PROG, PMAP_VERS)

    @rpc_client_send(PMAPPROC_SET, RpcInt, RpcInt, RpcInt, RpcInt)
    @rpc_client_obtain(RpcBool)
    def set(self, result: bool) -> bool:
        return result

    @rpc_client_send(PMAPPROC_UNSET, RpcInt, RpcInt, RpcInt, RpcInt)
    @rpc_client_obtain(RpcBool)
    def unset(self, result: bool) -> bool:
        return result

    @rpc_client_send(PMAPPROC_GETPORT, RpcInt, RpcInt, RpcInt, RpcInt)
    @rpc_client_obtain(RpcInt)
    def get_port(self, port: int) -> int:
        return port

    @rpc_client_send(PMAPPROC_DUMP)
    @rpc_client_obtain(RpcList(RpcFArray(RpcInt, 4)))
    def dump(self, mappings: list) -> list:
        return mappings

    @rpc_client_send(PMAPPROC_CALLIT, RpcInt, RpcInt, RpcInt, RpcBytes)
    @rpc_client_obtain(RpcInt, RpcBytes)
    def callit(self, port: int, result: str) -> int:
        return port, result


class TCPPortMapperClient(sunrpc.client.TCPClient, PortMapperClient):
    '''
    Portmapper client for TCP based connections.
    '''
    def __init__(self, host: str, port: int = PMAP_PORT):
        '''
        Initialize the client with the well known programm and
        version number used by portmappers.

        Parameters:
            host        host the portmapper is listening on
            port        port the portmapper is listening on

        Returns:
            None
        '''
        sunrpc.client.TCPClient.__init__(self, host, port, PMAP_PROG, PMAP_VERS)


class UDPPortMapperClient(sunrpc.client.UDPClient, PortMapperClient):
    '''
    Portmapper client for UDP based connections.
    '''
    def __init__(self, host: str, port: int = PMAP_PORT):
        '''
        Initialize the client with the well known programm and
        version number used by portmappers.

        Parameters:
            host        host the portmapper is listening on
            port        port the portmapper is listening on

        Returns:
            None
        '''
        sunrpc.client.UDPClient.__init__(self, host, port, PMAP_PROG, PMAP_VERS)


def get_client(host: str, port: int, protocol: str) -> PortMapperClient:
    '''
    Returns the corresponding PortMapperClient depending on the specified
    protocol. Allowed Protocols are 'tcp' and 'udp':

    Parameters:
        protocol        protocol specifieer (either 'tcp' or 'udp')

    Returns:
        PortMapperClient matching the desired protocol
    '''
    if protocol == 'udp':
        return UDPPortMapperClient(host, port)

    elif protocol == 'tcp':
        return TCPPortMapperClient(host, port)

    else:
        return None


def get_protocol_number(protocol: str) -> int:
    '''
    Returns the protocol number associated with the specifeid protocol.

    Parameters:
        protocol        protocol specifieer (either 'tcp' or 'udp')

    Returns:
        Number representation for the requested protocol.
    '''
    if protocol == 'udp':
        return IPPROTO_UDP

    elif protocol == 'tcp':
        return IPPROTO_TCP
