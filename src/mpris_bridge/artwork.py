from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

MAX_ARTWORK_BYTES = 5 * 1024 * 1024


class ArtworkCache:
    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}

    def data_uri(self, art_url: str | None) -> str | None:
        if not art_url:
            return None
        if art_url.startswith("data:"):
            return art_url
        if art_url in self._cache:
            return self._cache[art_url]

        try:
            result = _load_data_uri(art_url)
        except OSError:
            result = None

        self._cache[art_url] = result
        return result


def _load_data_uri(art_url: str) -> str | None:
    parsed = urlparse(art_url)
    if parsed.scheme in ("", "file"):
        path = Path(unquote(parsed.path if parsed.scheme == "file" else art_url))
        data = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        return encode_data_uri(data, mime)

    if parsed.scheme in ("http", "https"):
        request = Request(art_url, headers={"User-Agent": "mpris-bridge/0.1"})
        with urlopen(request, timeout=3) as response:
            data = response.read(MAX_ARTWORK_BYTES + 1)
            if len(data) > MAX_ARTWORK_BYTES:
                return None
            mime = response.headers.get_content_type() or "image/png"
            return encode_data_uri(data, mime)

    return None


def encode_data_uri(data: bytes, mime: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"
