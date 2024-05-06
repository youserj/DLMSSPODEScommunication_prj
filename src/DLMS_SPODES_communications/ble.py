import asyncio
import time
from itertools import count
import threading
import bleak
from .base import Base
from netaddr import EUI, mac_unix_expanded
from bleak.backends.bluezdbus.defs import GATT_CHARACTERISTIC_INTERFACE
from bleak.backends.winrt.client import GattCharacteristicProperties, GattCharacteristic


class BLE(Base):
    """KPZ implemented"""
    HDLC_FLAG = b"\x7E"
    DLMS_SERVICE_UUID: str = "0000ffe5-0000-1000-8000-00805f9b34fb"
    DLMS_SERVICE_UUID_OLD: str = "0000fff0-0000-1000-8000-00805f9b34fb"
    DLMS_RECV_BUF_UUID: str = "0000fff4-0000-1000-8000-00805f9b34fb"
    DLMS_SEND_BUF_UUID: str = "0000fff5-0000-1000-8000-00805f9b34fb"
    DLMS_RECV_BUF_UUID_OLD: str = "0000fff2-0000-1000-8000-00805f9b34fb"
    DLMS_SEND_BUF_UUID_OLD: str = "0000fff3-0000-1000-8000-00805f9b34fb"
    DLMS_READY_UUID: str = "0000ffe0-0000-1000-8000-00805f9b34fb"
    SEND_BUF_SIZE: int = 20
    SEND_BUF_SIZE_OLD: int = 1
    READY_OK: bytes = b'\x01'
    __addr: EUI
    __client: bleak.BleakClient
    __send_buf: bytearray
    __close_request: bool
    __timeout_counter: count
    __lock: threading.Lock
    __chunk_is_send: asyncio.Event
    __status: list[str]
    __send_buf_uuid: str
    __CONNECTED_STATUS: str = "connected"

    def __init__(self,
                 address: str | EUI = None,
                 inactivity_timeout: int = 120,
                 octet_timeout: float = 1.0,
                 discovery_timeout: int = 10):
        """ address: bluetooth mac address.
        port : Client port number. """
        super().__init__(inactivity_timeout, octet_timeout)
        self.__addr = EUI(address)
        """bluetooth mac address"""
        self.__addr.dialect = mac_unix_expanded  # for representation
        self.__client = bleak.BleakClient(
            address_or_ble_device=str(self.__addr),
            timeout=discovery_timeout,
            winrt=dict(use_cached_services=True))
        self.__close_request = True
        """ outside request for disconnect"""
        self.__conn_lock = threading.Lock()
        """locker for connection"""
        self.__status = ["initiate, not connected"]
        """status container of messages"""
        self.discovery_timeout = discovery_timeout
        self.recv_buff = bytearray()
        """ Received bytes."""
        self.recv_event = threading.Event()
        """ Received event."""

    def __repr__(self):
        params: list[str] = [F"address='{self.__client.address}'"]
        if self.inactivity_timeout != self.INACTIVITY_TIMEOUT_DEFAULT:
            params.append(F"inactivity_timeout={self.inactivity_timeout}")
        if self.discovery_timeout != self.DISCOVERY_TIMEOUT_DEFAULT:
            params.append(F"discovery_timeout={self.discovery_timeout}")
        if self.octet_timeout != self.OCTET_TIMEOUT_DEFAULT:
            params.append(F"octet_timeout={self.octet_timeout}")
        return F"{self.__class__.__name__}({', '.join(params)})"

    def __str__(self):
        return F"{self.__client.address}"

    @property
    def client(self) -> bleak.BleakClient:
        return self.__client

    def addListener(self, listener):
        raise NotImplementedError()

    def removeListener(self, listener):
        raise NotImplementedError()

    def get_report(self) -> str:
        return F"BLE: {self.__addr}"

    async def __read_buf_handle(self, sender: GATT_CHARACTERISTIC_INTERFACE, data: bytearray):
        match sender.uuid:
            case self.DLMS_RECV_BUF_UUID:
                self.__read_buf(data)
            case _:                       print(F"unknown sender characteristic {sender}: {data=}")

    def receive(self, buf: bytearray) -> bool:
        """ Receive new data synchronously from the media. Result in p.reply. Return True if new data is received. """
        if not self.recv_event.wait(self.inactivity_timeout):  # If timeout occurred.
            buf.extend(self.recv_buff)  # for inside buffer information
            return False
        self.recv_event.clear()
        buf.extend(self.recv_buff)
        self.recv_buff.clear()
        return True

    def __read_buf(self, data: bytearray):
        # print(F"READ: {data}")  # debug
        self.recv_buff.extend(data)
        if data[-1:] == b"\x7e":
            self.recv_event.set()
        else:
            """not enough OEF"""
        # print(F"{self.recv_buff=}")  # debug

    async def __send_chunk(self, buf_size: int, response: bool = False):
        self.__send_buf, data = self.__send_buf[buf_size:], self.__send_buf[:buf_size]
        # print(F"SEND: {data}")
        await self.__client.write_gatt_char(self.__send_buf_uuid, data, response)

    def __ready_handle(self, sender: GATT_CHARACTERISTIC_INTERFACE, data: bytearray):
        match sender.uuid, bytes(data):
            case self.DLMS_READY_UUID, self.READY_OK:
                self.__chunk_is_send.set()
            case _:
                raise ConnectionError(F"unknown ready characteristic {sender}: {data=}")

    def __run_coroutine_loop(self):
        asyncio.run(self.__start_coro())

    def open(self):
        self.__conn_lock.acquire()
        threading.Thread(target=self.__run_coroutine_loop).start()
        with self.__conn_lock:
            """wait connecting"""
            time.sleep(1)
            print("lock ble conn")    # debug
        if self.__status[0] != self.__CONNECTED_STATUS:
            raise ConnectionError(self.__status)

    async def __start_raise_timer(self, delay: int | float, message: str = ""):
        await asyncio.sleep(delay)
        raise TimeoutError(message)

    async def __start_wait_response(self, task: asyncio.Task):
        await self.__chunk_is_send.wait()
        task.cancel("message was send")

    async def __connect(self):
        self.__chunk_is_send = asyncio.Event()
        """send buffer locker"""
        if self.__client.is_connected:
            self.close()
        self.__close_request = False
        try:
            await self.__client.connect()
            self.__status = [self.__CONNECTED_STATUS]
        except OSError as e:
            self.__status = ["discovery timeout"]
            return
        except bleak.exc.BleakDeviceNotFoundError as e:
            self.__status = list(e.args)
            return
        except bleak.exc.BleakError as e:
            self.__status = list(e.args)
            return
        except Exception as e:
            print(e)
            self.__status = ["unknown error"]
        finally:
            self.__conn_lock.release()
        self.__send_buf = bytearray()
        """ initiate buffer for send to server"""

    async def __start_coro(self):
        await self.__connect()
        try:
            # search necessary services
            uuid_services: tuple[str] = tuple(s.uuid for s in self.__client.services)
            if self.DLMS_SERVICE_UUID in uuid_services:
                self.__send_buf_uuid = self.DLMS_SEND_BUF_UUID
                await self.__client.start_notify(self.DLMS_RECV_BUF_UUID,
                                                 callback=self.__read_buf_handle)
                await self.__client.start_notify(self.DLMS_READY_UUID,
                                                 callback=self.__ready_handle)
                while not self.__close_request:
                    # print(F"ble send buf: {self.__send_buf.hex()}")  # debug
                    if self.__send_buf:
                        self.__chunk_is_send.clear()
                        await self.__send_chunk(self.SEND_BUF_SIZE, response=True)
                        async with asyncio.TaskGroup() as tg:
                            task_raise = tg.create_task(self.__start_raise_timer(self.octet_timeout, "octet timeout: not got BLE acknowledge from characteristic write"))
                            tg.create_task(self.__start_wait_response(task_raise))
                    else:
                        await asyncio.sleep(0.1)  # check input data every 0.1 second before exit
            elif self.DLMS_SERVICE_UUID_OLD in uuid_services:
                self.__send_buf_uuid = self.DLMS_SEND_BUF_UUID_OLD
                full_request = asyncio.Event()
                while not self.__close_request:
                    if self.__send_buf:
                        if full_request.is_set():
                            full_request.clear()
                        await self.__send_chunk(self.SEND_BUF_SIZE_OLD, response=True)
                        if not self.__send_buf:
                            full_request.set()
                        # await asyncio.sleep(.1)
                    elif full_request.is_set():
                        self.__read_buf(await self.__client.read_gatt_char(self.DLMS_RECV_BUF_UUID_OLD))
                    else:
                        await asyncio.sleep(0.1)
                        print("DUMMY WAITING")
            else:
                self.close()
                self.__status.append(F"DLMS service:{self.DLMS_SERVICE_UUID} is absence in BluetoothLE server")
            self.__status.append(F"BLE CLOSE REQUEST {' buf:' + self.recv_buff.hex(' ') if self.recv_buff else ''}")
            self.recv_buff.clear()
        except Exception as e:
            self.__status.extend(e.args)
        finally:
            await self.__client.disconnect()

    def is_open(self):
        return self.__client.is_connected

    def close(self):
        """close connection with blocking until close ble session"""
        if self.__client.is_connected:
            self.__close_request = True
            disconnect_count = count(10, -1)  # wait of disconnecting for 10 second
            while self.__client.is_connected and next(disconnect_count) != 0:
                time.sleep(1)

    def send(self, data: bytes, receiver=None):
        """"""
        if not self.__client.is_connected:
            raise Exception("BLE no connection.", *self.__status)
        # TODO: add notification, see in GXNet.py
        else:
            self.__send_buf.extend(data)

    def getSynchronous(self):
        return self.__lock

    @classmethod
    async def search(cls, timeout: int) -> dict:
        scaner = bleak.BleakScanner()
        devices = await scaner.discover(timeout=timeout,
                                        return_adv=True)
        return devices

    async def get_characteristics(self) -> dict[str, bytes]:
        """todo: need refactoring with translate exception to outside"""
        ret: dict[str, bytes] = dict()
        self.__conn_lock.acquire()
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
