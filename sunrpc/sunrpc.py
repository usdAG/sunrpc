from __future__ import annotations

import xdrlib
import sunrpc.types

from enum import Enum
from typing import Any


RPCVERSION = 2

CALL = 0
REPLY = 1

AUTH_NULL = 0
AUTH_UNIX = 1
AUTH_SHORT = 2
AUTH_DES = 3

MSG_ACCEPTED = 0
MSG_DENIED = 1

SUCCESS = 0            # RPC executed successfully
PROG_UNAVAIL = 1       # remote hasn't exported program
PROG_MISMATCH = 2      # remote can't support version #
PROC_UNAVAIL = 3       # program can't support procedure
GARBAGE_ARGS = 4       # procedure can't decode params

RPC_MISMATCH = 0       # RPC version number != 2
AUTH_ERROR = 1         # remote can't authenticate caller

AUTH_BADCRED = 1       # bad credentials (seal broken)
AUTH_REJECTEDCRED = 2  # client must begin new session
AUTH_BADVERF = 3       # bad verifier (seal broken)
AUTH_REJECTEDVERF = 4  # verifier expired or replayed
AUTH_TOOWEAK = 5       # rejected for security reasons

FRAGMENT_SIZE = 0x7fffffff

PORTMAPPER = 100000


class RPCError(Exception):
    pass


class RPCBadFormat(RPCError):
    pass


class RPCBadVersion(RPCError):
    pass


class RPCGarbageArgs(RPCError):
    pass


class RPCUnpackError(RPCError):
    pass


class RPCBadType(RPCError):
    pass


def make_auth_null():
    return b''


class Type(Enum):
    '''
    Available Types for packing RPC packages.
    '''
    INT = 1
    UINT = 2
    BOOL = 3
    FLOAT = 6
    DOUBLE = 7
    STRING = 8
    BYTES = 9
    OPAQUE = 10
    ENUM = 11
    ARRAY = 12
    FSTRING = 13
    FARRAY = 14


class Packer(xdrlib.Packer):
    '''
    Packer extends xdrlib.Packer and adds relevant methods for packaging RPC packets.
    '''

    def pack_auth(self, auth: tuple) -> None:
        '''
        Pack authentication information into the packer. The auth tuple should
        contain the authentication package type and the associated data.

        Parameters:
            auth            tuple of authentication package type and data

        Returns:
            None
        '''
        flavor, stuff = auth
        self.pack_enum(flavor)
        self.pack_opaque(stuff)

    def pack_auth_unix(self, stamp: int, machinename: str, uid: int, gid: int, gids: list[int]) -> None:
        '''
        Pack unix authentication information.

        Parameters:
            stamp           timestamp
            machinename     the machinename
            uid             the userid
            gid             the group id
            gids            associated groups

        Returns:
            None
        '''
        self.pack_uint(stamp)
        self.pack_string(machinename)
        self.pack_uint(uid)
        self.pack_uint(gid)
        self.pack_uint(len(gids))
        for i in gids:
            self.pack_uint(i)

    def pack_callheader(self, xid: int, prog: int, vers: int, proc: int, cred: tuple, verf: tuple) -> None:
        '''
        Pack the header information for an RPC call.

        Parameters:
            xid
            prog            interface number to call
            vers            interface version to call
            proc            procedure number to call
            cred            credebtials to use for the call
            verf            verifier to use for the call

        Returns:
            None
        '''
        self.pack_uint(xid)
        self.pack_enum(CALL)
        self.pack_uint(RPCVERSION)
        self.pack_uint(prog)
        self.pack_uint(vers)
        self.pack_uint(proc)
        self.pack_auth(cred)
        self.pack_auth(verf)

    def pack_raw(self, data: bytes) -> None:
        '''
        Pack raw data to the packer.

        Parameters:
            data            data to write to the packer

        Returns:
            None
        '''
        self.__buf.write(data)


class Unpacker(xdrlib.Unpacker):
    '''
    Unpacker extends xdrlib.Unpacker and adds relevant methods for unpackaging RPC packets.
    '''

    def unpack_auth(self) -> tuple:
        '''
        Unpack authentication information from the unpacker. Return the authentication
        type and data as tuple.

        Parameters:
            None

        Returns:
            tuple           authentication type and data
        '''
        flavor = self.unpack_enum()
        stuff = self.unpack_opaque()
        return (flavor, stuff)

    def unpack_callheader(self) -> tuple[int, int, int, int, tuple, tuple]:
        '''
        Unpack a call header and return relevant call data as tuple.

        Parameters:
            None

        Returns:
            tuple           tuple containing the relevant call data
        '''
        xid = self.unpack_uint()
        temp = self.unpack_enum()

        if temp != CALL:
            raise RPCBadFormat(f'no CALL but {temp}')

        temp = self.unpack_uint()
        if temp != RPCVERSION:
            raise RPCBadVersion(f'bad RPC version {temp}')

        prog = self.unpack_uint()
        vers = self.unpack_uint()
        proc = self.unpack_uint()
        cred = self.unpack_auth()
        verf = self.unpack_auth()

        return xid, prog, vers, proc, cred, verf

    def unpack_replyheader(self) -> tuple[int, tuple]:
        '''
        Unpack a reply header and return the xid and the verifier.

        Parameters:
            None

        Returns:
            tuple           tuple containing the xid and the verifier
        '''
        xid = self.unpack_uint()
        mtype = self.unpack_enum()

        if mtype != REPLY:
            raise RPCUnpackError(f'no REPLY but {mtype}')

        stat = self.unpack_enum()
        self.process_message_type(stat)

        verf = self.unpack_auth()
        stat = self.unpack_enum()

        if stat == SUCCESS:
            return xid, verf

        else:
            self.process_result_type(stat)

    def process_message_type(self, stat: int) -> None:
        '''
        Check whether the packed response contains either MSG_ACCEPTED or
        MSG_DENIED.

        Parameters:
            stat            unpacked data

        Returns:
            None
        '''
        if stat == MSG_DENIED:

            stat = self.unpack_enum()
            if stat == RPC_MISMATCH:
                low = self.unpack_uint()
                high = self.unpack_uint()
                raise RPCUnpackError(f'MSG_DENIED: RPC_MISMATCH: {low}, {high}')

            if stat == AUTH_ERROR:
                stat = self.unpack_uint()
                raise RPCUnpackError(f'MSG_DENIED: AUTH_ERROR: {stat}')

            raise RPCUnpackError(f'MSG_DENIED: {stat}')

        if stat != MSG_ACCEPTED:
            raise RPCUnpackError(f'Neither MSG_DENIED nor MSG_ACCEPTED: {stat}')

    def process_result_type(self, stat: int) -> None:
        '''
        Check whether the packed response contains any other errors.

        Parameters:
            stat            unpacked data

        Returns:
            None
        '''
        if stat == PROG_UNAVAIL:
            raise RPCUnpackError('call failed: PROG_UNAVAIL')

        elif stat == PROG_MISMATCH:
            low = self.unpack_uint()
            high = self.unpack_uint()
            raise RPCUnpackError(f'call failed: PROG_MISMATCH: {low}, {high}')

        elif stat == GARBAGE_ARGS:
            raise RPCGarbageArgs

        raise RPCUnpackError(f'call failed: {stat}')


class Call:
    '''
    The Call class represents a single RPC call. It contains the
    underlying packer and unpacker for the call and should be used
    to pack arguments and to obtainr results.

    The Call class is only used by RPC clients, whereas RPC servers
    access the Packer and Unpacker classes directly.
    '''

    def __init__(self, xid: int, prog: int, vers: int, proc: int, cred: tuple = None, verf: tuple = None) -> None:
        '''
        Initializes the call with the required data.

        Parameters:
            xid         the current xid of the client
            prog        the program number targeted by the call
            vers        the program version targeted by the call
            proc        the procedure number targeted by the call
            cred        optional credentials to use during the call
            verf        optional verifier to use during the call

        Returns:
            None
        '''
        self.xid = xid

        self.prog = prog
        self.vers = vers
        self.proc = proc

        self.packer = Packer()
        self.unpacker = Unpacker('')

        self.cred = cred if cred else (AUTH_NULL, make_auth_null())
        self.verf = verf if verf else (AUTH_NULL, make_auth_null())

        self.packer.pack_callheader(xid, prog, vers, proc, self.cred, self.verf)

    def set_reply(self, reply: bytes) -> bool:
        '''
        Set the RPC reply for the call. This function verifies whether the
        reply contains matching xid for the call and returns true if this is
        the case. False is returned otherwise.
        '''
        self.unpacker.reset(reply)
        xid, verf = self.unpacker.unpack_replyheader()

        if xid == self.xid:
            return True

        else:
            self.unpacker.reset('')
            return False

    def pack(self, arg: sunrpc.types.RpcType):
        '''
        Add a new argument to the call. The argument should be an RpcType that
        contains a value.

        Parameters:
            arg         the argument to add

        Returns:
            None
        '''
        arg.pack(self.packer)

    def pack_all(self, args: list[sunrpc.types.RpcType]):
        '''
        Add a new arguments to the call. The arguments should be RpcTypes that
        contain a value.

        Parameters:
            args        the arguments to add

        Returns:
            None
        '''
        for arg in args:
            arg.pack(self.packer)

    def pack_raw(self, data: bytes):
        '''
        Put raw data into the packer.

        Parameters:
            data        data to put into the packer

        Returns:
            None
        '''
        self.packer.pack_raw(data)

    def unpack(self, ret: sunrpc.types.RpcType) -> Any:
        '''
        Unpack a value from the unpacker. This function takes an RpcType and returns
        the associated value obtained from the unpacker.

        Parameters:
            rets        expected type to unpack

        Returns:
            value       the unpacked value
        '''
        return ret.unpack(self.unpacker)

    def unpack_all(self, rets: list[sunrpc.types.RpcType]) -> list[Any]:
        '''
        Unpack values from the unpacker. This function takes a list of RpcTypes
        and returns an associated list of arguments obtained from the unpacker.

        Parameters:
            rets        list of expected RpcTypes

        Returns:
            list        list of unpacked types
        '''
        result = []
        for ret in rets:
            obj = ret()
            item = obj.unpack(self.unpacker)
            result.append(item)

        return result

    def bytes(self) -> bytes:
        '''
        Return the current packer buffer as bytes.

        Parameters:
            None

        Returns:
            bytes       current packer buffer
        '''
        return self.packer.get_buffer()

    def ubytes(self) -> bytes:
        '''
        Return the current unpacker buffer as bytes.

        Parameters:
            None

        Returns:
            bytes       current packer buffer
        '''
        return self.unpacker.get_buffer()
