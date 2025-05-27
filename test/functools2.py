from src.DLMS_SPODES_communications import base


async def open_close(m: base.Media) -> None:
    print(F"before open {m.is_open()=}")
    await m.open()
    print(F"after open {m.is_open()=}")
    await m.close()
    print(F"after close {m.is_open()=}")
