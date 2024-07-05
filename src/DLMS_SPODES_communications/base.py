from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import asyncio


@dataclass
class Media(ABC):
    recv_size: int = field(default=0xffff, init=False)

    @abstractmethod
    async def open(self):
        """Opens the media"""

    @abstractmethod
    def is_open(self):
        """Checks if the connection is established. Returns True, if the connection is established."""

    @abstractmethod
    async def close(self):
        """close media"""

    @abstractmethod
    async def send(self, data: bytes, receiver=None):
        """send data with media"""

    @abstractmethod
    async def receive(self, buf: bytearray):
        """receive data to media"""

    @abstractmethod
    def __repr__(self):
        """return all properties for restore"""


@dataclass
class StreamMedia(Media, ABC):
    _reader: asyncio.StreamReader | None = field(init=False, default=None)
    _writer: asyncio.StreamWriter | None = field(init=False, default=None)

    def is_open(self):
        if self._writer:
            return not self._writer.is_closing()
        else:
            return False

    async def close(self):
        if not self._writer.is_closing():
            self._writer.close()
            await self._writer.wait_closed()

    async def send(self, data: bytes, receiver=None):
        if not self._writer:
            raise Exception("Invalid connection.")
        await self._writer.drain()
        self._writer.write(data)

    async def receive(self, buf: bytearray):
        while True:
            buf.extend(await self._reader.read(self.recv_size))
            if buf[-1:] == b"\x7e" and len(buf) > 1:
                return
            await asyncio.sleep(.000001)
