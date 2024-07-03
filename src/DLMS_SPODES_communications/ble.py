import asyncio
import bleak
from .base import Media
from netaddr import EUI, mac_unix_expanded
from bleak.backends.bluezdbus.defs import GATT_CHARACTERISTIC_INTERFACE
from bleak.backends.winrt.client import GattCharacteristicProperties, GattCharacteristic


class BLEKPZ(Media):
    """KPZ implemented"""
    HDLC_FLAG = b"\x7E"
    DLMS_SERVICE_UUID: str = "0000ffe5-0000-1000-8000-00805f9b34fb"
    DLMS_RECV_BUF_UUID: str = "0000fff4-0000-1000-8000-00805f9b34fb"
    DLMS_SEND_BUF_UUID: str = "0000fff5-0000-1000-8000-00805f9b34fb"
    DLMS_READY_UUID: str = "0000ffe0-0000-1000-8000-00805f9b34fb"
    SEND_BUF_SIZE: int = 20
    SEND_BUF_SIZE_OLD: int = 1
    READY_OK: bytes = b'\x01'
    __addr: EUI
    __client: bleak.BleakClient = None
    __send_buf: bytearray
    __chunk_is_send: asyncio.Event
    __send_buf_uuid: str
    DISCOVERY_TIMEOUT_DEFAULT: int = 10
    """in sec"""
    OCTET_TIMEOUT_DEFAULT: float = 1.0
    """in sec"""

    def __init__(self,
                 address: str | EUI = None,
                 discovery_timeout: int = 10):
        """ address: bluetooth mac address.
        port : Client port number. """
        self.__addr = EUI(address)
        """bluetooth mac address"""
        self.__addr.dialect = mac_unix_expanded  # for representation
        self.discovery_timeout = discovery_timeout
        self.octet_timeout = self.OCTET_TIMEOUT_DEFAULT

    async def __connect(self):
        self.__chunk_is_send = asyncio.Event()
        """send buffer locker"""
        self.__client = bleak.BleakClient(
            address_or_ble_device=str(self.__addr),
            timeout=self.discovery_timeout,
            winrt=dict(use_cached_services=True))
        await self.__client.connect()
        self.recv_buff = bytearray()
        self.__send_buf = bytearray()
        """ initiate buffer for send to server"""
        self.buf_locker = asyncio.Lock()

    async def open(self):
        async def put_recv_buf(sender: GATT_CHARACTERISTIC_INTERFACE, data: bytearray):
            async with self.buf_locker:
                self.recv_buff.extend(data)

        def ready_handle(sender: GATT_CHARACTERISTIC_INTERFACE, ack: bytearray):
            if ack == self.READY_OK:
                self.__chunk_is_send.set()
            else:
                raise ConnectionError(F"got {ack=}, expected {self.READY_OK}")

        await self.__connect()
        # search necessary services
        uuid_services: tuple[str] = tuple(s.uuid for s in self.__client.services)
        if self.DLMS_SERVICE_UUID in uuid_services:
            self.__send_buf_uuid = self.DLMS_SEND_BUF_UUID
            await self.__client.start_notify(
                char_specifier=self.DLMS_RECV_BUF_UUID,
                callback=put_recv_buf)
            await self.__client.start_notify(
                char_specifier=self.DLMS_READY_UUID,
                callback=ready_handle)
        else:
            await self.close()
        self.recv_buff.clear()

    def is_open(self):
        if self.__client and self.__client.is_connected:
            return True
        else:
            return False

    async def close(self):
        """close connection with blocking until close ble session"""
        await self.__client.disconnect()

    def __repr__(self):
        params: list[str] = [F"address='{self.__client.address}'"]
        if self.discovery_timeout != self.DISCOVERY_TIMEOUT_DEFAULT:
            params.append(F"discovery_timeout={self.discovery_timeout}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    def __str__(self):
        return F"{self.__addr}"

    async def receive(self, buf: bytearray):
        while True:
            if self.recv_buff[-1:] == b"\x7e" and len(self.recv_buff) > 1:
                async with self.buf_locker:
                    buf.extend(self.recv_buff)
                    self.recv_buff.clear()
                return
            await asyncio.sleep(.000001)

    async def __send_chunk(self, data: bytes):
        # print(F"SEND: {data}")
        await self.__client.write_gatt_char(self.__send_buf_uuid, data, True)
        await self.__chunk_is_send.wait()

    async def send(self, data: bytes, receiver=None):
        """"""
        if not self.__client.is_connected:
            raise ConnectionError("BLE no connection")
        # TODO: add notification, see in GXNet.py
        else:
            pos: int = 0
            while c_data := data[pos: pos + self.SEND_BUF_SIZE]:
                self.__chunk_is_send.clear()
                await asyncio.wait_for(
                    fut=self.__send_chunk(c_data),
                    timeout=self.octet_timeout)
                pos += self.SEND_BUF_SIZE

    @classmethod
    async def search(cls, timeout: int) -> dict:
        scaner = bleak.BleakScanner()
        devices = await scaner.discover(timeout=timeout,
                                        return_adv=True)
        return devices

    async def get_characteristics(self) -> dict[str, bytes]:
        """todo: need refactoring with translate exception to outside"""
        ret: dict[str, bytes] = dict()
        await self.__connect()
        try:
            for s in self.__client.services:
                for c in s.characteristics:
                    c: bleak.BleakGATTCharacteristic
                    gatt_c: GattCharacteristic = c.obj
                    if gatt_c.characteristic_properties == GattCharacteristicProperties.READ:
                        try:
                            c_data = await self.__client.read_gatt_char(c)
                        except Exception as e:
                            c_data = e.args[0]
                        finally:
                            ret[c.description] = c_data
        except bleak.BleakError as e:
            """services has not been"""
        finally:
            await self.__client.disconnect()
        return ret
