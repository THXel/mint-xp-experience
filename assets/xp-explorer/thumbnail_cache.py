"""Bounded memory/disk cache of generated local thumbnails, keyed by source identity."""
import hashlib,os,tempfile,threading
from collections import OrderedDict
from pathlib import Path
from comfort import load_image
from gi.repository import GdkPixbuf,GLib
_lock=threading.RLock();_memory=OrderedDict();_writes=0

def folder():return Path(os.environ.get('XP_EXPLORER_CACHE_DIR',str(Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'xp-explorer/thumbnails')))
def key(uri,size):
    from core import file_for
    p=file_for(uri).get_path()
    if not p:return None
    st=os.stat(p);return hashlib.sha256(repr((p,st.st_dev,st.st_ino,st.st_mtime_ns,st.st_ctime_ns,st.st_size,size)).encode()).hexdigest()
def load(uri,size):
    global _writes
    try:cache_key=key(uri,size)
    except OSError:return None
    if cache_key is None:return None
    with _lock:
        if cache_key in _memory:_memory.move_to_end(cache_key);return _memory[cache_key]
    root=folder();target=root/(cache_key+'.png');pix=None
    try:
        if not root.is_symlink() and not target.is_symlink() and target.stat().st_size<1024*1024:
            info,w,h=GdkPixbuf.Pixbuf.get_file_info(str(target))
            if info and 0<w<=size and 0<h<=size:pix=GdkPixbuf.Pixbuf.new_from_file(str(target))
    except (OSError,GLib.Error):pass
    if pix is None:
        pix=load_image(uri,size)
        if pix is None:return None
        try:
            if key(uri,size)!=cache_key:return None
            if not root.is_symlink():
                root.mkdir(mode=0o700,parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='.thumb-',dir=root);os.close(fd)
                try:pix.savev(name,'png',[],[]);os.replace(name,target)
                finally:
                    if os.path.exists(name):os.unlink(name)
                with _lock:
                    _writes+=1
                    if _writes%32==0:prune(root)
        except (OSError,GLib.Error):pass
    with _lock:
        _memory[cache_key]=pix
        while len(_memory)>256:_memory.popitem(last=False)
    return pix

def prune(root):
    entries=[]
    for p in root.glob('*.png'):
        if len(p.stem)!=64 or any(c not in '0123456789abcdef' for c in p.stem) or p.is_symlink():continue
        try:st=p.stat();entries.append((st.st_mtime,st.st_size,p))
        except OSError:pass
    entries.sort(reverse=True);total=0
    for i,(_,size,p) in enumerate(entries):
        total+=size
        if i>=512 or total>32*1024*1024:
            try:p.unlink()
            except OSError:pass
