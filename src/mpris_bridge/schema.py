from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import APP_VERSION

MPRIS_PREFIX = "org.mpris.MediaPlayer2."

PLAYBACK_STATUS = {
    "Stopped": 3,
    "Playing": 4,
    "Paused": 5,
}

AUTO_REPEAT_MODE = {
    "None": 0,
    "Track": 1,
    "Playlist": 2,
}

UNKNOWN_LENGTH_SENTINEL = 2**62


def unwrap(value: Any) -> Any:
    if hasattr(value, "value"):
        return unwrap(value.value)
    if isinstance(value, dict):
        return {key: unwrap(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [unwrap(item) for item in value]
    return value


def first_string(value: Any, default: str = "") -> str:
    value = unwrap(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item:
                return item
    return default


def string_list(value: Any) -> list[str]:
    value = unwrap(value)
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def int_value(value: Any, default: int = 0) -> int:
    value = unwrap(value)
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def ms_from_microseconds(value: Any) -> int:
    microseconds = int_value(value)
    if microseconds <= 0 or microseconds >= UNKNOWN_LENGTH_SENTINEL:
        return 0
    return microseconds // 1000


def playback_status_code(value: Any) -> int:
    return PLAYBACK_STATUS.get(first_string(value), 0)


def auto_repeat_mode_code(value: Any) -> int:
    return AUTO_REPEAT_MODE.get(first_string(value, "None"), 0)


def playback_type_code(metadata: dict[str, Any]) -> int:
    if metadata.get("xesam:artist") or metadata.get("xesam:album"):
        return 1
    if metadata.get("xesam:url"):
        return 2
    return 0


def media_properties(metadata: dict[str, Any], thumbnail: str | None) -> dict[str, Any]:
    metadata = unwrap(metadata) or {}
    title = first_string(metadata.get("xesam:title"), "Unknown")
    artist = first_string(metadata.get("xesam:artist"), "Unknown")

    return {
        "Title": title,
        "Artist": artist,
        "AlbumTitle": first_string(metadata.get("xesam:album"), "Unknown"),
        "AlbumArtist": first_string(metadata.get("xesam:albumArtist"), "Unknown"),
        "Thumbnail": thumbnail,
        "AlbumTrackCount": int_value(metadata.get("xesam:albumTrackCount")),
        "TrackNumber": int_value(metadata.get("xesam:trackNumber")),
        "Genres": string_list(metadata.get("xesam:genre")),
        "Subtitle": first_string(metadata.get("xesam:contentCreated"), ""),
    }


def playback_info(player_props: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "PlaybackStatus": playback_status_code(player_props.get("PlaybackStatus")),
        "PlaybackType": playback_type_code(metadata),
        "PlaybackRate": unwrap(player_props.get("Rate", 1.0)),
        "IsShuffleActive": bool(unwrap(player_props.get("Shuffle", False))),
        "AutoRepeatMode": auto_repeat_mode_code(player_props.get("LoopStatus")),
    }


def timeline_properties(player_props: dict[str, Any]) -> dict[str, Any]:
    length_ms = ms_from_microseconds((unwrap(player_props.get("Metadata")) or {}).get("mpris:length"))
    position_ms = ms_from_microseconds(player_props.get("Position"))
    now = datetime.now(timezone.utc).isoformat()

    return {
        "Position": position_ms,
        "StartTime": 0,
        "EndTime": length_ms,
        "MinSeekTime": 0,
        "MaxSeekTime": length_ms,
        "LastUpdatedTime": now,
    }


def source_app_id(service_name: str, root_props: dict[str, Any]) -> str:
    desktop_entry = first_string(root_props.get("DesktopEntry"))
    if desktop_entry:
        return desktop_entry
    identity = first_string(root_props.get("Identity"))
    if identity:
        return identity
    return service_name.removeprefix(MPRIS_PREFIX)


def session_payload(
    service_name: str,
    root_props: dict[str, Any],
    player_props: dict[str, Any],
    thumbnail: str | None,
) -> dict[str, Any]:
    metadata = unwrap(player_props.get("Metadata")) or {}
    return {
        "source_app_id": source_app_id(service_name, root_props),
        "media_properties": media_properties(metadata, thumbnail),
        "playback_info": playback_info(player_props, metadata),
        "timeline_properties": timeline_properties(player_props),
    }


def select_current_session_id(sessions: list[dict[str, Any]]) -> str | None:
    if not sessions:
        return None

    def priority(session: dict[str, Any]) -> int:
        status = session["playback_info"]["PlaybackStatus"]
        if status == 4:
            return 0
        if status == 5:
            return 1
        return 2

    return sorted(sessions, key=lambda item: (priority(item), item["source_app_id"]))[0]["source_app_id"]


def bridge_payload(sessions: list[dict[str, Any]], app_version: str = APP_VERSION) -> dict[str, Any]:
    return {
        "app_version": app_version,
        "current_session_id": select_current_session_id(sessions),
        "sessions": sessions,
    }
