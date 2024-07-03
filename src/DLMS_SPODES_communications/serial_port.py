import asyncio
from dataclasses import dataclass, field
from serial_asyncio import open_serial_connection
from .base import StreamBase

BAUD_RATE: int = 9600


@dataclass
class Serial(StreamBase):
    port: str = "COM3"
    baudrate: int = 9600

    def __repr__(self):
        params: list[str] = [F"port='{self.port}'"]
        if self.baudrate != BAUD_RATE:
            params.append(F"baudrate={self.baudrate}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    async def open(self):
        """ coroutine start """
        self.reader, self.writer = await open_serial_connection(
            url=self.port,
            baudrate=self.baudrate)

    async def close(self):
        await asyncio.sleep(.1)  # need delay before close writer
        await super(Serial, self).close()

    def __str__(self):
        return F"{self.port},{self.baudrate}"


@dataclass
class RS485(Serial):
    lock: asyncio.Lock = field(init=False, default=asyncio.Lock())

    def __new__(cls,
                port: str,
                baudrate: int = 9600):
        if port not in medias.keys():
            new = super().__new__(cls)
            medias[port] = SerialConnector(new, 0)
            # medias[port][0].alien_frames = list()
        else:
            pass
        return medias[port].instance

    async def open(self):
        if medias[self.port].n_connected == 0:  # no one connected
            await super().open()
        else:
            print('already open:', medias)
        medias[self.port].n_connected += 1

    async def close(self):
        if medias[self.port].n_connected <= 1:  # one connected
            await super().close()
        else:
            print('has more one opened:', medias)
        medias[self.port].n_connected -= 1

    async def send(self, data: bytes, receiver=None):
        await self.lock.acquire()
        await super().send(data, receiver)

    async def receive(self, buf: bytearray):
        await super(RS485, self).receive(buf)
        self.lock.release()


@dataclass
class SerialConnector:
    instance: RS485
    n_connected: int


medias: dict[str, SerialConnector] = dict()


