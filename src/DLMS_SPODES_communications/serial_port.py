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

    async def close(self) -> None:
        await asyncio.sleep(.1)  # need delay before close writer
        await super(Serial, self).close()

    def __str__(self) -> str:
        return F"{self.port},{self.baudrate}"


@dataclass
class RS485(Serial):
    lock: asyncio.Lock = field(init=False, default=asyncio.Lock())

    async def open(self) -> result.SimpleOrError[float]:
        async with self.lock:
            if medias[self.port].n_connected == 0:  # no one connected
                return await super().open()
            medias[self.port].n_connected += 1
        return result.Simple(0.0).append_e(ValueError("already open"))

    async def close(self) -> None:
        async with self.lock:
            if medias[self.port].n_connected <= 1:  # one connected
                await super().close()
            else:
                print("has more one opened:", medias)
            medias[self.port].n_connected -= 1

    async def send(self, data: bytes) -> None:
        await self.lock.acquire()
        await super().send(data)

    async def receive(self, buf: bytearray) -> bool:
        res = await super(RS485, self).receive(buf)
        self.lock.release()
        return res


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
