"""Validated, bounded folder view settings; each write merges other open windows."""
import json,os,tempfile,time
from comfort import state_path
DEFAULT={'mode':'icons','zoom':48,'sort':'name','descending':False,'columns':[300,105,170,165]}
def read_all():
    try:
        value=json.loads(state_path().with_name('views.json').read_text());return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}
def normalize(value):
    result=dict(DEFAULT);result['columns']=list(DEFAULT['columns'])
    if not isinstance(value,dict):return result
    if value.get('mode') in ('icons','details'):result['mode']=value['mode']
    if value.get('sort') in ('name','size','mime','modified'):result['sort']=value['sort']
    result['descending']=value.get('descending') is True
    if type(value.get('zoom'))==int:result['zoom']=max(32,min(128,value['zoom']))
    widths=value.get('columns')
    if isinstance(widths,list) and len(widths)==4 and all(type(n)==int and 60<=n<=900 for n in widths):result['columns']=widths
    return result
def get(uri):return normalize(read_all().get(uri))
def save(uri,value):
    if not uri or uri=='computer:///':return
    values=read_all();values[uri]=dict(normalize(value),updated=time.time())
    values=dict(sorted(((k,v) for k,v in values.items() if isinstance(v,dict)),key=lambda item:item[1].get('updated',0) if isinstance(item[1].get('updated',0),(int,float)) else 0,reverse=True)[:500])
    p=state_path().with_name('views.json');p.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='.views-',dir=p.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(values,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
        os.replace(name,p)
    finally:
        if os.path.exists(name):os.unlink(name)
def sorted_rows(rows,key,descending):
    result=sorted(rows,key=lambda r:r[key].casefold() if isinstance(r[key],str) else r[key],reverse=descending)
    return sorted(result,key=lambda r:not r['dir'])
