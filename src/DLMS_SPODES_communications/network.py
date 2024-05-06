import asyncio
from enum import Enum
import socket
from .base import Base, StreamBase


class Network(Base):
    """only TCP"""
    host_name: str | None
    port: int
    is_server: bool
    eop: bytes | None
    __sock: socket.socket | None

    def __init__(self,
                 host: str = None,
                 port: int = 0,
                 inactivity_timeout: int = 120):
        """host : Host name.
        port : Client port number. """
        super().__init__(inactivity_timeout)
        self.host_name = host
        self.port = port
        self.__sock = None
        self.eop = b'\x7e'  # old values None
        """ Used end of packet """

    def __repr__(self):
        params: list[str] = [F"host='{self.host_name}', port={self.port}"]
        if self.inactivity_timeout != self.INACTIVITY_TIMEOUT_DEFAULT:
            params.append(F"inactivity_timeout={self.inactivity_timeout}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    def send(self, data: bytes, receiver=None):
        if not self.__sock:
            raise Exception("Invalid connection.")
        self.__sock.sendall(data)

    def receive(self, buf: bytearray) -> bool:
        try:
            while True:
                buf.extend(self.__sock.recv(1000))
                if buf[-1:] == b"\x7e" and len(buf) > 1:
                    return True
        except TimeoutError:
            return False

    def open(self):
        """Opens the connection. Protocol, Port and HostName must be set, before calling the Open method."""
        self.__sock = socket.create_connection(
            address=(self.host_name, self.port),
            timeout=self.inactivity_timeout
        )

    def close(self):
        if self.__sock:
            self.__sock.shutdown(socket.SHUT_RDWR)
            self.__sock.close()
            self.__sock = None

    def is_open(self):
        if self.__sock and self.__sock.fileno() != -1:
            return True
        else:
            return False

    def __str__(self):
        return F'{self.__class__.__name__} {self.host_name}:{self.port}'


class TagsName(Enum):
    ADDRESS = 'address'
    PORT = 'port'


class AsyncNetwork(StreamBase):

    def __init__(self,
                 host: str = None,
                 port: int = 0,
                 inactivity_timeout: int = 120):
        """host : Host name.
        port : Client port number. """
        super().__init__(inactivity_timeout)
        self.host_name = host
        self.port = port

    def __repr__(self):
        params: list[str] = [F"host='{self.host_name}', port={self.port}"]
        if self.inactivity_timeout != self.INACTIVITY_TIMEOUT_DEFAULT:
            params.append(F"inactivity_timeout={self.inactivity_timeout}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    async def open(self):
        """ coroutine start """
        self.reader, self.writer = await asyncio.open_connection(
            host=self.host_name,
            port=self.port)

    def __str__(self):
        return F"{self.host_name}:{self.port}"
