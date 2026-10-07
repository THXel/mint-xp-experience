"""User-local, write-ahead-journalled installation and recovery. GPL-3.0-or-later."""
from .panel_state import equivalent,preference,reconcile
from . import mime_state
import contextlib, datetime, fcntl, hashlib, json, os, shutil, stat, subprocess, tempfile, uuid
from pathlib import Path, PurePosixPath

class Conflict(RuntimeError): pass

def atomic(path, data, mode=0o600):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.mintxp-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as out: out.write(data); out.flush(); os.fsync(out.fileno())
        os.chmod(tmp,mode); os.replace(tmp,path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def encoded(value): return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
def stamp(): return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]

class Settings:
    def __init__(self,home=None):
        self.home=Path(home or Path.home())
        import gi
        from gi.repository import Gio, GLib
        self.Gio,self.GLib=Gio,GLib;self.cache={}
    def obj(self,schema):
        if schema not in self.cache:
            source=self.Gio.SettingsSchemaSource.get_default(); entry=source.lookup(schema,True)
            if not entry: raise RuntimeError('Missing GSettings schema: '+schema)
            self.cache[schema]=self.Gio.Settings.new_full(entry,None,None)
        return self.cache[schema]
    def pins_path(self,key):
        ident=key.split('/',1)[1]
        if not ident.isdigit():raise Conflict('Invalid panel instance')
        p=self.home/'.config/cinnamon/spices/grouped-window-list@cinnamon.org'/(ident+'.json')
        for ancestor in (p,*p.parents):
            if ancestor==self.home:break
            if ancestor.is_symlink():raise Conflict('Linked panel configuration protected')
        return p
    def get(self,key):
        if key.startswith('mintxp-pins/'):
            p=self.pins_path(key);data=json.loads(p.read_text()) if p.exists() else {}
            value=data.get('pinned-apps',{}).get('value')
            if value is not None and (not isinstance(value,list) or not all(isinstance(x,str) for x in value)):raise Conflict('Invalid pinned application list')
            return self.literal(value) if value is not None else None
        schema,name=key.split('/',1);obj=self.obj(schema)
        if name not in obj.props.settings_schema.list_keys(): raise RuntimeError('Unknown setting: '+key)
        val=obj.get_user_value(name);return val.print_(True) if val is not None else None
    def effective(self,schema,key): return self.obj(schema).get_value(key).unpack()
    def literal(self,value):
        if isinstance(value,bool): return self.GLib.Variant('b',value).print_(True)
        if isinstance(value,str): return self.GLib.Variant('s',value).print_(True)
        if isinstance(value,int): return self.GLib.Variant('i',value).print_(True)
        if isinstance(value,list): return self.GLib.Variant('as',value).print_(True)
        raise ValueError(value)
    def set(self,key,value):
        if key.startswith('mintxp-pins/'):
            p=self.pins_path(key);data=json.loads(p.read_text()) if p.exists() else {}
            if value is None:data.pop('pinned-apps',None)
            else:
                pins=self.GLib.Variant.parse(self.GLib.VariantType.new('as'),value,None,None).unpack()
                data.setdefault('pinned-apps',{'type':'generic'})['value']=pins
            if data:atomic(p,encoded(data),p.stat().st_mode&0o777 if p.exists() else 0o600)
            elif p.exists():p.unlink()
            if self.get(key)!=value:raise Conflict('Panel favourites did not persist')
            return
        schema,name=key.split('/',1); obj=self.obj(schema)
        if not obj.is_writable(name): raise Conflict('Setting is locked: '+key)
        if value is None: obj.reset(name)
        else:
            kind=obj.get_value(name).get_type(); val=self.GLib.Variant.parse(kind,value,None,None)
            if not obj.range_check(name,val) or not obj.set_value(name,val): raise ValueError(key)
        self.Gio.Settings.sync()
        if not equivalent(key,self.get(key),value): raise RuntimeError('Setting did not persist: '+key)

class Engine:
    def __init__(self,home=None,state=None,settings=None):
        self.home=Path(home or Path.home()).resolve()
        self.state=Path(state or os.environ.get('XDG_STATE_HOME',str(self.home/'.local/state')))/'mint-xp-experience'
        self.settings=settings if settings is not None else Settings(self.home)
        self.progress=None # Optional observer; must never affect transaction safety.
        # State and every ancestor must be ordinary directories, never redirected links.
        for p in [self.state,*self.state.parents]:
            if p.is_symlink(): raise Conflict('Linked state directory: '+str(p))
        self.state.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(self.state,0o700)
        self.objects=self.state/'objects';self.objects.mkdir(exist_ok=True,mode=0o700)
    def report(self,phase,done=0,total=None,detail=''):
        if self.progress:
            try:self.progress(phase,done,total,detail)
            except Exception:pass # A UI/observer failure cannot interrupt the journal.
    def tracked(self,mapping,phase):
        total=len(mapping);self.report(phase,0,total)
        for index,(key,value) in enumerate(mapping.items(),1):
            self.report(phase,index-1,total,str(value) if phase=='reference' else key)
            yield key,value
            self.report(phase,index,total,str(value) if phase=='reference' else key)
    def path(self,rel):
        p=PurePosixPath(rel)
        roots=('.local/share/','.local/bin/','.themes/','.icons/','.config/','.gtkrc-2.0')
        if not isinstance(rel,str) or p.is_absolute() or '..' in p.parts or str(p)!=rel or not (p.name=='org.mintxp.Computer.desktop' or rel.startswith(roots) or rel in ('.local','.local/share','.local/bin','.themes','.icons','.config')):
            raise Conflict('Unsafe destination: '+str(rel))
        out=self.home/rel
        if out==self.state or self.state in out.parents: raise Conflict('State cannot manage itself')
        for ancestor in [out,*out.parents]:
            if ancestor==self.home: break
            if ancestor.is_symlink(): raise Conflict('Linked destination protected: '+str(ancestor))
        return out
    def put(self,data):
        digest=hashlib.sha256(data).hexdigest();p=self.objects/digest
        if not p.exists(): atomic(p,data)
        elif p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest: raise Conflict('Damaged object: '+digest)
        return digest
    def data(self,desc):
        digest=desc['sha256']
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest): raise Conflict('Invalid digest')
        p=self.objects/digest
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest: raise Conflict('Backup integrity failure: '+digest)
        return p.read_bytes()
    def file(self,rel):
        p=self.path(rel)
        if not p.exists(): return None
        if not p.is_file(): raise Conflict('Not a regular file: '+rel)
        return {'sha256':self.put(p.read_bytes()),'mode':stat.S_IMODE(p.stat().st_mode)}
    def descriptor(self,data,mode=0o644): return {'sha256':self.put(data),'mode':mode}
    def read(self,name,default=None):
        p=self.state/name
        if p.is_symlink(): raise Conflict('Linked journal: '+name)
        return json.loads(p.read_text()) if p.exists() else default
    def save(self,name,value): atomic(self.state/name,encoded(value))
    @contextlib.contextmanager
    def lock(self):
        p=self.state/'lock'
        fd=os.open(p,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise Conflict('Another operation is running')
            yield
        finally: os.close(fd)
    def read_current(self): return self.read('current.json',{'files':{},'settings':{},'options':{},'installed':False})
    def capture(self,desired):
        return {'files':{k:self.file(k) for k,v in self.tracked(desired['files'],'capture')},'settings':{k:self.settings.get(k) for k in desired['settings']}}
    def check(self,record,allow_preferences=False):
        errors=[]
        for k,v in self.tracked(record['files'],'check'):
            try:
                actual=self.file(k)
                if actual!=v and not (allow_preferences and mime_state.allowed(self,k,actual)): errors.append('file: '+k)
                if v is not None: self.data(v)
            except Exception as e: errors.append(str(e))
        for k,v in record['settings'].items():
            try:
                actual=self.settings.get(k)
                adjustable=k in ('org.cinnamon.desktop.sound/event-sounds','org.gnome.desktop.sound/event-sounds') and actual in (None,'true','false')
                if not equivalent(k,actual,v) and not (allow_preferences and (adjustable or preference(k,actual))): errors.append('setting: '+k)
            except Exception as e: errors.append(str(e))
        return errors
    def safety_snapshot(self):
        """Read-only reference snapshot, never loaded wholesale over later personal changes."""
        root=self.state/'reference'/stamp();root.mkdir(parents=True,mode=0o700)
        for branch in ('/org/cinnamon/','/org/gnome/desktop/','/org/nemo/'):
            r=subprocess.run(['dconf','dump',branch],capture_output=True,check=True)
            atomic(root/(branch.strip('/').replace('/','-')+'.dconf'),r.stdout)
        candidates=[self.home/x for x in ('.config/gtk-3.0','.config/gtk-4.0','.config/cinnamon/spices','.config/mimeapps.list','.gtkrc-2.0','.config/gtk-2.0','.local/share/sounds/Windows-XP')]
        for schema,key,dirs in [('org.cinnamon.desktop.interface','gtk-theme',['.themes','.local/share/themes']),('org.cinnamon.theme','name',['.themes','.local/share/themes']),('org.cinnamon.desktop.interface','icon-theme',['.icons','.local/share/icons']),('org.cinnamon.desktop.interface','cursor-theme',['.icons','.local/share/icons'])]:
            name=self.settings.effective(schema,key)
            if isinstance(name,str) and '/' not in name and name not in ('.','..'):
                candidates.extend(self.home/d/name for d in dirs)
                candidates.extend(Path(d)/name for d in ('/usr/share/themes','/usr/share/icons') if (Path(d)/name).exists())
        uri=self.settings.effective('org.cinnamon.desktop.background','picture-uri')
        from urllib.parse import urlparse,unquote
        if uri.startswith('file://'):
            wallpaper=Path(unquote(urlparse(uri).path))
            if wallpaper.is_relative_to(self.home): candidates.append(wallpaper)
        candidates += [Path('/etc/lightdm'),Path('/etc/gtk-3.0/settings.ini')]
        # GTK, Cinnamon, icons and cursors can share a directory. Copy each
        # source once: copytree cannot recreate an already copied symlink.
        candidates=list(dict.fromkeys(candidates))
        # A wallpaper or nested theme already included in a directory snapshot
        # must not be copied over that snapshot a second time either.
        directories={p for p in candidates if p.is_dir() and not p.is_symlink()}
        candidates=[p for p in candidates if not any(parent in directories for parent in p.parents)]
        report=[]
        for _,p in self.tracked(dict(enumerate(candidates)),'reference'):
            if not p.exists() and not p.is_symlink(): continue
            dest=root/'files'/str(p).lstrip('/')
            try:
                dest.parent.mkdir(parents=True,exist_ok=True)
                if p.is_dir() and not p.is_symlink(): shutil.copytree(p,dest,symlinks=True,dirs_exist_ok=True)
                elif p.is_symlink(): dest.symlink_to(os.readlink(p))
                else: shutil.copy2(p,dest)
                report.append({'path':str(p),'saved':True})
            except OSError as e: report.append({'path':str(p),'saved':False,'error':str(e)})
        self.save(str(root.relative_to(self.state)/'report.json'),report)
        if any(not entry['saved'] for entry in report):raise Conflict('Reference backup incomplete; inspect '+str(root/'report.json'))
        return str(root)
    def verify_objects(self,record):
        for rel,desc in self.tracked(record['files'],'verify'):
            self.path(rel)
            if desc is not None: self.data(desc)
        for key in record['settings']: self.settings.get(key)
    def write_record(self,record):
        for rel,desc in self.tracked(record['files'],'files'):
            p=self.path(rel)
            if desc is None:
                if p.exists(): p.unlink()
            else: atomic(p,self.data(desc),desc['mode'])
        for key,val in self.tracked(record['settings'],'settings'): self.settings.set(key,val)
    def cleanup_dirs(self,dirs):
        for rel in sorted(dirs,key=lambda x:len(PurePosixPath(x).parts),reverse=True):
            p=self.path(rel)
            try:p.rmdir()
            except (FileNotFoundError,OSError):pass # Never delete unrelated/new user files.
    def transact(self,target,base,action,prior_base=...):
        if prior_base is ...:prior_base=self.read('baseline.json')
        target=mime_state.reconcile(self,reconcile(self,target))
        mime_before=target.pop('_mime_before',...)
        before=self.capture(target);self.verify_objects(target)
        if mime_before is not ... and before['files'].get(mime_state.REL)!=mime_before:raise Conflict('File associations changed during review; retry.')
        missing=[]
        for rel,desc in target['files'].items():
            if desc is None: continue
            for p in self.path(rel).parents:
                if p==self.home:break
                if not p.exists():missing.append(str(p.relative_to(self.home)))
        for key,value in target['settings'].items():
            if key.startswith('mintxp-pins/') and value is not None:
                for p in self.settings.pins_path(key).parents:
                    if p==self.home:break
                    if not p.exists():missing.append(str(p.relative_to(self.home)))
        journal={'id':stamp(),'action':action,'before':before,'target':target,'base':base,'prior_base':prior_base,'previous':self.read_current(),'created_dirs':sorted(set(missing))}
        self.save('pending.json',journal) # Full WAL is durable BEFORE the first managed change.
        try:
            self.write_record(target)
            errors=self.check(target)
            if errors:raise Conflict('\n'.join(errors))
        except Exception:
            self.recover_unlocked();raise
        self.report('commit')
        base['created_dirs']=sorted(set(base.get('created_dirs',[])+missing))
        self.save('baseline.json',base);self.save('current.json',target)
        self.save('history/'+journal['id']+'.json',journal)
        (self.state/'pending.json').unlink()
        if not target.get('installed'): self.cleanup_dirs(base.get('created_dirs',[]))
        return journal['id']
    def recover_unlocked(self):
        tx=self.read('pending.json')
        if not tx:return False
        # A process interruption can leave each item either before or after. Anything
        # else is an external change; block the ENTIRE rollback before any write.
        self.verify_objects(tx['before']); errors=[]
        now=self.capture(tx['target'])
        for kind in ('files','settings'):
            for key,val in now[kind].items():
                if not any(equivalent(key,val,x) if kind=='settings' else val==x for x in (tx['before'][kind][key],tx['target'][kind][key])):errors.append(key)
        if errors:raise Conflict('Recovery conflicts: '+'\n'.join(errors))
        self.write_record(tx['before']);self.save('current.json',tx['previous'])
        # A transaction may have committed metadata just before its interruption.
        if 'prior_base' in tx:
            if tx['prior_base'] is None:
                if (self.state/'baseline.json').exists():(self.state/'baseline.json').unlink()
            else:self.save('baseline.json',tx['prior_base'])
        self.cleanup_dirs(tx['created_dirs']);(self.state/'pending.json').unlink();return True
    def recover(self):
        with self.lock():return self.recover_unlocked()
    def apply(self,plan,reference=True):
        with self.lock():
            if self.read('pending.json'):raise Conflict('Interrupted operation: recover first')
            old=self.read_current()
            if not old.get('installed') and self.read('baseline.json') and not self.read('pending.json'):
                self.save('retired/'+stamp()+'.json',{'baseline':self.read('baseline.json'),'current':old})
                (self.state/'baseline.json').unlink();old={'files':{},'settings':{},'options':{},'installed':False};self.save('current.json',old)
            errors=self.check(old,allow_preferences=True)
            if errors:raise Conflict('Changes protected:\n'+'\n'.join(errors))
            prior_base=self.read('baseline.json')
            base=self.read('baseline.json',{'files':{},'settings':{},'created_dirs':[]})
            if prior_base is None:base['created_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.verify_objects(base)
            for kind in ('files','settings'):
                for key,_ in self.tracked(plan[kind],'capture'):
                    if key not in base[kind]:base[kind][key]=self.file(key) if kind=='files' else self.settings.get(key)
            # Deselected components return to their first preinstallation values.
            target={'files':dict(base['files']),'settings':dict(base['settings']),'options':plan.get('options',{}),'installed':True}
            for kind in ('files','settings'):target[kind].update(plan[kind])
            # Global mute is a user preference, not damage to installed assets.
            # Keep it on updates; explicit restore/uninstall still restores the
            # selected snapshot/baseline. transact journals actual before-values.
            for key in ('org.cinnamon.desktop.sound/event-sounds','org.gnome.desktop.sound/event-sounds'):
                if key in old['settings'] and key in plan['settings']:
                    target['settings'][key]=self.settings.get(key)
            if reference and not self.read('baseline.json'): self.safety_snapshot()
            # Save original values before any mutation, including interrupted first installs.
            self.save('baseline.json',base)
            return self.transact(target,base,'apply',prior_base)
    def uninstall(self):
        with self.lock():return self.uninstall_unlocked()
    def uninstall_unlocked(self):
        if self.read('pending.json'):raise Conflict('Interrupted operation: recover first')
        current=self.read_current();errors=self.check(current,allow_preferences=True)
        if errors:raise Conflict('Changes protected:\n'+'\n'.join(errors))
        base=self.read('baseline.json')
        if not base:raise Conflict('No installation baseline exists')
        target={'files':base['files'],'settings':base['settings'],'options':{},'installed':False}
        return self.transact(target,base,'uninstall')
    def backup(self,reason='manual'):
        with self.lock():
            if self.read('pending.json'):raise Conflict('Recover before backing up')
            current=self.read_current(); captured=self.capture(current)
            captured.update(options=current.get('options',{}),installed=current.get('installed',False),created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason=reason)
            if 'panel_managed_applets' in current:captured['panel_managed_applets']=current['panel_managed_applets']
            name=stamp();self.save('snapshots/'+name+'.json',captured);self.safety_snapshot();return name
    def restore(self,name):
        if not name or any(c not in '0123456789abcdefTZ-' for c in name):raise ValueError('Invalid backup name')
        with self.lock():
            if self.read('pending.json'):raise Conflict('Recover before restoring')
            errors=self.check(self.read_current(),allow_preferences=True)
            if errors:raise Conflict('Changes protected:\n'+'\n'.join(errors))
            snapshot=self.read('snapshots/'+name+'.json')
            if snapshot is None:raise ValueError('Backup not found')
            base=self.read('baseline.json')
            target={'files':dict(base['files']),'settings':dict(base['settings']),'options':snapshot['options'],'installed':snapshot['installed']}
            for kind in ('files','settings'): target[kind].update(snapshot[kind])
            if 'panel_managed_applets' in snapshot:target['panel_managed_applets']=snapshot['panel_managed_applets']
            return self.transact(target,base,'restore')
