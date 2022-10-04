from __future__ import annotations

import sys
import sunrpc
import socket
import asyncio
from abc import ABC
from typing import Callable, Any


class RPCHeaderError(Exception):
    '''
    '''
    def __init__(self, response: bytes) -> None:
        '''
        '''
        self.response = response


class Server(ABC):
    '''
    The server class can be used to create sunrpc servers. Server is an abstract
    class and cannot be used on it's own. TCPServer, AsyncTCPServer and UDPServer
    are the derived classes that can be used instead.
    '''

    def __init__(self, host: str, port: int, prog: int, vers: int) -> None:
        '''
        Initialize the RPC server. Custom RPC servers are expected to extend
        this class and to add additional methods within the constructor by calling
        self.add_method.

        Parameters:
            host            address to listen on
            port            port to bind to (0 = random)
            prog            program number to expose via RPC
            vers            program version to expose via RPC

        Returns:
            None
        '''
        self.host = host
        self.prog = prog
        self.vers = vers
        self.port = port

        self.mapper = None
        self.registered = False

        self.method_map = {}
        self.add_method(0, self.turn_around)

    def __del__(self) -> None:
        '''
        Unregister the server from the portmapper on deltetion.

        Parameters:
            None

        Returns:
            None
        '''
        if self.registered:
            self.unregister()

    def register(self, mapper_host: str = '127.0.0.1', mapper_port: int = 111, mapper_prot: str = 'udp') -> None:
        '''
        Register the server on a portmapper service. Per default, the portmapper
        is expected to listen on 127.0.0.1:111. If this is not the case, a custom
        endpoint can be specified via method parameters.

        Parameters:
            mapper_host     host where the portmapper is running
            mapper_port     port where the portmapper is running
            prot            protocol to use for the registration

        Returns:
            None
        '''
        if self.port == 0:
            raise sunrpc.RPCError('server must be bound first')

        if not self.mapper:
            self.mapper = sunrpc.portmapper.get_client(mapper_host, mapper_port, mapper_prot)
            self.mapper.connect()

        if not self.mapper.set(self.prog, self.vers, self.prot, self.port):
            raise sunrpc.RPCError('register failed')

        self.registered = True

    def unregister(self, mapper_host: str = '127.0.0.1', mapper_port: int = 111, mapper_prot: str = 'tcp') -> None:
        '''
        Unregister the server on a portmapper service. Per default, the portmapper
        is expected to listen on 127.0.0.1:111. If this is not the case, a custom
        endpoint can be specified via method parameters.

        Parameters:
            mapper_host     host where the portmapper is running
            mapper_port     port where the portmapper is running
            prot            protocol to use for the unregistration

        Returns:
            None
        '''
        if self.port == 0:
            raise sunrpc.RPCError('server must be bound first')

        if not self.mapper:
            self.mapper = sunrpc.portmapper.get_client(mapper_host, mapper_port, mapper_prot)
            self.mapper.connect()

        if not self.mapper.unset(self.prog, self.vers, self.prot, self.port):
            raise sunrpc.RPCError('unregister failed')

        self.registered = False

    def get_call_attrs(self, packer: sunrpc.Packer, unpacker: sunrpc.Unpacker) -> (int, int, tuple, tuple):
        '''
        Unpack the header of an incoming RPC call and obtain the xid, call
        ID, the authentication information and the verifier that was included
        in the call.

        Parameters:
            None

        Returns:
            tuple(xid, call_id, auth, verf)
        '''
        xid = unpacker.unpack_uint()
        packer.pack_uint(xid)

        temp = unpacker.unpack_enum()
        if temp != sunrpc.CALL:
            raise RPCHeaderError(None)

        packer.pack_uint(sunrpc.REPLY)
        temp = unpacker.unpack_uint()

        if temp != sunrpc.RPCVERSION:
            packer.pack_uint(sunrpc.MSG_DENIED)
            packer.pack_uint(sunrpc.RPC_MISMATCH)
            packer.pack_uint(sunrpc.RPCVERSION)
            packer.pack_uint(sunrpc.RPCVERSION)
            raise RPCHeaderError(packer.get_buf())

        packer.pack_uint(sunrpc.MSG_ACCEPTED)
        packer.pack_auth((sunrpc.AUTH_NULL, sunrpc.make_auth_null()))

        prog = unpacker.unpack_uint()

        if prog != self.prog:
            packer.pack_uint(sunrpc.PROG_UNAVAIL)
            raise RPCHeaderError(packer.get_buf())

        vers = unpacker.unpack_uint()
        if vers != self.vers:
            packer.pack_uint(sunrpc.PROG_MISMATCH)
            packer.pack_uint(self.vers)
            packer.pack_uint(self.vers)
            raise RPCHeaderError(packer.get_buf())

        call_id = unpacker.unpack_uint()
        auth = unpacker.unpack_auth()
        verf = unpacker.unpack_auth()

        return (xid, call_id, auth, verf)

    def process_call(self, xid: int, call_id: int, auth: tuple, verf: tuple,
                     packer: sunrpc.Packer, unpacker: sunrpc.Unpacker) -> None:
        '''
        Process an RPC call. The caller specified id is looked up
        within the method map and gets called if available. Other
        call attributes are also available within the arguments,
        but are not used by the default implementation

        Parameters:
            xid             the xid used by the call
            call_id         call_id specified within an RPC call
            auth            the auth information contained in the call
            verf            the verifier contained in the call

        Returns:
            None
        '''
        method = self.method_map.get(call_id)

        if method is None:
            packer.pack_uint(sunrpc.PROC_UNAVAIL)
            raise RPCHeaderError(packer.get_buf())

        packer.pack_uint(sunrpc.SUCCESS)
        method(packer, unpacker)

    def handle(self, call: bytes) -> bytes:
        '''
        Process an incoming RPC call and return the bytes for the response.

        Parameters:
            call            Incoming RPC call

        Returns:
            bytes           RPC response
        '''
        packer = sunrpc.Packer()
        unpacker = sunrpc.Unpacker(call)

        self.hook(unpacker.get_buffer(), True)

        try:
            xid, call_id, auth, verf = self.get_call_attrs(packer, unpacker)
            self.process_call(xid, call_id, auth, verf, packer, unpacker)

        except RPCHeaderError as e:
            return e.response

        except (EOFError, sunrpc.RPCGarbageArgs):
            # Too few or too many arguments
            packer.reset()
            packer.pack_uint(xid)
            packer.pack_uint(sunrpc.REPLY)
            packer.pack_uint(sunrpc.MSG_ACCEPTED)
            packer.pack_auth((sunrpc.AUTH_NULL, sunrpc.make_auth_null()))
            packer.pack_uint(sunrpc.GARBAGE_ARGS)

        self.hook(packer.get_buffer(), False)

        return packer.get_buf()

    def turn_around(self, packer, unpacker):
        '''
        This function should be called after reading the call specific arguments
        within the handler functions. It sets the unpacker for incoming data to
        done and starts with the packing of the response arguments.

        Parameters:
            None

        Returns:
            None
        '''
        try:
            unpacker.done()

        except RuntimeError:
            raise sunrpc.RPCGarbageArgs

    def add_method(self, proc: int, method: Callable) -> None:
        '''
        Adds a new RPC method to the server. The method is called, when
        the RPC server obtains a call with a procedure id specified by proc.

        Parameters:
            proc            The procedure id to define the method for
            method          The method to call

        Returns:
            None
        '''
        self.method_map[proc] = method

    def hook(self, data: bytes, is_request: bool) -> None:
        '''
        Hook that is called when packages are received from or send to the client.

        Parameters:
            data            Bytes that are send / received
            is_request      Whether the bytes are incoming or outgoing

        Returns:
            None
        '''
        pass


class TCPServer(Server):
    '''
    RPC TCP server. Only supports one connection at a time as it is single threaded.
    '''

    def __init__(self, host: str, port: int, prog: int, vers: int) -> None:
        '''
        Initialize the TCP server.

        Paramaters:
            host            address to listen on
            port            port to listen on (0 = random)
            prog            program version that is exposed
            vers            version of the program that is exposed

        Returns:
            None
        '''
        Server.__init__(self, host, port, prog, vers)
        self.prot = sunrpc.portmapper.IPPROTO_TCP

    def bind(self) -> None:
        '''
        Bind the RPC TCP server to the configured interface / port. When a random port
        (0) was specified, the bind action must be called before registering the RPC
        service.

        Parameters:
            None

        Returns:
            None
        '''
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.host, self.port = self.sock.getsockname()

    def listen(self) -> None:
        '''
        Listen for incoming connections and handle them.

        Parameters:
            None

        Returns:
            None
        '''
        self.sock.listen(0)

        while 1:
            sock, _ = self.sock.accept()
            self.handle_call(sock)

    def handle_call(self, sock: socket.socket) -> None:
        '''
        Each incoming connection is handeld by this function.

        Parameters:
            sock            Socket for the incoming connection

        Returns:
            None
        '''
        while 1:

            try:
                call = sunrpc.utils.recvrecord(sock)

            except EOFError:
                break

            except socket.error:
                print('socket error:', sys.exc_info()[0])
                break

            reply = self.handle(call)

            if reply is not None:
                sunrpc.utils.sendrecord(sock, reply)


class AsyncTCPServer(TCPServer):
    '''
    RPC TCP server based on asyncio. This one supports multiple connections at once.
    To really profit from it, RPC methods implemented by the RPC server should be
    async too.
    '''

    async def bind(self) -> None:
        '''
        Bind the RPC TCP server to the configured interface / port. When a random port
        (0) was specified, the bind action must be called before registering the RPC
        service.

        Parameters:
            None

        Returns:
            None
        '''
        self.server = await asyncio.start_server(self.handle_call, self.host, self.port)
        self.host, self.port = self.server.sockets[0].getsockname()

    async def listen(self) -> None:
        '''
        Listen for incoming connections and handle them.

        Parameters:
            None

        Returns:
            None
        '''
        async with self.server:
            await self.server.serve_forever()

    async def handle_call(self, reader: asyncio.streams.StreamReader, writer: asyncio.streams.StreamWriter):
        '''
        Each incoming connection is handeld by this function.

        Parameters:
            sock            Socket for the incoming connection

        Returns:
            None
        '''
        while 1:

            try:
                call = await sunrpc.utils.async_recvrecord(reader)

            except EOFError:
                break

            except socket.error:
                print('socket error:', sys.exc_info()[0])
                break

            reply = await self.handle(call)

            if reply is not None:
                await sunrpc.utils.async_sendrecord(writer, reply)

    async def handle(self, call: bytes) -> bytes:
        '''
        Process an incoming RPC call and return the bytes for the response.

        Parameters:
            call            Incoming RPC call

        Returns:
            bytes           RPC response
        '''
        packer = sunrpc.Packer()
        unpacker = sunrpc.Unpacker(call)

        self.hook(unpacker.get_buffer(), True)

        try:
            xid, call_id, auth, verf = self.get_call_attrs(packer, unpacker)
            await self.process_call(xid, call_id, auth, verf, packer, unpacker)

        except RPCHeaderError as e:
            return e.response

        except (EOFError, sunrpc.RPCGarbageArgs):
            # Too few or too many arguments
            packer.reset()
            packer.pack_uint(xid)
            packer.pack_uint(sunrpc.REPLY)
            packer.pack_uint(sunrpc.MSG_ACCEPTED)
            packer.pack_auth((sunrpc.AUTH_NULL, sunrpc.make_auth_null()))
            packer.pack_uint(sunrpc.GARBAGE_ARGS)

        self.hook(packer.get_buffer(), False)

        return packer.get_buf()

    async def process_call(self, xid: int, call_id: int, auth: tuple, verf: tuple,
                           packer: sunrpc.Packer, unpacker: sunrpc.Unpacker) -> None:
        '''
        Process an RPC call. The caller specified id is looked up
        within the method map and gets called if available. Other
        call attributes are also available within the arguments,
        but are not used by the default implementation

        Parameters:
            xid             the xid used by the call
            call_id         call_id specified within an RPC call
            auth            the auth information contained in the call
            verf            the verifier contained in the call

        Returns:
            None
        '''
        method = self.method_map.get(call_id)

        if method is None:
            packer.pack_uint(sunrpc.PROC_UNAVAIL)
            raise RPCHeaderError(packer.get_buf())

        packer.pack_uint(sunrpc.SUCCESS)

        if asyncio.iscoroutinefunction(method):
            await method(packer, unpacker)

        else:
            method(packer, unpacker)


class UDPServer(Server):
    '''
    RPC UDP Server.
    '''

    def __init__(self, host: str, port: int, prog: int, vers: int) -> None:
        '''
        Initialize the UDP server.

        Paramaters:
            host            address to listen on
            port            port to listen on (0 = random)
            prog            program version that is exposed
            vers            version of the program that is exposed

        Returns:
            None
        '''
        Server.__init__(self, host, port, prog, vers)
        self.prot = sunrpc.portmapper.IPPROTO_UDP

    def bind(self) -> None:
        '''
        Bind the RPC UDP server to the configured interface / port. When a random port
        (0) was specified, the bind action must be called before registering the RPC
        service.

        Parameters:
            None

        Returns:
            None
        '''
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.host, self.port = self.sock.getsockname()

    def listen(self) -> None:
        '''
        Listen for incoming connections and handle them.

        Parameters:
            None

        Returns:
            None
        '''
        while 1:
            self.handle_call()

    def handle_call(self) -> None:
        '''
        Each incoming connection is handeld by this function.

        Parameters:
            sock            Socket for the incoming connection

        Returns:
            None
        '''
        call, host_port = self.sock.recvfrom(8192)
        reply = self.handle(call)
        if reply is not None:
            self.sock.sendto(reply, host_port)


def rpc_server_obtain(*args: list[sunrpc.types.RpcType]) -> Callable:
    '''
    Decorator function to create RPC methods for RPC servers. The decorator declares
    the argument types expected by the RPC method. The following listing shows an example,
    where an RPC method is declared that expects a string, an integer and a boolean.

        @rpc_server_obtain(RpcStr, RpcInt, RpcBool)
        @rpc_server_return(RpcInt, RpcStr)
        def rpc_function(self, arg1: str, arg2: int, arg3: bool)

    rpc_server_obtain is intended to be used together with rpc_server_return, which declares
    the types of the return values of the RPC method. The decorated function can now be called
    by just passing a packer and an unpacker to it. Unpacking and packing of arguments is
    handeled automatically.

    Parameters:
        args        the argument types expected by the call

    Returns:
        Callable
    '''
    def decorator_rpc_server_obtain(func: Callable) -> Callable:
        '''
        The function that is wrapped by the decorator should expect a packer and the
        obtained RPC arguments send by the client as input parametsers.
        '''

        def wrapper(self, packer: sunrpc.Packer, unpacker: sunrpc.Unpacker):
            '''
            The wrapper returned by the decorator expects a packer and unpacker to be specified
            for the call.
            '''
            rpc_args = []

            for rpc_type in args:
                rpc_obj = rpc_type()
                rpc_arg = rpc_obj.unpack(unpacker)
                rpc_args.append(rpc_arg)

            return func(self, packer, *rpc_args)

        return wrapper

    return decorator_rpc_server_obtain


def rpc_server_obtain_async(*args: list[sunrpc.types.RpcType]) -> Callable:
    '''
    Basically the same as rpc_server_obtain but for async server side RPC functions.

    Parameters:
        args        the argument types expected by the call

    Returns:
        Callable
    '''
    def decorator_rpc_server_obtain(func: Callable) -> Callable:
        '''
        The function that is wrapped by the decorator should expect a packer and the
        obtained RPC arguments send by the client as input parametsers.
        '''

        async def wrapper(self, packer: sunrpc.Packer, unpacker: sunrpc.Unpacker):
            '''
            The wrapper returned by the decorator expects a packer and unpacker to be specified
            for the call.
            '''
            rpc_args = []

            for rpc_type in args:
                rpc_obj = rpc_type()
                rpc_arg = rpc_obj.unpack(unpacker)
                rpc_args.append(rpc_arg)

            return await func(self, packer, *rpc_args)

        return wrapper

    return decorator_rpc_server_obtain


def rpc_server_return(*args: list[sunrpc.types.RpcType]) -> Callable:
    '''
    Decorator function to create RPC methods for RPC servers. The decorator declares
    the return types that are returned by the RPC method. The following listing shows
    an example, where the declared RPC function returns an integer and a string.

        @rpc_server_obtain(RpcStr, RpcInt, RpcBool)
        @rpc_server_return(RpcInt, RpcStr)
        def rpc_function(self, arg1: str, arg2: int, arg3: bool)

    rpc_server_return is intended to be used together with rpc_server_obtain, which declares
    the types of incoming RPC parameters. The wrapped method rpc_function should return a
    list, where each list item maps to one of the specified RPC return values.

    Parameters:
        args        the return types emitted by the RPC function

    Returns:
        Callable
    '''
    def decorator_rpc_server_return(func: Callable) -> Callable:
        '''
        The wrapped function should expect a sunrpc.Packer and the method arguments
        obtain from the client as input parameters.
        '''

        def wrapper(self, packer: sunrpc.Packer, *method_args: list[Any]):
            '''
            The wrapper calls func with the obtained method parameters from the client and
            packs the return values according to the types specified within the decorator.
            '''
            results = func(self, *method_args)

            for rpc_type, result in zip(args, results):
                rpc_obj = rpc_type(result)
                rpc_obj.pack(packer)

        return wrapper

    return decorator_rpc_server_return


def rpc_server_return_async(*args: list[sunrpc.types.RpcType]) -> Callable:
    '''
    Basically the same as rpc_server_return but for async server side RPC functions.
    '''
    def decorator_rpc_server_return(func: Callable) -> Callable:
        '''
        The wrapped function should expect a sunrpc.Packer and the method arguments
        obtain from the client as input parameters.
        '''

        async def wrapper(self, packer: sunrpc.Packer, *method_args: list[Any]):
            '''
            The wrapper calls func with the obtained method parameters from the client and
            packs the return values according to the types specified within the decorator.
            '''
            results = await func(self, *method_args)

            for rpc_type, result in zip(args, results):
                rpc_obj = rpc_type(result)
                rpc_obj.pack(packer)

        return wrapper

    return decorator_rpc_server_return
