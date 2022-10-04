from __future__ import annotations

import sunrpc
from abc import ABC


class Proxy(sunrpc.server.Server, ABC):
    '''
    The proxy class can be used to create a proxy RPC server. All incomming calls
    are just passed to the specified target. Hooks can be used to inspect particular
    calls you are interested in.
    '''

    def __init__(self, host: str, port: int, prog: int, vers: int, target: str, tport: int = None,
                 tprog: int = None, tvers: int = None, tprot: str = 'tcp', dump: bool = True) -> None:
        '''
        Initialize the RPC proxy. The proxy needs at least to know where to listen,
        where to forward and which programm number and version number to use. Optionally
        you can specify a different programm number and version number for the listening
        and target component.

        Parameters:
            host            address to listen on
            port            port to bind to (0 = random)
            prog            program number to expose via RPC
            vers            program version to expose via RPC
            target          target to forward requests to
            tport           optional target port (default = port)
            tprog           optional target program number (default = prog)
            tvers           optional target version number (default = vers)
            tprot           optional target protocol to use (default = tcp)

        Returns:
            None
        '''
        sunrpc.server.Server.__init__(self, host, port, prog, vers)

        self.target = target
        self.tport = tport if tport is not None else port
        self.tprog = tprog if tprog is not None else prog
        self.tvers = tvers if tvers is not None else vers

        self.client = sunrpc.client.get_client(target, self.tport, self.tprog, self.tvers, tprot)
        self.client.connect()

        self.dump = dump

    def process_call(self, xid: int, call_id: int, auth: tuple, verf: tuple,
                     packer: sunrpc.Packer, unpacker: sunrpc.Unpacker) -> None:
        '''
        Process an RPC call. This method first checks whether a custom method
        was implemented for the requested call_id. If not the case, it uses the
        default plain_forward function, which just forwards the call to the target.

        Additionally, other information from the RPC call is used to create a new
        call header that is forwarded to the target.

        Parameters:
            xid             the xid used by the call
            call_id         call_id specified within an RPC call
            auth            the auth information contained in the call
            verf            the verifier contained in the call
            packer          the packer used for the current call
            unpacker        the unpacker used for the current call

        Returns:
            None
        '''
        self.client.cred = auth
        self.client.verf = verf
        self.client.lastxid = xid

        call = self.client.make_call(call_id)

        method = self.method_map.get(call_id, self.plain_forward)
        method(packer, unpacker, call)

    def plain_forward(self, packer: sunrpc.Packer, unpacker: sunrpc.Packer, call: sunrpc.Call) -> None:
        '''
        If no handle was specified for an incoming method call, this is the default
        function that is used for processing the call. It simply forwards the client
        request to the server and forwards the server response back to the client.

        Parameters:
            packer      the packer used for the current call
            unpacker    the unpacker used for the current call
            call        RPC call targeting the forwarding server

        Returns:
            None
        '''
        self.forward_request(unpacker, call)
        self.forward_response(packer, call)

    def forward_request(self, unpacker: sunrpc.Packer, call: sunrpc.Call) -> None:
        '''
        Forward the client request.

        Parameters:
            unpacker    the unpacker used for the current call
            call        RPC call targeting the forwarding server

        Returns:
            None
        '''
        position = unpacker.get_position()
        packet_buffer = unpacker.get_buffer()
        argument_buffer = packet_buffer[position:]

        if len(argument_buffer) > 0:
            call.pack_raw(argument_buffer)

        self.client.do_call(call)

    def forward_response(self, packer: sunrpc.Packer, call: sunrpc.Call) -> None:
        '''
        Forward the servers response.

        Parameters:
            packer      the packer used for the current call
            call        RPC call targeting the forwarding server

        Returns:
            None
        '''
        position = call.unpacker.get_position()
        packet_buffer = call.ubytes()
        argument_buffer = packet_buffer[position:]

        packer.pack_uint(sunrpc.SUCCESS)
        packer.pack_raw(argument_buffer)

    def hook(self, data: bytes, is_request: bool) -> None:
        '''
        The proxy class implements a default hook that prints a hexdump for each
        forwarded packet.

        Parameters:
            data            data that is currently forwarded
            is_request      determines whether the request is a request or a response

        Returns:
            None
        '''
        if not self.dump:
            return

        if is_request:
            sunrpc.utils.hexdump(data)

        else:
            sunrpc.utils.hexdump(data, 'red')


class TCPProxy(Proxy, sunrpc.server.TCPServer):
    '''
    RPC TCP proxy. Only supports one connection at a time as it is single threaded.
    '''
    def __init__(self, host: str, port: int, prog: int, vers: int, target: str, tport: int = None,
                 tprog: int = None, tvers: int = None, tprot: str = 'tcp', dump: bool = False) -> None:
        '''
        '''
        Proxy.__init__(self, host, port, prog, vers, target, tport, tprog, tvers, tprot, dump)
        self.prot = sunrpc.portmapper.IPPROTO_TCP


class AsyncTCPProxy(Proxy, sunrpc.server.AsyncTCPServer):
    '''
    RPC TCP proxy based on asyncio. This one supports multiple connections at once.
    '''
    def __init__(self, host: str, port: int, prog: int, vers: int, target: str, tport: int = None,
                 tprog: int = None, tvers: int = None, tprot: str = 'tcp', dump: bool = False) -> None:
        '''
        '''
        Proxy.__init__(self, host, port, prog, vers, target, tport, tprog, tvers, tprot, dump)
        self.prot = sunrpc.portmapper.IPPROTO_TCP


class UDPProxy(Proxy, sunrpc.server.UDPServer):
    '''
    RPC UDP proxy.
    '''
    def __init__(self, host: str, port: int, prog: int, vers: int, target: str, tport: int = None,
                 tprog: int = None, tvers: int = None, tprot: str = 'udp', dump: bool = False) -> None:
        '''
        '''
        Proxy.__init__(self, host, port, prog, vers, target, tport, tprog, tvers, tprot, dump)
        self.prot = sunrpc.portmapper.IPPROTO_UDP
