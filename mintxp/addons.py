"""Separate, reversible optional upstream applications. GPL-3.0-or-later."""
import hashlib,json,os,platform,posixpath,shutil,subprocess,tarfile,tempfile,urllib.parse,urllib.request,zipfile
from pathlib import Path,PurePosixPath
from .engine import Engine,Conflict
from .components import ROOT,desktop
from .flatpak_addons import FlatpakAddons

ASSETS=ROOT/'assets/addons'
DOWNLOADS=json.loads((ASSETS/'downloads.json').read_text())
CATALOG={
 'minesweeper':{'name':'Minesweeper XP','license':'MIT (upstream)','url':'https://github.com/AkshayKalose/Minesweeper-XP','legacy':'xp-community-minesweeper.desktop','icon':'gnome-mines'},
 'solitaire':{'name':'Solitär / Solitaire','license':'MIT; Temurin: GPL-2.0 with Classpath Exception','url':'https://github.com/danielricci/solitaire','legacy':'xp-community-solitaire.desktop','icon':'gnome-aisleriot'},
 'jspaint':{'name':'Paint - JS Paint','license':'MIT (code); third-party resource notices apply','url':'https://jspaint.app/about','legacy':'jspaint.desktop','icon':'applications-graphics'},
 'space-cadet':{'name':'3D Pinball (Flatpak)','license':'MIT (engine); separate original game data','url':'https://github.com/k4zmu2a/SpaceCadetPinball','icon':'applications-games'},
}
HOSTS={'github.com','api.github.com','codeload.github.com','raw.githubusercontent.com','release-assets.githubusercontent.com','objects.githubusercontent.com','nodejs.org'}

def safe_url(url):
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):raise Conflict('Unexpected download location: '+url)
 return url
class Redirects(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  return super().redirect_request(req,fp,code,msg,headers,safe_url(newurl))

def download(spec,target,report=lambda *a:None,cache=None):
 """Bounded HTTPS, checked redirects and exact SHA-256 before any extraction/run."""
 safe_url(spec['url']);target=Path(target);h=hashlib.sha256();count=0
 cached=Path(cache)/target.name if cache else None
 source=cached.open('rb') if cached and cached.is_file() else urllib.request.build_opener(Redirects()).open(urllib.request.Request(spec['url'],headers={'User-Agent':'Mint-XP-Experience/preview11'}),timeout=45)
 try:
  with source, target.open('wb') as out:
   report('download',0,spec['size'],target.name)
   while True:
    data=source.read(256*1024)
    if not data:break
    count+=len(data)
    if count>spec['size']:raise Conflict('Download exceeds reviewed size: '+target.name)
    out.write(data);h.update(data);report('download',count,spec['size'],target.name)
  if count!=spec['size'] or h.hexdigest()!=spec['sha256']:raise Conflict('Download checksum mismatch: '+target.name)
 except BaseException:
  target.unlink(missing_ok=True);raise
 return target

def unpack(archive,dest):
 """Validate the complete tar before writing; materialize internal file links only."""
 dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
 with tarfile.open(archive) as tar:
  members=tar.getmembers();names={};total=0;roots=set()
  if len(members)>15000:raise Conflict('Too many archive entries')
  for m in members:
   p=PurePosixPath(m.name)
   if not m.name or p.is_absolute() or '..' in p.parts or '\\' in m.name or '\0' in m.name or (not m.isdir() and str(p)!=m.name):raise Conflict('Unsafe archive path')
   if not (m.isfile() or m.isdir() or m.issym() or m.islnk()):raise Conflict('Special archive entry rejected')
   if str(p) in names:raise Conflict('Duplicate archive entry')
   names[str(p)]=m;roots.add(p.parts[0]);total+=m.size
   if total>400*1024*1024:raise Conflict('Archive exceeds size limit')
  if len(roots)!=1:raise Conflict('Archive must contain one root directory')
  root=next(iter(roots))
  def resolve(m,seen=()):
   if m.name in seen:raise Conflict('Archive link cycle')
   if m.issym() or m.islnk():
    if m.linkname.startswith('/') or '\\' in m.linkname:raise Conflict('Unsafe archive link')
    name=posixpath.normpath(posixpath.join(posixpath.dirname(m.name),m.linkname) if m.issym() else m.linkname)
    if not name.startswith(root+'/') or name not in names:raise Conflict('Escaping or broken archive link')
    return resolve(names[name],seen+(m.name,))
   return m
  resolved=[(m,resolve(m)) for m in members]
  if sum(src.size for m,src in resolved if src.isfile())>400*1024*1024:raise Conflict('Expanded links exceed size limit')
  for m,src in resolved:
   path=dest/m.name
   if src.isdir():
    # Directory aliases are not used by the application entry points. No live symlinks.
    if m.isdir():path.mkdir(parents=True,exist_ok=True)
   else:
    path.parent.mkdir(parents=True,exist_ok=True)
    with tar.extractfile(src) as inp,path.open('wb') as out:shutil.copyfileobj(inp,out)
    path.chmod(0o755 if src.mode&0o111 else 0o644)
 return dest/root

class Addons:
 def __init__(self,engine,cache=None):self.engine=engine;self.cache=cache;self.flatpak=FlatpakAddons(engine)
 def subengine(self,key):
  if key not in CATALOG or key=='space-cadet':raise Conflict('Unknown local add-on')
  e=Engine(self.engine.home,self.engine.state/'addons'/key,self.engine.settings);e.progress=self.engine.report;return e
 def status(self):
  result={}
  for key,item in CATALOG.items():
   if key=='space-cadet':
    try:entry=self.flatpak.status()[key]
    except (OSError,Conflict) as error:entry=dict(state='unavailable',detail=str(error))
    result[key]=dict(item,**entry);continue
   e=self.subengine(key);current=e.read_current();legacy=None
   for directory in (self.engine.home/'.local/share/applications',Path('/usr/share/applications'),Path('/usr/local/share/applications')):
    p=directory/item['legacy']
    if p.is_file():legacy=str(p);break
   own=self.engine.home/'.local/share/applications'/('mintxp-addon-'+key+'.desktop')
   if e.read('pending.json'):state='interrupted'
   elif current.get('installed'):state='managed'
   elif legacy or own.exists():state='external'
   else:state='absent'
   result[key]=dict(item,state=state,desktop=legacy or (str(own) if own.exists() else None))
  return result
 def preflight(self,key):
  if key in ('minesweeper','solitaire') and platform.machine() not in ('x86_64','amd64'):raise Conflict('This optional runtime is reviewed for Linux x86_64 only.')
  if key in ('minesweeper','jspaint'):
   try:
    import gi
    gi.require_version('WebKit2','4.1')
    from gi.repository import WebKit2
   except (ImportError,ValueError):raise Conflict('Install gir1.2-webkit2-4.1 using the Mint software manager, then retry.')
  if shutil.disk_usage(self.engine.state).free<1200*1024*1024:raise Conflict('At least 1.2 GiB of temporary free space is required.')
 def install(self,key):
  if key not in CATALOG:raise Conflict('Unknown add-on')
  if key=='space-cadet':return self.flatpak.install(key)
  with self.engine.lock():
   state=self.status()[key]['state']
   if state in ('managed','external'):return CATALOG[key]['name']+' — already installed; unchanged'
   if state=='interrupted':raise Conflict('Recover the interrupted installation first.')
   self.preflight(key)
   e=self.subengine(key);prefix='.local/share/mintxp-addons/'+key
   # Never appropriate an untracked directory left by another installer/person.
   target=e.path(prefix+'/launch.py').parent
   if target.exists() and any(target.iterdir()):raise Conflict('Untracked application directory protected: '+str(target))
   with tempfile.TemporaryDirectory(prefix='addon-',dir=self.engine.state) as td:
    temp=Path(td);payload=temp/'payload';payload.mkdir()
    def fetch(name):return download(DOWNLOADS[name],temp/name,self.engine.report,self.cache)
    if key=='minesweeper':
     source=unpack(fetch('mines-source.tar.gz'),temp/'source')
     node=unpack(fetch('node.tar.xz'),temp/'node');front=source/'frontend'
     for rel,changes in json.loads((ASSETS/'mines-patches.json').read_text()).items():
      p=source/rel;text=p.read_text()
      for old,new in changes:
       if not old or text.count(old)!=1:raise Conflict('Upstream source differs from reviewed compatibility patch')
       text=text.replace(old,new,1)
      p.write_text(text)
     lock=json.loads((front/'package-lock.json').read_text())
     for item in lock.get('packages',{}).values():
      if item.get('resolved') and (not item['resolved'].startswith('https://registry.npmjs.org/') or not item.get('integrity')):raise Conflict('Unreviewed npm download in upstream lockfile')
     env={k:v for k,v in os.environ.items() if not k.upper().startswith(('NPM_','NODE_'))}
     env.update(PATH=str(node/'bin')+':/usr/bin:/bin',HOME=str(temp/'build-home'),npm_config_cache=str(temp/'npm-cache'))
     self.engine.report('build',0,None,'Minesweeper XP / npm ci')
     cmd=[str(node/'bin/node'),str(node/'lib/node_modules/npm/bin/npm-cli.js'),'ci','--ignore-scripts','--no-audit','--no-fund','--registry=https://registry.npmjs.org','--userconfig=/dev/null','--globalconfig='+str(temp/'global.npmrc')]
     proc=subprocess.run(cmd,cwd=front,env=env,capture_output=True,text=True,timeout=600)
     if proc.returncode:raise Conflict('Minesweeper dependency build failed:\n'+proc.stderr[-2000:])
     proc=subprocess.run([str(node/'bin/node'),str(front/'node_modules/vite/bin/vite.js'),'build','--base','./'],cwd=front,env=env,capture_output=True,text=True,timeout=180)
     if proc.returncode:raise Conflict('Minesweeper frontend build failed:\n'+proc.stderr[-2000:])
     shutil.copytree(front/'dist',payload/'web');shutil.copy2(source/'LICENSE',payload/'LICENSE');shutil.copy2(source/'build/appicon.png',payload/'icon.png')
     # Keep dependency notices alongside the downloaded, locally built application.
     notices=payload/'notices';notices.mkdir()
     for i,p in enumerate(sorted((front/'node_modules').rglob('*'))):
      if p.is_file() and p.name.lower().startswith(('license','licence','copying')):shutil.copyfile(p,notices/(str(i)+'-'+p.name))
     shutil.copy2(front/'package-lock.json',payload/'package-lock.json')
    elif key=='jspaint':
     source=unpack(fetch('jspaint.tar.gz'),temp/'source')
     # Static web app is already present upstream. No obsolete Electron is installed.
     keep=('index.html','src','lib','styles','images','localization','help','audio','favicon.ico','manifest.webmanifest','LICENSE.txt')
     web=payload/'web';web.mkdir()
     for name in keep:
      p=source/name
      if p.is_dir():shutil.copytree(p,web/name)
      elif p.is_file():shutil.copy2(p,web/name)
     index=web/'index.html'
     # An offline editor should not fetch news images, cloud scripts or trackers.
     policy="<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self' data: blob:; script-src 'self' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' data: blob:; font-src 'self'; frame-src 'self'\">"
     index.write_text(index.read_text().replace('<head>','<head>\n'+policy,1))
    else:
     shutil.copyfile(fetch('solitaire.jar'),payload/'Solitaire.jar')
     with zipfile.ZipFile(payload/'Solitaire.jar') as jar:(payload/'icon.png').write_bytes(jar.read('content/solitaire_logo.png'))
     shutil.copyfile(fetch('solitaire-license'),payload/'LICENSE')
     java=unpack(fetch('java.tar.gz'),temp/'java');shutil.copytree(java,payload/'java')
    if key=='jspaint':shutil.copy2(ROOT/'assets/icons/scalable/apps/mintxp-paint.svg',payload/'icon.svg')
    shutil.copy2(ASSETS/'launch.py',payload/'launch.py')
    if key!='solitaire':shutil.copy2(ASSETS/'webapp.py',payload/'webapp.py')
    (payload/'application.json').write_text(json.dumps({'id':key,'name':CATALOG[key]['name']}))
    (payload/'sources.json').write_text(json.dumps({n:DOWNLOADS[n] for n in ({'minesweeper':['mines-source.tar.gz','node.tar.xz'],'jspaint':['jspaint.tar.gz'],'solitaire':['solitaire.jar','solitaire-license','java.tar.gz']}[key])},indent=2))
    files={}
    for p in sorted(payload.rglob('*')):
     if p.is_file():files[prefix+'/'+str(p.relative_to(payload))]=e.descriptor(p.read_bytes(),0o755 if p.stat().st_mode&0o111 else 0o644)
    icon=str(e.home/prefix/'icon.svg') if (payload/'icon.svg').exists() else str(e.home/prefix/'icon.png') if (payload/'icon.png').exists() else str(e.home/prefix/'web/images/icons/128x128.png') if (payload/'web/images/icons/128x128.png').exists() else CATALOG[key]['icon']
    files['.local/share/applications/mintxp-addon-'+key+'.desktop']=e.descriptor(desktop(CATALOG[key]['name'],str(e.home/prefix/'launch.py'),icon,category='Utility;Graphics;2DGraphics;RasterGraphics;' if key=='jspaint' else 'Game;X-XPCommunity;'))
    # Backup only the exact add-on destinations; the existing theme baseline is untouched.
    result=e.apply({'files':files,'settings':{},'options':{'addon':key}},reference=False)
   return CATALOG[key]['name']+' — '+str(result)
 def remove(self,key):
  if key=='space-cadet':return self.flatpak.remove(key)
  with self.engine.lock():
   e=self.subengine(key)
   if not e.read_current().get('installed'):raise Conflict('External applications are protected.')
   e.uninstall()
  return CATALOG[key]['name']+' — removed; application data retained'
 def recover(self,key):
  if key=='space-cadet':return self.flatpak.reconcile(key)
  with self.engine.lock():return self.subengine(key).recover()
 def verify(self,key):
  if key=='space-cadet':return self.flatpak.status()[key]
  e=self.subengine(key)
  if e.read('pending.json'):raise Conflict('Interrupted add-on operation')
  errors=e.check(e.read_current())
  if errors:raise Conflict('\n'.join(errors))
  return 'OK'
 def launch(self,key):
  if key=='space-cadet':return self.flatpak.launch(key)
  entry=self.status()[key]
  if entry['state']=='managed':subprocess.Popen(['/usr/bin/python3','-B',str(self.engine.home/'.local/share/mintxp-addons'/key/'launch.py')],start_new_session=True)
  elif entry['state']=='external':
   from gi.repository import Gio
   app=Gio.DesktopAppInfo.new_from_filename(entry['desktop'])
   if not app or not app.launch([],None):raise Conflict('Could not launch installed app')
  else:raise Conflict('Application is not installed')
