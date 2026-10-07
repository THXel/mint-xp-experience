#!/usr/bin/python3
"""Guarded, separate shutdown splash. Leaves the boot theme and initramfs intact."""
import hashlib,json,os,shlex,shutil,subprocess,sys,tempfile
from pathlib import Path
STATE=Path('/var/lib/mint-xp-experience-system/shutdown')
THEME=Path('/usr/share/plymouth/themes/mint-xp-shutdown')
HELPER=Path('/usr/lib/mint-xp-experience/shutdown-splash.py')
DROPINS=[Path('/etc/systemd/system')/(f'plymouth-{mode}.service.d')/'60-mint-xp.conf' for mode in ('poweroff','reboot')]
def digest(p):
    p=Path(p)
    if p.is_symlink():raise RuntimeError('Linked shutdown file is protected: '+str(p))
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def write(p,data,mode=0o644):
    p=Path(p);fd,name=tempfile.mkstemp(prefix='.mintxp-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.chmod(name,mode);os.replace(name,p)
    finally:
        if os.path.exists(name):os.unlink(name)
def save(s):write(STATE/'state.json',json.dumps(s,indent=2).encode(),0o600)
def guard(s):
    for r in s['files']:
        for parent in [Path(r['path']),*Path(r['path']).parents]:
            if parent.is_symlink():raise RuntimeError('Linked shutdown destination is protected: '+str(parent))
        if digest(r['path'])!=r['after']:raise RuntimeError('Later shutdown customization is protected: '+r['path'])
        if r['before'] is not None and digest(STATE/'backup'/r['backup'])!=r['before']:raise RuntimeError('Damaged shutdown backup')
def undo():
    if not (STATE/'state.json').exists():return
    s=json.loads((STATE/'state.json').read_text())
    if s['status']=='restored':return
    if s['status']=='applied':guard(s)
    else:
        for r in s['files']:
            if digest(r['path']) not in (r['before'],r['after']):raise RuntimeError('Later shutdown customization is protected: '+r['path'])
    s['status']='restoring';save(s)
    for r in reversed(s['files']):
        p=Path(r['path'])
        if r['before'] is None:p.unlink(missing_ok=True)
        else:write(p,(STATE/'backup'/r['backup']).read_bytes(),r['mode'])
    for name in sorted(s['dirs'],key=len,reverse=True):
        try:Path(name).rmdir()
        except OSError:pass
    s['status']='restored';save(s);subprocess.run(['/usr/bin/systemctl','daemon-reload'],check=True)
def payload(pkg):
    files={THEME/p.name:p.read_bytes() for p in (pkg/'assets/shutdown').iterdir() if p.is_file()}
    for name in ('bullet.png','capslock.png','entry.png','keyboard.png','keymap-render.png','lock.png'):
        p=Path('/usr/share/plymouth/themes/spinner')/name
        if p.exists():files[THEME/name]=p.read_bytes()
    import configparser,io
    target=THEME/'mint-xp-shutdown.plymouth';config=configparser.ConfigParser(interpolation=None);config.optionxform=str
    config.read_string(files[target].decode())
    words=MESSAGES.get(system_language(),MESSAGES['en'])
    for mode,text in zip(('shutdown','reboot'),words):config[mode]['Title']=text
    buffer=io.StringIO();config.write(buffer);files[target]=buffer.getvalue().encode()
    files[HELPER]=Path(__file__).read_bytes()
    for p in DROPINS:
        mode='reboot' if 'reboot' in str(p) else 'shutdown'
        files[p]=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -I -B '+str(HELPER)+' launch '+mode+'\n').encode()
    return files

def apply(pkg):
    if (STATE/'state.json').exists():
        s=json.loads((STATE/'state.json').read_text())
        if s['status']=='applied':
            guard(s)
            if any(digest(p)!=hashlib.sha256(b).hexdigest() for p,b in payload(pkg).items()):raise RuntimeError('Restore the shutdown splash before upgrading its system files.')
            return
        if s['status']!='restored':raise RuntimeError('Restore the interrupted shutdown splash first.')
        # A new complete snapshot follows a successful restore; retain the old journal.
        retired=STATE/('retired-'+str(__import__('time').time_ns()));retired.mkdir(mode=0o700)
        shutil.move(str(STATE/'backup'),str(retired/'backup'));shutil.move(str(STATE/'state.json'),str(retired/'state.json'))
    for p in DROPINS:
        unit=Path('/usr/lib/systemd/system')/p.parent.name.removesuffix('.d')
        expected='/usr/sbin/plymouthd --mode='+('reboot' if 'reboot' in str(p) else 'shutdown')+' --attach-to-session'
        if 'ExecStart='+expected+'\n' not in unit.read_text():raise RuntimeError('Review the changed native shutdown unit first: '+str(unit))
        for base in ('/etc/systemd/system','/run/systemd/system','/usr/lib/systemd/system'):
            if list((Path(base)/p.parent.name).glob('*.conf')):raise RuntimeError('Existing Plymouth shutdown drop-ins need review first.')
    data=payload(pkg);dirs=set();records=[]
    STATE.mkdir(mode=0o700,parents=True,exist_ok=True);(STATE/'backup').mkdir(mode=0o700)
    for i,(p,b) in enumerate(data.items()):
        for parent in [p,*p.parents]:
            if parent.is_symlink():raise RuntimeError('Linked shutdown destination is protected: '+str(parent))
        before=digest(p);mode=p.stat().st_mode&0o777 if p.exists() else 0o644
        if before is not None:shutil.copy2(p,STATE/'backup'/str(i))
        records.append(dict(path=str(p),before=before,after=hashlib.sha256(b).hexdigest(),backup=str(i),mode=mode))
        for parent in p.parents:
            if parent.exists():break
            dirs.add(str(parent))
    s=dict(status='installing',files=records,dirs=sorted(dirs));save(s)
    try:
        for d in sorted(dirs,key=len):
            Path(d).mkdir(mode=0o755,exist_ok=True);os.chmod(d,0o755)
        for p,b in data.items():write(p,b)
        subprocess.run(['/usr/bin/systemctl','daemon-reload'],check=True)
        s['status']='applied';save(s);guard(s)
    except BaseException:undo();raise

def commandline(text):
    # Preserve every real kernel option; change only this daemon's theme selection.
    return shlex.join([v for v in shlex.split(text) if not v.startswith('plymouth.splash=')]+['plymouth.splash=mint-xp-shutdown'])
MESSAGES={
 'de':('Der Computer wird heruntergefahren …','Der Computer wird neu gestartet …'),
 'en':('The computer is shutting down …','The computer is restarting …'),
 'fr':('Arrêt de l’ordinateur …','Redémarrage de l’ordinateur …'),
 'es':('Apagando el equipo …','Reiniciando el equipo …'),
 'it':('Arresto del computer …','Riavvio del computer …'),
 'pt':('A desligar o computador …','A reiniciar o computador …'),
 'nl':('De computer wordt afgesloten …','De computer wordt opnieuw gestart …'),
 'pl':('Zamykanie komputera …','Ponowne uruchamianie komputera …'),
 'tr':('Bilgisayar kapatılıyor …','Bilgisayar yeniden başlatılıyor …'),
 'ru':('Завершение работы …','Перезагрузка компьютера …'),
 'uk':('Завершення роботи …','Перезавантаження комп’ютера …'),
 'zh':('正在关闭计算机…','正在重新启动计算机…'),
 'ja':('シャットダウンしています…','再起動しています…'),
 'ko':('컴퓨터를 종료하는 중…','컴퓨터를 다시 시작하는 중…')}
def system_language():
    values={}
    try:
        for line in Path('/etc/default/locale').read_text().splitlines():
            if '=' in line:
                k,v=line.split('=',1);values[k]=v.strip().strip('"\'')
    except OSError:pass
    return (values.get('LC_ALL') or values.get('LC_MESSAGES') or values.get('LANG','en')).split('_')[0].split('.')[0]
def main():
    if len(sys.argv)!=3 or sys.argv[1]!='launch' or sys.argv[2] not in ('shutdown','reboot'):raise SystemExit(2)
    args=['/usr/sbin/plymouthd','--mode='+sys.argv[2],'--attach-to-session','--kernel-command-line='+commandline(Path('/proc/cmdline').read_text())]
    os.execv(args[0],args)
if __name__=='__main__':main()
