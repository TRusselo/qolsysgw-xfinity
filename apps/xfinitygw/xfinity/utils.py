import logging


LOGGER = logging.getLogger(__name__)


def defaultLoggerCallback(*args, **kwargs):
    """Default callback that just logs the arguments"""
    LOGGER.debug(f'Default callback called with args={args} and kwargs={kwargs}')