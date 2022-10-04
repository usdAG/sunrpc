from __future__ import annotations

import sunrpc
import string
import struct
import socket
import asyncio
from termcolor import cprint


def hexdump(data: bytes, color: str = 'green') -> None:
    '''
    Display input data in form of a hexdump.

    Parameters:
        data            Input data to display within the dump
        color           Color the dump is displayed in

    Returns:
        None
    '''
    if data is None:
        return

    for ctr in range(0, len(data), 16):

        items = data[ctr:ctr + 16]
        cprint('{:08x}: '.format(ctr), color, end='')

        for cts in range(0, 15, 2):

            byte = int.from_bytes(items[cts:cts + 2], 'big')
            cprint('{:04x} '.format(byte), color, end='')

        print(' ', end='')

        for item in items:

            if chr(item) not in string.printable or chr(item) in '\t\n\r\x0b\x0c':
                cprint('.', color, end='')

            else:
                cprint(chr(item), color, end='')

        print('')
    print('')


async def async_sendfrag(writer: asyncio.streams.StreamWriter, last: bool, frag: bytes) -> None:
    '''
    Used for sending RPC packets. Async variant. An RPC packet can theoretically exceed the
    maximum size of the underlying transport protocol. Therefore, RPC packets can be separated
    into multiple fragments. Each message indicates whether it is fragmented by using the first
    bit of the RPC header. If this bit is set (message usually starts with 0x80 in this case),
    the incoming RPC packet is considered the last fragment. If the first bit is zero, more data
    after the current packet is expected.

    Parameters:
        writer              StreamWriter to write the data to
        last                Whether this is the last fragment being send
        frag                Data to send

    Returns:
        None
    '''
    x = len(frag)

    if last:
        x = x | 0x80000000

    header = struct.pack('>I', x)
    writer.write(header + frag)

    await writer.drain()


async def async_sendrecord(writer: asyncio.streams.StreamWriter, record: bytes, frag_size: int = sunrpc.FRAGMENT_SIZE) -> None:
    '''
    Used for sending RPC packets. Async variant. Data with a size that exceeds the maximum
    fragment size is split into multiple fragments.

    Parameters:
        writer              StreamWriter to write the data to
        record              Data to send
        frag_size           Maximum fragment size (default is 2^31 - 1)

    Returns:
        None
    '''
    last = False
    length = len(record)

    while length > 0:

        if length <= frag_size:
            last = True

        await async_sendfrag(writer, last, record[0:frag_size])

        record = record[frag_size:]
        length = len(record)


async def async_recvfrag(reader: asyncio.streams.StreamReader) -> tuple[bool, bytes]:
    '''
    Obtain incoming RPC fragment. Async variant.

    Parameters:
        reader          StreamReader to obtain the fragment from

    Returns:
        tuple           tuple[last fragment?, bytes]
    '''
    header = await reader.read(4)

    if len(header) < 4:
        raise EOFError('RPC server send invalid response header.')

    header = struct.unpack('>I', header[0:4])[0]

    last = ((header & 0x80000000) != 0)
    size = int(header & 0x7fffffff)

    frag = bytearray()

    while len(frag) < size:
        buf = await reader.read(size - len(frag))
        if not buf:
            raise EOFError('RPC server send incomplete data')
        frag.extend(buf)

    return last, frag


async def async_recvrecord(reader: asyncio.streams.StreamReader) -> bytes:
    '''
    Obtain incoming RPC packet. Async variant.

    Parameters:
        reader          StreamReader to obtain the packet from

    Returns:
        bytes           obtained RPC packet
    '''
    last = False
    record = bytearray()

    while not last:
        last, frag = await async_recvfrag(reader)
        record.extend(frag)

    return bytes(record)


def sendfrag(sock: socket.socket, last: bool, frag: bytes) -> None:
    '''
    Used for sending RPC packets. An RPC packet can theoretically exceed the
    maximum size of the underlying transport protocol. Therefore, RPC packets can be separated
    into multiple fragments. Each message indicates whether it is fragmented by using the first
    bit of the RPC header. If this bit is set (message usually starts with 0x80 in this case),
    the incoming RPC packet is considered the last fragment. If the first bit is zero, more data
    after the current packet is expected.

    Parameters:
        writer              socket to write the data to
        last                Whether this is the last fragment being send
        frag                Data to send

    Returns:
        None
    '''
    x = len(frag)

    if last:
        x = x | 0x80000000

    header = struct.pack('>I', x)
    sock.sendall(header + frag)


def sendrecord(sock: socket.socket, record: bytes, frag_size: int = sunrpc.FRAGMENT_SIZE) -> None:
    '''
    Used for sending RPC packets. Data with a size that exceeds the maximum
    fragment size is split into multiple fragments.

    Parameters:
        writer              StreamWriter to write the data to
        record              Data to send
        frag_size           Maximum fragment size (default is 2^31 - 1)

    Returns:
        None
    '''
    last = False
    length = len(record)

    while length > 0:

        if length <= frag_size:
            last = True

        sendfrag(sock, last, record[0:frag_size])

        record = record[frag_size:]
        length = len(record)


def recvfrag(sock: socket.socket) -> tuple[bool, bytes]:
    '''
    Obtain incoming RPC fragment.

    Parameters:
        sock            StreamReader to obtain the fragment from

    Returns:
        tuple           tuple[last fragment?, bytes]
    '''
    header = sock.recv(4)

    if len(header) < 4:
        raise EOFError('RPC server send invalid response header.')

    header = struct.unpack('>I', header[0:4])[0]

    last = ((header & 0x80000000) != 0)
    size = int(header & 0x7fffffff)

    frag = bytearray()

    while len(frag) < size:
        buf = sock.recv(size - len(frag))
        if not buf:
            raise EOFError('RPC server send incomplete data')
        frag.extend(buf)

    return last, frag


def recvrecord(sock: socket.socket) -> bytes:
    '''
    Obtain incoming RPC packet.

    Parameters:
        sock            socket to obtain the packet from

    Returns:
        bytes           obtained RPC packet
    '''
    last = False
    record = bytearray()

    while not last:
        last, frag = recvfrag(sock)
        record.extend(frag)

    return bytes(record)
