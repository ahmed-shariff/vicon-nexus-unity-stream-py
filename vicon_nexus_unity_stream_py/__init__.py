from pkg_resources import get_distribution, DistributionNotFound

import logging
from loguru import logger

class __InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[__InterceptHandler()], level=0)

try:
    __version__ = get_distribution('vicon_nexus_unity_stream_py').version
except DistributionNotFound:
    __version__ = '(local)'
