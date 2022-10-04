from __future__ import annotations

import sunrpc
import socket
import asyncio
from select import select
from typing import Union, Callable


class Client:
    '''
    The Client class can be used to build RPC clients. It is extended by TCPClient
    and UDPClient, which should be used as the base class for writing actual RPC
    clients.
    '''

    def __init__(self, host: str, port: int, prog: int, vers: int) -> None:
        '''
        Initializes the client with the requied information. The specified
        parameters are expected to target the desired RCP service directly.
        If a portmapper needs to be used, this should be done in a seaprate
        step using the sunrpc.portmapper implementation.

        Parameters:
            host            target host to connect to
            port            target port to connect to
            prog            desired program number to connect to
            vers            desired version of the specified program

        Returns:
            None
        '''
        self.host = host
        self.port = port
        self.prog = prog
        self.vers = vers

        self.lastxid = 0
        self.cred = None
        self.verf = None

        self.broadcast = False

    def make_call(self, proc: int) -> sunrpc.Call:
        '''
        Prepare an RPC call. This method returns an object of the sunrpc.Call clas
        that can be used within the do_call method.

        Parameters:
            proc            procedure number to call

        Returns:
            Call            newly created Call object
        '''
        self.lastxid = self.lastxid + 1
        return sunrpc.Call(self.lastxid, self.prog, self.vers, proc, self.cred, self.verf)

    def do_call(self, call: sunrpc.Call) -> None:
        '''
        The do_call method performs the actual RPC call. This method needs to
        be overwritten by extending classes. These classes need to implement the
        underlying communication channel.

        Parameters:
            call        the sunrpc.Call to execute

        Returns:
            None
        '''
        raise NotImplementedError('do call needs to be overwritten by subclasses.')


class TCPClient(Client):
    '''
    The TCPClient implements a client that communicates via a plain TCP channel.
    RPC clients should extend this class if TCP is the desired communication
    protocol.
    '''

    def __init__(self, host: str, port: int, prog: int, vers: int) -> None:
        '''
        Just calls the initialization method of the implemented Client class and
        attempts to connect.

        Parameters:
            host            target host to connect to
            port            target port to connect to
            prog            desired program number to connect to
            vers            desired version of the specified program

        Returns:
            None
        '''
        Client.__init__(self, host, port, prog, vers)

    def connect(self):
        '''
        Connect to the configured TCP endpoint.

        Parameters:
            None

        Returns:
            None
        '''
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def close(self):
        '''
        Close the underlying TCP connection.

        Parameters:
            None

        Returns:
            None
        '''
        self.sock.close()

    def do_call(self, call: sunrpc.Call) -> None:
        '''
        Perform the actual call via TCP.

        Parameters:
            call        the sunrpc.Call to execute

        Returns:
            None
        '''
        sunrpc.utils.sendrecord(self.sock, call.bytes())

        while True:
            reply = sunrpc.utils.recvrecord(self.sock)
            if call.set_reply(reply):
                break


class AsyncTCPClient(TCPClient):
    '''
    The AsyncTCPClient implements a client that communicates via a TCP channel.
    Connections are established in an async manner, one connection per RPC message.
    '''

    async def do_call(self, call: sunrpc.Call) -> None:
        '''
        Perform the actual call via async TCP. This method establishes a connection
        to the server, sends the data contained within the call and obtains the
        response. Afterwards, the connection is closed.

        Parameters:
            call        the sunrpc.Call to execute

        Returns:
            None
        '''
        reader, writer = await asyncio.open_connection(self.host, self.port)

        await sunrpc.utils.async_sendrecord(writer, call.bytes())

        while True:
            reply = await sunrpc.utils.async_recvrecord(reader)

            if call.set_reply(reply):
                break

        writer.close()
        await writer.wait_closed()


class UDPClient(Client):
    '''
    The UDPClient implements a client that communicates via a plain UDP channel.
    RPC clients should extend this class if UDP is the desired communication
    protocol.
    '''

    def __init__(self, host: str, port: int, prog: int, vers: int) -> None:
        '''
        Just calls the initialization method of the implemented Client class and
        attempts to connect.

        Parameters:
            host            target host to connect to
            port            target port to connect to
            prog            desired program number to connect to
            vers            desired version of the specified program

        Returns:
            None
        '''
        Client.__init__(self, host, port, prog, vers)

        self.tunnel = None
        self.broadcast = False

    def connect(self) -> None:
        '''
        Connect to the configured UDP endpoint. If broadcast is not configured,
        a new UDP socket is created and connected to the client.

        If broadcast is configured and the current UDPClient contains the portmapper
        as a tunnel.

        Parameters:
            None

        Returns:
            None
        '''
        if self.tunnel is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            if not self.broadcast:
                self.sock.connect((self.host, self.port))

        else:
            self.tunnel.enable_broadcast()
            self.tunnel.connect()

    def close(self) -> None:
        '''
        Close the underlying UDP connection.

        Parameters:
            None

        Returns:
            None
        '''
        if self.tunnel is None:
            self.sock.close()

        else:
            self.tunnel.close()

    def enable_broadcast(self) -> None:
        '''
        Enable broadcasting mode for the client. When broadcasting is enabled, a UDPClient
        does not verify the source of incoming RPC packages. This allows a client to send
        a UDP RPC packet to IP1:PORT1 and to receive the response from IP2:PORT2. If
        broadcasting is not enabled, such a response would be blocked.

        Using the callit method on portmapper clients is one example use case, since the
        request is send to IP:111, but the response is received from IP:XYZ.
        '''
        self.broadcast = True

    def set_tunnel(self, host: str, port: str = 111) -> None:
        '''
        This method sets a tunnel for the RPC client. A tunnel is basically a portmapper
        that communicates via UDP to the specified target. It is used to wrap the actual
        RPC calls made on the client into a buffer that is send to the portmapper using
        the callit procedure. The portmapper then forwards the method call to the actual
        target. This may allows to bypass IP based access control on UDP based RPC services.

        The callit RPC method is nowadays often disabled by default on portmapper services.
        Using rpcbind on debian for example, it needs to be started with the -r option to
        enable it.

        Parameters:
            host        host where the portmapper is listening
            port        port where the portmapper is listening

        Returns:
            None
        '''
        self.tunnel = sunrpc.portmapper.get_client(host, port, 'udp')

    def do_call(self, call: sunrpc.Call) -> None:
        '''
        Perform the actual call via UDP. If a tunnel was configured, the
        call is dispatched using the callit method of the corresponding
        portmapper client.

        Parameters:
            call        the sunrpc.Call to execute

        Returns:
            None
        '''
        if self.tunnel is not None:
            port, data = self.tunnel.callit(self.prog, self.vers, call.proc, call.bytes())
            return

        if self.broadcast:
            self.sock.sendto(call.bytes(), (self.host, self.port))

        else:
            self.sock.send(call.bytes())

        count = 5
        timeout = 1
        bufsize = 8192

        while 1:
            r, w, x = [self.sock], [], []
            r, w, x = select(r, w, x, timeout)

            if self.sock not in r:
                count = count - 1

                if count < 0:
                    raise sunrpc.RPCError('timeout')

                if timeout < 25:
                    timeout = timeout * 2

                self.sock.send(call.bytes())
                continue

            reply = self.sock.recv(bufsize)
            if call.set_reply(reply):
                break


def get_client(host: str, port: int, prog: int, vers: int, protocol: str) -> Union(TCPClient, UDPClient):
    '''
    Returns the corresponding Client depending on the specified
    protocol. Allowed Protocols are 'tcp' and 'udp':

    Parameters:
        protocol        protocol specifier (either 'tcp' or 'udp')

    Returns:
        Either a TCPClient or UDPClient
    '''
    if protocol == 'udp':
        return UDPClient(host, port, prog, vers)

    elif protocol == 'tcp':
        return TCPClient(host, port, prog, vers)

    else:
        return None


def rpc_client_send(proc: int, *args: list[sunrpc.types.RpcType]) -> Callable:
    '''
    Decorator function to create RPC methods for RPC clients. The decorator declares
    the procedure number and argument types usd by a RPC method. The following listing
    shows an example, where the procedure number 4 is called on the server, which
    expects a string, an integer and a boolean as input arguments.

        @rpc_client_send(4, RpcStr, RpcInt, RpcBool)
        @rpc_client_obtain(RpcInt, RpcStr)
        def rpc_function(self, arg1: int, arg2: str)

    The rpc_function method can now be called with a string, an integer and a boolean
    and the packing and sending of arguments is handeled automatically. rpc_client_send
    should usually be combined with the rpc_client_obtain decorator listed below.

    Parameters:
        proc        the procedure number that should be called
        args        the argument types to use for the call

    Returns:
        Callable
    '''
    def decorator_rpc_client_send(func: Callable) -> Callable:
        '''
        The wrapped function is expected to take only an sunrpc.Call as input
        argument. When using the rpc_client_obtain decorator, this is handeled
        automatically. Otherwise your function signature should look like:

            func(self, call: sunrpc.Call)

        The sunrpc.Call type contains the underlying unpacker and RPC responses
        can be unpacked using the unpack or unpack_all methods.
        '''

        def wrapper(self, *method_args):
            '''
            The replacing function takes a list of method arguments and packs
            them according to the RpcType definitions specified within the decorator.
            '''
            call = self.make_call(proc)

            for rpc_type, arg in zip(args, method_args):
                rpc_obj = rpc_type(arg)
                call.pack(rpc_obj)

            self.do_call(call)

            return func(self, call)

        return wrapper

    return decorator_rpc_client_send


def rpc_client_obtain(*args: list[sunrpc.types.RpcType]) -> Callable:
    '''
    Decorator function to create RPC methods for RPC clients. The decorator declares
    Which argument types are expected to be returned by the RPC method. It should be
    used together with the rpc_client_send decorator. The following listing shows
    an example, where the targeted RPC function returns an integer and a string:

        @rpc_client_send(4, RpcStr, RpcInt, RpcBool)
        @rpc_client_obtain(RpcInt, RpcStr)
        def rpc_function(self, arg1: int, arg2: str)

    The rpc_function method can now be called with a string, an integer and a boolean
    and the packing and sending of arguments is handeled automatically. After obtaining
    the response from the RPC server, the original implementation of rpc_function is
    called with the obtain response parameters.

    Parameters:
        args        the argument types that are returned by the rpc method.

    Returns:
        Callable
    '''
    def decorator_rpc_client_obtain(func: Callable) -> Callable:
        '''
        The wrapped function should expect as many arguments as there are return
        values for the targeted RPC call.
        '''

        def wrapper(self, call: sunrpc.Call):
            '''
            The returned wrapper needs to be called with an sunrpc.Call type from which
            the RPC response can be obtained.
            '''
            rpc_response = call.unpack_all(args)
            return func(self, *rpc_response)

        return wrapper

    return decorator_rpc_client_obtain


def rpc_client_send_async(proc: int, *args: list[sunrpc.types.RpcType]) -> Callable:
    '''
    Basically the same as rpc_client_send but for async client side RPC functions.
    '''
    def decorator_rpc_client_send(func: Callable) -> Callable:
        '''
        The wrapped function is expected to take only an sunrpc.Call as input
        argument. When using the rpc_client_obtain decorator, this is handeled
        automatically. Otherwise your function signature should look like:

            async func(self, call: sunrpc.Call)

        The sunrpc.Call type contains the underlying unpacker and RPC responses
        can be unpacked using the unpack or unpack_all methods.
        '''

        async def wrapper(self, *method_args):
            '''
            The replacing function takes a list of method arguments and packs
            them according to the RpcType definitions specified within the decorator.
            '''
            call = self.make_call(proc)

            for rpc_type, arg in zip(args, method_args):
                rpc_obj = rpc_type(arg)
                call.pack(rpc_obj)

            await self.do_call(call)

            return await func(self, call)

        return wrapper

    return decorator_rpc_client_send


def rpc_client_obtain_async(*args: list[sunrpc.types.RpcType]) -> Callable:
    '''
    Basically the same as rpc_client_obtain but for async client side RPC functions.
    '''
    def decorator_rpc_client_obtain(func: Callable) -> Callable:
        '''
        The wrapped function should expect as many arguments as there are return
        values for the targeted RPC call.
        '''

        async def wrapper(self, call: sunrpc.Call):
            '''
            The returned wrapper needs to be called with an sunrpc.Call type from which
            the RPC response can be obtained.
            '''
            rpc_response = call.unpack_all(args)
            return await func(self, *rpc_response)

        return wrapper

    return decorator_rpc_client_obtain
