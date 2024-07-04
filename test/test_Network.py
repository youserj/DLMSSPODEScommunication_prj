import asyncio
import unittest
from src.DLMS_SPODES_communications.network import Network
from .functools2 import open_close


class TestType(unittest.TestCase):
    m = Network(
        host="127.0.0.1",
        port="10000")
    print(repr(m))

    def test_open_close(self):
        asyncio.run(open_close(self.m))

    def test_Network(self):
        async def main(m: Network):
            await m.open()
            print(F"{m.is_open()=}")
            data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
            await m.send(data)
            buf = bytearray()
            await m.receive(buf)
            print(F"{buf.hex(' ')=}")
            await m.close()

        asyncio.run(main(self.m))
