"""XP-styled, asynchronous file and volume properties; no file mutations."""
from xp_locale import t as _xp
import datetime,math,os
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gio,GLib
from core import file_for,format_size,transfer_size

def text(value):
    label=Gtk.Label(label=str(value),xalign=0);label.set_selectable(True);label.set_line_wrap(True);label.set_max_width_chars(52);return label
class Properties(Gtk.Dialog):
    def __init__(self,owner,row):
        super().__init__(title=_xp('Eigenschaften von ')+row['name'],transient_for=owner,modal=False)
        self.get_style_context().add_class('xp-explorer');self.set_default_size(465,390);self.cancel=Gio.Cancellable();self.alive=True
        self.connect('destroy',self.closed);self.connect('response',lambda *a:self.destroy());self.add_button(_xp('Schließen'),Gtk.ResponseType.CLOSE)
        self.pages=Gtk.Notebook();self.pages.set_border_width(12);self.get_content_area().pack_start(self.pages,True,True,0)
        general=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);general.set_border_width(16)
        header=Gtk.Box(spacing=12);header.pack_start(Gtk.Image.new_from_pixbuf(owner.pix(row.get('icon','folder'),48)),False,False,0);header.pack_start(text(row['name']),True,True,0);general.pack_start(header,False,False,0);general.pack_start(Gtk.Separator(),False,False,0)
        self.info=text(_xp('Eigenschaften werden geladen …'));general.pack_start(self.info,False,False,0);self.pages.append_page(general,Gtk.Label(label='Allgemein'))
        detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);detail.set_border_width(16);detail.pack_start(text('Ort: '+file_for(row['uri']).get_parse_name()),False,False,0)
        self.detail=text('');detail.pack_start(self.detail,False,False,0);self.pages.append_page(detail,Gtk.Label(label=_xp('Details')))
        self.show_all()
        def work():
            f=file_for(row['uri']);i=f.query_info('standard::*,time::modified,owner::user,access::*',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,self.cancel)
            size=transfer_size(row['uri'],self.cancel) if i.get_file_type()==Gio.FileType.DIRECTORY else i.get_size()
            fs=None
            if i.get_file_type()==Gio.FileType.DIRECTORY:
                try:fs=f.query_filesystem_info('filesystem::size,filesystem::free,filesystem::type',self.cancel)
                except GLib.Error:pass
            return i,size,fs
        def done(value,error):
            if not self.alive:return False
            if error:self.info.set_text(_xp('Nicht vollständig verfügbar: ')+str(error));return False
            i,size,fs=value;modified=i.get_attribute_uint64('time::modified');kind=_xp('Dateiordner') if i.get_file_type()==Gio.FileType.DIRECTORY else Gio.content_type_get_description(i.get_content_type() or '') or _xp('Datei')
            self.info.set_text(f'Typ: {kind}\nGröße: {format_size(size)}\nGeändert: '+(datetime.datetime.fromtimestamp(modified).strftime('%d.%m.%Y %H:%M') if modified else 'Unbekannt'))
            self.detail.set_text(_xp('Dateityp: ')+(i.get_content_type() or 'Unbekannt')+'\nSchreibbar: '+('Ja' if i.get_attribute_boolean('access::can-write') else 'Nein')+'\nBesitzer: '+(i.get_attribute_string('owner::user') or 'Unbekannt')+(_xp('\nVerknüpfung: ')+str(i.get_symlink_target()) if i.get_is_symlink() else ''))
            if fs and fs.has_attribute('filesystem::size'):
                total=fs.get_attribute_uint64('filesystem::size');free=fs.get_attribute_uint64('filesystem::free');self.volume(total,free,fs.get_attribute_string('filesystem::type') or 'Unbekannt')
            self.show_all();return False
        # A drive properties dialog must not crawl an entire disk just to show its capacity.
        if row.get('volume'):
            def work():
                f=file_for(row['uri']);i=f.query_info('standard::*,time::modified,owner::user,access::*',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,self.cancel);return i,0,f.query_filesystem_info('filesystem::size,filesystem::free,filesystem::type',self.cancel)
        owner.spawn(work,done)
    def volume(self,total,free,kind):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=15);box.set_border_width(18)
        area=Gtk.DrawingArea();area.set_size_request(220,160);ratio=max(0,min(1,(total-free)/total)) if total else 0
        def draw(w,c):
            x=w.get_allocated_width()/2;y=75;c.set_source_rgb(.2,.7,.95);c.arc(x,y,66,0,2*math.pi);c.fill();c.set_source_rgb(.08,.24,.74);c.move_to(x,y);c.arc(x,y,66,-math.pi/2,-math.pi/2+2*math.pi*ratio);c.close_path();c.fill();return False
        area.connect('draw',draw);box.pack_start(area,False,False,0);box.pack_start(text(f'Dateisystem: {kind}\nBelegt: {format_size(max(0,total-free))}\nFrei: {format_size(free)}\nGesamt: {format_size(total)}'),False,False,0);self.pages.append_page(box,Gtk.Label(label=_xp('Datenträger')))
    def closed(self,*args):self.alive=False;self.cancel.cancel()
