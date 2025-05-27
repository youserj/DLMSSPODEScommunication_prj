import asyncio
import unittest
from src.DLMS_SPODES_communications.ble import BLEKPZ
from .functools2 import open_close
import logging
import sys


logger = logging.getLogger(__name__)


logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # datefmt="%d.%m %H:%M:%S,%03d"
))
logger.addHandler(handler)
logger.info("start")


class TestType(unittest.TestCase):
    def setUp(self) -> None:
        self.m = BLEKPZ(
            # discovery_timeout='60',
            addr="0C:1C:57:B5:C6:08")

    def test_log(self) -> None:
        logger.info("hi")

    def test_open_close(self) -> None:
        asyncio.run(open_close(self.m))

    def test_write_read(self) -> None:
        async def main(m: BLEKPZ) -> None:
            await m.open()
            print(F"{m.is_open()=}")
            data = b"~\xa0\x14\x02!!\x93u\x12\x81\x80\x07\x05\x02\x04\x00\x06\x01\xef\xcb\xb3~"
            await m.send(data)
            buf = bytearray()
            await asyncio.wait_for(
                fut=m.receive(buf),
                timeout=5)
            print(F"{buf.hex(' ')=}")
            await m.close()

        asyncio.run(main(self.m))

    def test_search_dev(self) -> None:
        async def main() -> None:
            for k, v in (await BLEKPZ.search(5)).items():
                print(k, v)

        asyncio.run(main())
