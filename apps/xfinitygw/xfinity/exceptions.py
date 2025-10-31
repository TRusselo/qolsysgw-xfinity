class XfinityException(Exception):
    pass


class UnknownXfinityControlException(XfinityException):
    pass


class UnknownXfinityEventException(XfinityException):
    pass


class MissingUserCodeException(XfinityException):
    pass


class InvalidUserCodeException(XfinityException):
    pass