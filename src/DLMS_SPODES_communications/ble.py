import asyncio
import os
import bleak
from StructResult import result

from .base import Media
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends import characteristic
from bleak import exc
if os.name == "nt":
    from winrt.windows.devices.bluetooth.genericattributeprofile import GattCharacteristicProperties, GattCharacteristic
    # ruff: noqa: F401
    import winrt.windows.foundation.collections  # use for pyinstaller
elif os.name == "posix":
    """skip, not available"""


DISCOVERY_TIMEOUT_DEFAULT: float = 10.0
"""in sec"""


class BLEKPZ(Media):
    """KPZ implemented"""
    DLMS_SERVICE_UUID: str = "0000ffe5-0000-1000-8000-00805f9b34fb"
    DLMS_RECV_BUF_UUID: str = "0000fff4-0000-1000-8000-00805f9b34fb"
    DLMS_SEND_BUF_UUID: str = "0000fff5-0000-1000-8000-00805f9b34fb"
    DLMS_READY_UUID: str = "0000ffe0-0000-1000-8000-00805f9b34fb"
    SEND_BUF_SIZE: int = 20
    SEND_BUF_SIZE_OLD: int = 1
    READY_OK: bytes = b"\x01"
    _client: bleak.BleakClient
    __send_buf: bytearray
    __chunk_is_send: asyncio.Event
    __send_buf_uuid: str
    OCTET_TIMEOUT_DEFAULT: float = 1.0
    """in sec"""
    addr: str

    def __init__(self,
                 addr: str,
                 to_connection: float = DISCOVERY_TIMEOUT_DEFAULT) -> None:
        """ address: bluetooth mac address.
        port : Client port number. """
        self.addr = addr
        """bluetooth mac address"""
        self.to_connection = to_connection
        self._octet_timeout = self.OCTET_TIMEOUT_DEFAULT

    async def __connect(self) -> None:
        self.__chunk_is_send = asyncio.Event()
        """send buffer locker"""
        self._client = bleak.BleakClient(
            address_or_ble_device=self.addr,
            timeout=self.to_connection,
            # winrt=dict(use_cached_services=True)
        )
        await self._client.connect()
        self._recv_buff = bytearray()
        self.__send_buf = bytearray()
        """ initiate buffer for send to server"""
        self._buf_locker = asyncio.Lock()

    async def open(self) -> result.Ok | result.Error:
        async def put_recv_buf(_sender: characteristic.BleakGATTCharacteristic, data: bytearray) -> None:
            async with self._buf_locker:
                self._recv_buff.extend(data)

        def ready_handle(_sender: characteristic.BleakGATTCharacteristic, ack: bytearray) -> None:
            if ack == self.READY_OK:
                self.__chunk_is_send.set()
            else:
                raise ConnectionError(F"got {ack=!r}, expected {self.READY_OK!r}")

        try:
            async with asyncio.timeout(self.to_connection):
                await self.__connect()
        except TimeoutError as e:
            return result.Error.from_e(e)
        # search necessary services
        uuid_services: tuple[str, ...] = tuple(s.uuid for s in self._client.services)
        if self.DLMS_SERVICE_UUID in uuid_services:
            self.__send_buf_uuid = self.DLMS_SEND_BUF_UUID
            await self._client.start_notify(
                char_specifier=self.DLMS_RECV_BUF_UUID,
                callback=put_recv_buf)
            await self._client.start_notify(
                char_specifier=self.DLMS_READY_UUID,
                callback=ready_handle)
            self._recv_buff.clear()
            return result.OK
        await self.close()
        return result.Error.from_e(AttributeError("not find <UUID services>"))

    def is_open(self) -> bool:
        return (
            hasattr(self, "_client")
            and self._client.is_connected
        )

    async def close(self) -> None:
        """close connection with blocking until close ble session"""
        await self._client.disconnect()

    def __repr__(self) -> str:
        params: list[str] = [F"addr='{self._client.address}'"]
        if self.to_connection != DISCOVERY_TIMEOUT_DEFAULT:
            params.append(F"to_connection={self.to_connection}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    def __str__(self) -> str:
        return F"{self.addr}"

    async def receive(self, buf: bytearray) -> bool:
        while True:
            if self._recv_buff[-1:] == b"\x7e" and len(self._recv_buff) > 1:
                async with self._buf_locker:
                    buf.extend(self._recv_buff)
                    self._recv_buff.clear()
                return True
            await asyncio.sleep(.000001)

    async def __send_chunk(self, data: bytes) -> None:
        # print(F"SEND: {data}")
        await self._client.write_gatt_char(self.__send_buf_uuid, data, response=True)
        await self.__chunk_is_send.wait()

    async def send(self, data: bytes) -> None:
        """"""
        if not self._client.is_connected:
            raise ConnectionError("BLE no connection")
        # TODO: add notification, see in GXNet.py
        pos: int = 0
        while c_data := data[pos: pos + self.SEND_BUF_SIZE]:
            self.__chunk_is_send.clear()
            await asyncio.wait_for(
                fut=self.__send_chunk(c_data),
                timeout=self._octet_timeout)
            pos += self.SEND_BUF_SIZE

    @classmethod
    async def search(cls, timeout: int) -> dict[str, tuple[BLEDevice, AdvertisementData]]:
        scaner = bleak.BleakScanner()
        return await scaner.discover(
            timeout=timeout,
            return_adv=True
        )

    async def get_characteristics(self) -> dict[str, bytearray]:
        """todo: need refactoring with translate exception to outside"""
        ret: dict[str, bytearray] = {}
        await self.__connect()
        try:
            for s in self._client.services:
                for chc in s.characteristics:
                    gatt_c: GattCharacteristic = chc.obj
                    if gatt_c.characteristic_properties == GattCharacteristicProperties.READ:
                        try:
                            c_data = await self._client.read_gatt_char(chc)
                        except Exception as e:
                            c_data = e.args[0]
                        finally:
                            ret[chc.description] = c_data
        except exc.BleakError:
            """services has not been"""
        finally:
            await self._client.disconnect()
        return ret
