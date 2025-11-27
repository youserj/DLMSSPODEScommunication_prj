import asyncio
import time
from dataclasses import dataclass, field
from serial_asyncio import open_serial_connection
from .base import StreamMedia
from StructResult import result

BAUD_RATE: str = "9600"


@dataclass
class Serial(StreamMedia):
    port: str = "COM3"
    baudrate: str = "9600"
    to_connect: float = 3.0
    to_recv: float = 5.0
    to_close: float = 3.0
    to_drain: float = 2.0

    def __repr__(self) -> str:
        params: list[str] = [F"port='{self.port}'"]
        if self.baudrate != BAUD_RATE:
            params.append(F"baudrate={self.baudrate}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    async def open(self) -> result.SimpleOrError[float]:
        """ coroutine start """
        start = time.monotonic()
        try:
            self._reader, self._writer = await open_serial_connection(
                url=self.port,
                baudrate=self.baudrate)
            return result.Simple(time.monotonic() - start)
        except Exception as e:  # todo: make with concrete Exceptions
            return result.Error.from_e(e)

    async def close(self) -> result.SimpleOrError[float]:
        await asyncio.sleep(.01)  # need delay before close writer
        return await super(Serial, self).close()

    async def end_transaction(self) -> None:
        ...

    def __str__(self) -> str:
        return F"{self.port},{self.baudrate}"


@dataclass
class RS485(Serial):
    to_line: float = 5.0
    """line timeout"""
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)
    _in_transaction: bool = field(init=False, default=False)

    async def open(self) -> result.SimpleOrError[float]:
        async with self._lock:
            if (media := medias.get(self.port)) is None:
                return result.Error.from_e(ConnectionError(f"no find media with {self.port}"))
            media.n_connected += 1
            if medias[self.port].n_connected == 1:  # first connected
                return await super().open()
        return result.Simple(0.0).append_e(ValueError("already open"))

    async def close(self) -> result.SimpleOrError[float]:
        self.end_transaction()
        async with self._lock:
            if (media := medias.get(self.port)) is None:
                return result.Error.from_e(ConnectionError(f"no find media with {self.port}"))
            media.n_connected -= 1
            if media.n_connected <= 0:  # last connected
                return await super().close()
            else:
                return result.Simple(0.0).append_e(ValueError("has more connection"))

    async def send(self, data: bytes) -> None:
        try:
            await asyncio.wait_for(self._lock.acquire(), 
                                 timeout=self.to_line)
        except asyncio.TimeoutError:
            raise RuntimeError("Cannot acquire transaction lock - timeout")
        self._in_transaction = True
        try:
            await super().send(data)
        except Exception as e:
            self._cleanup_transaction()
            raise e

    async def receive(self, buf: bytearray) -> bool:
        if not self._in_transaction:
            raise RuntimeError("Receive outside transaction")
        return await super().receive(buf)

    async def end_transaction(self) -> None:
        self._cleanup_transaction()

    def _cleanup_transaction(self) -> None:
        if self._in_transaction:
            self._in_transaction = False
            self._lock.release()


@dataclass
class SerialConnector:
    instance: RS485
    n_connected: int


medias: dict[str, SerialConnector] = {}


def register_RS485(media: RS485) -> "RS485":
    if media.port not in medias:
        medias[media.port] = SerialConnector(media, 0)
        # medias[port][0].alien_frames = []
    else:
        pass
    return medias[media.port].instance
