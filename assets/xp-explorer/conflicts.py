"""Non-destructive batch conflict handling, including destination races."""
from xp_locale import t as _xp
import threading
from pathlib import Path
import gi
gi.require_version("Gtk","3.0")
from gi.repository import Gio,GLib,Gtk
from core import file_for,format_size
import datetime
from thumbnail_cache import load as thumbnail

def exists(file,cancel):
    try:file.query_info('standard::type',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel);return True
    except GLib.Error as e:
        if e.matches(Gio.io_error_quark(),Gio.IOErrorEnum.NOT_FOUND):return False
        raise

def conflict_error(error):
    return isinstance(error,FileExistsError) or (isinstance(error,GLib.Error) and error.matches(Gio.io_error_quark(),Gio.IOErrorEnum.EXISTS))

def transfer_resolved(uri,destination,cancel,perform,choose,replace=None,merge=None):
    src=file_for(uri);parent=file_for(destination);name=src.get_basename();target=parent.get_child(name);choice=None;number=1
    while True:
        cancel.set_error_if_cancelled()
        try:
            if exists(target,cancel):raise FileExistsError(target.get_parse_name())
            perform(target.get_uri());return True
        except Exception as error:
            if not conflict_error(error):raise
            if choice is None:choice=choose(name,target.get_parse_name(),cancel)
            if choice=='skip':return False
            if choice=='merge' and merge:return merge(target.get_uri())
            if choice=='replace' and replace:return replace(target.get_uri())
            if choice!='keep':cancel.cancel();cancel.set_error_if_cancelled()
            kind=src.query_file_type(Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
            suffix=Path(name).suffix if kind!=Gio.FileType.DIRECTORY else ''
            stem=name[:-len(suffix)] if suffix else name
            number+=1;target=parent.get_child(f'{stem} ({number}){suffix}')

class ConflictPrompt:
    def __init__(self,owner):self.owner=owner;self.all_choice=None
    def choose(self,name,target,cancel,source=None):
        if self.all_choice:return self.all_choice
        def details(uri):
            if not uri:return None
            try:
                f=file_for(uri);info=f.query_info('standard::size,standard::type,standard::content-type,time::modified',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
                kind=info.get_file_type();picture=thumbnail(uri,96) if info.get_content_type() and info.get_content_type().startswith('image/') else None
                return dict(uri=f.get_parse_name(),size=info.get_size(),date=datetime.datetime.fromtimestamp(info.get_attribute_uint64('time::modified')).strftime('%d.%m.%Y %H:%M'),kind=kind,local=f.is_native(),picture=picture)
            except Exception:return None
        incoming=details(source);existing=details(target)
        can_replace=bool(incoming and existing and all(x['local'] and x['kind']==Gio.FileType.REGULAR for x in (incoming,existing)))
        can_merge=bool(incoming and existing and all(x['local'] and x['kind']==Gio.FileType.DIRECTORY for x in (incoming,existing)))
        event=threading.Event();answer=['cancel'];dialog=[None]
        def show():
            if cancel.is_cancelled() or not self.owner.alive:event.set();return False
            d=Gtk.Dialog(title=_xp('Datei bereits vorhanden'),transient_for=self.owner,modal=True);dialog[0]=d
            d.get_style_context().add_class('xp-explorer');d.set_default_size(740,-1)
            box=d.get_content_area();box.set_border_width(18);box.set_spacing(14)
            lab=Gtk.Label(label=_xp('Vergleiche die vorhandene und die neue Datei. Ersetzen legt eine Sicherung an.'),xalign=0);lab.set_line_wrap(True);lab.set_max_width_chars(75);box.add(lab)
            comparison=Gtk.Box(spacing=18);comparison.set_homogeneous(True);box.add(comparison)
            for title,data in [('Vorhandene Datei',existing),('Neue Datei',incoming)]:
                card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);comparison.pack_start(card,True,True,0);heading=Gtk.Label(label=_xp(title),xalign=0);heading.get_style_context().add_class('xp-card-heading');card.add(heading)
                if data:
                    if data['picture']:card.add(Gtk.Image.new_from_pixbuf(data['picture']))
                    text=Gtk.Label(label=data['uri']+'\n'+(_xp('Dateiordner') if data['kind']==Gio.FileType.DIRECTORY else format_size(data['size']))+'\n'+data['date'],xalign=0);text.set_line_wrap(True);text.set_max_width_chars(40);card.add(text)
            all_box=Gtk.CheckButton(label=_xp('Für weitere Namenskonflikte dieses Vorgangs übernehmen'));box.add(all_box)
            d.add_buttons(_xp('Abbrechen'),Gtk.ResponseType.CANCEL,_xp('Überspringen'),1,_xp('Beide behalten'),2,_xp('Ersetzen (mit Sicherung)'),3,_xp('Ordner zusammenführen'),4);d.set_response_sensitive(3,can_replace);d.set_response_sensitive(4,can_merge);d.set_default_response(2)
            # Wrap long translations within each action instead of widening the window.
            for button in d.get_action_area().get_children():
                label=button.get_child()
                if isinstance(label,Gtk.Label):label.set_line_wrap(True);label.set_max_width_chars(17)
            def response(w,r):
                answer[0]={1:'skip',2:'keep',3:'replace',4:'merge'}.get(r,'cancel')
                if all_box.get_active() and answer[0] in ('skip','keep'):self.all_choice=answer[0]
                w.destroy();dialog[0]=None;event.set()
            d.connect('response',response);d.connect('destroy',lambda *_:event.set());d.show_all();return False
        GLib.idle_add(show)
        while not event.wait(.1):
            if cancel.is_cancelled():
                def close():
                    if dialog[0]:dialog[0].response(Gtk.ResponseType.CANCEL)
                    return False
                GLib.idle_add(close);cancel.set_error_if_cancelled()
        cancel.set_error_if_cancelled();return answer[0]
