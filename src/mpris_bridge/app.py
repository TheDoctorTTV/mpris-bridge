from __future__ import annotations

#################
### IMPORTS ###
#################

from flask import Flask, jsonify, request

from . import APP_VERSION
from .mpris import MprisReader

#################
### ROUTES ###
#################

# List the public endpoints shown by the root route.
ENDPOINTS = ["/", "/now-playing", "/sessions", "/health"]


#########################
### FLASK CORS SETUP ###
#########################

def configure_cors(app: Flask) -> None:
    # Add CORS headers after each response so browsers can read the API.
    @app.after_request
    def add_cors_headers(response):
        # Allow any local page or tool to call this bridge.
        response.headers["Access-Control-Allow-Origin"] = "*"
        # This API is read only, so GET and browser preflight OPTIONS are enough.
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        # Let browser clients send normal JSON content headers.
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response


########################
### APP FACTORY ###
########################

def create_app(reader: MprisReader | None = None) -> Flask:
    # Create the Flask app object used by the CLI and tests.
    app = Flask(__name__)
    # Register CORS headers once during app creation.
    configure_cors(app)

    # Use an injected reader for tests or create the real MPRIS reader.
    media_reader = reader or MprisReader()

    def current_media_payload(include_endpoints: bool = False):
        # Ask the reader for the current MPRIS state.
        payload = media_reader.get_payload()
        # The root endpoint also includes a small endpoint directory.
        if include_endpoints:
            payload["endpoints"] = ENDPOINTS
        return payload

    def error_payload(exc: Exception, include_endpoints: bool = False):
        # Keep error responses shaped like normal media responses.
        payload = {
            "app_version": APP_VERSION,
            "current_session_id": None,
            "sessions": [],
            "error": str(exc),
        }
        # Mirror the endpoint list on the root route even during failures.
        if include_endpoints:
            payload["endpoints"] = ENDPOINTS
        return payload

    ####################
    ### INDEX ROUTE ###
    ####################

    @app.get("/")
    def index():
        # Return current media plus endpoint links.
        try:
            return jsonify(current_media_payload(include_endpoints=True))
        except Exception as exc:
            # Return a structured 500 instead of exposing a Flask traceback.
            return jsonify(error_payload(exc, include_endpoints=True)), 500

    #####################
    ### HEALTH ROUTE ###
    #####################

    @app.get("/health")
    def health():
        # Give service managers a simple alive check.
        return jsonify({"ok": True, "app_version": APP_VERSION})

    #############################
    ### NOW PLAYING ROUTE ###
    #############################

    @app.get("/now-playing")
    def now_playing():
        # Return the main SMTC compatible payload.
        try:
            return jsonify(current_media_payload())
        except Exception as exc:
            # Keep failures machine readable for clients.
            return jsonify(error_payload(exc)), 500

    ########################
    ### SESSIONS ROUTE ###
    ########################

    @app.get("/sessions")
    def sessions():
        # Collect the active MPRIS service IDs.
        try:
            session_ids = media_reader.get_session_ids()
        except Exception as exc:
            # Return a list shaped error response for session browser clients.
            return jsonify({"sessions": [], "error": str(exc)}), 500

        # The optional HTML format is handy for opening the route in a browser.
        if request.args.get("format") == "html":
            items = "".join(f"<li>{item}</li>" for item in session_ids) or "<li>No active audio sources found.</li>"
            return f"<body><h3>Active Audio Sources</h3><ul>{items}</ul></body>"

        # Default response is a JSON array for simple clients.
        return jsonify(session_ids)

    # Return the fully configured Flask application.
    return app
