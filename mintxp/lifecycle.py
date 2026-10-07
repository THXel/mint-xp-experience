"""Cross-scope removal, read-only status and allowlisted diagnostic export."""
import datetime,hashlib,json,os,platform,shutil,stat,subprocess,re
from pathlib import Path
from .engine import Conflict,atomic,encoded
from .panel_state import equivalent,preference
COMPONENTS=('gtk','shell','cursor','icons','wallpaper','fonts','explorer','control','menu','taskbar','tray','default_manager','sounds','games','welcome_screen')
PREFIXES={'sounds':('.local/share/sounds/Mint-XP-Experience-Sounds/',),'icons':('.local/share/icons/Mint-XP-Experience-Icons/',),'tray':('.local/share/cinnamon/applets/mintxp-tray@mintxp/',),'gtk':('.themes/',),'shell':('.themes/',),'cursor':('.local/share/icons/Mint-XP-Experience-Cursors/',),'wallpaper':('.local/share/backgrounds/',),'explorer':('.local/share/xp-explorer/',),'control':('.local/share/xp-control-panel/',),'menu':('.local/share/cinnamon/applets/mintxp-menu@mintxp/',),'taskbar':('.local/share/cinnamon/applets/grouped-window-list@cinnamon.org/',),'default_manager':('.config/mimeapps.list',),'welcome_screen':('.local/share/mint-xp-welcome/','.config/autostart/mintxp-welcome.desktop')}
SCHEMAS={'icons':('icon-theme',),'tray':('enabled-applets','next-applet-id'),'fonts':('font',),'sounds':('sound/','org.cinnamon.sounds/','wm.preferences/bell-sound'),'gtk':('gtk-theme','wm.preferences/theme','button-layout'),'shell':('org.cinnamon.theme/',),'cursor':('cursor-theme',),'wallpaper':('background/',),'menu':('enabled-applets',),'taskbar':('panel-zone-',)}
SYSTEM=Path('/var/lib/mint-xp-experience-system')

def file_matches(engine,key,expected):
    try:
        p=engine.path(key)
        from . import mime_state
        if key==mime_state.REL:
            mime_state.parse(p.read_bytes() if p.exists() else b'');return True
        if expected is None:return not p.exists()
        return p.is_file() and stat.S_IMODE(p.stat().st_mode)==expected['mode'] and hashlib.sha256(p.read_bytes()).hexdigest()==expected['sha256']
    except (OSError,ValueError,Conflict):return False

def status(engine):
    current=engine.read_current();changed_files=[k for k,v in current['files'].items() if not file_matches(engine,k,v)];changed_settings=[]
    for key,value in current['settings'].items():
        try:
            actual=engine.settings.get(key)
            adjustable=key in ('org.cinnamon.desktop.sound/event-sounds','org.gnome.desktop.sound/event-sounds') and actual in (None,'true','false')
            if not equivalent(key,actual,value) and not preference(key,actual) and not adjustable:changed_settings.append(key)
        except Exception:changed_settings.append(key)
    rows=[]
    for key in COMPONENTS:
        enabled=bool(current.get('installed') and current.get('options',{}).get(key))
        changed=any(any(p.startswith(prefix) for prefix in PREFIXES.get(key,())) for p in changed_files) or any(any(part in k for part in SCHEMAS.get(key,())) for k in changed_settings)
        external=not enabled and any((engine.home/p.rstrip('/')).exists() for p in PREFIXES.get(key,()) if not p.startswith('.themes/'))
        rows.append({'component':key,'status':'changed' if changed else 'installed' if enabled else 'external' if external else 'disabled'})
    rows.append({'component':'system_appearance','status':'unverified' if SYSTEM.exists() else 'disabled'})
    history=sorted((engine.state/'history').glob('*.json'));snapshots=sorted((engine.state/'snapshots').glob('*.json'))
    def date(paths):return datetime.datetime.fromtimestamp(max(p.stat().st_mtime for p in paths),datetime.timezone.utc).isoformat() if paths else None
    baseline=engine.state/'baseline.json'
    recorded=engine.read('baseline.json',{}).get('created_at')
    try:recorded=datetime.datetime.fromisoformat(recorded).isoformat() if isinstance(recorded,str) else None
    except ValueError:recorded=None
    return {'installed':bool(current.get('installed')),'pending':bool(engine.read('pending.json')),'combined_phase':next((phase for phase in ('preflight-complete','system-step-not-completed','system-restored','complete') if phase==engine.read('combined-uninstall.json',{}).get('phase')),None),'components':rows,'changed_file_count':len(changed_files),'changed_setting_count':len(changed_settings),'baseline_at':recorded,'last_backup_at':date(snapshots),'last_transaction_at':date(history),'backup_count':len(snapshots)}

class SystemBridge:
    def present(self):return SYSTEM.exists()
    def undo(self):
        script=SYSTEM/'appearance.py'
        if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
            cmd=['/usr/bin/pkexec','--disable-internal-agent','/usr/bin/python3','-I','-B',str(script),'undo']
        else:cmd=['sudo','/usr/bin/python3','-I','-B',str(script),'undo']
        result=subprocess.run(cmd)
        if result.returncode in (126,127):raise Conflict('Administrator authentication was cancelled or unavailable. The user installation is unchanged.')
        if result.returncode:raise Conflict('System rollback could not complete. The user installation is unchanged; inspect the system rollback message.')

def uninstall_all(engine,bridge=None):
    bridge=bridge or SystemBridge()
    with engine.lock():
        if engine.read('pending.json'):raise Conflict('Recover the interrupted user operation before uninstalling.')
        current=engine.read_current();errors=engine.check(current,allow_preferences=True) if current.get('installed') else []
        if errors:raise Conflict('Changes protected:\n'+'\n'.join(errors))
        base=engine.read('baseline.json')
        if base:engine.verify_objects(base)
        # The lock covers authentication, system undo and user undo; another manager
        # cannot install into the gap between these scopes.
        state={'phase':'preflight-complete'};engine.save('combined-uninstall.json',state)
        if bridge.present():
            try:bridge.undo()
            except BaseException:
                engine.save('combined-uninstall.json',{'phase':'system-step-not-completed'});raise
        engine.save('combined-uninstall.json',{'phase':'system-restored'})
        result=engine.uninstall_unlocked() if current.get('installed') else 'User package already uninstalled'
        engine.save('combined-uninstall.json',{'phase':'complete'});return result

def diagnostic(engine,version):
    # Construct from an allowlist, never sanitize a dump of raw logs/configuration.
    snapshot=status(engine)
    return {'format':1,'package_version':version if isinstance(version,str) and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?',version) is not None else 'unknown','platform':{'system':platform.system(),'architecture':platform.machine(),'python':platform.python_version()},'installation':snapshot,'privacy':{'contains_paths':False,'contains_file_lists':False,'contains_credentials':False,'uploaded':False}}

def export_diagnostic(engine,path,version):
    path=Path(path)
    # New file only: neither replace another document nor follow a symlink.
    data=encoded(diagnostic(engine,version));fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    return path

def prepare_rescue(engine,root):
    """Retained recovery copy lives beside backups, independent of installed GUI files."""
    root=Path(root);target=engine.state/'rescue';module=target/'mintxp'
    for p in (target,module,*[module/n for n in ('__init__.py','engine.py','panel_state.py','mime_state.py','lifecycle.py','rescue.py')],target/'rescue.py',target/'manifest.json'):
        if p.is_symlink():raise Conflict('Linked rescue destination is protected')
    module.mkdir(parents=True,exist_ok=True,mode=0o700)
    paths={}
    for name in ('__init__.py','engine.py','panel_state.py','mime_state.py','lifecycle.py','rescue.py'):
        data=(root/'mintxp'/name).read_bytes();atomic(module/name,data);paths['mintxp/'+name]=hashlib.sha256(data).hexdigest()
    data=b'from mintxp.rescue import main\nif __name__=="__main__":main()\n';atomic(target/'rescue.py',data);paths['rescue.py']=hashlib.sha256(data).hexdigest()
    atomic(target/'manifest.json',encoded(paths));return target/'rescue.py'
