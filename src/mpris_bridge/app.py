from __future__ import annotations

from flask import Flask, jsonify, request

from . import APP_VERSION
from .mpris import MprisReader


def configure_cors(app: Flask) -> None:
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response


def create_app(reader: MprisReader | None = None) -> Flask:
    app = Flask(__name__)
    configure_cors(app)

    media_reader = reader or MprisReader()

    @app.get("/")
    def index():
        return jsonify(
            {
                "app_version": APP_VERSION,
                "endpoints": ["/now-playing", "/sessions", "/health"],
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "app_version": APP_VERSION})

    @app.get("/now-playing")
    def now_playing():
        try:
            return jsonify(media_reader.get_payload())
        except Exception as exc:
            return jsonify({"app_version": APP_VERSION, "current_session_id": None, "sessions": [], "error": str(exc)}), 500

    @app.get("/sessions")
    def sessions():
        try:
            session_ids = media_reader.get_session_ids()
        except Exception as exc:
            return jsonify({"sessions": [], "error": str(exc)}), 500

        if request.args.get("format") == "html":
            items = "".join(f"<li>{item}</li>" for item in session_ids) or "<li>No active audio sources found.</li>"
            return f"<body><h3>Active Audio Sources</h3><ul>{items}</ul></body>"

        return jsonify(session_ids)

    return app
