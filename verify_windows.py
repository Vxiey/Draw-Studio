"""Verifies dependencies and GUI startup without sending mouse input."""
import subprocess
import sys
from pathlib import Path

base=Path(__file__).resolve().parent
if sys.platform!='win32':raise SystemExit('Run this check on Windows.')
log=[]
commands=[['-m','unittest','discover','-s',str(base),'-p','test_*.py','-v'],
          [str(base/'DrawBot.py'),'--self-test'],[str(base/'DrawBot.py'),'--smoke-test'],
          [str(base/'MouseProbe.py'),'--diagnostics-only']]
passed=True
for arguments in commands:
    try:
        result=subprocess.run([sys.executable,*arguments],cwd=base,capture_output=True,text=True,timeout=60)
        log.append(f'{arguments}: exit {result.returncode}\n{result.stdout}\n{result.stderr}')
        if result.returncode:passed=False;break
    except subprocess.TimeoutExpired:
        log.append('The check exceeded 60 seconds and was stopped.');passed=False;break
log.append('PASSED: startup and logic. Actual drawing in the target application still needs verification.' if passed else 'FAILED: read the errors above.')
path=base/'verification.txt';path.write_text('\n'.join(log),encoding='utf-8')
print(log[-1]);print(f'Report: {path}')
raise SystemExit(0 if passed else 1)
