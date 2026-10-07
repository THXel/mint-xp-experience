#!/usr/bin/python3
"""Reviewable native UI for optional system appearance, with polkit authentication."""
import sys,subprocess,threading
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from mintxp.i18n import Translator
tr=Translator();de=tr.language=='de'
def txt(a,b):return a if de else b
class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title=tr('session_appearance'));self.set_default_size(700,560);self.set_position(Gtk.WindowPosition.CENTER);self.busy=False;self.connect('delete-event',lambda *_:self.busy);self.connect('destroy',Gtk.main_quit)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);box.set_border_width(22);self.add(box)
        info=Gtk.Label(label=txt('XP-Bootbildschirm und Anmeldeansicht\n\nDie Installation benötigt dein Administratorpasswort im normalen Systemdialog. Sie sichert die betroffenen Dateien und Boot-Images vor der Änderung. Automatische Anmeldung und Passwortprüfung bleiben unverändert.\n\nWelcome wird separat unter „Komponenten“ in der Theme-Verwaltung aktiviert.','XP boot splash and login appearance\n\nInstallation requests administrator authentication in the system dialog and backs up affected files and boot images before changing them. Automatic login and authentication stay unchanged.\n\nEnable Welcome separately under Components in the theme manager.'),xalign=0);info.set_line_wrap(True);box.pack_start(info,False,False,0)
        self.boot=Gtk.CheckButton(label=txt('Boot: schwarzer Hintergrund und blaue Ladebalken','Boot: black background and blue loading bars'));self.boot.set_active(True);box.pack_start(self.boot,False,False,0)
        self.login=Gtk.CheckButton(label=txt('Anmeldung: blaue XP-Ansicht mit nativer Benutzer-/Passwortauswahl','Login: blue XP appearance with native user/password selection'));self.login.set_active(True);box.pack_start(self.login,False,False,0)
        for label,fn in [(txt('Welcome-Vorschau','Welcome preview'),lambda:subprocess.Popen(['/usr/bin/python3','-B',str(ROOT/'assets/session/welcome.py'),'--preview','--duration','6'])),(txt('Installieren / prüfen','Install / check'),self.install),(txt('Systeminstallation überprüfen','Verify system installation'),lambda:self.run('verify')),(txt('Boot und Anmeldung zurücksetzen','Restore previous boot and login'),self.restore)]:
            b=Gtk.Button(label=label);b.connect('clicked',lambda _,fn=fn:fn());box.pack_start(b,False,False,0)
        self.status=Gtk.Label(xalign=0);self.status.set_line_wrap(True);self.status.set_selectable(True);box.pack_start(self.status,True,True,0)
        self.show_all()
    def install(self):
        if not self.boot.get_active() and not self.login.get_active():return
        self.run('apply',(['--boot'] if self.boot.get_active() else [])+(['--login'] if self.login.get_active() else []))
    def restore(self):
        d=Gtk.MessageDialog(transient_for=self,modal=True,buttons=Gtk.ButtonsType.OK_CANCEL,text=txt('Vorherige Boot- und Anmeldeoptik wiederherstellen?','Restore the previous boot and login appearance?'));d.set_default_response(Gtk.ResponseType.CANCEL);answer=d.run();d.destroy()
        if answer==Gtk.ResponseType.OK:self.run('undo')
    def run(self,action,options=()):
        if self.busy:return
        self.busy=True;self.status.set_text(txt('Systemdialog beachten. Bitte warten; das Boot-Image kann einige Minuten benötigen.','Check the system authentication dialog. Building the boot image may take a few minutes.'))
        installed=Path('/var/lib/mint-xp-experience-system/appearance.py');script=installed if action!='apply' and installed.parent.exists() else Path(__file__).with_name('appearance.py')
        def worker():
            try:
                r=subprocess.run(['/usr/bin/pkexec','/usr/bin/python3','-I','-B',str(script),action,*options],capture_output=True,text=True);message=(r.stdout+'\n'+r.stderr)[-6000:] if r.returncode else txt('Erfolgreich. Ein Neustart wurde nicht ausgelöst.\n','Done. No reboot was triggered.\n')+r.stdout[-1500:]
            except Exception as e:message=str(e)
            GLib.idle_add(done,message)
        def done(message):self.busy=False;self.status.set_text(message);return False
        threading.Thread(target=worker,daemon=False).start()
if __name__=='__main__':Window();Gtk.main()
