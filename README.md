# MPRIS Bridge

MPRIS Bridge is a lightweight Linux service that exposes MPRIS media sessions as a clean REST API compatible with the SMTC Bridge JSON shape.

It reads active players from the session DBus using `org.mpris.MediaPlayer2.*` services and returns SMTC style field names so existing now playing widgets can consume the data with minimal changes. MPRIS Bridge is a Linux port of nutty's original [SMTC Bridge](https://github.com/nuttylmao/smtc-bridge) project.

## Quick Start

```bash
python -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e .
.venv/bin/mpris-bridge
```

The `--system-site-packages` flag lets the app use the distro provided `python-dbus` binding. On Arch based systems install it with `sudo pacman -S python-dbus` if it is missing.

By default the API listens on:

http://127.0.0.1:5000/now-playing

Configuration can be changed in `settings.ini`, with command line flags, or with `MPRIS_BRIDGE_HOST` and `MPRIS_BRIDGE_PORT`.

## Build a Single Binary

```bash
python scripts/build_binary.py
```

The build script creates `.venv` with system site packages, installs the build dependency, and writes the binary to `dist/mpris-bridge`.

The built binary still reads an external `settings.ini` from the directory where you run it, and falls back to `127.0.0.1:5000` when no settings file is present.

## Systemd User Service

The systemd setup is optional. From a release archive or this repo after building:

```bash
./install_systemd_user.sh
```

When running from a source checkout instead of an extracted release archive, use `scripts/install_systemd_user.sh`.

This installs the binary to `~/.local/bin/mpris-bridge`, writes the user unit to `~/.config/systemd/user/mpris-bridge.service`, creates `~/.config/mpris-bridge/settings.ini` if needed, then enables and starts the user service.

Useful commands:

```bash
systemctl --user status mpris-bridge.service
systemctl --user restart mpris-bridge.service
journalctl --user -u mpris-bridge.service -f
```

To uninstall the service and installed binary:

```bash
./uninstall_systemd_user.sh
```

When running from a source checkout instead of an extracted release archive, use `scripts/uninstall_systemd_user.sh`.

The uninstall script keeps `~/.config/mpris-bridge/settings.ini` by default. Pass `--purge-config` to remove it too, or `--keep-binary` to leave `~/.local/bin/mpris-bridge` in place.

## Package a Release Zip

```bash
python scripts/package_release.py
```

The package script builds `dist/mpris-bridge` and creates `release/mpris-bridge-<version>-linux-<arch>.zip` containing:

| Path | Purpose |
| :--- | :--- |
| `bin/mpris-bridge` | Single-file binary. |
| `install_systemd_user.sh` | Installs and starts the optional systemd user service. |
| `uninstall_systemd_user.sh` | Stops and removes the optional systemd user service. |
| `systemd/mpris-bridge.service` | User service unit installed by the script. |
| `settings.ini` | Default API host and port config. |
| `README.md` | Usage docs. |

## Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Returns the current media state as JSON plus endpoint links. |
| `GET` | `/now-playing` | Returns the current media state as JSON. |
| `GET` | `/sessions` | Returns a JSON list of active media session IDs. |
| `GET` | `/sessions?format=html` | Returns a simple browser view of active sessions. |
| `GET` | `/health` | Returns service health and version. |

## Schema

`/now-playing` returns the same top level shape as SMTC Bridge:

```json
{
  "app_version": "string",
  "current_session_id": "string",
  "sessions": [
    {
      "source_app_id": "string",
      "media_properties": {
        "Title": "string",
        "Artist": "string",
        "AlbumTitle": "string",
        "AlbumArtist": "string",
        "Thumbnail": "string (base64 data URI)",
        "AlbumTrackCount": "integer",
        "TrackNumber": "integer",
        "Genres": "array of strings",
        "Subtitle": "string"
      },
      "playback_info": {
        "PlaybackStatus": "integer",
        "PlaybackType": "integer",
        "PlaybackRate": "number or null",
        "IsShuffleActive": "boolean",
        "AutoRepeatMode": "integer"
      },
      "timeline_properties": {
        "Position": "integer (ms)",
        "StartTime": "integer (ms)",
        "EndTime": "integer (ms)",
        "MinSeekTime": "integer (ms)",
        "MaxSeekTime": "integer (ms)",
        "LastUpdatedTime": "string (ISO 8601)"
      }
    }
  ]
}
```

## MPRIS Mapping

Playback status follows SMTC Bridge values:

| MPRIS | Value |
| :--- | :--- |
| `Stopped` | `3` |
| `Playing` | `4` |
| `Paused` | `5` |

Loop status maps to auto repeat mode:

| MPRIS | Value |
| :--- | :--- |
| `None` | `0` |
| `Track` | `1` |
| `Playlist` | `2` |

MPRIS does not expose a global focused media session like Windows SMTC. `current_session_id` is selected from the active sessions by priority: playing first, paused second, then the first remaining session by source ID.

Album art is read from `mpris:artUrl` and returned as a data URI when the source is a local file or an HTTP URL under 5 MB.

## Credits

MPRIS Bridge is a Linux port of [SMTC Bridge](https://github.com/nuttylmao/smtc-bridge), created by [nutty](https://nutty.gg/). The REST schema and endpoint shape are intentionally compatible with that project.
