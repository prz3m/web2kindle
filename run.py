import argparse
import logging
import os
from pathlib import Path

import uvicorn


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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the web2kindle server.")
    parser.add_argument(
        "--secrets-dir",
        default=".",
        help="directory containing web2kindle.conf, client_secret.json, and token.json",
    )
    parser.add_argument(
        "--documents-dir",
        default=Path(os.environ.get("WEB2KINDLE_DOCUMENTS_DIR", "documents")),
        type=Path,
        help="directory for queued articles, generated EPUBs, and working files",
    )
    args = parser.parse_args(argv)
    os.environ["WEB2KINDLE_SECRETS_DIR"] = args.secrets_dir
    os.environ["WEB2KINDLE_DOCUMENTS_DIR"] = str(
        args.documents_dir.expanduser()
    )

    from server.api import app

    uvicorn.run(app, host="127.0.0.1", port=8666)


if __name__ == "__main__":
    main()
