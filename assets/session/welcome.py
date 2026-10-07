#!/usr/bin/python3
"""Brief post-login decoration, never an authentication or lock screen."""
import argparse,os,time,signal,fcntl,json
from pathlib import Path
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0');gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk,Gdk,GLib,Pango,PangoCairo
from visuals import background,brand
WORDS={'de':'Willkommen','en':'Welcome','fr':'Bienvenue','es':'Bienvenido','it':'Benvenuto','pt':'Bem-vindo','nl':'Welkom','pl':'Witamy','tr':'Hoş geldiniz','ru':'Добро пожаловать','uk':'Ласкаво просимо','zh':'欢迎','ja':'ようこそ','ko':'환영합니다'}
def language():
    try:
        p=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'mint-xp-experience/preferences.json'
        chosen=json.loads(p.read_text()).get('language','auto')
        if chosen in WORDS:return chosen
    except (OSError,ValueError,TypeError,AttributeError):pass
    loc=os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG','en')
    if loc in ('C','POSIX') or loc.startswith('C.'):return 'en'
    for candidate in ([loc] if os.environ.get('LC_ALL') else os.environ.get('LANGUAGE','').split(':')+[loc]):
        value=candidate.split('.')[0].split('_')[0].split('-')[0]
        if value in WORDS:return value
    return 'en'
def settings():
    values={'duration':2.6,'fade':True,'monitors':'all'}
    try:
        p=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'mint-xp-experience/session.json';data=json.loads(p.read_text())
        import math
        duration=data.get('duration')
        if isinstance(duration,(int,float)) and not isinstance(duration,bool) and math.isfinite(duration) and .5<=duration<=8:values['duration']=duration
        if isinstance(data.get('fade'),bool):values['fade']=data['fade']
        if data.get('monitors') in ('primary','all'):values['monitors']=data['monitors']
    except (OSError,ValueError,TypeError,AttributeError):pass
    return values
class Welcome:
    def __init__(self,preview=False,duration=2.6,lang=None,fade=True,monitors="all"):
        self.windows=[];self.start=time.monotonic();self.duration=duration;self.lang=lang or language();self.preview=preview;self.fade=fade
        display=Gdk.Display.get_default();primary=display.get_primary_monitor() or display.get_monitor(0)
        indices=[i for i in range(display.get_n_monitors()) if preview or monitors=="all" or display.get_monitor(i)==primary]
        if preview:indices=indices[:1]
        for i in indices:
            monitor=primary if preview else display.get_monitor(i);geo=monitor.get_geometry();w=Gtk.Window(title='Mint XP – Welcome preview' if preview else 'Mint XP Welcome')
            w.set_wmclass('mintxp-welcome','MintXPWelcome');w.set_app_paintable(True)
            if preview:w.set_default_size(1000,650);w.set_position(Gtk.WindowPosition.CENTER)
            else:
                w.set_decorated(False);w.set_skip_taskbar_hint(True);w.set_skip_pager_hint(True);w.set_keep_above(True);w.set_accept_focus(False);w.move(geo.x,geo.y);w.fullscreen_on_monitor(w.get_screen(),i)
            area=Gtk.DrawingArea();w.add(area);area.connect('draw',self.draw,monitor==primary or preview);w.connect('delete-event',lambda *_:self.quit());w.connect('key-press-event',self.key);w.add_events(Gdk.EventMask.BUTTON_PRESS_MASK);w.connect('button-press-event',lambda *_:self.quit());w.show_all();self.windows.append(w)
        GLib.timeout_add(30,self.tick)
    def draw(self,area,c,main):
        a=area.get_allocation();w,h=a.width,a.height;background(c,w,h)
        if main:
            scale=min(w/1440,h/900);brand(c,w*.19,h*.42,1.2*scale)
            layout=PangoCairo.create_layout(c);layout.set_text(WORDS.get(self.lang,WORDS['en']),-1);layout.set_font_description(Pango.FontDescription(f'Liberation Sans Italic {max(24,int(48*scale))}'))
            tw,th=layout.get_pixel_size()
            if tw>w*.43:
                layout.set_font_description(Pango.FontDescription(f'Liberation Sans Italic {max(12,int(48*scale*w*.43/tw))}'));tw,th=layout.get_pixel_size()
            x=w*.53;y=h*.49-th/2;c.set_source_rgba(0,.15,.45,.5);c.move_to(x+2,y+3);PangoCairo.show_layout(c,layout);c.set_source_rgb(1,1,1);c.move_to(x,y);PangoCairo.show_layout(c,layout)
    def key(self,w,e):
        if Gdk.keyval_name(e.keyval)=='Escape':return self.quit()
        return False
    def tick(self):
        elapsed=time.monotonic()-self.start
        if elapsed>self.duration:return self.quit()
        if self.fade and elapsed>self.duration-.35:
            for w in self.windows:
                if w.is_composited():w.set_opacity(max(0,(self.duration-elapsed)/.35))
        return True
    def quit(self):
        for w in self.windows:w.destroy()
        self.windows=[];Gtk.main_quit();return False

def main():
    p=argparse.ArgumentParser();p.add_argument('--preview',action='store_true');p.add_argument('--duration',type=float,default=None);p.add_argument('--language',choices=list(WORDS));p.add_argument('--monitors',choices=['all','primary']);p.add_argument('--no-fade',action='store_true');args=p.parse_args()
    if not args.preview and (os.environ.get('SSH_CONNECTION') or not os.environ.get('DISPLAY')):return
    lock=None
    if not args.preview:
        runtime=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())));lock=open(runtime/'mintxp-welcome.lock','w')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
    # Independent watchdog: decoration must never trap the desktop.
    signal.signal(signal.SIGALRM,lambda *_:os._exit(0));signal.alarm(12)
    values=settings();duration=values['duration'] if args.duration is None else args.duration
    import math
    if not math.isfinite(duration):duration=2.6
    Welcome(args.preview,max(.5,min(duration,8)),args.language,values['fade'] and not args.no_fade,args.monitors or values['monitors']);Gtk.main()
if __name__=='__main__':main()
