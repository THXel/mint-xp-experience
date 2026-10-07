"""Bounded user preferences and desktop links; never execute user-supplied commands."""
from xp_locale import t as _xp
import json,os,tempfile
from pathlib import Path
from gi.repository import GLib,Gio
DEFAULT_FAVORITES=['cinnamon-settings-sound.desktop','cinnamon-display-panel.desktop','cinnamon-settings-themes.desktop']
ALIASES={
 'cinnamon-display-panel.desktop':'monitor bildschirm aufloesung auflosung skalierung hdmi',
 'cinnamon-settings-sound.desktop':'lautsprecher mikrofon headset kopfhorer kopfhoerer audio ton volume',
 'mintupdate.desktop':'updates update aktualisieren sicherheitsupdates',
 'cinnamon-settings-themes.desktop':'theme themes design aussehen icons symbole mauszeiger',
 'cinnamon-network-panel.desktop':'wlan wifi lan internet ethernet verbindung',
 'cinnamon-settings-power.desktop':'akku strom energiesparen standby bereitschaft',
 'cinnamon-settings-mouse.desktop':'maus cursor zeiger touchpad scrollen',
 'cinnamon-settings-user.desktop':'profil avatar benutzerbild konto',
 'cinnamon-settings-screensaver.desktop':'sperren bildschirmsperre sperrbildschirm',
 'cinnamon-settings-fonts.desktop':'schrift textgroesse textgrosse lesbarkeit',
 'mintdrivers.desktop':'grafikkarte nvidia amd treiber driver',
 'system-config-printer.desktop':'drucker drucken scanner',
 'cinnamon-settings-calendar.desktop':'datum uhr zeit zeitzone kalender',
 'cinnamon-settings-keyboard.desktop':'tastatur tasten shortcuts tastenkurzel tastenkürzel'}

class Preferences:
    def __init__(self):
        root=Path(os.environ.get('XP_CONTROL_STATE_DIR',str(Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'xp-control-panel')))
        self.path=root/'preferences.json';self.error=None;self.data={}
        try:
            if self.path.is_symlink():raise ValueError(_xp('Verknüpfte Einstellungsdatei wird nicht überschrieben.'))
            if self.path.exists():
                if self.path.stat().st_size>100000:raise ValueError(_xp('Einstellungsdatei ist zu groß.'))
                self.data=json.loads(self.path.read_text())
                if not isinstance(self.data,dict):raise ValueError(_xp('Ungültige Einstellungsdatei.'))
        except (ValueError,OSError) as error:self.error=str(error);self.data={}
    def save(self,values):
        if self.error:raise OSError(_xp('Einstellungen bleiben geschützt: ')+self.error)
        if self.path.is_symlink():raise OSError(_xp('Verknüpfte Einstellungsdatei wird nicht überschrieben.'))
        data=dict(self.data,**values);self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix='.preferences-',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path);self.data=data
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

def fit_geometry(saved,areas):
    try:
        x,y,w,h=[int(saved[k]) for k in ('x','y','width','height')]
        if w<400 or h<250 or not areas:return None
    except (KeyError,TypeError,ValueError,OverflowError):return None
    a=max(areas,key=lambda a:max(0,min(x+w,a[0]+a[2])-max(x,a[0]))*max(0,min(y+h,a[1]+a[3])-max(y,a[1])))
    w=min(w,a[2]-8);h=min(h,a[3]-45)
    return max(a[0],min(x,a[0]+a[2]-w)),max(a[1],min(y,a[1]+a[3]-h-40)),w,h

def create_shortcut(entry,desktop_dir=None):
    directory=desktop_dir or GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP)
    if not directory:raise OSError(_xp('Es ist kein Desktop-Ordner eingerichtet.'))
    directory=Path(directory)
    if not directory.is_dir():raise OSError(_xp('Der Desktop-Ordner ist nicht erreichbar.'))
    source=Path('/usr/share/applications')/entry['desktop']
    target=directory/('XP-'+source.name)
    # Only a trusted, installed entry is copied; exclusive creation protects existing files.
    data=source.read_bytes()
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o755)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    except BaseException:
        target.unlink();raise
    trusted=True
    try:Gio.File.new_for_path(str(target)).set_attribute_string('metadata::trusted','true',Gio.FileQueryInfoFlags.NONE,None)
    except GLib.Error:trusted=False
    return target,trusted
