"""Local file replacements with atomic journals and conservative crash recovery."""
import json,os,stat,uuid,time,tempfile,datetime,re
from pathlib import Path
from core import file_for,move_item,copy_item,delete_item,format_size
from comfort import state_path
from xp_locale import t as _xp
from gi.repository import GLib

def regular(uri):
    p=file_for(uri).get_path()
    if not p or not stat.S_ISREG(Path(p).lstat().st_mode):raise ValueError(_xp('Ersetzen ist nur für lokale Dateien möglich. Für Ordner bitte „Beide behalten“ wählen.'))
    return Path(p)
def identity(uri):
    st=regular(uri).stat();return [st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,stat.S_IMODE(st.st_mode)]
def same(uri,expected):
    try:return expected is not None and identity(uri)==expected
    except (OSError,ValueError):return False
def records():return state_path().parent/'replacements'
def write_record(path,item):
    path=Path(path)
    if path.parent.is_symlink() or path.is_symlink():raise ValueError('Linked recovery index')
    fd,name=tempfile.mkstemp(prefix='.record-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(item,f);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(name):os.unlink(name)
def phase(item,value):item['phase']=value;write_record(item['record'],item)
def paths(item):
    backup=Path(file_for(item['backup']).get_path() or '');target=Path(file_for(item['new']).get_path() or '');folder=backup.parent
    if not backup.is_absolute() or not target.is_absolute() or backup.name!='original' or not re.fullmatch(r'\.xp-replaced-[a-f0-9]{32}',folder.name) or folder.parent!=target.parent or Path(item['record'])!=records()/(folder.name+'.json') or folder.is_symlink() or Path(item['record']).is_symlink():raise ValueError('Invalid replacement recovery record')
    return backup,target,folder,folder/'replaced-result'
def cleanup(item):
    backup,target,folder,staged=paths(item)
    if os.path.lexists(backup) or os.path.lexists(staged):return
    Path(item['record']).unlink(missing_ok=True)
    try:folder.rmdir()
    except OSError:pass

def replace(source,target,cancel,history,cut=False,progress=None):
    from journal import fingerprint
    src=regular(source);dst=regular(target)
    if os.path.samefile(src,dst):raise ValueError(_xp('Quelle und Ziel sind identisch.'))
    cancel.set_error_if_cancelled();before=fingerprint(target,cancel)
    folder=dst.parent/('.xp-replaced-'+uuid.uuid4().hex);folder.mkdir(mode=0o700);backup=(folder/'original').as_uri()
    index=records();index.mkdir(parents=True,exist_ok=True);record=index/(folder.name+'.json')
    item=dict(kind='replace',old=source if cut else None,new=target,backup=backup,record=str(record),stamp=None,backup_stamp=None,created=time.time(),phase='prepared',original_identity=identity(target),result_identity=None)
    write_record(record,item)
    try:
        if fingerprint(target,cancel)!=before:raise ValueError(_xp('Die Zieldatei wurde inzwischen verändert.'))
        move_item(target,backup,cancel);item['backup_stamp']=fingerprint(backup,None);phase(item,'original_saved')
        if cut:move_item(source,target,cancel)
        else:copy_item(source,target,cancel,progress)
        item['stamp']=fingerprint(target,None);item['result_identity']=identity(target);phase(item,'installed');history.add(item);return True
    except BaseException:
        if file_for(backup).query_exists(None) and not os.path.lexists(dst):move_item(backup,target,None)
        cleanup(item);raise

def validate(item,cancel=None):
    from journal import fingerprint
    backup,target,folder,staged=paths(item)
    # A restore interrupted after staging can safely resume only for known identities.
    if os.path.lexists(staged):
        if not same(staged.as_uri(),item.get('result_identity')):raise ValueError(_xp('Die Datei wurde verändert. Die Sicherung bleibt erhalten.'))
        original=backup if os.path.lexists(backup) else target
        if not same(original.as_uri(),item.get('original_identity')):raise ValueError(_xp('Die Datei wurde verändert. Die Sicherung bleibt erhalten.'))
        if original==backup and os.path.lexists(target):raise FileExistsError(_xp('Am ursprünglichen Ort existiert bereits ein Eintrag.'))
    elif not item.get('stamp'):
        if os.path.lexists(target) or not same(backup.as_uri(),item.get('original_identity')):raise ValueError(_xp('Unterbrochener Vorgang: Bitte die Sicherung als zusätzliche Datei retten.'))
    else:
        regular(item['backup']);regular(item['new'])
        if not item.get('backup_stamp') or fingerprint(item['new'],cancel)!=item['stamp'] or fingerprint(item['backup'],cancel)!=item['backup_stamp']:raise ValueError(_xp('Die Datei wurde verändert. Die Sicherung bleibt erhalten.'))
    if item.get('old') and os.path.lexists(file_for(item['old']).get_path() or '') and (item.get('stamp') or os.path.lexists(staged)):raise FileExistsError(_xp('Am ursprünglichen Ort existiert bereits ein Eintrag.'))

def restore(item,cancel=None):
    validate(item,cancel);backup,target,folder,staged=paths(item)
    if cancel:cancel.set_error_if_cancelled()
    if not item.get('stamp') and not os.path.lexists(staged):
        move_item(backup.as_uri(),target.as_uri(),None);cleanup(item);return item['new']
    # Do not cancel a short sequence after it creates a gap at the destination.
    if not os.path.lexists(staged):
        item.setdefault('original_identity',identity(backup.as_uri()));item.setdefault('result_identity',identity(target.as_uri()));phase(item,'restoring')
        move_item(item['new'],staged.as_uri(),None)
    if os.path.lexists(backup):move_item(backup.as_uri(),target.as_uri(),None)
    phase(item,'original_restored')
    if item.get('old'):move_item(staged.as_uri(),item['old'],None)
    else:delete_item(staged.as_uri(),None)
    cleanup(item);return item['new']

def rescue_copy(item,cancel=None):
    backup,target,folder,staged=paths(item)
    source=backup if os.path.lexists(backup) else staged
    regular(source.as_uri())
    suffix=target.suffix;stem=target.name[:-len(suffix)] if suffix else target.name
    for n in range(1,10001):
        destination=target.with_name(_xp('{0} (gerettet {1}){2}').format(stem,n,suffix))
        if not os.path.lexists(destination):
            try:return copy_item(source.as_uri(),destination.as_uri(),cancel)
            except Exception as error:
                from conflicts import conflict_error
                if conflict_error(error):continue
                raise
    raise ValueError(_xp('Kein freier Dateiname gefunden.'))

def summaries():
    result=[]
    for p in sorted(records().glob('*.json')):
        try:
            if p.is_symlink() or p.stat().st_size>16384:continue
            item=json.loads(p.read_text());backup,target,folder,staged=paths(item)
            if item.get('kind')!='replace' or item['record']!=str(p):continue
            size=sum(x.lstat().st_size for x in (backup,staged) if x.exists() and not x.is_symlink());created=item.get('created',p.stat().st_mtime)
            try:validate(item);status=_xp('Wiederherstellbar');ready=True
            except (OSError,ValueError,KeyError,GLib.Error):status=_xp('Prüfung nötig – Sicherung behalten');ready=False
            result.append((item,size,datetime.datetime.fromtimestamp(created).strftime('%d.%m.%Y %H:%M'),status,ready))
        except (OSError,ValueError,KeyError,TypeError,OverflowError):continue
    return result

def show_recovery(owner):
    from gi.repository import Gtk
    d=Gtk.Dialog(title=_xp('Ersetzte Dateien wiederherstellen'),transient_for=owner,modal=True);d.set_default_size(850,440);d.add_buttons(_xp('Schließen'),Gtk.ResponseType.CANCEL,_xp('Sicherungsordner öffnen'),2,_xp('Zusätzliche Kopie retten'),3,_xp('Wiederherstellen'),Gtk.ResponseType.OK)
    for button in d.get_action_area().get_children():
        label=button.get_child()
        if isinstance(label,Gtk.Label):label.set_line_wrap(True);label.set_max_width_chars(20)
    box=d.get_content_area();box.set_border_width(12);box.set_spacing(10)
    lab=Gtk.Label(label=_xp('Sicherungen bleiben erhalten. Veränderte Dateien werden nicht überschrieben.'),xalign=0);lab.set_line_wrap(True);box.add(lab)
    model=Gtk.ListStore(str,str,str,str,object,bool)
    tree=Gtk.TreeView(model=model)
    for i,title in enumerate(('Datei','Sicherungsdatum','Speicherbedarf','Status')):
        col=Gtk.TreeViewColumn(_xp(title),Gtk.CellRendererText(),text=i);col.set_resizable(True);col.set_expand(i==0);tree.append_column(col)
    sc=Gtk.ScrolledWindow();sc.add(tree);box.pack_start(sc,True,True,0)
    def selected(*args):
        m,it=tree.get_selection().get_selected()
        for r in (2,3):d.set_response_sensitive(r,it is not None)
        d.set_response_sensitive(Gtk.ResponseType.OK,it is not None and m[it][5])
    selected();tree.get_selection().connect('changed',selected)
    alive=[True];d.connect('destroy',lambda *_:alive.__setitem__(0,False))
    def ready(rows,error):
        if not alive[0]:return
        if error:lab.set_text(str(error));return
        for item,size,date,status,allowed in rows:model.append([file_for(item['new']).get_parse_name(),date,format_size(size),status,item,allowed])
        lab.set_text(_xp('{0} Sicherungen · {1} Speicherbedarf').format(len(rows),format_size(sum(x[1] for x in rows))))
    owner.spawn(summaries,ready);d.show_all();r=d.run();m,it=tree.get_selection().get_selected();item=dict(m[it][4]) if it is not None else None;d.destroy()
    if item and r==2:owner.app.window(file_for(item['backup']).get_parent().get_uri(),tree=True)
    elif item and r in (3,Gtk.ResponseType.OK):
        def work(uri,cancel):
            if r==3:rescue_copy(item,cancel)
            else:restore(item,cancel);owner.app.undo_history.discard_uri(item['new'])
        owner.operation(_xp('Wird wiederhergestellt …'),[item['new']],work,kind='undo')
