"""GIO-backed filesystem operations. Never overwrite; permanent deletion is a separately confirmed action."""
from xp_locale import t as _xp
from pathlib import Path
import os, uuid
import gi
gi.require_version('Gio','2.0')
from gi.repository import Gio, GLib
ATTR='standard::*,time::modified,access::*,trash::orig-path'
FLAGS=Gio.FileCopyFlags.NOFOLLOW_SYMLINKS|Gio.FileCopyFlags.ALL_METADATA

def file_for(value):
    return Gio.File.new_for_uri(value) if '://' in value else Gio.File.new_for_path(os.path.abspath(os.path.expanduser(value)))
def child_name(name):
    if not name or name in ('.','..') or '/' in name or '\0' in name:
        raise ValueError(_xp('Bitte einen einzelnen, gültigen Namen eingeben.'))
    return name

def listing(uri,hidden=False,cancel=None,on_batch=None):
    root=file_for(uri);result=[];batch=[]
    enum=root.enumerate_children(ATTR,Gio.FileQueryInfoFlags.NONE,cancel)
    try:
        while True:
            i=enum.next_file(cancel)
            if i is None:break
            if not hidden and ((i.has_attribute('standard::is-hidden') and i.get_is_hidden()) or i.get_name().endswith('~')):continue
            result.append({'uri':root.get_child(i.get_name()).get_uri(),'name':i.get_display_name(),
              'dir':i.get_file_type()==Gio.FileType.DIRECTORY,'link':(i.has_attribute('standard::is-symlink') and i.get_is_symlink()),
              'mountable':i.get_file_type()==Gio.FileType.MOUNTABLE,
              'target':i.get_attribute_string('standard::target-uri') if i.has_attribute('standard::target-uri') else None,
              'shortcut':i.get_file_type()==Gio.FileType.SHORTCUT,'size':i.get_size() if i.has_attribute('standard::size') else 0,
              'modified':i.get_attribute_uint64('time::modified'),'icon':i.get_icon(),
              'original':i.get_attribute_byte_string('trash::orig-path') if i.has_attribute('trash::orig-path') else None,
              'mime':i.get_content_type() or 'application/octet-stream',
              'writable':i.get_attribute_boolean('access::can-write')})
            if on_batch:
                batch.append(result[-1])
                if len(batch)>=150:on_batch(batch);batch=[]
    finally:enum.close(None)
    if on_batch and batch:on_batch(batch)
    return sorted(result,key=lambda r:(not r['dir'],r['name'].casefold()))

def _assert_destination(src,dst):
    if src.equal(dst):raise ValueError(_xp('Quelle und Ziel sind identisch.'))
    if dst.query_exists(None):raise FileExistsError(_xp('Der Name existiert bereits: ')+dst.get_parse_name())
    if src.query_file_type(Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,None)==Gio.FileType.DIRECTORY:
        if dst.has_prefix(src):raise ValueError(_xp('Ein Ordner kann nicht in sich selbst kopiert oder verschoben werden.'))
        if src.get_path() and dst.get_path():
            a,b=Path(src.get_path()).resolve(),Path(dst.get_path()).resolve()
            if b==a or a in b.parents:raise ValueError('Das Ziel liegt innerhalb des Quellordners.')

def copy_item(source,destination,cancel=None,progress=None):
    src,dst=file_for(source),file_for(destination);_assert_destination(src,dst)
    parent=dst.get_parent()
    if parent is None:raise ValueError(_xp('Ungültiges Ziel.'))
    staging=parent.get_child('.xp-copy-'+uuid.uuid4().hex);created=[];copied=0
    def recurse(a,b):
        nonlocal copied
        info=a.query_info('standard::type,standard::is-symlink,standard::size',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
        if info.get_file_type()==Gio.FileType.DIRECTORY:
            b.make_directory(cancel);created.append(b)
            enum=a.enumerate_children('standard::name',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
            try:
                while True:
                    i=enum.next_file(cancel)
                    if i is None:break
                    recurse(a.get_child(i.get_name()),b.get_child(i.get_name()))
            finally:enum.close(None)
            # Directory timestamps/mode are best effort; files use ALL_METADATA.
            try:a.copy_attributes(b,Gio.FileCopyFlags.ALL_METADATA,cancel)
            except GLib.Error:pass
        else:
            created.append(b)
            size=info.get_size() if info.get_file_type()==Gio.FileType.REGULAR else 0
            def report(current,total,*unused):
                if progress:progress(a.get_basename(),copied+min(current,size))
            a.copy(b,FLAGS,cancel,report if progress else None,None)
            copied+=size
            if progress:progress(a.get_basename(),copied)
    try:
        recurse(src,staging)
        staging.move(dst,Gio.FileCopyFlags.NOFOLLOW_SYMLINKS,cancel,None,None)
    except BaseException:
        # Remove only entries owned by this operation, never enumerate user-added data.
        for f in reversed(created):
            try:f.delete(None)
            except GLib.Error:pass
        raise
    return dst.get_uri()

def move_item(source,destination,cancel=None):
    a,b=file_for(source),file_for(destination);_assert_destination(a,b)
    a.move(b,Gio.FileCopyFlags.NOFOLLOW_SYMLINKS,cancel,None,None)
    return b.get_uri()

def new_folder(parent,name):
    f=file_for(parent).get_child(child_name(name));f.make_directory(None);return f.get_uri()
def rename_item(uri,name):
    f=file_for(uri);p=f.get_parent()
    if p is None:raise ValueError(_xp('Dieser Ort kann nicht umbenannt werden.'))
    return move_item(uri,p.get_child(child_name(name)).get_uri())
def trash_item(uri,cancel=None):
    file_for(uri).trash(cancel)

def format_size(n):return GLib.format_size(n)


def transfer_size(uri,cancel=None):
    """Count regular-file payload without following symlinks; runs in a worker."""
    f=file_for(uri);info=f.query_info('standard::type,standard::size',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
    if info.get_file_type()==Gio.FileType.REGULAR:return info.get_size()
    if info.get_file_type()!=Gio.FileType.DIRECTORY:return 0
    total=0;enum=f.enumerate_children('standard::name',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
    try:
        while True:
            item=enum.next_file(cancel)
            if item is None:break
            total+=transfer_size(f.get_child(item.get_name()).get_uri(),cancel)
    finally:enum.close(None)
    return total


def delete_item(uri,cancel=None):
    """Permanent deletion, only called after explicit UI confirmation. Never follow links."""
    f=file_for(uri)
    if f.get_parent() is None or f.get_uri() in ('trash:///','network:///','computer:///'):
        raise ValueError(_xp('Dieser Stammordner darf nicht gelöscht werden.'))
    if cancel:cancel.set_error_if_cancelled()
    # GVfs trash deletion removes the top-level item and its trash metadata together.
    if f.has_uri_scheme('trash'):
        f.delete(cancel);return
    info=f.query_info('standard::type,standard::is-symlink',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
    if info.get_file_type()==Gio.FileType.DIRECTORY and not (info.has_attribute('standard::is-symlink') and info.get_is_symlink()):
        # fd-relative rmtree resists local symlink replacement races.
        if f.is_native():
            import shutil
            if not shutil.rmtree.avoids_symlink_attacks:raise ValueError(_xp('Sicheres rekursives Löschen ist hier nicht verfügbar.'))
            def check(function,path,exc):raise exc[1]
            shutil.rmtree(f.get_path(),onerror=check);return
        enum=f.enumerate_children('standard::name',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
        try:
            while True:
                item=enum.next_file(cancel)
                if item is None:break
                delete_item(f.get_child(item.get_name()).get_uri(),cancel)
        finally:enum.close(None)
    f.delete(cancel)


def trash_with_location(uri,cancel=None):
    """Identify the actual moved inode despite GVfs's short trash-list cache delay."""
    import time
    src=file_for(uri)
    identity=None
    if src.is_native():
        st=os.lstat(src.get_path());identity=(st.st_dev,st.st_ino)
    before={r['uri'] for r in listing('trash:///',True,cancel)} if src.is_native() else set()
    src.trash(cancel)
    if not src.is_native():return None
    # The file operation succeeded. Even a subsequent cancellation should not lose
    # its undo record. Never guess between older entries with the same original path.
    end=time.monotonic()+1.2
    while True:
        try:
            matches=[]
            for row in listing('trash:///',True,None):
                if row.get('original')!=src.get_path():continue
                payload=file_for(row['target']).get_path() if row.get('target') else None
                if payload:
                    try:
                        st=os.lstat(payload)
                        if (st.st_dev,st.st_ino)!=identity:continue
                    except OSError:continue
                elif row['uri'] in before:continue
                matches.append(row['uri'])
            if len(matches)==1:return matches[0]
        except GLib.Error:return None
        if time.monotonic()>=end:return None
        time.sleep(.05)
