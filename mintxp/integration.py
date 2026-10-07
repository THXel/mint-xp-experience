"""Local icon preference, desktop shortcut and per-field panel favourites."""
import ast,json,re
from pathlib import Path
from .engine import Conflict
EXPLORER='org.mintxp.Explorer.desktop'

def desktop_directory(home):
    home=Path(home);config=home/'.config/user-dirs.dirs';folder=home/'Desktop'
    if config.is_file():
        match=re.search(r'^XDG_DESKTOP_DIR="([^"\n]+)"\s*$',config.read_text(),re.M)
        if match:
            value=match[1].replace('${HOME}',str(home)).replace('$HOME',str(home))
            if '$' in value:return None
            folder=Path(value)
    if not folder.is_absolute() or not folder.is_relative_to(home) or not folder.is_dir():return None
    return folder

def local_icons(home):
    for directory in (Path(home)/'.local/share/icons',Path(home)/'.icons'):
        for name in ('XP-Icons-Mint','Windows-XP','Windows XP'):
            p=directory/name
            if (p/'index.theme').is_file() and not p.is_symlink():return str(p)
    return ''

def pin_explorer(engine,settings,root,replace_nemo=False):
    entries=engine.settings.effective('org.cinnamon','enabled-applets')
    defaults=json.loads((root/'assets/taskbar/settings-schema.json').read_text())['pinned-apps']['default']
    for entry in entries or []:
        fields=entry.split(':')
        if len(fields)<5 or fields[3].lstrip('!')!='grouped-window-list@cinnamon.org':continue
        key='mintxp-pins/'+fields[4];value=engine.settings.get(key)
        pins=ast.literal_eval(value.removeprefix('@as ')) if value is not None else list(defaults)
        if not isinstance(pins,list) or not all(isinstance(p,str) for p in pins):raise Conflict('Invalid panel favourites')
        removed={EXPLORER,'nemo.desktop','nemo-home.desktop'} if replace_nemo else {EXPLORER}
        settings[key]=engine.settings.literal([EXPLORER,*[p for p in pins if p not in removed]])
