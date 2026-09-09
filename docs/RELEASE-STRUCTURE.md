# Download and package layout

## Windows installer

`DrawStudio-<version>-Windows-x64-Setup.exe` installs the complete app and provides
an uninstaller. Python is bundled. Use this for normal installation and in-app
updates. Profiles/settings are stored separately from the installed program.

## Portable ZIP

`DrawStudio-<version>-Windows-x64.zip` contains a `DrawStudio` folder with
`DrawStudio.exe` and its supporting files. Extract everything, then launch the
EXE from that folder. Moving only the EXE or running it inside the ZIP will not
work reliably. Using the in-app installer from a portable build performs a
normal installation; it does not patch the portable folder.

## Source archive

GitHub's source archives contain Python code, build scripts and documentation.
They do not contain the packaged application. Use `Start.bat` with Python 3.10+
on Windows, or download the installer/portable release instead.

## Verification files

Each release includes `DrawStudio-<version>-SHA256.txt` and a manifest with file
sizes, version metadata and checksums. Hash verification checks file integrity;
it does not provide a trusted publisher signature. Published rc2 is unsigned.

[Downloads](https://github.com/Vxiey/Draw-Studio/releases/tag/v1.0.133-rc2)
