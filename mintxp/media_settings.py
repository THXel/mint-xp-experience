"""Apply imported media separately from desktop, boot, games or panel installation."""
import copy
from .engine import Conflict
from .components import plan,COMPONENTS,THEME,DEFAULTS
from .sounds import PREFIX,settings_keys,imported_plan,ensure_ready

def apply(engine,options):
 current=engine.read_current()
 if not current.get('installed'):raise Conflict('Install the desktop before applying media separately.')
 target=copy.deepcopy(current);snapshot=engine.backup(reason='media')
 mode=options.get('icon_mode','bundled');source=options.get('icon_import','')
 if mode=='imported' and not source:raise Conflict('Choose an icon pack or ISO first.')
 # Only media inputs belong in this plan. Reusing installation options leaks
 # disabled_applets into the panel planner even when menu/tray are disabled.
 scoped=dict(DEFAULTS,**dict.fromkeys(COMPONENTS,False))
 scoped.update(icons=True,icon_mode=mode,icon_import=source,prefer_local_icons=False)
 icons=plan(engine,scoped)
 prefixes=('.local/share/icons/'+THEME+'-Icons/','.local/share/icons/'+THEME+'-Imported/')
 target['files']={k:v for k,v in target['files'].items() if not k.startswith(prefixes)}
 target['files'].update({k:v for k,v in icons['files'].items() if k.startswith(prefixes)})
 target['files'].update({k:v for k,v in icons['files'].items() if k.startswith('.local/share/xp-explorer/companion/')})
 target['settings'].update({k:v for k,v in icons['settings'].items() if k.endswith('/icon-theme')})
 target['options'].update(icons=True,icon_mode=mode,icon_import=source,prefer_local_icons=False)
 if options.get('sounds') and options.get('sound_source') not in (':keep:',':builtin:'):
  sound=imported_plan(engine,options,reimport=True);ensure_ready(sound['report'])
  target['files']={k:v for k,v in target['files'].items() if not k.startswith(PREFIX)};target['files'].update(sound['files'])
  target['settings']={k:v for k,v in target['settings'].items() if k not in settings_keys()};target['settings'].update(sound['settings'])
  for key in ('sounds','sound_source','sound_theme','sound_choices','sound_preserve'):target['options'][key]=options[key]
 elif current.get('options',{}).get('sound_source')==':builtin:':
  retire_luna(target)
 return {'snapshot':snapshot,'transaction':engine.apply(target,False)}


def retire_luna(target):
 """Retire only the former bundled pack; Engine restores its original baseline."""
 if target.get('options',{}).get('sound_source')!=':builtin:':return False
 target['files']={k:v for k,v in target['files'].items() if not k.startswith((PREFIX,'.local/share/mint-xp-experience/assets/sounds/luna/'))}
 target['settings']={k:v for k,v in target['settings'].items() if k not in settings_keys()}
 target['options'].update(sounds=False,sound_source=':keep:',sound_choices={})
 return True
