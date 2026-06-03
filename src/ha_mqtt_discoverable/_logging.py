from __future__ import annotations

from typing import Protocol, cast

import structlog


class Logger(Protocol):
    def debug(self, event: str, *args: object, **kw: object) -> object: ...

    def info(self, event: str, *args: object, **kw: object) -> object: ...

    def warning(self, event: str, *args: object, **kw: object) -> object: ...

    def error(self, event: str, *args: object, **kw: object) -> object: ...

    def exception(self, event: str, *args: object, **kw: object) -> object: ...


def get_logger(name: str) -> Logger:
    return cast(Logger, structlog.get_logger(name))
