#!/usr/bin/python3
"""Explicit admin-only LightDM/Plymouth installation, with private exact backups.
GPL-3.0-or-later. Does not restart services, change autologin, GRUB or authentication.
"""
import argparse,configparser,fcntl,hashlib,io,json,os,re,shutil,stat,subprocess,tempfile,time
from pathlib import Path
PKG=Path(__file__).resolve().parents[1]
STATE=Path('/var/lib/mint-xp-experience-system')
THEME=Path('/usr/share/plymouth/themes/mint-xp-experience')
LOGIN=Path('/usr/share/themes/Mint-XP-Login')
ART=Path('/usr/share/backgrounds/mint-xp-experience-session')
CONF=Path('/etc/lightdm/slick-greeter.conf')

def sha(p):
    p=Path(p)
    if p.is_symlink():raise RuntimeError('Linked file is protected: '+str(p))
    if not p.exists():return None
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def atomic(path,data,mode=0o644):
    path=Path(path);fd,name=tempfile.mkstemp(prefix='.mintxp-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.chmod(name,mode);os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
def replace_file(source,target,mode):
    target=Path(target);fd,name=tempfile.mkstemp(prefix='.mintxp-',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as out,Path(source).open('rb') as src:shutil.copyfileobj(src,out);out.flush();os.fsync(out.fileno())
        os.chmod(name,mode);os.replace(name,target)
    finally:
        if os.path.exists(name):os.unlink(name)
def config(data,section,values):
    c=configparser.ConfigParser(interpolation=None);c.read_string(data)
    if section not in c:c[section]={}
    for key,value in values.items():c[section][key]=str(value)
    out=io.StringIO();c.write(out);return out.getvalue().encode()
def run(args,**kwargs):return subprocess.run(args,check=True,text=True,**kwargs)
def alternative():return run(['/usr/bin/update-alternatives','--query','default.plymouth'],capture_output=True).stdout

def validate_path(p):
    for parent in [p,*p.parents]:
        if parent.is_symlink():raise RuntimeError('Linked destination is protected: '+str(parent))
def objects(pkg):
    result={}
    for source,target in [(pkg/'assets/boot',THEME),(pkg/'assets/gtk',LOGIN)]:
        for p in source.rglob('*'):
            if p.is_symlink():raise RuntimeError('Linked source refused: '+str(p))
            if p.is_file():result[target/p.relative_to(source)]=p.read_bytes()
    result[ART/'login.png']=(pkg/'assets/session/login.png').read_bytes()
    # Retain the distribution's native password/keyboard symbols, not a custom password UI.
    for name in ('bullet.png','capslock.png','entry.png','keyboard.png','keymap-render.png','lock.png'):
        p=Path('/usr/share/plymouth/themes/spinner')/name
        if p.exists():result[THEME/name]=p.read_bytes()
    return result

def state():return json.loads((STATE/'state.json').read_text())
def save(s):atomic(STATE/'state.json',(json.dumps(s,indent=2)+'\n').encode(),0o600)
def verify_backups(s):
    """Retain and verify historical recovery data independently of live files."""
    for r in s['files']:
        if r['before'] is not None and sha(STATE/'backup'/r['backup'])!=r['before']:
            raise RuntimeError('Damaged backup: '+r['path'])

def guard(s,resuming=False):
    verify_backups(s)
    for r in s['files']:
        p=Path(r['path']);validate_path(p)
        allowed={r['before'],r.get('after')} if resuming else {r['after'] if s['status']=='applied' else r['before']}
        if sha(p) not in allowed:raise RuntimeError('A later change is protected: '+str(p))
    if s.get('alternative_after') and alternative() not in ([s['alternative_before'],s['alternative_after']] if resuming else [s['alternative_after'] if s['status']=='applied' else s['alternative_before']]):raise RuntimeError('Plymouth selection has changed since installation.')

def retire_restored(s):
    """A completed uninstall no longer owns the current system configuration.

    A new apply validates destinations and captures today's files and Plymouth
    selection as its own baseline. Never retire active or interrupted journals.
    """
    if s['status']!='restored':raise RuntimeError('Restore the interrupted system appearance installation first.')
    verify_backups(s)
    retired=STATE/'retired'/str(time.time_ns());retired.mkdir(parents=True,mode=0o700)
    shutil.move(str(STATE/'backup'),str(retired/'backup'))
    shutil.move(str(STATE/'state.json'),str(retired/'state.json'))

def restore_alternative(s):
    if not s['boot']:return
    before=s['alternative_before'];value=re.search(r'^Value: (.+)$',before,re.M).group(1)
    run(['/usr/bin/update-alternatives','--remove','default.plymouth',str(THEME/'mint-xp-experience.plymouth')])
    run(['/usr/bin/update-alternatives','--auto','default.plymouth'] if '\nStatus: auto\n' in before else ['/usr/bin/update-alternatives','--set','default.plymouth',value])
    if alternative()!=before:raise RuntimeError('Previous Plymouth selection could not be restored exactly.')

def shutdown_module():
    import importlib.util
    spec=importlib.util.spec_from_file_location('mintxp_system_shutdown',Path(__file__).with_name('shutdown.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.STATE=STATE/'shutdown'
    return module

def undo(failed=False):
    s=state()
    if s['status']=='restored':verify_backups(s);print('Already restored.');return
    if not failed:guard(s,s['status'] in ('restoring','installing'))
    shutdown_module().undo()
    s['status']='restoring';save(s)
    # Restore the boot images before removing the theme they referenced.
    for r in sorted(s['files'],key=lambda r:not r['path'].startswith('/boot/')):
        p=Path(r['path'])
        if r['before'] is None:
            if p.exists():p.unlink()
        else:replace_file(STATE/'backup'/r['backup'],p,r['mode'])
    restore_alternative(s)
    for p in sorted(s['created_dirs'],key=len,reverse=True):
        try:Path(p).rmdir()
        except OSError:pass
    s['status']='restored';save(s);guard(s);print('Previous boot and login appearance restored. No restart performed.')

def apply(boot=True,login=True):
    if (STATE/'state.json').exists():
        s=state()
        if s['status']=='applied':
            guard(s)
            if (s['boot'],s['login'])!=(boot,login):raise RuntimeError('Restore the existing system installation before choosing different components.')
            if boot:
                shutdown=shutdown_module()
                shutdown.apply(PKG)
                shutil.copy2(PKG/'system/shutdown.py',STATE/'shutdown.py')
                shutil.copy2(Path(__file__),STATE/'appearance.py')
            print('Already installed; verification OK. Shutdown appearance updated.');return
        if s['status']!='restored':raise RuntimeError('An interrupted system appearance journal exists. Restore/inspect it before a new installation.')
        retire_restored(s)
    if not boot and not login:raise RuntimeError('No component selected.')
    os_release=Path('/etc/os-release').read_text()
    if 'ID=linuxmint' not in os_release or 'VERSION_ID="22.3"' not in os_release:raise RuntimeError('This preview requires Linux Mint 22.3.')
    if boot and Path('/etc/plymouth/plymouthd.conf').exists():
        c=configparser.ConfigParser();c.read('/etc/plymouth/plymouthd.conf')
        if c.has_option('Daemon','Theme'):raise RuntimeError('An explicit Plymouth Theme override needs manual review first.')
    payload=objects(PKG);payload={p:b for p,b in payload.items() if (boot and p.is_relative_to(THEME)) or (login and (p.is_relative_to(LOGIN) or p.is_relative_to(ART)))}
    for directory in ([THEME] if boot else [])+([LOGIN,ART] if login else []):
        if directory.exists() or directory.is_symlink():raise RuntimeError('Existing destination is protected: '+str(directory))
    if login:
        payload[CONF]=config(CONF.read_text() if CONF.exists() else '', 'Greeter',{'background':str(ART/'login.png'),'background-color':'#5b7fd3','draw-user-backgrounds':'false','draw-grid':'false','theme-name':LOGIN.name,'font-name':'Liberation Sans 11','content-align':'right','show-hostname':'false','show-keyboard':'true','show-a11y':'true','show-power':'true','show-clock':'true','stretch-background-across-monitors':'false'})
    kernels=[]
    if boot:
        kernels=[os.uname().release]
        linked=Path('/boot/initrd.img').resolve()
        if linked.name.startswith('initrd.img-'):kernels.append(linked.name[len('initrd.img-'):])
        kernels=sorted(set(kernels))
        if not all(re.fullmatch(r'[a-zA-Z0-9.+_-]+',k) for k in kernels):raise RuntimeError('Invalid kernel name')
    images=[Path('/boot')/('initrd.img-'+k) for k in kernels]
    for p in images:
        validate_path(p)
        if not p.is_file():raise RuntimeError('Missing boot image: '+str(p))
    required=sum(p.stat().st_size for p in images)*3+100*1024*1024
    if shutil.disk_usage('/boot').free<required or shutil.disk_usage(STATE).free<required:raise RuntimeError('Insufficient space for boot image backup and rebuild.')
    backup=STATE/'backup';backup.mkdir(mode=0o700);records=[];dirs=set()
    for i,p in enumerate([*payload,*images]):
        validate_path(p);before=sha(p);mode=stat.S_IMODE(p.stat().st_mode) if p.exists() else 0o644
        if before is not None:shutil.copy2(p,backup/str(i))
        records.append({'path':str(p),'backup':str(i),'before':before,'after':hashlib.sha256(payload[p]).hexdigest() if p in payload else before,'mode':mode})
        for parent in p.parents:
            if parent.exists():break
            dirs.add(str(parent))
    s={'status':'installing','boot':boot,'login':login,'files':records,'created_dirs':sorted(dirs),'kernels':kernels,'alternative_before':alternative() if boot else None,'alternative_after':None};save(s)
    shutil.copy2(Path(__file__),STATE/'appearance.py');os.chmod(STATE/'appearance.py',0o700)
    try:
        for directory in sorted(dirs,key=len):
            Path(directory).mkdir(exist_ok=True,mode=0o755);os.chmod(directory,0o755)
        for p,data in payload.items():atomic(p,data)
        if login:
            for p in (ART/'login.png',LOGIN/'gtk-3.0/gtk.css'):run(['/usr/sbin/runuser','-u','lightdm','--','test','-r',str(p)])
        if boot:
            run(['/usr/bin/update-alternatives','--install','/usr/share/plymouth/themes/default.plymouth','default.plymouth',str(THEME/'mint-xp-experience.plymouth'),'150'])
            run(['/usr/bin/update-alternatives','--set','default.plymouth',str(THEME/'mint-xp-experience.plymouth')]);s['alternative_after']=alternative();save(s)
            for kernel,p in zip(kernels,images):
                temp=STATE/('initrd-'+kernel+'.new')
                try:
                    run(['/usr/sbin/mkinitramfs','-o',str(temp),kernel])
                    contents=run(['/usr/bin/lsinitramfs',str(temp)],capture_output=True).stdout
                    for name in ('mint-xp-experience.plymouth','throbber-0001.png','two-step.so','lock.png','bullet.png'):
                        if name not in contents:raise RuntimeError('New boot image missing '+name)
                    # Write-ahead expected checksum, then atomically replace only a validated image.
                    next(r for r in s['files'] if r['path']==str(p))['after']=sha(temp);save(s)
                    replace_file(temp,p,next(r['mode'] for r in s['files'] if r['path']==str(p)))
                finally:
                    if temp.exists():temp.unlink()
        if boot:
            shutdown=shutdown_module()
            shutdown.apply(PKG);shutil.copy2(PKG/'system/shutdown.py',STATE/'shutdown.py')
        s['status']='applied';save(s);guard(s);print('XP boot/login appearance installed. Autologin and authentication unchanged. No reboot performed.')
    except BaseException:
        undo(failed=True);raise

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['apply','verify','undo']);p.add_argument('--boot',action='store_true');p.add_argument('--login',action='store_true');args=p.parse_args()
    if os.geteuid()!=0:raise SystemExit('Administrator authentication required. Use pkexec or sudo; do not send passwords in chat.')
    os.umask(0o077);os.environ['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
    validate_path(STATE);STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (STATE/'lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.action=='apply':apply(args.boot,args.login)
        elif args.action=='undo':undo()
        else:
            guard(state())
            shutdown=shutdown_module()
            if (shutdown.STATE/'state.json').exists():
                extra=json.loads((shutdown.STATE/'state.json').read_text())
                if extra['status']=='applied':shutdown.guard(extra)
            print('System appearance and backups verified:',state()['status'])
if __name__=='__main__':main()
