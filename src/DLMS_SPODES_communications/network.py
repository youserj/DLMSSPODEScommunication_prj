import asyncio
from dataclasses import dataclass

from StructResult import result

from .base import StreamMedia


@dataclass
class Network(StreamMedia):
    host: str = "127.0.0.1"
    port: str = "4059"
    to_connection: float = 60.0
    to_recv: float = 5.0
    to_close: float = 3.0
    to_drain: float = 2.0

    def __repr__(self) -> str:
        params: list[str] = [F"host='{self.host}', port={self.port}"]
        return F"{self.__class__.__name__}({', '.join(params)})"

    async def open(self) -> result.Ok | result.Error:
        """ coroutine start """
        try:
            async with asyncio.timeout(self.to_connection):
                self._reader, self._writer = await asyncio.open_connection(
                    host=self.host,
                    port=self.port)
            return result.OK
        except Exception as e:
            return result.Error.from_e(e)

    def __str__(self) -> str:
        return F"{self.host}:{self.port}"
