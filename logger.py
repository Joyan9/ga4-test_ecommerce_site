from loguru import logger
import sys


def setup_logger(level: str = "INFO"):
    logger.remove()
    logger.add(sys.stderr, level=level, colorize=True, backtrace=False, diagnose=False)
    return logger


__all__ = ["setup_logger"]
