import logging
import os


def _configure_logging() -> None:
    package_logger = logging.getLogger("web2kindle")
    level_name = os.environ.get("WEB2KINDLE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    package_logger.setLevel(level)
    package_logger.propagate = False

    if not package_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s"
            )
        )
        package_logger.addHandler(handler)


_configure_logging()

from server.api import app  # noqa: E402, F401
