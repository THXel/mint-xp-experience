"""Explicit local directory merge, no link traversal and no implicit overwrite."""
import os,stat
from pathlib import Path
from gi.repository import Gio
from core import file_for,copy_item,move_item,transfer_size
from conflicts import exists,transfer_resolved
from replacements import replace
from xp_locale import t as _xp

def local_directory(uri):
    path=file_for(uri).get_path()
    if not path or not stat.S_ISDIR(os.lstat(path).st_mode):raise ValueError(_xp('Zusammenführen ist nur für lokale Ordner ohne Verknüpfungen möglich.'))
    return Path(path)
def merge(source,target,cancel,history,choose,cut=False,progress=None):
    src=local_directory(source);dst=local_directory(target);a=src.resolve();b=dst.resolve()
    if a==b or a in b.parents or b in a.parents:raise ValueError(_xp('Quelle und Ziel dürfen nicht ineinander liegen.'))
    skipped=[False];bytes_done=[0]
    def directory(a,b):
        local_directory(a.get_uri());local_directory(b.get_uri());mode=stat.S_IMODE(os.lstat(a.get_path()).st_mode)
        enum=a.enumerate_children('standard::name,standard::type',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
        try:
            while True:
                cancel.set_error_if_cancelled();info=enum.next_file(cancel)
                if info is None:break
                child=a.get_child(info.get_name());destination=b.get_child(info.get_name())
                if info.get_file_type()==Gio.FileType.DIRECTORY and destination.query_file_type(Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)==Gio.FileType.DIRECTORY:
                    directory(child,destination);continue
                size=transfer_size(child.get_uri(),cancel) if progress else 0
                def tick(name,current):
                    if progress:progress(name,bytes_done[0]+current)
                def perform(uri):
                    if cut:
                        before=history.prepare(child.get_uri(),cancel);result=move_item(child.get_uri(),uri,cancel);history.remember(child.get_uri(),result,None,before)
                    else:result=copy_item(child.get_uri(),uri,cancel,tick);history.remember_created(result,None)
                ok=transfer_resolved(child.get_uri(),b.get_uri(),cancel,perform,lambda name,path,c:choose(name,path,c,source=child.get_uri()),lambda uri:replace(child.get_uri(),uri,cancel,history,cut,tick))
                if not ok:skipped[0]=True
                bytes_done[0]+=size
        finally:enum.close(None)
        if cut:
            # Remove only an empty source directory. A concurrent arrival keeps it alive.
            from gi.repository import GLib
            try:a.delete(cancel);history.add(dict(kind='removed_dir',new=a.get_uri(),old=None,mode=mode))
            except GLib.Error as e:
                if not e.matches(Gio.io_error_quark(),Gio.IOErrorEnum.NOT_EMPTY):raise
    directory(file_for(source),file_for(target));return not skipped[0]
