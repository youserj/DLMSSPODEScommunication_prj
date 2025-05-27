import asyncio
from dataclasses import dataclass
from .base import StreamMedia


@dataclass
class Network(StreamMedia):
    host: str = "127.0.0.1"
    port: str = "4059"
    to_recv: float = 5.0
    to_close: float = 3.0
    drain_timeout: float = 2.0

    def __repr__(self) -> str:
        params: list[str] = [F"host='{self.host}', port={self.port}"]
        return F"{self.__class__.__name__}({', '.join(params)})"

    async def open(self) -> None:
        """ coroutine start """
        self._reader, self._writer = await asyncio.open_connection(
            host=self.host,
            port=self.port)

    def __str__(self) -> str:
        return F"{self.host}:{self.port}"
