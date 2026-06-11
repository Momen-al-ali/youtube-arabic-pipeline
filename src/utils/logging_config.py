
import logging
import sys
from src.utils.config import get_config


def get_logger(name: str) -> logging.Logger:
    config = get_config()

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(config.log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(config.log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger