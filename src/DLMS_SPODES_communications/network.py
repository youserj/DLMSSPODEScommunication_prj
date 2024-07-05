import asyncio
from dataclasses import dataclass
from enum import Enum
from .base import StreamMedia


class TagsName(Enum):
    ADDRESS = 'address'
    PORT = 'port'


@dataclass
class Network(StreamMedia):
    host: str = "127.0.0.1"
    port: str = '4059'

    def __repr__(self):
        params: list[str] = [F"host='{self.host}', port={self.port}"]
        return F"{self.__class__.__name__}({', '.join(params)})"

    async def open(self):
        """ coroutine start """
        self._reader, self._writer = await asyncio.open_connection(
            host=self.host,
            port=self.port)

    def __str__(self):
        return F"{self.host}:{self.port}"
