"""Paint preparation via Windows UI Automation; no canvas input or document clearing."""
from __future__ import annotations
import base64
import json
import os
import re
import subprocess
import time

# Kept inline so frozen builds need no PowerShell resource or Python COM package.
_SCRIPT = r'''
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]HANDLE)
$process=Get-Process -Id $root.Current.ProcessId
if ($process.ProcessName -notmatch '^(mspaint|PaintApp|Paint)$') { throw 'Target is not Microsoft Paint.' }
$all=$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
$rows=@()
for($i=0;$i -lt $all.Count;$i++) {
 $e=$all.Item($i); $c=$e.Current; $b=$c.BoundingRectangle
 if($c.IsOffscreen -or !$c.IsEnabled -or $b.Width -le 0 -or $b.Height -le 0){continue}
 $label=''; if($c.LabeledBy){$label=$c.LabeledBy.Current.Name}
 $v=''; try{$v=$e.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value}catch{}
 $rows+=@{id=$i;name=$c.Name;label=$label;kind=$c.ControlType.ProgrammaticName;rect=@($b.Left,$b.Top,$b.Right,$b.Bottom);value=$v}
}
ACTION
ConvertTo-Json -InputObject @($rows) -Depth 5 -Compress
'''


def automation(handle, *, element=None, action=None, cancelled=lambda:False):
    if os.name!='nt':raise OSError('Automatic Paint preparation requires Windows.')
    if cancelled():raise InterruptedError('Paint preparation cancelled.')
    command=''
    if element is not None:
        # Re-resolve by identity and rectangle; never trust an old tree index.
        payload=base64.b64encode(json.dumps(element).encode()).decode()
        command=f"$wanted=([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{payload}')) | ConvertFrom-Json)\n"
        command+=r'''
$matches=@($rows | Where-Object { $_.name -eq $wanted.name -and $_.kind -eq $wanted.kind -and (($_.rect -join ',') -eq ($wanted.rect -join ',')) })
if($matches.Count -ne 1){throw 'Paint controls moved or are ambiguous. Retry preparation.'}
$e=$all.Item([int]$matches[0].id)
'''
        if action=='invoke':
            command+=r'''
try{$e.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()}
catch [System.InvalidOperationException] {$e.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()}
'''
        elif action=='size':
            command+=r'''
$p=$e.GetCurrentPattern([System.Windows.Automation.RangeValuePattern]::Pattern)
if($p.Current.Minimum -gt 1 -or $p.Current.Maximum -lt 1){throw 'Paint size does not expose a 1 px value.'}
$p.SetValue(1)
if($p.Current.Value -ne 1){throw 'Paint did not accept 1 px.'}
'''
        else:raise ValueError('Unsupported Paint control action.')
    script=_SCRIPT.replace('HANDLE',str(int(handle))).replace('ACTION',command)
    encoded=base64.b64encode(script.encode('utf-16-le')).decode()
    executable=os.path.join(os.environ.get('SystemRoot',r'C:\Windows'),'System32','WindowsPowerShell','v1.0','powershell.exe')
    process=subprocess.Popen([executable,'-NoProfile','-NonInteractive','-EncodedCommand',encoded],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    deadline=time.monotonic()+12
    try:
        while True:
            if cancelled():raise InterruptedError('Paint preparation cancelled.')
            if time.monotonic()>deadline:raise TimeoutError('Paint controls did not respond. Close any open menu and retry.')
            try:out,err=process.communicate(timeout=.1);break
            except subprocess.TimeoutExpired:pass
        if process.returncode:raise ValueError(err.decode('utf-8',errors='replace').strip()[-1200:])
        data=json.loads(out.decode('utf-8-sig'))
        return data if isinstance(data,list) else [data]
    finally:
        if process.poll() is None:process.kill();process.communicate()


def find_control(nodes, names, *, kind=None):
    def matches(n):
        text=str(n.get('label') or n.get('name') or '').strip().casefold()
        text=re.sub(r'\s*\([^)]*\)\s*$','',text).rstrip(':').strip()
        return text in names and (kind is None or str(n.get('kind','')).endswith(kind))
    hits=[n for n in nodes if matches(n)]
    if len(hits)!=1:raise ValueError('Paint control not uniquely identified: '+', '.join(names))
    return hits[0]


def center(node):
    l,t,r,b=node['rect']
    return round((l+r)/2),round((t+b)/2)


def rgb_controls(nodes):
    result={}
    for key,names in (('RedField',('red','röd')),('GreenField',('green','grön')),('BlueField',('blue','blå'))):
        try:field=find_control(nodes,names,kind='Edit')
        except ValueError:
            label=find_control(nodes,names,kind='Text')
            lx,ly=center(label)
            # Paint puts labels beside numeric edits. Associate the same row,
            # accepting only one nearby field instead of guessing field order.
            hits=[n for n in nodes if str(n.get('kind','')).endswith('Edit')
                  and abs(center(n)[1]-ly)<(n['rect'][3]-n['rect'][1])*.5
                  and 0<=label['rect'][0]-n['rect'][2]<=max(80,n['rect'][2]-n['rect'][0])]
            if len(hits)!=1:raise ValueError('Could not identify Paint '+key+'. Open Edit colors in RGB mode.')
            field=hits[0]
        if not str(field.get('value','')).isdigit() or not 0<=int(field['value'])<=255:
            raise ValueError('Paint RGB field did not expose a valid numeric value.')
        result[key]=center(field)
    if len(set(result.values()))!=3:raise ValueError('Paint RGB fields overlap.')
    result['ConfirmColor']=center(find_control(nodes,('ok',),kind='Button'))
    return result


def ensure_paint(enumerate_windows, *, cancelled=lambda:False, launch=None, wait=None):
    from PaintFullCalibration import choose_paint_window
    from threading import Event
    wait=wait or Event().wait
    def candidates():return [n for n in enumerate_windows() if re.search(r'(?:^|[–—-]\s*)Paint\s*$',str(n.get('title','')),re.I)]
    if cancelled():raise InterruptedError()
    found=candidates()
    if found:return choose_paint_window(found)
    if launch is None:
        launch=lambda:subprocess.Popen([os.path.join(os.environ.get('SystemRoot',r'C:\Windows'),'System32','mspaint.exe')])
    launch()
    for _ in range(40):
        if cancelled():raise InterruptedError('Paint preparation cancelled.')
        found=candidates()
        if found:return choose_paint_window(found)
        wait(.2)
    raise ValueError('Paint did not open in time. Open it and retry.')


def prepare_controls(handle, *, cancelled=lambda:False, backend=automation):
    """Select pencil/1 px and capture fresh RGB controls; dismiss with Cancel."""
    def scan():return backend(handle,cancelled=cancelled)
    def invoke(node):return backend(handle,element=node,action='invoke',cancelled=cancelled)
    nodes=scan()
    # An already-open color dialog is dismissed without accepting changes.
    try:rgb_controls(nodes)
    except ValueError:pass
    else:
        invoke(find_control(nodes,('cancel','avbryt'),kind='Button'));nodes=scan()
    pencil=find_control(nodes,('pencil','penna','blyertspenna'),kind='Button')
    invoke(pencil)
    nodes=scan()
    size=find_control(nodes,('size','brush size','pencil size','storlek','penselstorlek','pennstorlek','thickness','tjocklek'),kind='Slider')
    backend(handle,element=size,action='size',cancelled=cancelled)
    nodes=scan()
    opener=find_control(nodes,('edit colors','edit colours','redigera färger'),kind='Button')
    invoke(opener)
    # Poll the UI tree, not a fixed dialog coordinate or a canvas test stroke.
    deadline=time.monotonic()+5
    while True:
        nodes=scan()
        try:
            controls=rgb_controls(nodes)
            cancel=find_control(nodes,('cancel','avbryt'),kind='Button')
            break
        except ValueError:
            if time.monotonic()>deadline:raise ValueError('Paint color dialog could not be calibrated. Close the dialog and retry in RGB mode.')
    invoke(cancel)
    controls['OpenCustomColor']=center(opener)
    return controls
