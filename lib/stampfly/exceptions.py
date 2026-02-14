"""
StampFly SDK exceptions

StampFly SDK のカスタム例外クラス
"""


class StampFlyException(Exception):
    """Base exception for StampFly SDK

    StampFly SDK の基底例外クラス
    """

    pass


class StampFlyConnectionError(StampFlyException):
    """Connection to vehicle failed

    機体への接続に失敗
    """

    pass


class StampFlyCommandError(StampFlyException):
    """Vehicle rejected command

    機体がコマンドを拒否
    """

    pass
