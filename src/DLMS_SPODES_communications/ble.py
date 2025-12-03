import asyncio
from dataclasses import dataclass, field
from typing import ClassVar
import os
import bleak
from StructResult import result
import time
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


@dataclass
class BLEKPZ(Media):
    """KPZ implemented"""
    addr: str = "00:00:00:00:00:00"
    "mac address"
    to_connect: float = DISCOVERY_TIMEOUT_DEFAULT
    to_recv: float = 1.0
    to_close: float = 10.0
    pair: bool = False
    DLMS_SERVICE_UUID: ClassVar[str] = "0000ffe5-0000-1000-8000-00805f9b34fb"
    DLMS_RECV_BUF_UUID: ClassVar[str] = "0000fff4-0000-1000-8000-00805f9b34fb"
    DLMS_SEND_BUF_UUID: ClassVar[str] = "0000fff5-0000-1000-8000-00805f9b34fb"
    DLMS_READY_UUID: ClassVar[str] = "0000ffe0-0000-1000-8000-00805f9b34fb"
    READY_OK: ClassVar[bytes] = b"\x01"
    EOF: ClassVar[bytes] = b"\x7e"
    is_first_recv_chunk: bool = True
    _client: bleak.BleakClient = field(init=False)
    __chunk_is_send: asyncio.Event = field(init=False)
    __c_send: characteristic.BleakGATTCharacteristic = field(init=False)

    async def __connect(self) -> None:
        self.__chunk_is_send = asyncio.Event()
        """send buffer locker"""
        self._client = bleak.BleakClient(
            address_or_ble_device=self.addr,
            services=(self.DLMS_SERVICE_UUID,),
            timeout=self.to_connect,
            pair=self.pair,
            # winrt=dict(use_cached_services=True)
        )
        await self._client.connect()
        self._recv_buff = bytearray()
        """ initiate buffer for send to server"""
        self._buf_locker = asyncio.Lock()
        self._eof_detected = asyncio.Event()

    async def _setup_notifications(self) -> result.Ok | result.Error:
        async def put_recv_buf(_sender: characteristic.BleakGATTCharacteristic, data: bytearray) -> None:
            async with self._buf_locker:
                self._recv_buff.extend(data)
                if data.count(self.EOF) >= 1:
                    self._eof_detected.set()

        def ready_handle(_sender: characteristic.BleakGATTCharacteristic, ack: bytearray) -> None:
            if ack == self.READY_OK:
                self.__chunk_is_send.set()
            else:
                raise ConnectionError(F"got {ack=!r}, expected {self.READY_OK!r}")  # todo: make with message, non raise Callback

        try:
            service = self._client.services.get_service(self.DLMS_SERVICE_UUID)
        except exc.BleakError as e:
            return result.Error.from_e(e, msg="get service")
        if not service:
            return result.Error.from_e(AttributeError("not find <UUID services>"))
        self.__c_send = service.get_characteristic(self.DLMS_SEND_BUF_UUID)
        if not self.__c_send:
            return result.Error.from_e(AttributeError("not find <SEND characteristic>"))
        c_recv = service.get_characteristic(self.DLMS_RECV_BUF_UUID)
        if not c_recv:
            return result.Error.from_e(AttributeError("not find <RECV characteristic>"))
        try:
            await self._client.start_notify(
                char_specifier=c_recv,
                callback=put_recv_buf)
            c_ready = service.get_characteristic(self.DLMS_READY_UUID)
            if not c_ready:
                return result.Error.from_e(AttributeError("not find <READY characteristic>"))
            await self._client.start_notify(
                char_specifier=c_ready,
                callback=ready_handle)
            return result.OK
        except Exception as e:
            return result.Error.from_e(e, msg="start notify")

    async def open(self) -> result.SimpleOrError[float]:
        start = time.monotonic()
        try:
            async with asyncio.timeout(self.to_connect):
                await self.__connect()
        except (exc.BleakError, TimeoutError) as e:
            return result.Error.from_e(e)
        if isinstance(res_setup := await self._setup_notifications(), result.Error):
            await self.close()
            return res_setup
        self._recv_buff.clear()
        self._eof_detected.clear()
        return result.Simple(time.monotonic() - start)

    def is_open(self) -> bool:
        return (
            hasattr(self, "_client")
            and self._client.is_connected
        )

    async def close(self) -> result.SimpleOrError[float]:
        """close connection with blocking until close ble session"""
        start = time.monotonic()
        await self._client.disconnect()
        await asyncio.sleep(0.01)  # timeout before next connection
        return result.Simple(time.monotonic() - start)

    def __repr__(self) -> str:
        params: list[str] = [F"addr='{self._client.address}'"]
        if self.to_connect != DISCOVERY_TIMEOUT_DEFAULT:
            params.append(F"to_connect={self.to_connect}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    def __str__(self) -> str:
        return F"{self.addr}"

    async def receive(self, buf: bytearray) -> bool:
        try:
            await asyncio.wait_for(self._eof_detected.wait(), timeout=self.to_recv)
            async with self._buf_locker:
                if self._recv_buff:
                    buf.extend(self._recv_buff)
                    self._recv_buff.clear()
                    self._eof_detected.clear()
                    return True
            return False
        except TimeoutError:
            async with self._buf_locker:
                if self._recv_buff:
                    buf.extend(self._recv_buff)
                    self._recv_buff.clear()
                    self._eof_detected.clear()
                    print(f"Received partial message due to timeout: {buf.hex()}")
            return False
        
    async def end_transaction(self) -> None:
        async with self._buf_locker: 
            self._recv_buff.clear()
            self._eof_detected.clear()

    async def send(self, data: bytes) -> None:
        async def send_chunk(data: bytes) -> None:
            await self._client.write_gatt_char(self.__c_send, data, response=True)
            await self.__chunk_is_send.wait()

        if not self._client.is_connected:
            raise ConnectionError("BLE no connection")
        pos: int = 0
        while c_data := data[pos: (next_pos := pos + self.__c_send.max_write_without_response_size)]:
            self.__chunk_is_send.clear()
            await asyncio.wait_for(
                fut=send_chunk(c_data),
                timeout=self.to_recv)
            pos = next_pos

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
