import asyncio
from dataclasses import dataclass, field
from serial_asyncio import open_serial_connection
from .base import StreamMedia

BAUD_RATE: str = "9600"


@dataclass
class Serial(StreamMedia):
    port: str = "COM3"
    baudrate: str = "9600"
    to_recv: float = 5.0
    to_close: float = 3.0
    to_drain: float = 2.0

    def __repr__(self) -> str:
        params: list[str] = [F"port='{self.port}'"]
        if self.baudrate != BAUD_RATE:
            params.append(F"baudrate={self.baudrate}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    async def open(self) -> None:
        """ coroutine start """
        self._reader, self._writer = await open_serial_connection(
            url=self.port,
            baudrate=self.baudrate)

    async def close(self) -> None:
        await asyncio.sleep(.1)  # need delay before close writer
        await super(Serial, self).close()

    def __str__(self) -> str:
        return F"{self.port},{self.baudrate}"


@dataclass
class RS485(Serial):
    lock: asyncio.Lock = field(init=False, default=asyncio.Lock())

    def __new__(cls,
                port: str,
                baudrate: str = "9600") -> "RS485":
        if port not in medias:
            new = RS485(port, baudrate)
            medias[port] = SerialConnector(new, 0)
            # medias[port][0].alien_frames = list()
        else:
            pass
        return medias[port].instance

    async def open(self) -> None:
        if medias[self.port].n_connected == 0:  # no one connected
            await super().open()
        else:
            print("already open:", medias)
        medias[self.port].n_connected += 1

    async def close(self) -> None:
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
