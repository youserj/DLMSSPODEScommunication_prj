import asyncio
import platform
from dataclasses import dataclass
import time
from StructResult import result
from .base import StreamMedia


_platform = platform.system()
CONN_ERROR: str = "Network connection"


@dataclass
class Network(StreamMedia):
    host: str = "127.0.0.1"
    port: str = "4059"
    to_connect: float = 20.0
    to_recv: float = 5.0
    to_close: float = 3.0
    to_drain: float = 2.0

    def __repr__(self) -> str:
        params: list[str] = [F"host='{self.host}', port={self.port}"]
        return F"{self.__class__.__name__}({', '.join(params)})"
    if _platform == "Windows":
        async def open(self) -> result.SimpleOrError[float]:
            start = time.monotonic()
            attempt = 1
            acc = result.ErrorAccumulator()
            while True:
                try:
                    async with asyncio.timeout(self.to_connect):
                        self._reader, self._writer = await asyncio.open_connection(
                            host=self.host,
                            port=self.port)
                    break
                except OSError as e:
                    if getattr(e, "winerror", None) == 121:    # limit by OS(21-23 second)
                        if (time.monotonic() - start) < self.to_connect:
                            attempt += 1
                            acc.append_e(e)
                            continue
                        e = TimeoutError(f"with {attempt=}")
                    return result.Error.from_e(e, CONN_ERROR)
                except Exception as e:
                    return result.Error.from_e(e, CONN_ERROR)
            return acc.merge_err(result.Simple(time.monotonic() - start))
    else:
        async def open(self) -> result.SimpleOrError[float]:
            start = time.monotonic()
            try:
                async with asyncio.timeout(self.to_connect):
                    self._reader, self._writer = await asyncio.open_connection(
                        host=self.host,
                        port=self.port)
                return result.Simple(time.monotonic() - start)
            except Exception as e:
                return result.Error.from_e(e, CONN_ERROR)

    async def end_transaction(self) -> None:
        ...

    def __str__(self) -> str:
        return F"{self.host}:{self.port}"
