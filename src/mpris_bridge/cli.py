from __future__ import annotations

#################
### IMPORTS ###
#################

import argparse
import logging

from .app import create_app
from .config import load_config


##########################
### COMMAND LINE APP ###
##########################

def main(argv: list[str] | None = None) -> int:
    # Define supported command line options.
    parser = argparse.ArgumentParser(description="Expose Linux MPRIS sessions through a REST API.")
    parser.add_argument("--config", default="settings.ini", help="Path to settings.ini")
    parser.add_argument("--host", help="Host to bind")
    parser.add_argument("--port", type=int, help="Port to bind")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug logging")
    args = parser.parse_args(argv)

    # Load config file defaults, then let CLI flags override them.
    config = load_config(args.config)
    host = args.host or config.host
    port = args.port or config.port

    # Hide Flask request logging unless debug mode is enabled.
    if not args.debug:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)

    # Create and run the Flask application.
    app = create_app()
    app.run(host=host, port=port, threaded=True, use_reloader=False, debug=args.debug)
    # Return a shell success code when the server exits normally.
    return 0
