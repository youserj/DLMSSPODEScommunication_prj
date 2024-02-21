from typing import Any
from serial_asyncio import open_serial_connection
import serial
from serial import Serial
from .base import Base, StreamBase

BAUD_RATE: int = 9600


class SerialPort(Base):

    def __init__(self,
                 port: str,
                 baudrate: int = 9600,
                 inactivity_timeout: int = 120,
                 send_timeout: int = 1):
        super(SerialPort, self).__init__(inactivity_timeout)
        self.__client = Serial(
            baudrate=baudrate,
            timeout=inactivity_timeout,
            write_timeout=send_timeout
        )
        self.__client.port = port

    @property
    def port(self):
        return self.__client.port

    @property
    def baudrate(self):
        return self.__client.baudrate

    def open(self):
        self.__client.open()

    def receive(self, buf: bytearray) -> bool:
        while True:
            buf.extend(char := self.__client.read())
            # print(F"{buf=}")
            if char == b"\x7e" and len(buf) > 1:
                return True
            elif char == b"":
                return False

    def close(self):
        self.__client.close()

    def send(self, data: bytes, receiver=None):
        self.__client.write(data)

    def __repr__(self):
        params: list[str] = [F"port='{self.__client.port}'"]
        if self.__client.baudrate != BAUD_RATE:
            params.append(F"baudrate={self.__client.baudrate}")
        if self.__client.bytesize != serial.EIGHTBITS:
            params.append(F"dataBits={self.__client.bytesize}")
        if self.inactivity_timeout != self.INACTIVITY_TIMEOUT_DEFAULT:
            params.append(F"inactivity_timeout={self.inactivity_timeout}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    def __str__(self):
        return F"{self.__class__.__name__} {self.__client.port}: {self.__client.baudrate} {self.__client.bytesize}{self.__client.parity}{self.__client.stopbits}"

    def is_open(self):
        return self.__client.is_open


class RS485(SerialPort):
    alien_frames: list[Any]

    def __new__(cls,
                port: str,
                baudrate: int = 9600,
                inactivity_timeout: int = 120):
        if port not in medias.keys():
            medias[port] = [super().__new__(cls), 0]
            medias[port][0].alien_frames = list()
        else:
            pass
        return medias[port][0]

    def open(self):
        if self.port in medias.keys():
            medias[self.port][1] += 1
            print('open:', medias)
            if medias[self.port][1] == 1:
                pass
            else:
                return
        else:
            pass
        super(RS485, self).open()

    def close(self):
        if self.port in medias.keys() and self.is_open():
            if medias[self.port][1] <= 1:
                medias.pop(self.port)
            else:
                medias[self.port][1] -= 1
                return
            print(medias)
        super(RS485, self).close()


medias: dict[str, list[RS485, int]] = dict()


class AsyncSerial(StreamBase):

    def __init__(self,
                 port: str,
                 baudrate: int = 9600,
                 inactivity_timeout: int = 120,
                 send_timeout: int = 1):
        super().__init__(inactivity_timeout)
        self.port = port
        self.baudrate = baudrate

    def __repr__(self):
        params: list[str] = [F"port='{self.port}'"]
        if self.baudrate != BAUD_RATE:
            params.append(F"baudrate={self.baudrate}")
        # if self.__client.bytesize != serial.EIGHTBITS:
        #     params.append(F"dataBits={self.__client.bytesize}")
        if self.inactivity_timeout != self.INACTIVITY_TIMEOUT_DEFAULT:
            params.append(F"inactivity_timeout={self.inactivity_timeout}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    async def open(self):
        """ coroutine start """
        self.reader, self.writer = await open_serial_connection(
            url=self.port,
            baudrate=self.baudrate)
