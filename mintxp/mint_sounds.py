"""Select the Mint audio already installed by the distribution, with normal undo."""
import json
from pathlib import Path
from .engine import Conflict, encoded

SOURCE = ':mint:'
ART = Path('/usr/share/mint-artwork/sounds')
THEME = Path('/usr/share/sounds/LinuxMint')


def plan(engine):
    from .sounds import PREFIX, CINNAMON, ALIASES
    from gi.repository import Gio
    if not (THEME/'index.theme').is_file():
        raise Conflict('The original Linux Mint sound theme is not installed')
    settings = {};events = {};preview = {}
    schemas = Gio.SettingsSchemaSource.get_default()
    def default(schema, key):
        found = schemas.lookup(schema, True)
        if not found or not found.has_key(key):raise Conflict('Mint sound setting unavailable: '+key)
        return found.get_key(key).get_default_value().unpack()
    def put(schema, key, value):settings[schema+'/'+key] = engine.settings.literal(value)
    for event in CINNAMON:
        file = ART/(event+('.ogg' if event == 'logout' else '.oga'))
        if not file.is_file():raise Conflict('Original Mint sound missing: '+file.name)
        put('org.cinnamon.sounds', event+'-file', str(file))
        enabled = default('org.cinnamon.sounds', event+'-enabled')
        put('org.cinnamon.sounds', event+'-enabled', enabled)
        events[event] = {'mapped':True, 'file':str(file), 'enabled':enabled, 'preserved':False}
    volume = ART/'volume.oga'
    if not volume.is_file():raise Conflict('Original Mint volume sound missing')
    put('org.cinnamon.desktop.sound', 'volume-sound-file', str(volume))
    put('org.cinnamon.desktop.sound', 'volume-sound-enabled', default('org.cinnamon.desktop.sound','volume-sound-enabled'))
    put('org.cinnamon.desktop.wm.preferences','bell-sound',default('org.cinnamon.desktop.wm.preferences','bell-sound'))
    events['volume']={'mapped':True,'file':str(volume),'enabled':default('org.cinnamon.desktop.sound','volume-sound-enabled'),'preserved':False}
    events['bell']={'mapped':True,'file':str(volume),'enabled':None,'preserved':False}
    for schema in ('org.cinnamon.desktop.sound','org.gnome.desktop.sound'):
        put(schema,'theme-name','LinuxMint');put(schema,'event-sounds',True)
    for event in ALIASES:
        for suffix in ('.oga','.ogg','.wav'):
            p=THEME/'stereo'/(event+suffix)
            if p.is_file():preview[event]=str(p);break
    art_events={'bell':'volume','bell-terminal':'volume','audio-volume-change':'volume',
                'notification':'notification','message':'notification','message-new-instant':'notification',
                'device-added':'plug','device-removed':'unplug','trash-empty':'trash',
                'window-new':'map','window-close':'close','window-minimized':'minimize',
                'window-unminimized':'map','window-maximized':'maximize','window-unmaximized':'unmaximize'}
    for event,stem in art_events.items():
        if (ART/(stem+'.oga')).is_file():preview[event]=str(ART/(stem+'.oga'))
    report={'format':2,'pack':'mint','wave_files':0,'unique_files':len(set(preview.values())),
            'aliases':preview,'preview_files':preview,'ambiguous':{},'disabled_events':[],
            'cinnamon':events,'missing_aliases':sorted(set(ALIASES)-set(preview)),
            'unassigned_files':[]}
    return {'files':{PREFIX+'mapping.json':engine.descriptor(encoded(report),0o600)},
            'settings':settings,'report':report}
