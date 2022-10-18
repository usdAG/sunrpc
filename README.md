### sunrpc

----

*sunrpc* is a python library implementing [RFC1057](https://datatracker.ietf.org/doc/html/rfc1057). The library
from this repository is based on code snippets from various different other repositories. See the [references](#references)
section at the end of the document for a list of resources. The library is not complete yet and some operations
and message types might be missing. However, it should already be sufficient to build and access simple RPC services
like for example portmappers.

![](https://github.com/usdAG/sunrpc/workflows/main%20Python%20CI/badge.svg?branch=main)
![](https://github.com/usdAG/sunrpc/workflows/develop%20Python%20CI/badge.svg?branch=develop)
[![](https://img.shields.io/badge/version-1.1.0-blue)](https://github.com/usdAG/sunrpc/releases)
[![](https://img.shields.io/badge/build%20system-pip-blue)](https://pypi.org/project/sunrpc)
![](https://img.shields.io/badge/python-9%2b-blue)
[![](https://img.shields.io/badge/license-GPL%20v3.0-blue)](https://github.com/usdAG/sunrpc/blob/main/LICENSE)


### Installation

----

*sunrpc* can be installed via [pip](https://pypi.org/project/pip/) by running the following command:

```console
[user@host ~]$ pip3 install --user sunrpc
```

Alternatively you can build the package from source running:

```console
[user@host ~]$ pip3 install --user --upgrade build
[user@host ~]$ git clone https://github.com/usdAG/sunrpc
[user@host ~]$ cd sunrpc && python3 -m build
[user@host ~/sunrpc]$ pip3 install --user dist/*.whl
```


### Usage

----

Creating servers and clients with *sunrpc* is pretty simple. The library uses an annotation based approach
for creating the required *RPC* methods and abstracts the implementation details from the user. The following
listing contains an example for an simple *Hello World RPC Server*:

```python
from __future__ import annotations

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
        # 1337 is the programm number and 2 the version number supported by the server
        TCPServer.__init__(self, host, port, 1337, 2)

        # assign the procedure number 1 for self.hello_world
        self.add_method(1, self.hello_world)

    # define the hello_world RPC method that expects an string as input argument
    # and returns a string back to the client.
    @rpc_server_obtain(RpcStr)
    @rpc_server_return(RpcStr)
    def hello_world(self, message: str) -> str:
        '''
        Obtain the message from the client, print it and return 'Hello World :D'
        '''
        print(f'[+] The client said: {message}')
        return ['Hello World :D']


# create the server and start it. Calls are handeled automatically from here
server = HelloWorldServer('127.0.0.1', 4444)
server.bind()
server.listen()
```

The `rpc_obtain_server` and `rpc_return_server` decorators define the expected incoming argument
types and return values for *RPC* methods. Each *RPC* methods need to be registered within the
constructor and gets assigned a unique procedure ID. The client side code uses `rpc_obtain_client`
and `rpc_send_client` to call *RPC* methods:

```python
from __future__ import annotations

from sunrpc.types import RpcStr
from sunrpc.client import TCPClient, rpc_client_send, rpc_client_obtain


class HelloWorldClient(TCPClient):
    '''
    Client class that communicates to the HelloWorldServer.
    '''
    # hello_world calls the RPC method with procedure number 1 and sends one
    # RpcStr as argument. The result is an RpcStr returned by the server that
    # gets passed to the hello_world method.
    @rpc_client_send(1, RpcStr)
    @rpc_client_obtain(RpcStr)
    def hello_world(self, result: str) -> str:
        '''
        Send a string to the server and print the result.
        '''
        return result


# 1337 is the programm number and 2 the version number supported by the sever
client = HelloWorldClient('127.0.0.1', 4444, 1337, 2)
client.connect()

response = client.hello_world('Hello :D')
print(response)
```

For more complex usage examples, check the *portmapper-client* and *portmapper-server* implementations
from the [examples](./examples) folder. There is also [an example](./examples/portmapper-server-asyncio.py)
for building a server with *asnycio*.


### Proxy RPC Traffic

----

The `sunrpc.proxy` namespace contains methods and classes for building RPC proxies. The following example
demonstrates how to write a portmapper proxy, that forwards incoming portmap requests to the specified
target:

```python
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
        UDPProxy.__init__(self, host, port, 100000, 2, target, tport, dump = True)


# Just create a dummy proxy from localhost:4444 to localhost:111
server = PortMapperProxy('127.0.0.1', 4444, '127.0.0.1', 111)
server.bind()

print('[+] Portmapper proxy started :)')
server.listen()
```

When `dump` is set to `True`, a hexdump is created for each forwarded message. Moreover,
*hooks* can be implemented to modify certain RPC requests.


### References

----

The initial rpc implementation we used for this library can be found within the following repositories:

* [https://github.com/xbmc/python/blob/master/Demo/rpc/rpc.py](https://github.com/xbmc/python/blob/master/Demo/rpc/rpc.py)
* [https://github.com/python-ivi/python-vxi11/blob/master/vxi11/rpc.py](https://github.com/python-ivi/python-vxi11/blob/master/vxi11/rpc.py)
