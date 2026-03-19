"""
StampFly CLI Commands

Each module in this package implements a CLI command.
"""

from . import version
from . import doctor
from . import build
from . import flash
from . import monitor
from . import log
from . import sim
from . import cal
from . import setup
from . import sysid
from . import flight
from . import query
from . import rc
from . import lesson
from . import competition
from . import docs

__all__ = [
    "version",
    "doctor",
    "build",
    "flash",
    "monitor",
    "log",
    "sim",
    "cal",
    "setup",
    "sysid",
    "flight",
    "query",
    "rc",
    "lesson",
    "competition",
    "docs",
]
