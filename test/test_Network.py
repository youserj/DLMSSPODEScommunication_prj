import asyncio
import unittest
from src.DLMS_SPODES_communications.network import Network, AsyncNetwork


class TestType(unittest.TestCase):
    def test_Network(self):
        driver = Network(
            host="127.0.0.1",
            port=10000)
        driver.open()
        print(F"{driver.is_open()=}")
        data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
        driver.send(data)
        buf = bytearray()
        driver.receive(buf)
        print(F"{buf.hex(' ')=}")
        driver.close()

    def test_AsyncNetwork(self):
        async def main(d: AsyncNetwork):
            await d.open()
            print(F"{driver.is_open()=}")
            data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
            await driver.send(data)
            buf = bytearray()
            await driver.receive(buf)
            print(F"{buf.hex(' ')=}")
            await d.close()

        driver = AsyncNetwork(
            host="127.0.0.1",
            port=10000)
        asyncio.run(main(driver))
