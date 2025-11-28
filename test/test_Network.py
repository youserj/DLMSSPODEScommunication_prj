import asyncio
import unittest
from src.DLMS_SPODES_communications.network import Network
from StructResult import result
from test.functools2 import open_close


class TestType(unittest.TestCase):
    def setUp(self) -> None:
        self.m = Network(
            host="178.170.223.243",
            port="8888",
            to_connect=40.0
        )
        self.m2 = Network(
            host="178.170.223.210",
            port="8888",
            to_connect=40.0
        )
        print(repr(self.m))

    def test_open_close(self) -> None:
        asyncio.run(open_close(self.m))

    def test_multy_open_close(self) -> None:
        async def multy() -> None:
            for _ in range(100):
                await open_close(self.m)
        asyncio.run(multy())

    def test_timeout(self) -> None:
        async def time_out() -> None:
            await self.m.open()
            await asyncio.sleep(600)
            print(f"{self.m.is_open()=}")
            await self.m.close()
        asyncio.run(time_out())

    def test_cooperative_open_close(self) -> None:
        medias = [Network(
            host="178.170.223.217",
            port="8888",
            to_connect=40.0
        ) for _ in range(10)]
        
        async def multy() -> None:
            async with asyncio.TaskGroup() as tg:
                for m in medias:
                    print(await m.open())
            for m in medias:
                print(F"is open {m.is_open()=}")
            data = bytes.fromhex("7E A0 07 03 21 93 0F 01 7E")
            async with asyncio.TaskGroup() as tg:
                for m in medias:
                    await m.send(data)
            bufs = []
            async with asyncio.TaskGroup() as tg:
                for m in medias:
                    bufs.append(bytearray())
                    print(await m.receive(bufs[-1]))
            await asyncio.sleep(5)
            print(bufs)
            async with asyncio.TaskGroup() as tg:
                for m in medias:
                    print(await m.close())
            for m in medias:
                print(F"is open {m.is_open()=}")

        asyncio.run(multy())

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
