import logging
import os
import sys
from logging import StreamHandler, FileHandler, Formatter


def configure_logging_from_env(log_file: str | None = None) -> logging.Logger:
    """Configure root logging based on the DEBUG environment variable.

    If DEBUG=="True" then enable very verbose console logging (DEBUG) with
    an exhaustive formatter (module, function, line). Otherwise default to
    INFO with a compact formatter.

    Args:
        log_file: optional path to a file to also emit logs to.

    Returns:
        The configured root logger.
    """
    root = logging.getLogger()

    # Remove existing handlers so configuration is deterministic when called
    # multiple times (useful during tests and interactive runs).
    for h in list(root.handlers):
        root.removeHandler(h)

    debug_env = os.getenv("DEBUG", "False")
    is_debug = debug_env == "True"

    level = logging.DEBUG if is_debug else logging.INFO
    root.setLevel(level)

    if is_debug:
        fmt = (
            "%(asctime)s [%(levelname)s] %(name)s %(module)s:%(funcName)s:%(lineno)d - %(message)s"
        )
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

    formatter = Formatter(fmt)

    # Console handler (explicitly to stdout so CI and terminal see it predictably)
    ch = StreamHandler(stream=sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # Optional file handler for persistent logs
    if log_file:
        fh = FileHandler(log_file)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        root.addHandler(fh)

    # In debug mode, make a few noisy third-party loggers more verbose so
    # terminal output is exhaustive while debugging.
    if is_debug:
        for noisy in ("urllib3", "tavily", "llama", "openai", "requests"):
            logging.getLogger(noisy).setLevel(logging.DEBUG)

    root.debug("Logging configured. DEBUG=%s, level=%s, log_file=%s", debug_env, level, log_file)
    return root


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper to get a child logger after configuration."""
    return logging.getLogger(name)
