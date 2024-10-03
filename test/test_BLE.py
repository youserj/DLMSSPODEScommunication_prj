import asyncio
import unittest
from src.DLMS_SPODES_communications.ble import BLEKPZ, logger
from .functools2 import open_close
import logging
import sys


logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # datefmt="%d.%m %H:%M:%S,%03d"
))
logger.addHandler(handler)
logger.info("start")


class TestType(unittest.TestCase):
    m = BLEKPZ(
        # discovery_timeout='60',
        addr="A0:6C:65:53:7D:86")

    def test_log(self):
        logger.info('hi')

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

    def test_search_dev(self):
        async def main():
            for k, v in (await BLEKPZ.search(5)).items():
                print(k, v)

        asyncio.run(main())
