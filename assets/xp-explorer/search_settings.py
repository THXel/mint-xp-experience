"""Small private MRU search history; never remember credentials in URI authorities."""
import json,os,tempfile
from urllib.parse import urlsplit
from comfort import state_path

def path():return state_path().with_name('search.json')
def valid(value):
    if not isinstance(value,str) or not value.strip() or len(value)>1024 or any(c in value for c in '\n\r\x00'):return False
    try:return '://' not in value or (urlsplit(value).username is None and urlsplit(value).password is None)
    except ValueError:return False

def load():
    try:
        p=path();raw=json.loads(p.read_text()) if p.stat().st_size<=65536 else {}
    except (OSError,ValueError):raw={}
    if not isinstance(raw,dict):raw={}
    return {key:[x for x in raw.get(key,[]) if valid(x)][:12] if isinstance(raw.get(key),list) else [] for key in ('terms','locations')}
def save(data):
    p=path();p.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='.search-',dir=p.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
        os.replace(name,p)
    finally:
        if os.path.exists(name):os.unlink(name)
def remember(term,location):
    data=load()
    for key,value in [('terms',term),('locations',location)]:
        if valid(value):data[key]=[value]+[x for x in data[key] if x!=value][:11]
    save(data)
def clear():save({'terms':[],'locations':[]})
