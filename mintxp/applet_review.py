"""Read-only panel inventory and explicit, reversible applet selection."""
import json
from pathlib import Path
from .engine import Conflict
XP_MENU='mintxp-menu@mintxp'
OWN={XP_MENU,'mintxp-tray@mintxp'}
KEY='org.cinnamon/enabled-applets'
def parts(entry):
 p=entry.split(':')
 if len(p)!=5 or not p[2].lstrip('-').isdigit() or not p[4].isdigit():raise Conflict('Unsupported applet entry; panel unchanged.')
 return p

def identity(entry):
 p=parts(entry);return p[3]+':'+p[4]

def metadata(engine,uuid):
 if '/' in uuid or uuid in ('.','..'):return {}
 for root in (engine.home/'.local/share/cinnamon/applets',Path('/usr/share/cinnamon/applets')):
  p=root/uuid/'metadata.json'
  try:
   if p.stat().st_size>65536:continue
   data=json.loads(p.read_text());return data if isinstance(data,dict) else {}
  except (OSError,ValueError):pass
 return {}

def inventory(engine,options):
 if not any(options.get(k) for k in ('shell','menu','taskbar','tray')):return []
 entries=list(engine.settings.effective('org.cinnamon','enabled-applets'))
 # Disabled applets remain selectable when revisiting the installer.
 saved=engine.read_current().get('options',{}).get('disabled_applets',[])
 if saved:
  from .tray_plan import original_setting
  entries+= [s for s in original_setting(engine,'org.cinnamon','enabled-applets') if identity(s) in saved and identity(s) not in {identity(x) for x in entries}]
 result=[]
 for entry in entries:
  p=parts(entry);uuid=p[3].lstrip('!');data=metadata(engine,uuid)
  if uuid in OWN:continue
  menu=('menu' in uuid.lower() or data.get('role')=='menu') and options.get('menu')
  if not menu and uuid.endswith('@cinnamon.org'):continue
  result.append({'id':identity(entry),'name':str(data.get('name') or uuid)[:100],'uuid':uuid,'panel':p[0],'zone':p[1],'reason':'applet_menu_reason' if menu else 'applet_custom_reason'})
 return result

def configure(engine,options,entries,next_id):
 selected=options.get('disabled_applets',[])
 if not isinstance(selected,list) or any(not isinstance(x,str) for x in selected):raise Conflict('Invalid applet selection')
 allowed={r['id'] for r in inventory(engine,options)}
 if set(selected)-allowed:raise Conflict('Applet selection changed. Review the current panel before installing.')
 source=list(entries);kept=[]
 for entry in source:
  p=parts(entry)
  disable=identity(entry) in selected
  # Cinnamon may have recreated an instance after the initial baseline.
  disable=disable or (sum(parts(x)[3]==p[3] for x in source)==1 and any(x.rsplit(':',1)[0]==p[3] for x in selected))
  if not disable:kept.append(entry)
 live=engine.settings.effective('org.cinnamon','enabled-applets')
 next_id=max([int(next_id),*[int(parts(x)[4])+1 for x in live]])
 if options.get('menu') and not any(parts(s)[3]==XP_MENU for s in kept):
  existing=next((s for s in live if parts(s)[3]==XP_MENU),None)
  if existing:kept.append(existing)
  else:
   panels=[parts(s)[0] for s in source];panel='panel1' if 'panel1' in panels else next(iter(panels),None)
   if not panel:raise Conflict('No panel found for the XP Start menu.')
   position=min([int(parts(s)[2]) for s in kept if parts(s)[0]==panel and parts(s)[1]=='left']+[0])-1
   kept.append(f'{panel}:left:{position}:{XP_MENU}:{next_id}');next_id+=1
 return kept,next_id

def check_review(engine,options):
 expected=options.get('reviewed_applets')
 if expected is not None and expected!=engine.settings.effective('org.cinnamon','enabled-applets'):
  raise Conflict('The panel changed since review. Please review the applet selection again.')
