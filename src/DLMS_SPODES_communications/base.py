from typing import Protocol
from dataclasses import dataclass, field
from contextlib import suppress
import asyncio
from StructResult import result


@dataclass
class Media(Protocol):
    recv_size: int = field(default=0xffff, init=False)
    to_connection: float
    to_recv: float
    to_close: float
    to_drain: float

    async def open(self) -> result.Ok | result.Error: ...

    def is_open(self) -> bool: ...

    async def close(self) -> None: ...

    async def send(self, data: bytes) -> None: ...

    async def receive(self, buf: bytearray) -> bool: ...


class StreamMedia(Media, Protocol):
    _reader: asyncio.StreamReader
    _writer: asyncio.StreamWriter

    def is_open(self) -> bool:
        return (
            hasattr(self, "_writer")
            and not self._writer.is_closing()
        )

    async def close(self) -> None:
        if not hasattr(self, "_writer"):
            return
        if not self._writer.is_closing():
            self._writer.close()
            with suppress(asyncio.TimeoutError, ConnectionError):
                await asyncio.wait_for(self._writer.wait_closed(), timeout=self.to_close)

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
