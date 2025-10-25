import asyncio
import unittest
from src.DLMS_SPODES_communications.network import Network
from StructResult import result
from .functools2 import open_close


class TestType(unittest.TestCase):
    def setUp(self) -> None:
        self.m = Network(
            host="178.170.223.243",
            port="8888",
            to_connect=40.0
        )
        print(repr(self.m))

    def test_open_close(self) -> None:
        asyncio.run(open_close(self.m))

    def test_Network(self) -> None:
        async def main(m: Network) -> None:
            if isinstance(res_open := await m.open(), result.Error):
                res_open.unwrap()
            print(res_open)
            print(F"{m.is_open()=}")
            data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
            await asyncio.sleep(.1)
            await m.send(data)
            buf = bytearray()
            await m.receive(buf)
            print(F"{buf.hex(' ')=}")
            await m.close()

        asyncio.run(main(self.m))
