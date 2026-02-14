"""
StampFly Python SDK — djitellopy-compatible interface for StampFly drone

djitellopy 互換の StampFly Python SDK

Usage:
    from stampfly import StampFly
    drone = StampFly()
    drone.connect()
    drone.takeoff()
    drone.land()
    drone.end()
"""

from .stampfly import StampFly
from .exceptions import StampFlyException, StampFlyConnectionError, StampFlyCommandError

__all__ = [
    "StampFly",
    "StampFlyException",
    "StampFlyConnectionError",
    "StampFlyCommandError",
]
