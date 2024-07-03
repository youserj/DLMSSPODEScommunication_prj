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
    reader: asyncio.StreamReader | None = field(init=False, default=None)
    writer: asyncio.StreamWriter | None = field(init=False, default=None)

    def is_open(self):
        if self.writer:
            return not self.writer.is_closing()
        else:
            return False

    async def close(self):
        if not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()

    async def send(self, data: bytes, receiver=None):
        if not self.writer:
            raise Exception("Invalid connection.")
        await self.writer.drain()
        self.writer.write(data)

    async def receive(self, buf: bytearray):
        while True:
            buf.extend(await self.reader.read(self.recv_size))
            if buf[-1:] == b"\x7e" and len(buf) > 1:
                return
            await asyncio.sleep(.000001)
