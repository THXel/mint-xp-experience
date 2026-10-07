#!/usr/bin/python3
"""Dismissible session-ending decoration. Never initiates logout or power-off."""
import argparse,os,signal,time
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0');gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk,Gdk,GLib,Pango,PangoCairo
from visuals import background,brand
from welcome import language
WORDS={
 'de':('Abmelden …','Der Computer wird heruntergefahren …','Der Computer wird neu gestartet …'),
 'en':('Logging off …','The computer is shutting down …','The computer is restarting …'),
 'fr':('Déconnexion …','Arrêt de l’ordinateur …','Redémarrage de l’ordinateur …'),
 'es':('Cerrando sesión …','Apagando el equipo …','Reiniciando el equipo …'),
 'it':('Disconnessione …','Arresto del computer …','Riavvio del computer …'),
 'pt':('A terminar sessão …','A desligar o computador …','A reiniciar o computador …'),
 'nl':('Afmelden …','De computer wordt afgesloten …','De computer wordt opnieuw gestart …'),
 'pl':('Wylogowywanie …','Zamykanie komputera …','Ponowne uruchamianie komputera …'),
 'tr':('Oturum kapatılıyor …','Bilgisayar kapatılıyor …','Bilgisayar yeniden başlatılıyor …'),
 'ru':('Выход из системы …','Завершение работы …','Перезагрузка компьютера …'),
 'uk':('Вихід із системи …','Завершення роботи …','Перезавантаження комп’ютера …'),
 'zh':('正在注销…','正在关闭计算机…','正在重新启动计算机…'),
 'ja':('ログオフしています…','シャットダウンしています…','再起動しています…'),
 'ko':('로그오프 중…','컴퓨터를 종료하는 중…','컴퓨터를 다시 시작하는 중…')}
def message(mode,lang,elapsed):
    return WORDS.get(lang,WORDS['en'])[0 if elapsed<1.4 or mode=='logout' else 2 if mode=='reboot' else 1]
def draw(area,c,label):
    a=area.get_allocation();w,h=a.width,a.height;background(c,w,h)
    scale=max(.55,min(w/1440,h/900));brand(c,w/2-126*scale,h*.40,scale)
    layout=PangoCairo.create_layout(c);layout.set_text(label,-1)
    layout.set_font_description(Pango.FontDescription('Sans '+str(max(13,int(20*scale)))))
    layout.set_width(int(w*.85*Pango.SCALE));layout.set_alignment(Pango.Alignment.CENTER)
    _,th=layout.get_pixel_size();x=w*.075;y=h*.56-th/2
    c.set_source_rgba(0,.12,.4,.6);c.move_to(x+1,y+2);PangoCairo.show_layout(c,layout)
    c.set_source_rgb(1,1,1);c.move_to(x,y);PangoCairo.show_layout(c,layout)
class Shutdown:
    def __init__(self,mode,preview=False,duration=30):
        self.start=time.monotonic();self.mode=mode;self.lang=language();self.duration=duration;self.windows=[]
        display=Gdk.Display.get_default()
        for i in range(1 if preview else display.get_n_monitors()):
            w=Gtk.Window(title='Mint XP – Shutdown preview' if preview else 'Mint XP – Session ending')
            w.set_wmclass('mintxp-shutdown','MintXPShutdown')
            if preview:w.set_default_size(1000,650);w.set_position(Gtk.WindowPosition.CENTER)
            else:
                g=display.get_monitor(i).get_geometry();w.set_decorated(False);w.set_skip_taskbar_hint(True);w.set_skip_pager_hint(True);w.set_keep_above(True);w.set_accept_focus(False);w.move(g.x,g.y);w.fullscreen_on_monitor(w.get_screen(),i)
            area=Gtk.DrawingArea();w.add(area);area.connect('draw',lambda a,c:draw(a,c,message(self.mode,self.lang,time.monotonic()-self.start)))
            w.connect('delete-event',lambda *_:self.quit());w.connect('key-press-event',lambda _,e:self.quit() if Gdk.keyval_name(e.keyval)=='Escape' else False)
            w.add_events(Gdk.EventMask.BUTTON_PRESS_MASK);w.connect('button-press-event',lambda *_:self.quit());w.show_all();self.windows.append(w)
        GLib.timeout_add(100,self.tick)
    def tick(self):
        if time.monotonic()-self.start>=self.duration:return self.quit()
        for w in self.windows:w.queue_draw()
        return True
    def quit(self):
        for w in self.windows:w.destroy()
        self.windows=[];Gtk.main_quit();return False

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['shutdown','reboot','logout'],default='shutdown');p.add_argument('--preview',action='store_true');args=p.parse_args()
    if not os.environ.get('DISPLAY'):return
    signal.signal(signal.SIGALRM,lambda *_:os._exit(0));signal.alarm(35)
    Shutdown(args.mode,args.preview,8 if args.preview else 30);Gtk.main()
if __name__=='__main__':main()
