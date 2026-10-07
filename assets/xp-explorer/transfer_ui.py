"""Classic file-operation dialog. Animation is decorative; progress is actual work."""
from xp_locale import t as _xp
import math,time
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk,GLib,Pango
from transfer_scene import endpoints,paper_at
class TransferDialog(Gtk.Dialog):
    def __init__(self,owner,title,cancel,kind='copy'):
        super().__init__(title=title.replace(' …',''),transient_for=owner,modal=False)
        self.get_style_context().add_class('xp-explorer');self.get_style_context().add_class('xp-transfer')
        self.set_default_size(470,250);self.set_resizable(False);self.phase=0;self.kind=kind;self.started=time.monotonic()
        source,target=endpoints(kind);self.source=owner.pix(source,52);self.target=owner.pix(target,52) if target else None
        box=self.get_content_area();box.set_border_width(18);box.set_spacing(11)
        self.scene=Gtk.DrawingArea();self.scene.set_size_request(430,91);self.scene.connect('draw',self.draw_scene);box.pack_start(self.scene,False,False,0)
        self.caption=Gtk.Label(label=_xp('Dateien werden vorbereitet …'),xalign=0);self.caption.set_ellipsize(Pango.EllipsizeMode.MIDDLE);box.pack_start(self.caption,False,False,0)
        self.bar=Gtk.ProgressBar();self.bar.set_show_text(True);box.pack_start(self.bar,False,False,0)
        self.details=Gtk.Label(label=_xp('Die Größe wird ermittelt.'),xalign=0);self.details.set_line_wrap(True);self.details.set_max_width_chars(58);box.pack_start(self.details,False,False,0)
        self.add_button(_xp('Abbrechen'),Gtk.ResponseType.CANCEL);self.connect('response',lambda *a:cancel.cancel());self.connect('delete-event',self.hide_window)
        self.timer=GLib.timeout_add(40,self.animate);self.connect('destroy',self.stop_animation);self.show_all()
    def stop_animation(self,*args):
        if self.timer:GLib.source_remove(self.timer);self.timer=0
    def animate(self):
        enabled=Gtk.Settings.get_default().get_property('gtk-enable-animations')
        self.phase=((time.monotonic()-self.started)/2.15)%1 if enabled else .35
        if self.get_mapped():self.scene.queue_draw()
        return True
    def hide_window(self,*args):self.hide();return True
    def update(self,caption,fraction,details,bar_text):
        self.caption.set_text(caption);self.details.set_text(details);self.bar.set_text(bar_text)
        if fraction is None:self.bar.pulse()
        else:self.bar.set_fraction(max(0,min(1,fraction)))
    def draw_scene(self,w,c):
        width=w.get_allocated_width()
        # Original vector icons at either end: folder, bin, or a dissolving sheet.
        for pix,x in ((self.source,3),(self.target,width-58)):
            if pix:Gdk.cairo_set_source_pixbuf(c,pix,x,28);c.paint()
        for i in range(3):
            x,y,angle,alpha,t=paper_at(self.kind,self.phase,i,width)
            c.save();c.translate(x,y);c.rotate(angle)
            if self.kind in ('delete','empty-trash') and t>.76:
                # Small paper fragments disperse; no misleading destination folder.
                for j in range(5):
                    c.set_source_rgba(.45,.58,.72,alpha)
                    c.rectangle((j%3)*6+(t-.76)*j*30,(j//3)*7+(t-.76)*j*15,4,5);c.fill()
            else:
                c.set_source_rgba(.16,.27,.43,alpha*.18);c.rectangle(2,3,18,24);c.fill()
                c.move_to(0,0);c.line_to(12,0);c.line_to(18,6);c.line_to(18,24);c.line_to(0,24);c.close_path()
                c.set_source_rgba(1,1,1,alpha);c.fill_preserve();c.set_source_rgba(.37,.48,.65,alpha);c.set_line_width(1);c.stroke()
                c.move_to(12,0);c.line_to(12,6);c.line_to(18,6);c.set_source_rgba(.72,.83,.95,alpha);c.fill()
                c.set_source_rgba(.42,.56,.72,alpha)
                for line in range(3):c.move_to(4,10+line*4);c.line_to(14,10+line*4);c.stroke()
            c.restore()
        return False
