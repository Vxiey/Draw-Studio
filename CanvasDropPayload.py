"""Parse drag/drop payloads for direct game-canvas image drops.

Browser drags are not identical to File Explorer drags. Depending on Chrome,
Edge, Windows and TkDND, Draw Studio may receive a local file path, a file://
URI, plain URL text or a small HTML fragment containing an image URL. This
module normalizes those forms without performing network access.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from pathlib import Path
import re
from urllib.parse import parse_qs, unquote, urlparse

_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
_IMG_SRC_RE = re.compile(
    r'''(?:src|data-src|data-original)\s*=\s*["'](https?://[^"']+)["']''',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CanvasDropSource:
    source: str
    label: str
    kind: str  # 'file' or 'url'


def _file_uri_to_path(value: str) -> str | None:
    try:
        parsed = urlparse(value)
    except Exception:
        return None
    if parsed.scheme.lower() != 'file':
        return None
    path = unquote(parsed.path or '')
    # file:///C:/... -> C:/... on Windows. UNC keeps //host/share.
    if parsed.netloc:
        path = f'//{parsed.netloc}{path}'
    elif len(path) >= 3 and path[0] == '/' and path[2] == ':':
        path = path[1:]
    return path or None


def _looks_like_image_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix.lower()
        host = (parsed.hostname or '').lower()
    except Exception:
        return False
    if suffix in _IMAGE_EXTENSIONS:
        return True
    # Google Images commonly supplies extensionless CDN URLs.
    return any(token in host for token in ('gstatic.com', 'googleusercontent.com', 'ggpht.com'))


def _clean_url(value: str) -> str:
    value = unescape(str(value or '').strip().strip('{}').strip('"\''))
    # HTML attributes often leave a trailing punctuation token after extraction.
    return value.rstrip('),;')


def _unwrap_image_search_url(url: str) -> str:
    """Unwrap common image-search redirect URLs without network access."""
    try:
        parsed=urlparse(url)
        host=(parsed.hostname or '').lower()
        query=parse_qs(parsed.query)
    except Exception:
        return url
    keys=()
    if 'google.' in host or host.endswith('google.com'):
        keys=('imgurl','mediaurl')
    elif 'bing.com' in host:
        keys=('mediaurl','imgurl')
    for key in keys:
        for value in query.get(key) or ():
            candidate=_clean_url(unquote(str(value)))
            if urlparse(candidate).scheme.lower() in ('http','https'):
                return candidate
    return url


def parse_canvas_drop(raw_data: object, *, split_items=()) -> CanvasDropSource:
    """Return one safe file/HTTP image source from a TkDND payload.

    ``split_items`` should normally be ``root.tk.splitlist(event.data)`` when
    available. It is optional so the parser can also handle DND_TEXT/HTML data.
    """
    raw = str(raw_data or '').strip()
    items = [str(item).strip().strip('{}') for item in (split_items or ()) if str(item).strip()]

    # 1) Local files and file:// URIs take priority because they need no network.
    for item in items + ([raw] if raw else []):
        candidate = item.strip().strip('{}').strip('"')
        file_path = _file_uri_to_path(candidate)
        if file_path:
            candidate = file_path
        try:
            path = Path(candidate)
            exists = path.is_file()
        except OSError:
            exists = False
        if exists:
            if path.suffix.lower() not in _IMAGE_EXTENSIONS:
                raise ValueError('Drop an image file (PNG, JPG, WEBP or BMP).')
            return CanvasDropSource(str(path), path.name, 'file')

    # 2) Prefer explicit <img src=...> or lazy-load image attributes from HTML.
    html_urls = [_clean_url(match) for match in _IMG_SRC_RE.findall(unescape(raw))]
    for url in html_urls:
        if urlparse(url).scheme.lower() in ('http', 'https'):
            return CanvasDropSource(_unwrap_image_search_url(url), 'Dropped web image', 'url')

    # 3) Plain text/URI-list drops. Rank likely image URLs before generic URLs.
    urls = []
    seen = set()
    for text in items + ([raw] if raw else []):
        text = unescape(text)
        direct = _clean_url(text)
        if not any(ch.isspace() for ch in direct) and urlparse(direct).scheme.lower() in ('http', 'https'):
            candidates = [direct]
        else:
            candidates = [_clean_url(match) for match in _URL_RE.findall(text)]
        for url in candidates:
            if url not in seen and urlparse(url).scheme.lower() in ('http', 'https'):
                seen.add(url); urls.append(url)
    if urls:
        urls.sort(key=lambda url: (not _looks_like_image_url(url), len(url)))
        return CanvasDropSource(_unwrap_image_search_url(urls[0]), 'Dropped web image', 'url')

    raise ValueError(
        'No image was found in the drop. Drag the image itself from Chrome/Edge or drop a local image file.'
    )
