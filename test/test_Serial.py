import asyncio
import unittest
from src.DLMS_SPODES_communications.serial_port import Serial, RS485, medias
from .functools2 import open_close


class TestType(unittest.TestCase):
    m = Serial(port="COM13")

    def test_open_close(self):
        asyncio.run(open_close(self.m))

    def test_Serial(self):
        async def main(m: Serial):
            await m.open()
            data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
            await m.send(data)
            buf = bytearray()
            await asyncio.wait_for(
                fut=m.receive(buf),
                timeout=3)
            print(F"{buf.hex(' ')=}")
            await m.close()

        asyncio.run(main(self.m))

    def test_Serial_without_recv(self):
        async def main(m: Serial):
            await m.open()
            data = bytes.fromhex("7E A0 07 05 21 93 0F 01 7E")
            await m.send(data)
            await m.close()
            print("1 end")
            await m.open()
            print(F"{m.is_open()=}")
            data = bytes.fromhex("7E A0 07 06 21 93 0F 01 7E")
            await m.send(data)
            await m.close()
            print("2 end")

        asyncio.run(main(self.m))

    def test_RS485_open_close(self):
        async def main():
            nonlocal d1, d2
            await d1.open()
            print(F"{d1.is_open()=} {medias[d1.port].n_connected=}")
            await d1.close()
            await d2.open()
            await d1.lock.acquire()
            print(F"{d2.is_open()=} {medias[d2.port].n_connected=}")
            await d1.open()
            print(F"{d1.is_open()=} {medias[d1.port].n_connected=}")
            await d2.close()
            await d1.close()
            print(F"{medias=}")

        d1 = RS485(
            port="COM13")
        d2 = RS485(
            port="COM13")
        asyncio.run(main())

    @staticmethod
    async def get_response(d: Serial | RS485, data: bytes, t=3) -> bytes:
        await d.send(data)
        await asyncio.wait_for(d.receive(buf := bytearray()), t)
        return buf

    def test_RS485_send_recv(self):
        async def main():
            nonlocal d1, d2
            await d1.open()
            await d2.open()
            print(F"{d2.is_open()=} {medias[d2.port].n_connected=}")
            data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
            out = await self.get_response(d2, data)
            print(out.hex("."))
            print(F"{d1.is_open()=} {medias[d1.port].n_connected=}")
            await d2.close()
            await d1.close()
            print(F"{medias[d1.port].n_connected=}")

        d1 = RS485(
            port="COM13")
        d2 = RS485(
            port="COM13")
        asyncio.run(main())

    def test_RS485_send_recv_group(self):
        async def main():
            nonlocal d1, d2
            await d1.open()
            await d2.open()
            print(F"{d2.is_open()=} {medias[d2.port].n_connected=}")
            data_wrong = bytes.fromhex("7E A0 07 03 21 93 0F 02 7E")
            data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
            async with asyncio.TaskGroup() as ts:
                t1 = ts.create_task(self.get_response(d1, data))
                t2 = ts.create_task(self.get_response(d2, data))
            print(t1.result())
            print(t2.result())
            print(F"{d1.is_open()=} {medias[d1.port].n_connected=}")
            await d2.close()
            await d1.close()
            print(F"{medias[d1.port].n_connected=}")

        d1 = RS485(
            port="COM13")
        d2 = RS485(
            port="COM13")
        asyncio.run(main())
