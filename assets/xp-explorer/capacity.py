"""Filesystem capacity sampled by the existing worker; a thin XP segment meter."""
import os,math
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk
import cairo

def usage(path):
    try:
        s=os.statvfs(path);total=s.f_blocks*s.f_frsize
        if total<=0:return None
        free=max(0,min(total,s.f_bavail*s.f_frsize));used=max(0,min(total,(s.f_blocks-s.f_bfree)*s.f_frsize))
        return dict(total=total,free=free,used=used,fraction=used/total)
    except OSError:return None

class CapacityBar(Gtk.DrawingArea):
    def __init__(self,stats,tooltip):
        super().__init__();self.stats=stats;self.set_size_request(130,9);self.set_hexpand(True);self.set_valign(Gtk.Align.CENTER)
        self.set_tooltip_text(tooltip);self.get_accessible().set_name(tooltip);self.connect('draw',self.draw_meter)
    def draw_meter(self,widget,cr):
        w=self.get_allocated_width();h=self.get_allocated_height()
        cr.set_source_rgb(.52,.57,.64);cr.rectangle(0,0,w,h);cr.fill()
        cr.set_source_rgb(.98,.98,.96);cr.rectangle(1,1,w-2,h-2);cr.fill()
        if not self.stats:return False
        fraction=max(0,min(1,float(self.stats['fraction'])));filled=(w-4)*fraction
        cr.save();cr.rectangle(2,2,filled,h-4);cr.clip()
        # Red also reflects low user-available space, including reserved filesystem blocks.
        low=self.stats['free']/self.stats['total']<=.10
        gradient=cairo.LinearGradient(0,2,0,h-2)
        colors=[(.98,.63,.51),(.84,.23,.12),(.68,.10,.05)] if low else [(.67,.91,.43),(.26,.67,.12),(.13,.47,.06)]
        for stop,color in zip([0,.45,1],colors):gradient.add_color_stop_rgb(stop,*color)
        cr.set_source(gradient)
        for x in range(2,max(2,math.ceil(w-2)),8):cr.rectangle(x,2,6,h-4)
        cr.fill();cr.restore();return False
