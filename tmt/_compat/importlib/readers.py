from __future__ import annotations

import sys

if sys.version_info < (3, 12):
    from importlib_resources.readers import MultiplexedPath
else:
    from importlib.readers import MultiplexedPath

__all__ = [
    "MultiplexedPath",
    ]