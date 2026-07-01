from __future__ import annotations

#################
### IMPORTS ###
#################

import base64
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

#########################
### ARTWORK LIMITS ###
#########################

# Limit remote artwork so the API does not embed huge images in JSON.
MAX_ARTWORK_BYTES = 5 * 1024 * 1024


#########################
### ARTWORK CACHE ###
#########################

class ArtworkCache:
    def __init__(self) -> None:
        # Map original artwork URL to encoded data URI or None.
        self._cache: dict[str, str | None] = {}

    def data_uri(self, art_url: str | None) -> str | None:
        # Missing artwork stays missing.
        if not art_url:
            return None
        # Already embedded artwork can pass straight through.
        if art_url.startswith("data:"):
            return art_url
        # Return cached result so repeated API calls are cheap.
        if art_url in self._cache:
            return self._cache[art_url]

        # Convert local files or remote URLs into data URIs.
        try:
            result = _load_data_uri(art_url)
        except OSError:
            # File and network errors should not break the media payload.
            result = None

        # Cache both successes and failures for this process.
        self._cache[art_url] = result
        return result


#############################
### ARTWORK LOADING ###
#############################

def _load_data_uri(art_url: str) -> str | None:
    # Parse the URL so local paths and remote URLs can be handled separately.
    parsed = urlparse(art_url)
    # Empty scheme and file scheme both mean local filesystem artwork.
    if parsed.scheme in ("", "file"):
        path = Path(unquote(parsed.path if parsed.scheme == "file" else art_url))
        data = path.read_bytes()
        # Guess a browser friendly MIME type from the filename.
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        return encode_data_uri(data, mime)

    # HTTP artwork is downloaded with a small timeout and size limit.
    if parsed.scheme in ("http", "https"):
        request = Request(art_url, headers={"User-Agent": "mpris-bridge/0.1"})
        with urlopen(request, timeout=3) as response:
            data = response.read(MAX_ARTWORK_BYTES + 1)
            # Reject artwork bigger than the configured cap.
            if len(data) > MAX_ARTWORK_BYTES:
                return None
            mime = response.headers.get_content_type() or "image/png"
            return encode_data_uri(data, mime)

    # Unsupported schemes are ignored.
    return None


########################
### DATA URI ENCODE ###
########################

def encode_data_uri(data: bytes, mime: str) -> str:
    # Base64 encode bytes so the image can travel inside JSON.
    encoded = base64.b64encode(data).decode("ascii")
    # Return a standards compatible data URI.
    return f"data:{mime};base64,{encoded}"
