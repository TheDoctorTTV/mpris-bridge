from __future__ import annotations

#################
### IMPORTS ###
#################

from datetime import datetime, timezone
from typing import Any

from . import APP_VERSION

########################
### MPRIS CONSTANTS ###
########################

# Prefix shared by all MPRIS player service names.
MPRIS_PREFIX = "org.mpris.MediaPlayer2."

# Numeric status codes expected by SMTC Bridge style clients.
PLAYBACK_STATUS = {
    "Stopped": 3,
    "Playing": 4,
    "Paused": 5,
}

# Numeric repeat mode codes expected by SMTC Bridge style clients.
AUTO_REPEAT_MODE = {
    "None": 0,
    "Track": 1,
    "Playlist": 2,
}

# Some players expose a huge sentinel value when track length is unknown.
UNKNOWN_LENGTH_SENTINEL = 2**62


##########################
### VALUE NORMALIZERS ###
##########################

def unwrap(value: Any) -> Any:
    # python-dbus scalar values store the real value on a value attribute.
    if hasattr(value, "value"):
        return unwrap(value.value)
    # Recursively unwrap dictionaries from DBus.
    if isinstance(value, dict):
        return {key: unwrap(item) for key, item in value.items()}
    # Recursively unwrap lists and tuples from DBus.
    if isinstance(value, (list, tuple)):
        return [unwrap(item) for item in value]
    # Plain Python values are already ready to use.
    return value


def first_string(value: Any, default: str = "") -> str:
    # Accept either a single string or a list of strings.
    value = unwrap(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        # Return the first nonempty string in list metadata.
        for item in value:
            if isinstance(item, str) and item:
                return item
    return default


def string_list(value: Any) -> list[str]:
    # Normalize a metadata string or string array into a Python list.
    value = unwrap(value)
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        # Keep only nonempty strings.
        return [item for item in value if isinstance(item, str) and item]
    return []


def int_value(value: Any, default: int = 0) -> int:
    # Normalize DBus values before checking the type.
    value = unwrap(value)
    # bool is a subclass of int, so reject it explicitly.
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def ms_from_microseconds(value: Any) -> int:
    # MPRIS position and length values are microseconds.
    microseconds = int_value(value)
    # Zero, negative, and sentinel values mean no known duration.
    if microseconds <= 0 or microseconds >= UNKNOWN_LENGTH_SENTINEL:
        return 0
    # API payloads expose milliseconds.
    return microseconds // 1000


########################
### CODE MAPPERS ###
########################

def playback_status_code(value: Any) -> int:
    # Convert MPRIS playback status text into client numeric code.
    return PLAYBACK_STATUS.get(first_string(value), 0)


def auto_repeat_mode_code(value: Any) -> int:
    # Convert MPRIS loop status text into client numeric code.
    return AUTO_REPEAT_MODE.get(first_string(value, "None"), 0)


def playback_type_code(metadata: dict[str, Any]) -> int:
    # Artist or album metadata means the source is likely music.
    if metadata.get("xesam:artist") or metadata.get("xesam:album"):
        return 1
    # URL metadata without music markers is treated like a web or video source.
    if metadata.get("xesam:url"):
        return 2
    # Unknown media type.
    return 0


#############################
### PAYLOAD BUILDERS ###
#############################

def media_properties(metadata: dict[str, Any], thumbnail: str | None) -> dict[str, Any]:
    # Normalize metadata before reading xesam fields.
    metadata = unwrap(metadata) or {}
    # Title and artist have visible fallback values for clients.
    title = first_string(metadata.get("xesam:title"), "Unknown")
    artist = first_string(metadata.get("xesam:artist"), "Unknown")

    # Return the media metadata block expected by bridge clients.
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
    # Return playback state and mode information.
    return {
        "PlaybackStatus": playback_status_code(player_props.get("PlaybackStatus")),
        "PlaybackType": playback_type_code(metadata),
        "PlaybackRate": unwrap(player_props.get("Rate", 1.0)),
        "IsShuffleActive": bool(unwrap(player_props.get("Shuffle", False))),
        "AutoRepeatMode": auto_repeat_mode_code(player_props.get("LoopStatus")),
    }


def timeline_properties(player_props: dict[str, Any]) -> dict[str, Any]:
    # Length is nested inside Metadata and position is a direct player property.
    length_ms = ms_from_microseconds((unwrap(player_props.get("Metadata")) or {}).get("mpris:length"))
    position_ms = ms_from_microseconds(player_props.get("Position"))
    # Timestamp uses UTC ISO format for clients that compare freshness.
    now = datetime.now(timezone.utc).isoformat()

    # Return current playhead position and seek range.
    return {
        "Position": position_ms,
        "StartTime": 0,
        "EndTime": length_ms,
        "MinSeekTime": 0,
        "MaxSeekTime": length_ms,
        "LastUpdatedTime": now,
    }


def source_app_id(service_name: str, root_props: dict[str, Any]) -> str:
    # DesktopEntry is the most stable app identifier when provided.
    desktop_entry = first_string(root_props.get("DesktopEntry"))
    if desktop_entry:
        return desktop_entry
    # Identity is a human readable fallback.
    identity = first_string(root_props.get("Identity"))
    if identity:
        return identity
    # Fall back to the DBus service suffix.
    return service_name.removeprefix(MPRIS_PREFIX)


def session_payload(
    service_name: str,
    root_props: dict[str, Any],
    player_props: dict[str, Any],
    thumbnail: str | None,
) -> dict[str, Any]:
    # Metadata can be absent or still wrapped in DBus types.
    metadata = unwrap(player_props.get("Metadata")) or {}
    # Build one complete session entry.
    return {
        "source_app_id": source_app_id(service_name, root_props),
        "media_properties": media_properties(metadata, thumbnail),
        "playback_info": playback_info(player_props, metadata),
        "timeline_properties": timeline_properties(player_props),
    }


###############################
### CURRENT SESSION PICKER ###
###############################

def select_current_session_id(sessions: list[dict[str, Any]]) -> str | None:
    # No sessions means there is no current source.
    if not sessions:
        return None

    def priority(session: dict[str, Any]) -> int:
        # Prefer actively playing media.
        status = session["playback_info"]["PlaybackStatus"]
        if status == 4:
            return 0
        # Paused media is next best.
        if status == 5:
            return 1
        # Stopped or unknown media is lowest priority.
        return 2

    # Sort by priority first, then app ID for stable output.
    return sorted(sessions, key=lambda item: (priority(item), item["source_app_id"]))[0]["source_app_id"]


###########################
### TOP LEVEL PAYLOAD ###
###########################

def bridge_payload(sessions: list[dict[str, Any]], app_version: str = APP_VERSION) -> dict[str, Any]:
    # Wrap sessions with app version and current session selection.
    return {
        "app_version": app_version,
        "current_session_id": select_current_session_id(sessions),
        "sessions": sessions,
    }
