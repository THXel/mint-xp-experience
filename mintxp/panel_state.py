"""Reconcile panel preferences without discarding added or moved user applets."""
import ast,json,copy
PREFIX='org.cinnamon/'
ZONES={PREFIX+n for n in ('panel-zone-icon-sizes','panel-zone-symbolic-icon-sizes','panel-zone-text-sizes')}
APPLETS=PREFIX+'enabled-applets';NEXT=PREFIX+'next-applet-id'
def decode(key,value):
 if value is None:return None
 value=ast.literal_eval(value.removeprefix('@as ') if key==APPLETS and isinstance(value,str) else value)
 if key in ZONES:
  value=json.loads(value)
  if not isinstance(value,list) or not all(isinstance(row,dict) and 'panelId' in row for row in value):raise ValueError('Invalid panel sizing')
 if key==APPLETS:
  if not isinstance(value,list):raise ValueError('Invalid applets')
  for entry in value:
   p=entry.split(':')
   if len(p)!=5 or not p[0].startswith('panel') or p[1] not in ('left','center','right') or not p[2].lstrip('-').isdigit() or not p[4].isdigit():raise ValueError('Invalid applet entry')
 if key==NEXT and (type(value)!=int or value<0):raise ValueError('Invalid next ID')
 return value
def equivalent(key,a,b):
 if a==b:return True
 if key not in ZONES:return False
 try:return decode(key,a)==decode(key,b)
 except (ValueError,TypeError,SyntaxError):return False
def preference(key,value):
 if key not in ZONES|{APPLETS,NEXT}:return False
 try:decode(key,value);return value is not None
 except (ValueError,TypeError,SyntaxError,AttributeError):return False

def applets_merge(old,live,wanted):
 old=[x.split(':') for x in old];live=[x.split(':') for x in live];wanted=[x.split(':') for x in wanted]
 consumed=set()
 for e in old:
  match=next((i for i,p in enumerate(live) if p[3:]==e[3:]),None)
  if match is None and sum(p[3]==e[3] for p in old)==1:
   ids=[i for i,p in enumerate(live) if p[3]==e[3]]
   if len(ids)==1:match=ids[0]
  d=next((p for p in wanted if p[4]==e[4]),None)
  if d is None and sum(p[3]==e[3] for p in wanted)==1:d=next(p for p in wanted if p[3]==e[3])
  if d is not None:consumed.add(tuple(d))
  if match is None:continue # An applet deliberately removed by the user stays removed.
  p=live[match]
  if d is None:live.pop(match)
  else:
   p[3]=d[3]
   for index in (0,1,2):
    if p[index]==e[index]:p[index]=d[index]
  # Keep each current instance ID, including a menu recreated by Cinnamon.
 live=[p for p in live if p is not None]
 for d in wanted:
  if tuple(d) in consumed:continue
  # A disabled applet may have been re-added by the user with a new ID.
  if sum(x[3]==d[3] for x in wanted)==1 and sum(x[3]==d[3] for x in live)==1 and not any(x[3]==d[3] for x in old):continue
  p=list(d)
  if any(x[4]==p[4] for x in live):p[4]=str(max(int(x[4]) for x in live)+1)
  live.append(p)
 return [':'.join(p) for p in live]
def reconcile(engine,target):
 previous=engine.read_current()
 target=copy.deepcopy(target)
 if target.get('installed') and APPLETS in target['settings']:
  target.setdefault('panel_managed_applets',target['settings'][APPLETS])
 if not previous.get('installed'):return target
 for key,wanted in list(target['settings'].items()):
  if key not in previous['settings']:continue
  expected=previous['settings'].get(key);actual=engine.settings.get(key)
  if key not in ZONES|{APPLETS,NEXT}:continue
  if key!=APPLETS and equivalent(key,actual,expected):continue
  if not preference(key,actual):continue # The normal conflict check rejects malformed values.
  # Retain the intended panel separately from its merged live preferences.
  # Otherwise the next update would take ownership of a user's added applet.
  managed=previous.get('panel_managed_applets',expected) if key==APPLETS else expected
  old=decode(key,managed);live=decode(key,actual);desired=decode(key,wanted)
  if key==NEXT:merged=max(live,desired or 0)
  elif key==APPLETS:
   if old is None or desired is None:continue
   merged=applets_merge(old,live,desired)
  else:
   # Revert only individual zone values still matching what we installed.
   if old is None:merged=live
   else:
    oldrows={str(r['panelId']):r for r in old};newrows={str(r['panelId']):r for r in (desired or [])};merged=copy.deepcopy(live)
    for row in merged:
     ident=str(row['panelId'])
     for zone in ('left','center','right'):
      if row.get(zone)==oldrows.get(ident,{}).get(zone) and zone in newrows.get(ident,{}):row[zone]=newrows[ident][zone]
   merged=json.dumps(merged,separators=(',',':'))
  target['settings'][key]=engine.settings.literal(merged)
 if NEXT in target['settings'] and APPLETS in target['settings']:
  entries=decode(APPLETS,target['settings'][APPLETS]) or []
  needed=max([int(x.split(':')[4])+1 for x in entries]+[0])
  if needed>(decode(NEXT,target['settings'][NEXT]) or 0):target['settings'][NEXT]=engine.settings.literal(needed)
 return target
