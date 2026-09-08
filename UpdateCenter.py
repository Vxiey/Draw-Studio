"""Manual GitHub release update checks for Draw Studio.

Privacy/safety design:
- No background checks.
- No telemetry or machine identifiers.
- No downloads or installs.
- Network access occurs only when the user explicitly presses Check for updates.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from Version import APP_VERSION, BUILD_CHANNEL

GITHUB_REPOSITORY = "yesverynice12/Draw-Studio"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases?per_page=100"
GITHUB_RELEASES_PAGE = f"https://github.com/{GITHUB_REPOSITORY}/releases"

_STAGE_RANK = {"alpha": 0, "a": 0, "beta": 1, "b": 1, "rc": 2, "stable": 3, "final": 3}
_VERSION_RE = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:[-_.]?(?P<stage>alpha|a|beta|b|rc)(?:[-_.]?(?P<num>\d+))?)?$",
    re.IGNORECASE,
)


class UpdateCheckError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedVersion:
    major: int
    minor: int
    patch: int
    stage_rank: int
    stage_number: int

    def key(self) -> tuple[int, int, int, int, int]:
        return (self.major, self.minor, self.patch, self.stage_rank, self.stage_number)


def normalize_tag(tag: object) -> str:
    return str(tag or "").strip().removeprefix("v")


def parse_version(value: object) -> ParsedVersion | None:
    text = normalize_tag(value)
    match = _VERSION_RE.fullmatch(text)
    if not match:
        return None
    stage = (match.group("stage") or "stable").lower()
    return ParsedVersion(
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        _STAGE_RANK.get(stage, 0),
        int(match.group("num") or 0),
    )


def is_newer_version(candidate: object, current: object = APP_VERSION) -> bool:
    candidate_version = parse_version(candidate)
    current_version = parse_version(current)
    if candidate_version is None or current_version is None:
        return False
    return candidate_version.key() > current_version.key()


def _release_allowed(release: dict, channel: str) -> bool:
    if not isinstance(release, dict) or bool(release.get("draft")):
        return False
    tag = normalize_tag(release.get("tag_name"))
    if parse_version(tag) is None:
        return False
    # Beta builds may see both beta/prerelease and stable releases. A stable
    # channel intentionally ignores GitHub prereleases.
    if str(channel).lower() == "stable" and bool(release.get("prerelease")):
        return False
    return True


def select_best_release(releases: Iterable[dict], *, channel: str = BUILD_CHANNEL) -> dict | None:
    candidates = [item for item in releases if _release_allowed(item, channel)]
    if not candidates:
        return None
    candidates.sort(key=lambda item: parse_version(item.get("tag_name")).key(), reverse=True)
    return candidates[0]


def check_for_updates(*, request_get=None, timeout=(4, 8)) -> dict:
    """Check GitHub Releases after an explicit user action.

    ``request_get`` exists for deterministic unit tests. Production calls use
    requests.get and send only a generic User-Agent/Accept header.
    """
    if request_get is None:
        import requests
        request_get = requests.get
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"DrawStudio/{APP_VERSION}",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    try:
        response = request_get(GITHUB_RELEASES_API, headers=headers, timeout=timeout)
        response.raise_for_status()
        releases = response.json()
    except Exception as error:
        raise UpdateCheckError(f"Could not check GitHub Releases: {error}") from error
    if not isinstance(releases, list):
        raise UpdateCheckError("GitHub returned an unexpected releases response.")

    release = select_best_release(releases)
    if release is None:
        return {
            "current_version": APP_VERSION,
            "latest_version": "",
            "update_available": False,
            "release_url": GITHUB_RELEASES_PAGE,
            "release_name": "",
            "prerelease": False,
            "message": "No published Draw Studio release was found yet.",
        }

    latest = normalize_tag(release.get("tag_name"))
    available = is_newer_version(latest, APP_VERSION)
    url = str(release.get("html_url") or GITHUB_RELEASES_PAGE)
    name = str(release.get("name") or release.get("tag_name") or latest)[:160]
    if available:
        message = f"Download version {latest}"
    else:
        message = "You are on the latest version."
    return {
        "current_version": APP_VERSION,
        "latest_version": latest,
        "update_available": available,
        "release_url": url,
        "release_name": name,
        "prerelease": bool(release.get("prerelease")),
        "message": message,
    }
