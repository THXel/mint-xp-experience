"""Compose panel additions without replacing the user's other applets."""
from .engine import Conflict
UUID='mintxp-tray@mintxp'

def original_setting(engine,schema,key):
    """Compose optional changes from their shared baseline, including schema defaults."""
    if not engine.read_current().get('installed'):return engine.settings.effective(schema,key)
    baseline=engine.read('baseline.json',{}).get('settings',{})
    name=schema+'/'+key
    if name not in baseline:return engine.settings.effective(schema,key)
    from gi.repository import GLib
    obj=engine.settings.obj(schema)
    value=(obj.get_default_value(key) if baseline[name] is None else GLib.Variant.parse(obj.get_value(key).get_type(),baseline[name],None,None)).unpack()
    if schema=='org.cinnamon' and key=='enabled-applets':
        current=engine.read_current();recorded=current.get('settings',{}).get(name)
        if recorded is not None:
            previous=GLib.Variant.parse(obj.get_value(key).get_type(),recorded,None,None).unpack()
            live=engine.settings.effective(schema,key)
            # A stale baseline may contain a menu absent from both the last
            # managed panel and today's panel. An update must not resurrect it.
            # Applets explicitly disabled by the installer remain restorable
            # when the user deselects them in the applet review.
            known={entry.split(':')[3] for entry in previous+live}
            disabled={entry.rsplit(':',1)[0] for entry in current.get('options',{}).get('disabled_applets',[])}
            value=[entry for entry in value if entry.split(':')[3] in known|disabled]
    return value

def add_tray(applets,next_id):
    entries=list(applets);parts=[s.split(':') for s in entries]
    if any(len(p)<5 for p in parts):raise Conflict('Unsupported panel entry. Keep the current panel unchanged.')
    if any(p[3].lstrip('!')==UUID for p in parts):return entries,next_id
    panels={p[0] for p in parts if p[1]=='right' and p[3].lstrip('!') in ('systray@cinnamon.org','xapp-status@cinnamon.org')}
    if len(panels)!=1:raise Conflict('Select one panel with a native notification area on its right before enabling the XP notification area.')
    panel=panels.pop()
    try:
        order=min(int(p[2]) for p in parts if p[0]==panel and p[1]=='right')-1
        ident=max([int(next_id),*[int(p[4])+1 for p in parts]])
    except (ValueError,TypeError):raise Conflict('Invalid panel order or applet ID.')
    entries.append(f'{panel}:right:{order}:{UUID}:{ident}')
    return entries,ident+1
