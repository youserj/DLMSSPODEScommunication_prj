import asyncio
import unittest
from src.DLMS_SPODES_communications.ble import BLEKPZ
from .functools2 import open_close
import logging
import sys
from StructResult import result


logger = logging.getLogger(__name__)


logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # datefmt="%d.%m %H:%M:%S,%03d"
))
logger.addHandler(handler)
logger.info("start")
import os


class TestType(unittest.TestCase):
    def setUp(self) -> None:
        print(f"{os.name=}")
        self.m = BLEKPZ(
            to_connect=20.0,
            to_recv=20.0,
            # addr="0C:1C:57:B5:C6:08"
            # addr="5C:53:10:5A:E2:4B"
            # addr="5C:53:10:5A:DF:CD"
            # addr="66:84:46:05:AC:24"
            addr="5C:53:10:5A:E2:48"
            # addr="5C:53:10:5A:E2:3F"
        )

    def test_log(self) -> None:
        logger.info("hi")

    def test_open_close(self) -> None:
        asyncio.run(open_close(self.m))
        asyncio.run(open_close(self.m))

    def test_write_read(self) -> None:
        async def main(m: BLEKPZ) -> None:
            if isinstance(res_open := await m.open(), result.Error):
                raise ValueError("Open error")
            print(F"{m.is_open()=}")
            data = b"~\xa0\x14\x02!!\x93u\x12\x81\x80\x07\x05\x02\x04\x00\x06\x01\xef\xcb\xb3~"
            await m.send(data)
            buf = bytearray()
            await m.receive(buf)
            print(F"{buf.hex(' ')=}")
            if m.is_open():
                await m.close()
            else:
                print("already closed")

        async def several(m: BLEKPZ) -> None:
            for i in range(10):
                await main(m)

        asyncio.run(several(self.m))

    def test_search_dev(self) -> None:
        async def main() -> None:
            for k, v in (await BLEKPZ.search(10)).items():
                print(k, v)

        asyncio.run(main())
