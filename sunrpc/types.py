from __future__ import annotations

from xdrlib import Packer, Unpacker
from typing import Any, Callable
from functools import partial


def raise_helper(exception: Exception):
    '''
    Helper function to raise exceptions from lambda.
    '''
    raise exception


class RpcType:
    '''
    Parent type for all RpcTypes. Each type is expected to store its packer and unpacker
    function within the packer_func and unpacker_func properties.
    '''
    packer_func = lambda x: raise_helper(NotImplementedError('Not implemented for RpcType'))
    unpacker_func = lambda x: raise_helper(NotImplementedError('Not implemented for RpcType'))

    def __init__(self) -> None:
        '''
        RpcType is abstract and never contains a value.
        '''
        self.value = None

    def post_processing(self, value: Any) -> Any:
        '''
        A post processing function can be defined by RpcTypes and is called after unpacking
        This is e.g. used to decode bytes to str when using the RpcString type.
        '''
        return value

    def pack(self, packer: Packer) -> None:
        '''
        When calling pack, the currently defined packer_func is used on the specified packer.
        '''
        self.__class__.packer_func(packer, self.value)

    def unpack(self, unpacker: Unpacker) -> Any:
        '''
        When calling unpack, the currently defined unpacker_func is used on the specified unpacker.
        '''
        value = self.__class__.unpacker_func(unpacker)
        return self.post_processing(value)


class RpcInt(RpcType):
    '''
    RpcInt type.
    '''
    packer_func = Packer.pack_int
    unpacker_func = Unpacker.unpack_int

    def __init__(self, value: int = None) -> None:
        '''
        Initialize the RpcInt type.

        Parameters:
            value           integer value

        Return:
            None
        '''
        if value and type(value) != int:
            raise ValueError('RpcInt needs to be initialized as integer')

        self.value = value


class RpcUInt(RpcType):
    '''
    RpcUInt type.
    '''
    packer_func = Packer.pack_uint
    unpacker_func = Unpacker.unpack_uint

    def __init__(self, value: int = None) -> None:
        '''
        Initialize the RpcUInt type.

        Parameters:
            value           integer value

        Return:
            None
        '''
        if value and type(value) != int:
            raise ValueError('RpcUInt needs to be initialized as integer')

        self.value = value


class RpcBool(RpcType):
    '''
    RpcBool type.
    '''
    packer_func = Packer.pack_bool
    unpacker_func = Unpacker.unpack_bool

    def __init__(self, value: bool = None) -> None:
        '''
        Initialize the RpcBool type.

        Parameters:
            value           boolean value

        Return:
            None
        '''
        if value and type(value) != bool:
            raise ValueError('RpcBool needs to be initialized as boolean')

        self.value = value


class RpcFloat(RpcType):
    '''
    RpcFloat type.
    '''
    packer_func = Packer.pack_float
    unpacker_func = Unpacker.unpack_float

    def __init__(self, value: float = None) -> None:
        '''
        Initialize the RpcFloat type.

        Parameters:
            value           float value

        Return:
            None
        '''
        if type(value) != float:
            raise ValueError('RpcFloat needs to be initialized as float')

        self.value = value


class RpcDouble(RpcType):
    '''
    RpcDouble type.
    '''
    packer_func = Packer.pack_double
    unpacker_func = Unpacker.unpack_double

    def __init__(self, value: float = None) -> None:
        '''
        Initialize the RpcDouble type.

        Parameters:
            value           float value

        Return:
            None
        '''
        if type(value) != float:
            raise ValueError('RpcDouble needs to be initialized as float')

        self.value = value


class RpcStr(RpcType):
    '''
    RpcStr type.
    '''
    packer_func = Packer.pack_string
    unpacker_func = Unpacker.unpack_string

    def __init__(self, value: str = None) -> None:
        '''
        Initialize the RpcStr type.

        Parameters:
            value           string value

        Return:
            None
        '''
        if value:
            if type(value) != str:
                raise ValueError('RpcStr needs to be initialized as string')

            self.value = value.encode()

        else:
            self.value = value

    def post_processing(self, value):
        '''
        '''
        return value.decode()


class RpcBytes(RpcType):
    '''
    RpcBytes type.
    '''
    packer_func = Packer.pack_bytes
    unpacker_func = Unpacker.unpack_bytes

    def __init__(self, value: bytes = None) -> None:
        '''
        Initialize the RpcBytes type.

        Parameters:
            value           bytes value

        Return:
            None
        '''
        if value and type(value) != bytes:
            raise ValueError('RpcBytes needs to be initialized as bytes')

        self.value = value


def RpcFString(length: int) -> type:
    '''
    Create the type for an RpcFString object. The type needs to be created with
    an explicit length.
    '''
    class RpcFStringType(RpcType):
        '''
        RpcFString type.
        '''
        packer_func = lambda x, y: Packer.pack_fstring(x, length, y)
        unpacker_func = lambda x: Unpacker.unpack_fstring(x, length)

        def __init__(self, value: str = None) -> None:
            '''
            Initialize the RpcFString type.

            Parameters:
                value           string value

            Return:
                None
            '''
            if value:

                if type(value) != str:
                    raise ValueError('RpcFString needs to be initialized as string')

                if len(value) != length:
                    raise ValueError('RpcFString with incorrect length')

                self.value = value.decode()

            self.value = value

    return RpcFStringType


def RpcFBytes(length: int) -> type:
    '''
    Create the type for an RpcFString object. The type needs to be created with
    an explicit length.
    '''
    class RpcFBytesType(RpcType):
        '''
        RpcFBytes type.
        '''
        packer_func = lambda x, y: Packer.pack_fstring(x, length, y)
        unpacker_func = lambda x: Unpacker.unpack_fstring(x, length)

        def __init__(self, value: bytes = None) -> None:
            '''
            Initialize the RpcFBytes type.

            Parameters:
                value           string value

            Return:
                None
            '''
            if value:

                if type(value) != bytes:
                    raise ValueError('RpcFBytes needs to be initialized as bytes')

                if len(value) != length:
                    raise ValueError('RpcFBytes with incorrect length')

            self.value = value

    return RpcFBytesType


def RpcList(inner_type: RpcType):
    '''
    Create the type for an RpcList object. The RpcListType needs to know the inner type
    it contains and this information is required during creation.
    '''
    class RpcListType(RpcType):
        '''
        RpcList type.
        '''
        packer_func = lambda x, y: Packer.pack_list(x, y, partial(inner_type.packer_func, x))
        unpacker_func = lambda x: Unpacker.unpack_list(x, partial(inner_type.unpacker_func, x))

        def __init__(self, value: Any = None) -> Callable:
            '''
            Initialize the RpcList type.

            Parameters:
                value           list value

            Return:
                None
            '''
            if value:

                if type(value) != list:
                    raise ValueError('RpcList needs to be initialized as list')

                inner_type = type(value[0])
                for item in value:

                    if type(item) != inner_type:
                        raise ValueError('RpcList needs to be homogeneous')

            self.value = value

    return RpcListType


def RpcArray(inner_type: RpcType):
    '''
    Create the type for an RpcArray object. The RpcArrayType needs to know the inner type
    it contains and this information is required during creation.
    '''
    class RpcArrayType(RpcType):
        '''
        RpcArray type.
        '''
        packer_func = lambda x, y: Packer.pack_array(x, y, partial(inner_type.packer_func, x))
        unpacker_func = lambda x: Unpacker.unpack_array(x, partial(inner_type.unpacker_func, x))

        def __init__(self, value: list = None) -> None:
            '''
            Initialize the RpcArray type.

            Parameters:
                value           list value

            Return:
                None
            '''
            if value:

                if type(value) != list:
                    raise ValueError('RpcArray needs to be initialized as list')

                inner_type = type(value[0])
                for item in value:

                    if type(item) != inner_type:
                        raise ValueError('RpcArray needs to be homogeneous')

            self.value = value

    return RpcArrayType


def RpcFArray(inner_type: RpcType, length: int):
    '''
    Create the type for an RpcFArray object. The RpcFArrayType needs to know the inner type
    it contains and its length. This information is required during creation.
    '''
    class RpcFArrayType(RpcType):
        '''
        RpcFArray type.
        '''
        packer_func = lambda x, y: Packer.pack_farray(x, length, y, partial(inner_type.packer_func, x))
        unpacker_func = lambda x: Unpacker.unpack_farray(x, length, partial(inner_type.unpacker_func, x))

        def __init__(self, value: list = None) -> None:
            '''
            Initialize the RpcFArray type.

            Parameters:
                value           list value

            Return:
                None
            '''
            if value:

                if type(value) != list:
                    raise ValueError('RpcFArray needs to be initialized as list')

                if len(value) != length:
                    raise ValueError('RpcFArray with incorrect length')

                itype = type(value[0])
                for item in value:

                    if type(item) != itype:
                        raise ValueError('RpcList needs to be homogeneous')

            self.value = value

    return RpcFArrayType
