"""Original XP-inspired vector drawing; GPL-3.0-or-later. No Microsoft assets."""
import math
import cairo

def color(c,value):
    h=value.lstrip('#');c.set_source_rgb(*(int(h[i:i+2],16)/255 for i in (0,2,4)))
def text(c,value,x,y,size=24,fill='#ffffff',italic=False,bold=False):
    c.select_font_face('Liberation Sans',cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL);c.set_font_size(size);color(c,fill);c.move_to(x,y);c.show_text(value)
def brand(c,x,y,scale=1):
    c.save();c.translate(x,y);c.scale(scale,scale)
    for dx,dy,fill in [(0,0,'#f28b36'),(31,0,'#7cbe43'),(0,31,'#3f8fdf'),(31,31,'#e9c642')]:
        color(c,fill);c.rectangle(dx,dy,26,26);c.fill()
    text(c,'Mint',78,48,53,bold=True);text(c,'XP',193,24,28,'#ffac43',bold=True)
    text(c,'Experience',80,72,18);c.restore()
def background(c,w,h):
    g=cairo.LinearGradient(0,0,w,h);g.add_color_stop_rgb(0,.40,.58,.88);g.add_color_stop_rgb(1,.31,.45,.77);c.set_source(g);c.paint()
    color(c,'#00309d');c.rectangle(0,0,w,h*.115);c.fill();color(c,'#003899');c.rectangle(0,h*.86,w,h*.14);c.fill()
    c.set_source_rgba(.82,.9,1,.9);c.rectangle(0,h*.115,w,2);c.fill()
    g=cairo.LinearGradient(0,0,w,0);g.add_color_stop_rgba(0,1,.65,.1,0);g.add_color_stop_rgba(.3,1,.76,.35,1);g.add_color_stop_rgba(1,1,.65,.1,0);c.set_source(g);c.rectangle(0,h*.86,w,3);c.fill()
def login(c,w,h):
    background(c,w,h);scale=min(w/1600,h/1000);brand(c,w*.16,h*.43,1.3*scale)
    g=cairo.LinearGradient(0,h*.22,0,h*.77);g.add_color_stop_rgba(0,1,1,1,0);g.add_color_stop_rgba(.5,1,1,1,.65);g.add_color_stop_rgba(1,1,1,1,0);c.set_source(g);c.rectangle(w*.52,h*.22,2,h*.55);c.fill()
def boot(c,w,h,frame=0):
    color(c,'#000000');c.paint();s=min(w/640,h/360);c.save();c.translate(w/2-320*s,h/2-180*s);c.scale(s,s)
    brand(c,192,78,1.1)
    color(c,'#929292');c.set_line_width(1.5);c.rectangle(220,225,200,21);c.stroke()
    c.save();c.rectangle(223,228,194,15);c.clip();x=180+(frame%48)*5.3
    for i in range(3):
        g=cairo.LinearGradient(0,228,0,242);g.add_color_stop_rgb(0,.12,.35,.87);g.add_color_stop_rgb(.5,.4,.63,1);g.add_color_stop_rgb(1,.06,.17,.66);c.set_source(g);c.rectangle(x+i*11,228,9,14);c.fill()
    c.restore();text(c,'Linux Mint',272,287,15,'#a8a8a8');c.restore()
def png(path,w,h,draw):
    s=cairo.ImageSurface(cairo.FORMAT_ARGB32,w,h);draw(cairo.Context(s),w,h);s.write_to_png(str(path))
