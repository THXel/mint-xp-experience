"""Session undo for file operations: validate current targets before reverting them."""
from xp_locale import t as _xp
import hashlib,os,stat,threading
from gi.repository import Gio,GLib
from core import trash_item,delete_item
from contextlib import contextmanager
from pathlib import Path
from core import file_for,move_item

def fingerprint(uri,cancel=None):
    path=file_for(uri).get_path()
    if not path:
        digest=hashlib.sha256()
        def remote(f,relative):
            info=f.query_info('standard::type,standard::is-symlink,standard::symlink-target,standard::size,time::modified,time::modified-usec,etag::value,id::file',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
            digest.update(repr((relative,int(info.get_file_type()),info.get_size() if info.has_attribute('standard::size') else 0,info.get_attribute_uint64('time::modified'),info.get_attribute_uint32('time::modified-usec'),info.get_attribute_string('etag::value'),info.get_attribute_string('id::file'),info.get_symlink_target() if info.has_attribute('standard::symlink-target') else None)).encode())
            if info.get_file_type()==Gio.FileType.DIRECTORY and not (info.has_attribute('standard::is-symlink') and info.get_is_symlink()):
                enum=f.enumerate_children('standard::name',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel);names=[]
                try:
                    while True:
                        row=enum.next_file(cancel)
                        if row is None:break
                        names.append(row.get_name())
                finally:enum.close(None)
                for name in sorted(names):remote(f.get_child(name),relative+'/'+name)
        remote(file_for(uri),'');return digest.hexdigest()
    digest=hashlib.sha256();root=Path(path)
    def visit(p,relative):
        if cancel and cancel.is_cancelled():raise RuntimeError(_xp('Prüfung abgebrochen.'))
        st=p.lstat()
        digest.update(repr((relative,st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns)).encode())
        if stat.S_ISLNK(st.st_mode):digest.update(os.readlink(p).encode())
        elif stat.S_ISDIR(st.st_mode):
            for child in sorted(p.iterdir(),key=lambda p:p.name):visit(child,relative+'/'+child.name)
    visit(root,'');return digest.hexdigest()

class UndoHistory:
    def __init__(self):self.items=[];self.lock=threading.RLock();self.local=threading.local()
    def prepare(self,old,cancel=None):
        previous=self.peek()
        if previous and previous.get('kind')=='group':previous=previous['items'][-1]
        if not previous or file_for(previous['new']).get_uri()!=file_for(old).get_uri():return None
        try:return fingerprint(old,cancel)
        except (OSError,ValueError,RuntimeError,GLib.Error):return None
    def remember(self,old,new,cancel=None,before=None):
        # A failed snapshot must not turn an already successful move into a reported failure.
        try:stamp=fingerprint(new,cancel)
        except (OSError,ValueError,RuntimeError,GLib.Error):return False
        self.add(dict(old=old,new=new,stamp=stamp,before=before,kind='move'))
        return True
    def add(self,item):
        with self.lock:
            active=getattr(self.local,'batch',None)
            if active is not None:active.append(item)
            else:self.items.append(item);self.items=self.items[-30:]
    def remember_created(self,uri,cancel=None,kind='created'):
        try:stamp=fingerprint(uri,cancel)
        except (OSError,ValueError,RuntimeError,GLib.Error):return False
        self.add(dict(kind=kind,old=None,new=uri,stamp=stamp));return True
    @contextmanager
    def batch(self):
        self.local.batch=[]
        try:yield
        finally:
            entries=self.local.batch;self.local.batch=None
            if entries:self.add(entries[0] if len(entries)==1 else dict(kind='group',items=entries,new=entries[-1]['new']))
    def peek(self):
        with self.lock:
            active=getattr(self.local,'batch',None)
            return dict(active[-1]) if active else dict(self.items[-1]) if self.items else None
    def validate(self,item,cancel=None):
        if item.get('kind')=='removed_dir':
            p=file_for(item['new']).get_path()
            if not p or os.path.lexists(p):raise FileExistsError(_xp('Am ursprünglichen Ort existiert bereits ein Eintrag.'))
            return
        if item.get('kind')=='replace':
            from replacements import validate
            return validate(item,cancel)
        if fingerprint(item['new'],cancel)!=item['stamp']:raise ValueError(_xp('Die Datei oder der Ordner wurde inzwischen verändert. Rückgängig wurde gestoppt.'))
        if item.get('kind') not in ('created','restored') and file_for(item['old']).query_exists(cancel):raise FileExistsError(_xp('Am ursprünglichen Ort existiert bereits ein Eintrag.'))
    def undo_one(self,item,cancel=None):
        self.validate(item,cancel)
        if item.get('kind')=='removed_dir':
            f=file_for(item['new']);f.make_directory(cancel);os.chmod(f.get_path(),item['mode']);return item['new']
        if item.get('kind')=='replace':
            from replacements import restore
            return restore(item,cancel)
        if item.get('kind')=='created':delete_item(item['new'],cancel);return item['new']
        if item.get('kind')=='restored':trash_item(item['new'],cancel);return item['new']
        return move_item(item['new'],item['old'],cancel)
    def undo(self,cancel=None):
        with self.lock:
            if not self.items:raise ValueError(_xp('Kein rückgängig machbarer Dateivorgang vorhanden.'))
            item=self.items[-1]
            if item.get('kind')=='group':
                for child in item['items']:self.validate(child,cancel)
                while item['items']:
                    result=self.undo_one(item['items'][-1],cancel);item['items'].pop()
                self.items.pop();return result
            result=self.undo_one(item,cancel);self.items.pop()
            previous=self.items[-1] if self.items else None
            candidates=previous['items'] if previous and previous.get('kind')=='group' else [previous] if previous else []
            for prior in candidates:
                if prior.get('new')==item.get('old') and item.get('before')==prior.get('stamp'):
                    try:prior['stamp']=fingerprint(item['old'],cancel)
                    except (OSError,ValueError,RuntimeError,GLib.Error):pass
            return result

    def discard_uri(self,uri):
        target=file_for(uri)
        def retained(item):
            f=file_for(item['new']);return not (f.equal(target) or f.has_prefix(target))
        with self.lock:
            kept=[]
            for item in self.items:
                if item.get('kind')=='group':
                    item['items']=[x for x in item['items'] if retained(x)]
                    if item['items']:item['new']=item['items'][-1]['new'];kept.append(item)
                elif retained(item):kept.append(item)
            self.items=kept
