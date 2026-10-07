"""Private WAV import and transactional Cinnamon/freedesktop sound assignments."""
import io,json,re,subprocess,wave,unicodedata
from .sound_sources import source_data
from pathlib import Path
from .engine import Conflict,encoded
BUILTIN=':builtin:'
NAME='Mint-XP-Experience-Sounds'
PREFIX='.local/share/sounds/'+NAME+'/'
# Standard event IDs plus the aliases already used by the personal XP setup.
ALIASES={
 'dialog-information':'Notify','message':'Notify','message-new-instant':'Notify','notification':'Notify',
 'dialog-warning':'Exclamation','dialog-error':'Critical Stop','dialog-error-serious':'Error',
 'bell':'Ding','bell-terminal':'Ding','audio-volume-change':'Ding',
 'device-added':'Hardware Insert','device-removed':'Hardware Remove','device-failed':'Hardware Fail',
 'desktop-login':'Startup','desktop-logout':'Shutdown','trash-empty':'Recycle','complete':'Print complete',
 'battery-low':'Battery Low','battery-caution':'Battery Low','battery-critical':'Battery Critical',
 'window-new':'Restore','window-close':'Menu Command','window-minimized':'Minimize',
 'window-unminimized':'Restore','window-maximized':'Restore','window-unmaximized':'Restore',
 'service-login':'Logon Sound','service-logout':'Logoff Sound','phone-incoming-call':'Ringin','phone-outgoing-calling':'Ringout',
}
CINNAMON={
 'login':('Startup','desktop-login'),'logout':('Shutdown','desktop-logout'),
 'switch':('Start',None),'close':('Menu Command','window-close'),'map':('Restore','window-new'),
 'minimize':('Minimize','window-minimized'),'maximize':('Restore','window-maximized'),
 'unmaximize':('Restore','window-unmaximized'),'tile':('Restore',None),
 'plug':('Hardware Insert','device-added'),'unplug':('Hardware Remove','device-removed'),
 'notification':('Notify','notification'),
}

def settings_keys():
 keys=[schema+'/'+key for schema in ('org.cinnamon.desktop.sound','org.gnome.desktop.sound') for key in ('theme-name','event-sounds')]
 keys += ['org.cinnamon.sounds/'+event+suffix for event in CINNAMON for suffix in ('-file','-enabled')]
 keys += ['org.cinnamon.desktop.sound/volume-sound-file','org.cinnamon.desktop.sound/volume-sound-enabled','org.cinnamon.desktop.wm.preferences/bell-sound']
 return set(keys)

# Exact normalized names only: never guess by a short substring such as "error".
SYNONYMS={
 'Notify':('Notification','Benachrichtigung','Hinweis','Information','Info'),
 'Exclamation':('Warning','Warnung','Ausruf','Ausrufezeichen'),
 'Critical Stop':('Critical Error','Fatal Error','Kritischer Fehler','Kritischer Abbruch'),
 'Error':('Fehler','Program Error'), 'Ding':('Bell','Klingel','Volume','Lautstaerke'),
 'Hardware Insert':('Device Added','Device Connected','USB Connect','Hardware hinzugefuegt','Geraet angeschlossen'),
 'Hardware Remove':('Device Removed','Device Disconnected','USB Disconnect','Hardware entfernt','Geraet entfernt'),
 'Hardware Fail':('Device Failed','Hardwarefehler','Geraetefehler'),
 'Startup':('System Start','Start Windows','Hochfahren','Systemstart'),
 'Shutdown':('Windows Shutdown','System Shutdown','Herunterfahren','Windows beenden'),
 'Recycle':('Recycle Bin','Empty Trash','Trash Empty','Papierkorb leeren','Papierkorb'),
 'Print complete':('Print Complete','Printing Complete','Druck abgeschlossen','Druckvorgang beendet'),
 'Battery Low':('Akku schwach','Niedriger Akkustand'), 'Battery Critical':('Akku kritisch','Kritischer Akkustand'),
 'Restore':('Window Restore','Wiederherstellen','Fenster wiederherstellen'),
 'Minimize':('Minimise','Window Minimize','Minimieren','Fenster minimieren'),
 'Menu Command':('MenuCommand','Window Close','Fenster schliessen','Menuebefehl'),
 'Logon Sound':('Logon','Login','Anmelden','Anmeldung'),
 'Logoff Sound':('Logoff','Logout','Abmelden','Abmeldung'),
 'Ringin':('Incoming Call','Eingehender Anruf'), 'Ringout':('Outgoing Call','Ausgehender Anruf'),
 'Start':('Navigation Start','Start Navigation','Navigation starten','Arbeitsflaeche wechseln'),
}
def normal(name):
 name=name.casefold().replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')
 name=''.join(c for c in unicodedata.normalize('NFKD',name) if c.isalnum())
 for prefix in ('microsoftwindowsxp','microsoftwindows','windowsxp','winxp','windows','xp','luna'):
  if name.startswith(prefix):name=name[len(prefix):];break
 return name

def source_folder(engine,options):
 if options.get('sound_source') in (BUILTIN,':keep:'):raise Conflict('Select a soundpack or ISO first. No bundled sounds are provided.')
 if options.get('sound_source'):return Path(options['sound_source']).expanduser().resolve(strict=True)
 name=options.get('sound_theme','Windows-XP')
 if not isinstance(name,str) or not name or '/' in name or '\\' in name or name in ('.','..'):raise Conflict('Invalid sound theme name')
 return (engine.home/'.local/share/sounds'/name).resolve(strict=True)

def imported_plan(engine,options,reimport=False):
 """Return only sound files/settings. Reuse the managed copy after source removal."""
 if options.get('sound_source')==':mint:':
  from .mint_sounds import plan
  return plan(engine)
 current=engine.read_current();old=current.get('options',{})
 if not reimport and old.get('sounds') and all(options.get(k,d)==old.get(k,d) for k,d in [('sound_source',''),('sound_theme','Windows-XP'),('sound_preserve',True),('sound_choices',{})]) and current['files'].get(PREFIX+'mapping.json'):
  files={k:v for k,v in current['files'].items() if k.startswith(PREFIX) and v is not None}
  settings={k:v for k,v in current['settings'].items() if k in settings_keys()}
  report=json.loads(engine.data(files[PREFIX+'mapping.json']))
  return {'files':files,'settings':settings,'report':report}
 source=source_folder(engine,options)
 if source==engine.home or source==Path('/'):raise Conflict('Choose the soundpack folder, not your home or filesystem root.')
 dest=engine.path(PREFIX+'index.theme').parent
 if dest.exists() and any(p.is_file() or p.is_symlink() for p in dest.rglob('*')) and not current['files'].get(PREFIX+'mapping.json'):raise Conflict('Untracked sound destination protected: '+str(dest))
 try:payload,resolved,disabled=source_data(source)
 except (ValueError,OSError) as error:raise Conflict(str(error)) from error
 if not payload:raise Conflict('No supported PCM WAV files found in the selected folder or archive.')
 for rel,data in payload.items():
  try:
   with wave.open(io.BytesIO(data)) as wav:
    if wav.getnchannels() not in (1,2) or not 8000<=wav.getframerate()<=192000 or wav.getsampwidth() not in (1,2,3,4) or wav.getnframes()==0:raise ValueError('Unsupported PCM format')
    if len(wav.readframes(wav.getnframes()))!=wav.getnframes()*wav.getnchannels()*wav.getsampwidth():raise ValueError('Truncated audio')
  except (wave.Error,EOFError,ValueError) as error:raise Conflict('Invalid PCM WAV '+rel+': '+str(error))
 files={PREFIX+'originals/'+rel:engine.descriptor(data) for rel,data in payload.items()}
 ambiguous={};choices=options.get('sound_choices',{})
 if not isinstance(choices,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in choices.items()):raise Conflict('Invalid sound choices')
 def choose(key,matches):
  if not matches:return None
  if choices.get(key) in matches:return choices[key]
  # Identical copies are harmless; different versions require a real selection.
  if len({payload[rel] for rel in matches})==1:return min(matches,key=lambda rel:(len(Path(rel).parts),rel))
  ambiguous[key]=sorted(matches);return None
 def named(stem):
  canonical=[rel for rel in payload if normal(Path(rel).stem)==normal(stem)]
  names={normal(n) for n in SYNONYMS.get(stem,())}
  return choose('stem:'+stem,canonical or [rel for rel in payload if normal(Path(rel).stem) in names])
 aliases={};missing=[]
 for event,stem in ALIASES.items():
  if event in disabled:continue
  explicit=[rel for rel in payload if normal(Path(rel).stem)==normal(event)]
  rel=choose('event:'+event,explicit) if explicit else named(stem)
  if rel:aliases[event]=rel
  else:missing.append(event)
 # Preserve custom event IDs from an already configured source theme.
 for rel in payload:
  event=Path(rel).stem
  if Path(rel).parent.name=='stereo' and re.fullmatch(r'[a-z0-9][a-z0-9-]*',event) and event not in disabled and event not in ALIASES:
   candidates=[name for name in payload if Path(name).parent.name=='stereo' and Path(name).stem==event]
   selected=choose('event:'+event,candidates)
   if selected:aliases[event]=selected
 for event,rel in aliases.items():files[PREFIX+'stereo/'+event+'.wav']=engine.descriptor(payload[rel])
 for event in disabled:
  if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',event):raise Conflict('Invalid disabled event name')
  files[PREFIX+'stereo/'+event+'.disabled']=engine.descriptor(b'')
 title='Mint XP Experience - Imported Sounds'
 files[PREFIX+'index.theme']=engine.descriptor(('[Sound Theme]\nName='+title+'\nInherits=freedesktop\nDirectories=stereo\n\n[stereo]\nOutputProfile=stereo\n').encode())
 settings={};events={}
 def setv(schema,key,value):
  engine.settings.get(schema+'/'+key);settings[schema+'/'+key]=engine.settings.literal(value)
 def assign(schema,filekey,enabledkey,stem,alias,event):
  rel=None;preserved=False
  oldfile=engine.settings.effective(schema,filekey)
  if options.get('sound_preserve',True) and oldfile:
   rel=resolved.get(Path(oldfile).expanduser().resolve())
   previous=Path(oldfile)
   if rel is None and previous.is_relative_to(dest/'originals'):
    candidate=str(previous.relative_to(dest/'originals'))
    if candidate in payload:rel=candidate
   preserved=rel is not None
  rel=rel or aliases.get(alias) or (None if 'event:'+str(alias) in ambiguous else named(stem))
  if not rel:events[event]={'mapped':False};return
  setv(schema,filekey,str(engine.home/(PREFIX+'originals/'+rel)))
  enabled=engine.settings.effective(schema,enabledkey) if preserved and enabledkey else event!='close'
  if enabledkey:setv(schema,enabledkey,enabled)
  events[event]={'mapped':True,'file':'originals/'+rel,'enabled':enabled if enabledkey else None,'preserved':preserved}
 for event,(stem,alias) in CINNAMON.items():assign('org.cinnamon.sounds',event+'-file',event+'-enabled',stem,alias,event)
 assign('org.cinnamon.desktop.sound','volume-sound-file','volume-sound-enabled','Ding','audio-volume-change','volume')
 assign('org.cinnamon.desktop.wm.preferences','bell-sound',None,'Ding','bell','bell')
 for schema in ('org.cinnamon.desktop.sound','org.gnome.desktop.sound'):
  setv(schema,'theme-name',NAME);setv(schema,'event-sounds',True)
 report={'format':2,'pack':'custom','ambiguous':ambiguous,'wave_files':len(payload),'unique_files':len(resolved),'aliases':aliases,'disabled_events':sorted(disabled),'cinnamon':events,'missing_aliases':missing,'unassigned_files':sorted(resolved[path] for path in set(resolved)-{(source/rel).resolve() for rel in list(aliases.values())+[e['file'].removeprefix('originals/') for e in events.values() if e['mapped']]})}
 files[PREFIX+'mapping.json']=engine.descriptor(encoded(report),0o600)
 return {'files':files,'settings':settings,'report':report}

def ensure_ready(report):
 if report.get('ambiguous'):raise Conflict('Multiple different sounds match an event. Open the sound assignment preview and choose a file for each ambiguous event.')
 if not report['aliases'] and not any(e['mapped'] for e in report['cinnamon'].values()):raise Conflict('No known sound names or event aliases found. Use the sound assignment preview to review the filenames.')

def apply_import(engine,options,prepared=None):
 if not engine.read_current().get('installed'):raise Conflict('Install the theme manager first, or select sounds in the component preview.')
 result=prepared if prepared is not None else imported_plan(engine,options,reimport=True);ensure_ready(result['report']);snapshot=engine.backup(reason='sounds');target=engine.read_current()
 target['files']={k:v for k,v in target['files'].items() if not k.startswith(PREFIX)}
 target['settings']={k:v for k,v in target['settings'].items() if k not in settings_keys()}
 target['files'].update(result['files']);target['settings'].update(result['settings'])
 for key in ('sound_theme','sound_source','sound_preserve','sound_choices'):target['options'][key]=options.get(key,{'sound_theme':'Windows-XP','sound_source':'','sound_preserve':True,'sound_choices':{}}[key])
 target['options']['sounds']=True;transaction=engine.apply(target,reference=False)
 return {'snapshot':snapshot,'transaction':transaction,**result['report']}

def remove_import(engine):
 target=engine.read_current()
 if not target.get('options',{}).get('sounds'):raise Conflict('No active sound import')
 snapshot=engine.backup(reason='sounds');target['files']={k:v for k,v in target['files'].items() if not k.startswith(PREFIX)}
 target['settings']={k:v for k,v in target['settings'].items() if k not in settings_keys()}
 target['options']['sounds']=False
 return {'snapshot':snapshot,'transaction':engine.apply(target,reference=False)}

def verify(engine):
 current=engine.read_current();files={k:v for k,v in current['files'].items() if k.startswith(PREFIX) and v is not None}
 if not current.get('options',{}).get('sounds') or not files:raise Conflict('No active sound import')
 errors=engine.check({'files':files,'settings':{k:v for k,v in current['settings'].items() if k in settings_keys()}},allow_preferences=True)
 if errors:raise Conflict('\n'.join(errors))
 report=json.loads(engine.data(files[PREFIX+'mapping.json']));return {'integrity':'OK',**report}

def play_test(engine,event='bell'):
 report=verify(engine)
 if report.get('pack')=='mint':
  path=report.get('preview_files',{}).get(event)
  if not path:raise Conflict('No Mint sound mapped for '+event)
  subprocess.run(['canberra-gtk-play','--file='+path],check=True,timeout=20)
  return 'Playback request completed: '+event
 if event not in ALIASES:raise Conflict('Unknown test event')
 if not (engine.home/(PREFIX+'stereo/'+event+'.wav')).exists():raise Conflict('No sound mapped for '+event)
 subprocess.run(['canberra-gtk-play','--id='+event],check=True,timeout=20)
 return 'Playback request completed: '+event
