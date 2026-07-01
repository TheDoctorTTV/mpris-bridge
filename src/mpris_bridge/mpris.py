from __future__ import annotations

#################
### IMPORTS ###
#################

from typing import Any

from .artwork import ArtworkCache
from .schema import MPRIS_PREFIX, bridge_payload, session_payload, unwrap

########################
### DBUS CONSTANTS ###
########################

# Standard object path used by MPRIS media players.
MPRIS_PATH = "/org/mpris/MediaPlayer2"
# Standard DBus service and path used to enumerate names on the session bus.
DBUS_SERVICE = "org.freedesktop.DBus"
DBUS_PATH = "/org/freedesktop/DBus"
# DBus interface that exposes properties for MPRIS root and player objects.
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
# Root MPRIS interface contains identity and desktop entry data.
ROOT_INTERFACE = "org.mpris.MediaPlayer2"
# Player MPRIS interface contains metadata, playback state, and timeline data.
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"


#######################
### MPRIS READER ###
#######################

class MprisReader:
    def __init__(self, artwork_cache: ArtworkCache | None = None) -> None:
        # Cache artwork conversions so repeated API calls avoid repeated file or network reads.
        self.artwork_cache = artwork_cache or ArtworkCache()

    def get_payload(self) -> dict[str, Any]:
        # Import dbus lazily so the package can still be imported on systems without python-dbus.
        try:
            import dbus
        except ImportError as exc:
            raise RuntimeError("Install python-dbus or your distro python-dbus package to read MPRIS sessions") from exc

        # The session bus is where desktop media players publish MPRIS services.
        bus = dbus.SessionBus()
        # Find all DBus names that look like media player sessions.
        names = self._list_media_services(bus)
        sessions = []
        for name in names:
            # Read each session defensively because players can disappear while being queried.
            session = self._read_session(dbus, bus, name)
            if session is not None:
                sessions.append(session)
        # Convert all sessions into the public bridge payload.
        return bridge_payload(sessions)

    def get_session_ids(self) -> list[str]:
        # Reuse the normal payload so ID selection rules stay in one place.
        payload = self.get_payload()
        return [session["source_app_id"] for session in payload["sessions"]]

    def _list_media_services(self, bus: Any) -> list[str]:
        # MPRIS service names all start with org.mpris.MediaPlayer2.
        return sorted(str(name) for name in bus.list_names() if str(name).startswith(MPRIS_PREFIX))

    def _read_session(self, dbus_module: Any, bus: Any, service_name: str) -> dict[str, Any] | None:
        # Query one media player and return None if it cannot be read.
        try:
            # Get the MPRIS object from the player service.
            proxy = bus.get_object(service_name, MPRIS_PATH)
            # Wrap the object with the DBus Properties interface.
            props = dbus_module.Interface(proxy, PROPERTIES_INTERFACE)
            # Root properties describe the application.
            root_props = unwrap(props.GetAll(ROOT_INTERFACE))
            # Player properties describe the current media item.
            player_props = unwrap(props.GetAll(PLAYER_INTERFACE))
        except Exception:
            # Ignore stale or broken players so one bad session does not break the API.
            return None

        # Metadata is optional, so fall back to an empty dict.
        metadata = unwrap(player_props.get("Metadata")) or {}
        # Convert artwork URL or file path to an embeddable data URI when possible.
        thumbnail = self.artwork_cache.data_uri(metadata.get("mpris:artUrl"))
        # Shape raw DBus properties into the public session object.
        return session_payload(service_name, root_props, player_props, thumbnail)
