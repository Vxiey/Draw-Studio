"""User-triggered GitHub release checks and verified Windows installer updates."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from Version import APP_VERSION, BUILD_CHANNEL

GITHUB_REPOSITORY = "Vxiey/Draw-Studio"
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
    parsed = parse_version(tag)
    if parsed is None:
        return False
    channel = str(channel or "beta").lower()
    # Channel floors prevent an RC build from being pointed back toward beta
    # releases. Higher patch versions still compare normally inside the allowed
    # channel set. Stable accepts published non-prereleases only.
    if channel == "stable":
        return not bool(release.get("prerelease")) and parsed.stage_rank >= _STAGE_RANK["stable"]
    if channel == "rc":
        return parsed.stage_rank >= _STAGE_RANK["rc"]
    if channel == "beta":
        return parsed.stage_rank >= _STAGE_RANK["beta"]
    return True


def select_best_release(releases: Iterable[dict], *, channel: str | None = None) -> dict | None:
    channel = BUILD_CHANNEL if channel is None else str(channel)
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
        "installer": installer_asset(release),
    }


def installer_asset(release):
    """Only the exact Windows installer for this release is eligible."""
    from urllib.parse import urlparse,unquote
    version=normalize_tag(release.get('tag_name'))
    if parse_version(version) is None:return None
    name=f'DrawStudio-{version}-Windows-x64-Setup.exe'
    hits=[]
    for asset in release.get('assets') or ():
        if not isinstance(asset,dict) or asset.get('name')!=name:continue
        url=str(asset.get('browser_download_url') or '')
        parsed=urlparse(url)
        expected=f'/{GITHUB_REPOSITORY}/releases/download/{release["tag_name"]}/{name}'
        if parsed.scheme!='https' or parsed.netloc!='github.com' or unquote(parsed.path)!=expected or parsed.query or parsed.fragment:continue
        digest=str(asset.get('digest') or '')
        if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}',digest):continue
        size=asset.get('size')
        if type(size) is not int or not 0<size<=2*1024**3:continue
        hits.append(dict(name=name,url=url,sha256=digest[7:].lower(),size=size,version=version))
    return hits[0] if len(hits)==1 else None


def download_installer(asset, *, directory=None, request_get=None, cancelled=lambda:False, progress=lambda done,total:None):
    """Stream to a unique staging file; publish only after size/hash validation."""
    import hashlib,os,tempfile,time
    from pathlib import Path
    from urllib.parse import urlparse
    if request_get is None:
        import requests
        request_get=requests.get
    if directory is None:
        from RuntimePaths import data_dir
        directory=data_dir()/'updates'
    root=Path(directory);root.mkdir(parents=True,exist_ok=True)
    # Revalidate metadata even when called without check_for_updates.
    version=asset.get('version','');name=asset.get('name','')
    parts=urlparse(str(asset.get('url',''))).path.split('/')
    if len(parts)<3:raise UpdateCheckError('Invalid installer URL.')
    tag=parts[-2]
    candidate=dict(tag_name=tag,assets=[dict(name=name,browser_download_url=asset.get('url'),digest='sha256:'+str(asset.get('sha256','')),size=asset.get('size'))])
    if installer_asset(candidate)!=asset or normalize_tag(tag)!=version:raise UpdateCheckError('Invalid installer metadata.')
    if cancelled():raise InterruptedError('Update cancelled.')
    fd,temp=tempfile.mkstemp(prefix='download-',suffix='.part',dir=root)
    path=Path(temp);response=None
    try:
        total=0;digest=hashlib.sha256();deadline=time.monotonic()+1800
        with os.fdopen(fd,'wb') as output:
            response=request_get(asset['url'],stream=True,timeout=(5,15),headers={'User-Agent':f'DrawStudio/{APP_VERSION}'})
            response.raise_for_status()
            final=urlparse(str(getattr(response,'url',asset['url'])))
            if final.scheme!='https' or final.hostname not in ('github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'):
                raise UpdateCheckError('Installer download redirected to an unexpected host.')
            for chunk in response.iter_content(chunk_size=256*1024):
                if cancelled():raise InterruptedError('Update cancelled.')
                if time.monotonic()>deadline:raise UpdateCheckError('Update download timed out.')
                if not chunk:continue
                total+=len(chunk)
                if total>asset['size']:raise UpdateCheckError('Installer exceeds its published size.')
                digest.update(chunk);output.write(chunk);progress(total,asset['size'])
            output.flush();os.fsync(output.fileno())
        if cancelled():raise InterruptedError('Update cancelled.')
        if total!=asset['size'] or digest.hexdigest()!=asset['sha256']:
            raise UpdateCheckError('Installer checksum or size mismatch. Nothing was installed; try again.')
        with path.open('rb') as check:
            if check.read(2)!=b'MZ':raise UpdateCheckError('Downloaded file is not a Windows installer.')
        destination=path.with_suffix('.exe');path.replace(destination)
        return str(destination)
    finally:
        if response is not None and hasattr(response,'close'):response.close()
        path.unlink(missing_ok=True)


def launch_installer(path, asset, *, executable=None, launcher=None, cancelled=lambda:False):
    """Recheck staged bytes and open the normal installer, never a shell command."""
    import hashlib,os,subprocess,sys
    from pathlib import Path
    if os.name!='nt':raise UpdateCheckError('Automatic installation requires Windows.')
    target=Path(path)
    digest=hashlib.sha256()
    with target.open('rb') as stream:
        if stream.read(2)!=b'MZ':raise UpdateCheckError('Invalid installer.')
        stream.seek(0)
        for block in iter(lambda:stream.read(1024*1024),b''):
            if cancelled():raise InterruptedError('Update cancelled.')
            digest.update(block)
    if target.stat().st_size!=asset['size'] or digest.hexdigest()!=asset['sha256']:
        raise UpdateCheckError('Installer changed after download; check for updates again.')
    args=[str(target),'/SP-','/NORESTART']
    current=Path(executable or sys.executable)
    # Installed builds update in place. Portable/source builds use the normal
    # installer destination rather than overwriting a checkout or random folder.
    if current.name.lower()=='drawstudio.exe' and (current.parent/'unins000.exe').is_file():
        args.append('/DIR='+str(current.parent))
    if cancelled():raise InterruptedError('Update cancelled.')
    return (launcher or subprocess.Popen)(args)
