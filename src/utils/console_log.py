"""App-owned console logging, kept separate from third-party library noise.

Third-party dependencies (onnxruntime, numba, coloredlogs, ...) use the stdlib
``logging`` module on their own, with no configuration from this app. Left alone,
their loggers fall back to the root logger's "handler of last resort" and print
straight to stderr. :func:`configure_console_logging` raises the root logger's
threshold above every real level so those propagate nowhere, while the app's own
``"dotformat"`` logger gets its own handler and stays fully independent
(``propagate=False``) of whatever the root logger is doing.

Not to be confused with ``services.log_service``/``services.conversion_service``,
which manage the in-app, database-backed conversion history shown in the History
dialog -- an unrelated concept that predates this module.
"""
from __future__ import annotations

import logging
import sys

LOGGER_NAME = "dotformat"

_configured = False


def configure_console_logging(level: int = logging.INFO) -> logging.Logger:
    """Set up the app's console logger. Safe to call more than once.

    Silences third-party loggers by raising the root logger's threshold, then
    gives the app's own logger a dedicated stdout handler and timestamped
    formatter, independent of the root logger's configuration.
    """
    global _configured

    logging.getLogger().setLevel(logging.CRITICAL + 1)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if not _configured:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        _configured = True

    return logger


def get_logger() -> logging.Logger:
    """The app's console logger. Configures it with defaults if not done yet."""
    if not _configured:
        return configure_console_logging()
    return logging.getLogger(LOGGER_NAME)


def log_debug(msg: str, *args, **kwargs) -> None:
    get_logger().debug(msg, *args, **kwargs)


def log_info(msg: str, *args, **kwargs) -> None:
    get_logger().info(msg, *args, **kwargs)


def log_warning(msg: str, *args, **kwargs) -> None:
    get_logger().warning(msg, *args, **kwargs)


def log_error(msg: str, *args, **kwargs) -> None:
    get_logger().error(msg, *args, **kwargs)


def log_critical(msg: str, *args, **kwargs) -> None:
    get_logger().critical(msg, *args, **kwargs)


__all__ = [
    "LOGGER_NAME",
    "configure_console_logging",
    "get_logger",
    "log_debug",
    "log_info",
    "log_warning",
    "log_error",
    "log_critical",
]
