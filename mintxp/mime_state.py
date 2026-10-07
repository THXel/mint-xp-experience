"""Manage only the folder default; other application associations belong to the user."""
import configparser,copy,re
REL='.config/mimeapps.list'
SECTION='Default Applications'
KEY='inode/directory'
EXPLORER='org.mintxp.Explorer.desktop'

def parse(data):
 text=data.decode('utf-8') if data else ''
 cp=configparser.ConfigParser(interpolation=None,strict=False,delimiters=('=',),empty_lines_in_values=False)
 cp.optionxform=str
 # Some applications append duplicate keys. Preserve those unrelated lines,
 # but refuse ambiguity in the one entry we own.
 section=None;seen_section=False;seen_key=False
 for line in text.splitlines():
  if line.strip().startswith('['):
   section=line.strip()
   if section=='['+SECTION+']':
    if seen_section:raise ValueError('Duplicate folder-default section')
    seen_section=True
  if section=='['+SECTION+']' and re.match(r'^\s*inode/directory\s*=',line):
   if seen_key:raise ValueError('Duplicate folder default')
   seen_key=True
 cp.read_string(text)
 if cp.defaults():raise ValueError('Unexpected MIME defaults')
 for section in cp:
  for value in cp[section].values():
   if '\n' in value:raise ValueError('Multiline MIME association')
 return cp

def directory(data):return parse(data).get(SECTION,KEY,fallback=None)

def replace(data,value,keep_section=False):
 text=(data or b'').decode('utf-8');parse(data)
 lines=text.splitlines(keepends=True);out=[];inside=False;found=False;section_at=None
 for line in lines:
  if line.strip().startswith('['):
   if inside and not found and value is not None:
    if out and not out[-1].endswith('\n'):out[-1]+='\n'
    out.append(KEY+'='+value+'\n');found=True
   inside=line.strip()=='['+SECTION+']'
   if inside:section_at=len(out)
  if inside and re.match(r'^\s*inode/directory\s*=',line):
   found=True
   if value is not None:
    prefix=re.match(r'^[^=]*=[ \t]*',line)[0];end='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
    out.append(prefix+value+end)
  else:out.append(line)
 if value is not None and not found:
  if out and not out[-1].endswith('\n'):out[-1]+='\n'
  if section_at is None:out.append('['+SECTION+']\n')
  out.append(KEY+'='+value+'\n')
 if value is None and section_at is not None and not keep_section:
  end=next((i for i in range(section_at+1,len(out)) if out[i].strip().startswith('[')),len(out))
  if not any(x.strip() for x in out[section_at+1:end]):del out[section_at:end]
 return ''.join(out).encode()

def allowed(engine,rel,desc):
 if rel!=REL:return False
 data=engine.data(desc) if desc else b''
 parse(data);return True

def reconcile(engine,target):
 old=engine.read_current()
 if REL not in target['files'] or not old.get('installed') or REL not in old['files']:return target
 before=engine.file(REL);actual=engine.data(before) if before else b''
 expected=engine.data(old['files'][REL]) if old['files'][REL] else b''
 wanted_desc=target['files'][REL];wanted=engine.data(wanted_desc) if wanted_desc else b''
 live_value=directory(actual);expected_value=directory(expected);desired_value=directory(wanted)
 personal=old.get('mime_user_choice',False) or live_value!=expected_value
 value=live_value if personal else desired_value
 if personal and target.get('installed') and desired_value!=expected_value and desired_value==EXPLORER+';':
  value=desired_value;personal=False
 # If the user reordered alternatives, remove only our disappearing launcher.
 if not target.get('installed') and value and EXPLORER in value.split(';'):
  values=[v for v in value.split(';') if v and v!=EXPLORER]
  if not values:values=[v for v in (desired_value or '').split(';') if v and v!=EXPLORER]
  value=';'.join(values)+';' if values else None
 result=replace(actual,value,parse(wanted).has_section(SECTION))
 target=copy.deepcopy(target);target['mime_user_choice']=personal;target['_mime_before']=before
 target['files'][REL]=engine.descriptor(result,(before or wanted_desc or {'mode':0o600})['mode']) if result or wanted_desc is not None else None
 return target
