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

_INVOKE_ACTION = r'''
$activated=$false
$pattern=$null
if($e.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$pattern)) {
    ([System.Windows.Automation.InvokePattern]$pattern).Invoke(); $activated=$true
}
if(!$activated) {
    $pattern=$null
    if($e.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$pattern)) {
        ([System.Windows.Automation.SelectionItemPattern]$pattern).Select(); $activated=$true
    }
}
if(!$activated) {
    $pattern=$null
    if($e.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern,[ref]$pattern)) {
        ([System.Windows.Automation.TogglePattern]$pattern).Toggle(); $activated=$true
    }
}
if(!$activated) {
    $pattern=$null
    if($e.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$pattern)) {
        $expand=[System.Windows.Automation.ExpandCollapsePattern]$pattern
        if($expand.Current.ExpandCollapseState -ne [System.Windows.Automation.ExpandCollapseState]::Expanded) {$expand.Expand()}
        $activated=$true
    }
}
if(!$activated) {
    $pattern=$null
    if($e.TryGetCurrentPattern([System.Windows.Automation.LegacyIAccessiblePattern]::Pattern,[ref]$pattern)) {
        ([System.Windows.Automation.LegacyIAccessiblePattern]$pattern).DoDefaultAction(); $activated=$true
    }
}
if(!$activated) {
    # Modern Paint/XAML controls sometimes expose a valid named Button without
    # InvokePattern or SelectionItemPattern. Focus + Enter is a bounded fallback
    # on that already re-resolved UI element; it never guesses a canvas position.
    try {
        $e.SetFocus()
        Start-Sleep -Milliseconds 60
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
        $activated=$true
    } catch {}
}
if(!$activated){throw 'Paint control could not be activated with supported UI Automation patterns or focused Enter.'}
'''

_CUSTOM_COLOR_NAMES = (
    'edit colors','edit colours','edit color','edit colour',
    'custom color','custom colour','more colors','more colours',
    'redigera färger','anpassad färg','fler färger',
)


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
            command+=_INVOKE_ACTION
        elif action=='size':
            command+=r'''
$pattern=$null
if(!$e.TryGetCurrentPattern([System.Windows.Automation.RangeValuePattern]::Pattern,[ref]$pattern)) {throw 'Paint size control does not expose RangeValuePattern.'}
$p=[System.Windows.Automation.RangeValuePattern]$pattern
if($p.Current.Minimum -gt 1 -or $p.Current.Maximum -lt 1){throw 'Paint size does not expose a 1 px value.'}
$p.SetValue(1)
if([Math]::Abs($p.Current.Value-1) -gt 0.001){throw 'Paint did not accept 1 px.'}
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


def _normalized_name(node):
    text=str(node.get('label') or node.get('name') or '').strip().casefold()
    return re.sub(r'\s*\([^)]*\)\s*$','',text).rstrip(':').strip()


def find_control(nodes, names, *, kind=None):
    names=tuple(str(name).casefold() for name in names)
    def matches(n):
        return _normalized_name(n) in names and (kind is None or str(n.get('kind','')).endswith(kind))
    hits=[n for n in nodes if matches(n)]
    if len(hits)!=1:raise ValueError('Paint control not uniquely identified: '+', '.join(names))
    return hits[0]


def find_custom_color_opener(nodes):
    """Find Paint's Edit colors control across classic and current XAML variants."""
    names=set(_CUSTOM_COLOR_NAMES)
    hits=[]
    for node in nodes:
        kind=str(node.get('kind',''))
        if _normalized_name(node) in names and any(kind.endswith(suffix) for suffix in ('Button','MenuItem','Custom')):
            hits.append(node)
    if len(hits)!=1:
        raise ValueError('Paint Edit colors / custom color control was not uniquely identified.')
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
    """Select Pencil/1 px, open Edit colors, capture numeric RGB controls, then dismiss with Cancel."""
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
    opener=find_custom_color_opener(nodes)
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
            if time.monotonic()>deadline:raise ValueError('Paint Edit colors opened, but numeric RGB controls could not be calibrated. Keep the dialog in RGB mode and retry.')
    invoke(cancel)
    controls['OpenCustomColor']=center(opener)
    return controls
