from __future__ import annotations

import argparse
import logging

from .app import create_app
from .config import load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expose Linux MPRIS sessions through a REST API.")
    parser.add_argument("--config", default="settings.ini", help="Path to settings.ini")
    parser.add_argument("--host", help="Host to bind")
    parser.add_argument("--port", type=int, help="Port to bind")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug logging")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    host = args.host or config.host
    port = args.port or config.port

    if not args.debug:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)

    app = create_app()
    app.run(host=host, port=port, threaded=True, use_reloader=False, debug=args.debug)
    return 0
