from __future__ import annotations

from typing import Any

from .artwork import ArtworkCache
from .schema import MPRIS_PREFIX, bridge_payload, session_payload, unwrap

MPRIS_PATH = "/org/mpris/MediaPlayer2"
DBUS_SERVICE = "org.freedesktop.DBus"
DBUS_PATH = "/org/freedesktop/DBus"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
ROOT_INTERFACE = "org.mpris.MediaPlayer2"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"


class MprisReader:
    def __init__(self, artwork_cache: ArtworkCache | None = None) -> None:
        self.artwork_cache = artwork_cache or ArtworkCache()

    def get_payload(self) -> dict[str, Any]:
        try:
            import dbus
        except ImportError as exc:
            raise RuntimeError("Install python-dbus or your distro python-dbus package to read MPRIS sessions") from exc

        bus = dbus.SessionBus()
        names = self._list_media_services(bus)
        sessions = []
        for name in names:
            session = self._read_session(dbus, bus, name)
            if session is not None:
                sessions.append(session)
        return bridge_payload(sessions)

    def get_session_ids(self) -> list[str]:
        payload = self.get_payload()
        return [session["source_app_id"] for session in payload["sessions"]]

    def _list_media_services(self, bus: Any) -> list[str]:
        return sorted(str(name) for name in bus.list_names() if str(name).startswith(MPRIS_PREFIX))

    def _read_session(self, dbus_module: Any, bus: Any, service_name: str) -> dict[str, Any] | None:
        try:
            proxy = bus.get_object(service_name, MPRIS_PATH)
            props = dbus_module.Interface(proxy, PROPERTIES_INTERFACE)
            root_props = unwrap(props.GetAll(ROOT_INTERFACE))
            player_props = unwrap(props.GetAll(PLAYER_INTERFACE))
        except Exception:
            return None

        metadata = unwrap(player_props.get("Metadata")) or {}
        thumbnail = self.artwork_cache.data_uri(metadata.get("mpris:artUrl"))
        return session_payload(service_name, root_props, player_props, thumbnail)
