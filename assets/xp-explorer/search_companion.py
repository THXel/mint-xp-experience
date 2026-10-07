"""Original Cairo penguin, or private ISO frames. No Windows code is executed."""
import json,math,re,time
from pathlib import Path
from collections import OrderedDict
import gi
gi.require_version('Gtk','3.0');gi.require_version('GdkPixbuf','2.0')
from gi.repository import Gtk,Gdk,GdkPixbuf,GLib
from xp_locale import t as _xp
from comfort import read_state,write_state

class Companion(Gtk.DrawingArea):
    STATES={'idle':'RestPose','welcome':'Greet','searching':'Searching','found':'Pleased','empty':'Thinking'}
    def __init__(self,folder=None):
        super().__init__();self.set_size_request(160,125);self.set_halign(Gtk.Align.CENTER)
        self.folder=Path(folder) if folder else Path(__file__).resolve().parent/'companion'
        self.animations={};self.cache=OrderedDict();self.state='welcome';self.frame=0;self.deadline=0;self.started=time.monotonic();self.timer=0
        self.animate=read_state().get('search_animation',True) is not False;self.choice=read_state().get('search_companion','auto');self.on_preferences=None
        self.set_tooltip_text(_xp('Suchbegleiter – Animation unten ein- oder ausschalten'))
        try:
            p=self.folder/'character.json'
            if p.is_symlink() or p.stat().st_size>1024*1024:raise ValueError('manifest')
            m=json.loads(p.read_text());count=0
            if m.get('format')!=1 or any(type(m.get(k))!=int or not 0<m[k]<=256 for k in ('width','height')):raise ValueError('dimensions')
            for name in self.STATES.values():
                frames=m['animations'].get(name,[])
                if len(frames)>1000:raise ValueError('frames')
                for filename,duration in frames:
                    if not re.fullmatch('[a-f0-9]{24}\\.png',filename) or type(duration)!=int or not 20<=duration<=10000:raise ValueError('frame')
                    p=self.folder/filename
                    if p.is_symlink() or p.stat().st_size>1024*1024:raise ValueError('image')
                    count+=1
                if frames:self.animations[name]=frames
            if not self.animations.get('RestPose'):raise ValueError('rest pose')
        except (OSError,ValueError,KeyError,TypeError):self.animations={}
        if self.choice not in ('auto','dog','penguin','none') or self.choice=='dog' and not self.animations:self.choice='auto'
        self.set_size_request(160,20 if self.choice=='none' else 125)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK);self.connect('button-press-event',self.context_menu)
        self.connect('draw',self.draw);self.connect('map',lambda *_:self.start_timer());self.connect('unmap',lambda *_:self.stop_timer());self.connect('destroy',lambda *_:self.stop_timer())
    def select(self,choice):
        if choice==self.choice or choice not in ('auto','dog','penguin','none'):return
        if choice=='dog' and not self.animations:return
        self.choice=choice;state=read_state();state['search_companion']=choice;write_state(state)
        self.set_size_request(160,20 if choice=='none' else 125);self.frame=0;self.deadline=0
        if choice=='none':self.stop_timer()
        elif self.get_mapped():self.start_timer()
        self.queue_draw()
        if self.on_preferences:self.on_preferences()
    def context_menu(self,widget,event):
        if event.button!=3:return False
        menu=Gtk.Menu();group=None
        for choice,title in [('auto','Automatisch'),('dog','Hund (aus eigener ISO)'),('penguin','Pinguin'),('none','Ohne Begleiter')]:
            item=Gtk.RadioMenuItem.new_with_label(group,_xp(title));group=item.get_group();item.set_active(self.choice==choice);item.set_sensitive(choice!='dog' or bool(self.animations));item.connect('activate',lambda w,c=choice:self.select(c) if w.get_active() else None);menu.add(item)
        menu.add(Gtk.SeparatorMenuItem());animation=Gtk.CheckMenuItem(label=_xp('Suchbegleiter animieren'));animation.set_active(self.animate);animation.connect('toggled',lambda w:self.enable(w.get_active()));menu.add(animation);menu.show_all();menu.popup_at_pointer(event);self.popup=menu;return True
    def start_timer(self):
        if self.animate and self.choice!='none' and not self.timer:self.timer=GLib.timeout_add(60,self.tick)
    def stop_timer(self):
        if self.timer:GLib.source_remove(self.timer);self.timer=0
    def enable(self,enabled):
        if self.animate==enabled:return
        self.animate=enabled;state=read_state();state['search_animation']=enabled;write_state(state)
        self.start_timer() if enabled and self.get_mapped() else self.stop_timer();self.queue_draw()
        if self.on_preferences:self.on_preferences()
    def set_state(self,state):
        self.state=state;self.frame=0;self.deadline=0;self.started=time.monotonic();self.queue_draw()
    def tick(self):self.queue_draw();return True
    def draw(self,w,c):
        width=self.get_allocated_width();height=self.get_allocated_height()
        if self.choice=='none':return False
        frames=self.animations.get(self.STATES[self.state],self.animations.get('RestPose')) if self.choice in ('auto','dog') else None
        if frames:
            try:
                now=time.monotonic()
                if not self.animate:frames=self.animations['RestPose'];index=0
                else:
                    if self.deadline and now>=self.deadline:
                        self.frame+=1
                        if self.frame>=len(frames):
                            if self.state in ('welcome','found','empty'):self.set_state('idle');frames=self.animations['RestPose']
                            self.frame=0
                        self.deadline=0
                    index=self.frame
                name,duration=frames[index]
                if not self.deadline:self.deadline=now+duration/1000
                if name not in self.cache:
                    p=self.folder/name
                    # Check dimensions before decoding, including changed private files.
                    info,w,h=GdkPixbuf.Pixbuf.get_file_info(str(p))
                    if not info or not 0<w<=256 or not 0<h<=256:raise ValueError('dimensions')
                    self.cache[name]=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(p),112,112,True)
                    if len(self.cache)>32:self.cache.popitem(last=False)
                pix=self.cache[name];self.cache.move_to_end(name);Gdk.cairo_set_source_pixbuf(c,pix,(width-pix.get_width())/2,height-pix.get_height());c.paint();return False
            except (GLib.Error,OSError,ValueError,IndexError):self.animations={};self.cache.clear()
        # Original artwork: a friendly penguin with a magnifying glass.
        t=time.monotonic()-self.started if self.animate else 0
        bounce=abs(math.sin(t*4))*4 if self.state in ('found','welcome') else math.sin(t*2)*1.1
        c.translate(width/2,height-59-bounce)
        def oval(x,y,rx,ry,color):
            c.save();c.translate(x,y);c.scale(rx,ry);c.set_source_rgba(*color);c.arc(0,0,1,0,math.tau);c.fill();c.restore()
        oval(0,49,42,5,(.1,.2,.3,.18));oval(-19,43,17,7,(.98,.65,.12,1));oval(19,43,17,7,(.98,.65,.12,1))
        oval(-32,10,10,28,(.12,.18,.24,1));oval(32,9,10,26,(.12,.18,.24,1))
        oval(0,5,34,43,(.10,.16,.22,1));oval(0,14,24,30,(.96,.98,1,1))
        oval(0,-27,29,28,(.10,.16,.22,1));oval(-12,-25,13,17,(1,1,1,1));oval(12,-25,13,17,(1,1,1,1))
        look=math.sin(t*2)*2 if self.state=='searching' else 0
        blink=self.animate and t%5>4.85
        for x in (-11,11):oval(x+look,-25,3,1 if blink else 5,(.07,.12,.17,1))
        c.set_source_rgb(1,.65,.12);c.move_to(-9,-14);c.line_to(0,-5);c.line_to(9,-14);c.close_path();c.fill()
        angle=math.sin(t*2)*.13 if self.state=='searching' else -.15
        c.save();c.translate(31,14);c.rotate(angle);c.set_source_rgb(.32,.22,.1);c.set_line_width(7);c.move_to(0,3);c.line_to(10,22);c.stroke()
        c.set_source_rgba(.68,.89,1,.65);c.arc(-6,-10,16,0,math.tau);c.fill_preserve();c.set_source_rgb(.45,.58,.7);c.set_line_width(4);c.stroke();c.set_source_rgba(1,1,1,.8);c.set_line_width(2);c.arc(-6,-10,11,3.4,4.8);c.stroke();c.restore()
        return False
