"""Small bounded image previews and per-user window geometry, separate from theme data."""
import json,os,tempfile
from pathlib import Path
import gi
gi.require_version('GdkPixbuf','2.0');gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0')
from gi.repository import GdkPixbuf,Gdk

def state_path():
    return Path(os.environ.get('XP_EXPLORER_STATE_DIR',str(Path.home()/'.config/xp-explorer')))/'window.json'
def read_state():
    try:
        d=json.loads(state_path().read_text())
        return d if isinstance(d,dict) else {}
    except (OSError,ValueError):return {}
def write_state(state):
    p=state_path();p.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.window-',dir=p.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(state,f);f.flush();os.fsync(f.fileno())
        os.replace(name,p)
    finally:
        if os.path.exists(name):os.unlink(name)
def clamp_geometry(state,areas):
    """Fit saved client geometry in a current workarea, allowing titlebar clearance."""
    try:
        x,y,w,h=[int(state[k]) for k in ('x','y','width','height')]
        if w<300 or h<200:raise ValueError()
    except (KeyError,ValueError,TypeError,OverflowError):return None
    a=max(areas,key=lambda a:max(0,min(x+w,a[0]+a[2])-max(x,a[0]))*max(0,min(y+h,a[1]+a[3])-max(y,a[1])))
    w=min(w,a[2]);h=min(h,max(200,a[3]-45));x=max(a[0],min(x,a[0]+a[2]-w));y=max(a[1],min(y,a[1]+a[3]-h-40))
    return x,y,w,h

def load_image(uri,size):
    from core import file_for
    p=file_for(uri).get_path()
    if not p or not os.path.isfile(p) or os.path.getsize(p)>50*1024*1024:return None
    info,w,h=GdkPixbuf.Pixbuf.get_file_info(p)
    if not info or w<=0 or h<=0 or w*h>40_000_000:return None
    return GdkPixbuf.Pixbuf.new_from_file_at_scale(p,size,size,True)
