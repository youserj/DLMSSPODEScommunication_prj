from typing import Protocol
from dataclasses import dataclass, field
from contextlib import suppress
import asyncio
import time
from StructResult import result


@dataclass
class Media(Protocol):
    recv_size: int = field(default=0xffff, init=False)
    to_connect: float
    to_recv: float
    to_close: float

    async def open(self) -> result.SimpleOrError[float]:
        """get connection time"""

    def is_open(self) -> bool: ...

    async def close(self) ->  result.SimpleOrError[float]:
        """return disconnection time"""

    async def send(self, data: bytes) -> None: ...

    async def receive(self, buf: bytearray) -> bool: ...


class StreamMedia(Media, Protocol):
    _reader: asyncio.StreamReader
    _writer: asyncio.StreamWriter
    to_drain: float

    def is_open(self) -> bool:
        return (
            hasattr(self, "_writer")
            and not self._writer.is_closing()
        )

    async def close(self) -> result.SimpleOrError[float]:
        start = time.monotonic()
        if not hasattr(self, "_writer"):
            return result.Error.from_e(ConnectionError("no stream writer available"))
        if not self._writer.is_closing():
            self._writer.close()
            try:
                await asyncio.wait_for(self._writer.wait_closed(), timeout=self.to_close)
                # await asyncio.sleep(0.1)
            except (asyncio.TimeoutError, ConnectionError) as e:
                self._writer.transport.abort()
                return result.Error.from_e(ConnectionError("close timeout"))
        return result.Simple(time.monotonic() - start)

    async def send(self, data: bytes) -> None:
        if self._writer is None:
            raise RuntimeError("Writer not available")
        self._writer.write(data)
        try:
            await asyncio.wait_for(self._writer.drain(), timeout=self.to_drain)
        except asyncio.TimeoutError:
            raise RuntimeError(f"Drain timeout ({self.to_drain}s) exceeded")

    async def receive(self, buf: bytearray) -> bool:
        try:
            while True:
                data = await asyncio.wait_for(
                    self._reader.read(self.recv_size),
                    timeout=self.to_recv
                )
                if not data:  # EOF
                    return False
                buf.extend(data)
                if buf.endswith(b"\x7e"):
                    return True
        except asyncio.TimeoutError:
            return False
