"""Create a release-grade Windows package for Draw Studio.

Run on Windows:
    py -3 build_release.py
    py -3 build_release.py --installer

The default artifact is a PyInstaller onedir build packed as a ZIP. With
--installer, Inno Setup is used to create a per-user installer as well.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from Version import APP_VERSION

BASE = Path(__file__).resolve().parent
DIST = BASE / "dist" / "DrawStudio"
RELEASE = BASE / "release"


def run(command: list[str], *, cwd: Path = BASE) -> None:
    print("+", " ".join(map(str, command)))
    subprocess.run(command, cwd=cwd, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_onedir(destination: Path) -> None:
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(DIST.rglob("*")):
            if path.is_file():
                relative = Path("DrawStudio") / path.relative_to(DIST)
                archive.write(path, relative.as_posix())


def find_iscc() -> Path | None:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
    ]
    found = shutil.which("iscc") or shutil.which("ISCC.exe")
    if found:
        candidates.insert(0, Path(found))
    return next((path for path in candidates if path.is_file()), None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--installer", action="store_true", help="Also build the Inno Setup installer")
    parser.add_argument("--skip-tests", action="store_true", help="Skip Python tests (not recommended for releases)")
    parser.add_argument("--gpu", action="store_true", help="Bundle optional NVIDIA CUDA/CuPy acceleration")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Release EXEs must be built on Windows. Use the included GitHub Actions workflow or Build-Release.bat on a Windows PC.")
    github_ref=os.environ.get('GITHUB_REF_NAME','').strip()
    github_ref_type=os.environ.get('GITHUB_REF_TYPE','').strip()
    if github_ref_type == 'tag' and github_ref and github_ref != f'v{APP_VERSION}':
        raise SystemExit(f'Git tag {github_ref!r} does not match Version.py ({APP_VERSION}). Expected tag v{APP_VERSION}.')

    # A clean Windows machine may have Python but not the source dependencies.
    # Bootstrap only the packages declared by the project before running tests.
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run([sys.executable, "-m", "pip", "install", "-r", str(BASE / "requirements.txt")])

    if not args.skip_tests:
        run([sys.executable, "-m", "unittest", "discover", "-v"])
        run([sys.executable, "DrawBot.py", "--self-test"])

    run([sys.executable, "build_exe.py"] + (["--gpu"] if args.gpu else []))
    exe = DIST / "DrawStudio.exe"
    if not exe.is_file() or exe.read_bytes()[:2] != b"MZ":
        raise SystemExit("Release build did not produce a valid DrawStudio.exe.")

    # Run the frozen binary's non-interactive logic smoke test before packaging.
    run([str(exe), "--self-test"], cwd=DIST)

    RELEASE.mkdir(exist_ok=True)
    # Standard artifact template: DrawStudio-{APP_VERSION}-Windows-x64.zip
    suffix = "-CUDA" if args.gpu else ""
    zip_path = RELEASE / f"DrawStudio-{APP_VERSION}-Windows-x64{suffix}.zip"
    zip_onedir(zip_path)
    hash_rows = [f"{sha256(zip_path)}  {zip_path.name}"]

    if args.installer and args.gpu:
        raise SystemExit("The CUDA release currently ships as a ZIP. Build the standard installer separately without --gpu.")

    if args.installer:
        iscc = find_iscc()
        if iscc is None:
            raise SystemExit("Inno Setup 6 was not found. Install it or run without --installer.")
        run([str(iscc), f"/DMyAppVersion={APP_VERSION}", str(BASE / "installer" / "DrawStudio.iss")])
        setup = RELEASE / f"DrawStudio-{APP_VERSION}-Windows-x64-Setup.exe"
        if not setup.is_file() or setup.read_bytes()[:2] != b"MZ":
            raise SystemExit("Installer build did not produce the expected Setup.exe.")
        hash_rows.append(f"{sha256(setup)}  {setup.name}")

    checksum = RELEASE / f"DrawStudio-{APP_VERSION}-SHA256.txt"
    checksum.write_text("\n".join(hash_rows) + "\n", encoding="utf-8")
    print("\nRelease artifacts:")
    for row in hash_rows:
        print(" ", row)
    print(" ", checksum)
    print("\nThe EXE and installer are unsigned until you add your own Authenticode code-signing certificate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
