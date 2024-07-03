import asyncio
import unittest
from src.DLMS_SPODES_communications.ble import BLEKPZ


class TestType(unittest.TestCase):
    def test_open_close(self):
        async def main(d: BLEKPZ):
            await d.open()
            await d.close()

        driver = BLEKPZ(
            address="6C:79:B8:C4:DB:E3")
        asyncio.run(main(driver))

    def test_write_read(self):
        async def main(d: BLEKPZ):
            await d.open()
            print(F"{driver.is_open()=}")
            data = b'~\xa0\x14\x02!!\x93u\x12\x81\x80\x07\x05\x02\x04\x00\x06\x01\xef\xcb\xb3~'
            await driver.send(data)
            buf = bytearray()
            await asyncio.wait_for(
                fut=driver.receive(buf),
                timeout=5)
            print(F"{buf.hex(' ')=}")
            await d.close()

        driver = BLEKPZ(
            address="6C:79:B8:C4:DB:E3")
        asyncio.run(main(driver))
