import asyncio
import unittest
from src.DLMS_SPODES_communications.ble import BLEKPZ
from .functools2 import open_close


class TestType(unittest.TestCase):
    m = BLEKPZ(
        addr="6C:79:B8:C4:DB:E3")

    def test_open_close(self):
        asyncio.run(open_close(self.m))

    def test_write_read(self):
        async def main(m: BLEKPZ):
            await m.open()
            print(F"{m.is_open()=}")
            data = b'~\xa0\x14\x02!!\x93u\x12\x81\x80\x07\x05\x02\x04\x00\x06\x01\xef\xcb\xb3~'
            await m.send(data)
            buf = bytearray()
            await asyncio.wait_for(
                fut=m.receive(buf),
                timeout=5)
            print(F"{buf.hex(' ')=}")
            await m.close()

        asyncio.run(main(self.m))
