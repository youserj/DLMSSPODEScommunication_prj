import asyncio
import unittest
from src.DLMS_SPODES_communications.serial_port import AsyncSerial, SerialPort


class TestType(unittest.TestCase):
    def test_Network(self):
        driver = SerialPort(
            port="COM3")
        driver.open()
        print(F"{driver.is_open()=}")
        data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
        driver.send(data)
        buf = bytearray()
        driver.receive(buf)
        print(F"{buf.hex(' ')=}")
        driver.close()

    def test_AsyncSerial(self):
        async def main(d: AsyncSerial):
            await d.open()
            print(F"{driver.is_open()=}")
            data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
            await driver.send(data)
            buf = bytearray()
            await driver.receive(buf)
            print(F"{buf.hex(' ')=}")
            await d.close()

        driver = AsyncSerial(
            port="COM3")
        asyncio.run(main(driver))
