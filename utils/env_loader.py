import os
from dotenv import load_dotenv
from typing import Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


def load_env(path: Optional[str] = None) -> None:
    """Load environment variables from a .env file if present.

    This is a thin wrapper over python-dotenv's load_dotenv. By default it
    searches for a `.env` file in the current working directory.
    """
    if path:
        loaded = load_dotenv(dotenv_path=path)
        logger.debug("Loaded .env from %s: %s", path, loaded)
    else:
        loaded = load_dotenv()
        logger.debug("Loaded .env from default locations: %s", loaded)


def get_required(key: str) -> str:
    """Return the environment variable value or raise a helpful error.

    Use this for keys that must be set for runtime.
    """
    val = os.getenv(key)
    if not val:
        logger.error("Required environment variable '%s' is not set", key)
        raise EnvironmentError(f"Required environment variable '{key}' is not set")
    return val


def get_optional(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)
