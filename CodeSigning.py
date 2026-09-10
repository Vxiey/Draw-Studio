"""Opt-in Authenticode signing using a provisioned Windows certificate store.

No certificate creation, private-key export or trust-store changes are performed.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path


class SigningError(RuntimeError):pass


def signing_configuration(environ=None):
    env=os.environ if environ is None else environ
    thumb=str(env.get('IMAGEDRAWBOT_SIGNING_THUMBPRINT','')).replace(' ','')
    if not re.fullmatch(r'[0-9a-fA-F]{40}',thumb):
        raise SigningError('Set IMAGEDRAWBOT_SIGNING_THUMBPRINT to a provisioned code-signing certificate thumbprint.')
    tool=env.get('IMAGEDRAWBOT_SIGNTOOL') or shutil.which('signtool.exe')
    if not tool or not Path(tool).is_file():raise SigningError('Set IMAGEDRAWBOT_SIGNTOOL to Windows SDK signtool.exe.')
    if any(c in str(tool) for c in ('"','$','\n','\r')):raise SigningError('Unsupported SignTool path.')
    return str(Path(tool).resolve()),thumb.upper()


def sign_arguments(tool,thumb,path):
    return [tool,'sign','/sha1',thumb,'/s','My','/fd','SHA256','/tr','http://timestamp.digicert.com','/td','SHA256',str(path)]


def validate_certificate(config):
    tool,thumb=config
    # Require RSA and a code-signing EKU. Public trust is checked separately by
    # SignTool /pa against the file, not inferred from subject/display names.
    command=(f"$ErrorActionPreference='Stop';$c=Get-Item Cert:\\CurrentUser\\My\\{thumb};"
             "if(!$c.HasPrivateKey){throw 'Private signing key is unavailable'};"
             "if($c.PublicKey.Oid.Value -ne '1.2.840.113549.1.1.1'){throw 'An RSA certificate is required'};"
             "if(!($c.EnhancedKeyUsageList.ObjectId.Value -contains '1.3.6.1.5.5.7.3.3')){throw 'Code-signing EKU is missing'}")
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],check=True,timeout=30)


def verify(path,config):
    result=subprocess.run([config[0],'verify','/pa','/all',str(path)],capture_output=True,timeout=90)
    return result.returncode==0


def sign_file(path,config):
    subprocess.run(sign_arguments(*config,path),check=True,timeout=180)
    # /tw makes a missing timestamp fail this strict release path as a warning.
    subprocess.run([config[0],'verify','/pa','/all','/tw',str(path)],check=True,timeout=90)


def sign_distribution(root,config):
    files=sorted(p for p in Path(root).rglob('*') if p.is_file() and p.suffix.lower() in ('.exe','.dll','.pyd'))
    if not files:raise SigningError('No native release binaries were found.')
    for path in files:
        # Preserve valid upstream signatures; timestamp/sign unsigned native
        # dependencies as part of the distributed application.
        if not verify(path,config):sign_file(path,config)
    for path in files:
        if not verify(path,config):raise SigningError(f'Signature verification failed: {path.name}')
    return len(files)


def inno_arguments(config):
    tool,thumb=config
    command=f'$q{tool}$q sign /sha1 {thumb} /s My /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $f'
    return ['/DSignRelease','/Simagedrawbot='+command]
