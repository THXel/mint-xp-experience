"""Private, bounded XP installation-media import. Never executes Windows code."""
import ctypes as C,ctypes.util,hashlib,io,json,os,re,stat,subprocess,sys,tempfile,uuid,wave
from pathlib import Path,PurePosixPath
from .sound_sources import safe_name
from .pe_icons import icons,ico,bitmap,bitmap_rgba
MAX_FILE=40*1024*1024
SOUNDS={'xpballn':'Balloon','xpbatcrt':'Battery Critical','xpbatlow':'Battery Low','xpblkpop':'Pop-up Blocked','xpcrtstp':'Critical Stop','xpdef':'Default','xpding':'Ding','xperror':'Error','xpexcl':'Exclamation','xphdfail':'Hardware Fail','xphdinst':'Hardware Insert','xphdrem':'Hardware Remove','xpinfbar':'Information Bar','xplogoff':'Logoff Sound','xplogon':'Logon Sound','xpmenu':'Menu Command','xpmin':'Minimize','xpnotify':'Notify','xpprint':'Print complete','xprecycl':'Recycle','xprestor':'Restore','xpringin':'Ringin','xprngout':'Ringout','xpshutdn':'Shutdown','xpstart':'Start','xpstartu':'Startup'}
# Resource IDs, not Explorer's zero-based shell icon indices.
ICON_MAP={1:'text-x-generic unknown application-octet-stream',2:'text-plain',3:'application-x-executable application-x-desktop',4:'folder inode-directory system-file-manager',5:'folder-open document-open',8:'drive-harddisk drive-harddisk-system',9:'drive-harddisk-usb drive-removable-media',12:'drive-optical media-optical',16:'computer user-desktop org.mintxp.Explorer',19:'network-workgroup network network-wired',18:'network-server',32:'user-trash',33:'user-trash-full',20:'preferences-system preferences-desktop cinnamon-settings',23:'edit-find system-search',17:'printer',44:'folder-favorites'}

# Verified against XP Shell32 resource sheets; aliases cover our UI and Mint settings.
ICON_MAP.update({4: 'folder inode-directory system-file-manager folder-download folder-publicshare folder-templates folder-saved-search', 5: 'folder-open document-open', 235: 'user-home go-home folder-documents', 236: 'folder-pictures', 237: 'folder-music', 238: 'folder-videos', 39: 'folder-edit', 36: 'folder-remote folder-network', 258: 'folder-new', 270: 'preferences-desktop-theme cs-themes preferences-desktop-wallpaper cs-backgrounds', 271: 'system-software-install system-software-update mintinstall mintupdate', 269: 'system-users cs-user cs-users avatar-default', 268: 'preferences-desktop-accessibility cs-universal-access', 276: 'preferences-desktop-locale cs-date-time preferences-system-time', 277: 'cs-sound audio-card preferences-desktop-sound', 274: 'preferences-system-hardware cs-general', 222: 'media-optical-dvd', 225: 'audio-x-generic', 224: 'video-x-generic', 226: 'image-x-generic', 28: 'system-shutdown', 35: 'system-log-out', 48: 'system-lock-screen', 24: 'help-browser', 45: 'dialog-password', 155: 'preferences-desktop-font cs-fonts', 242: 'edit-rename', 250: 'accessories-paint', 322: 'starred', 257: 'network-transmit-receive', 329: 'system-reboot', 331: 'media-eject'})
EXTRA_MAP={
 "main":{100:"input-mouse cs-mouse preferences-desktop-mouse",200:"input-keyboard cs-keyboard preferences-desktop-keyboard"},
 "timedate":{1:"preferences-system-time cs-calendar"},
 "mmsys":{3004:"audio-volume-high audio-volume-medium audio-volume-low"},
}

def members(source,wanted,kind):
 """Yield selected bytes, never materialize archive-controlled filenames."""
 lib=C.CDLL(ctypes.util.find_library('archive'))
 def fn(name,result,args):
  f=getattr(lib,name);f.restype=result;f.argtypes=args;return f
 ptr=C.c_void_p;new=fn('archive_read_new',ptr,[]);free=fn('archive_read_free',C.c_int,[ptr]);support=fn('archive_read_support_format_'+kind,C.c_int,[ptr]);opening=fn('archive_read_open_filename',C.c_int,[ptr,C.c_char_p,C.c_size_t]);next_=fn('archive_read_next_header',C.c_int,[ptr,C.POINTER(ptr)]);name_=fn('archive_entry_pathname',C.c_char_p,[ptr]);size_=fn('archive_entry_size',C.c_int64,[ptr]);type_=fn('archive_entry_filetype',C.c_uint,[ptr]);links=[fn('archive_entry_'+k,C.c_char_p,[ptr]) for k in ('symlink','hardlink')];read=fn('archive_read_data',C.c_ssize_t,[ptr,ptr,C.c_size_t]);skip=fn('archive_read_data_skip',C.c_int,[ptr]);error=fn('archive_error_string',C.c_char_p,[ptr])
 h=new();entry=ptr();buffer=C.create_string_buffer(65536);seen=set();total=0
 def check(code):
  if code<0:raise ValueError((error(h) or b'Unreadable installation archive').decode('utf8','replace'))
 try:
  check(support(h));check(opening(h,os.fsencode(source),65536))
  for count in range(30000):
   code=next_(h,C.byref(entry))
   if code==1:return
   check(code);name=os.fsdecode(name_(entry) or b'')
   if name in ('.','./'):skip(h);continue
   name=safe_name(name);key=name.casefold().removesuffix(';1')
   if not wanted(key):check(skip(h));continue
   if key in seen:raise ValueError('Duplicate installation resource')
   seen.add(key)
   if any(f(entry) for f in links) or type_(entry)!=stat.S_IFREG:raise ValueError('Linked or special installation resource')
   size=size_(entry)
   if not 0<size<=MAX_FILE:raise ValueError('Oversized installation resource')
   chunks=[];actual=0
   while True:
    n=read(h,buffer,len(buffer));check(n)
    if not n:break
    actual+=n;total+=n
    if actual>size or total>128*1024*1024:raise ValueError('Expanded resource limit')
    chunks.append(buffer.raw[:n])
   if actual!=size:raise ValueError('Truncated installation resource')
   yield key,b''.join(chunks)
  raise ValueError('Too many ISO entries')
 finally:free(h)

def unpack(data,temp):
 if not data.startswith(b'MSCF'):return data
 p=temp/'resource.cab';p.write_bytes(data)
 result=list(members(p,lambda name:True,'cab'))
 if len(result)!=1:raise ValueError('Expected single-file installation cabinet')
 return result[0][1]

def worker(source,dest):
 from gi.repository import Gio
 import gi
 gi.require_version('GdkPixbuf','2.0');from gi.repository import GdkPixbuf
 source=Path(source);dest=Path(dest);before=source.stat()
 if not stat.S_ISREG(before.st_mode) or not 32768<before.st_size<=5*1024**3:raise ValueError('Choose an XP installation ISO (up to 5 GiB)')
 def wanted(name):
  p=PurePosixPath(name)
  return len(p.parts)==2 and p.parts[0] in ('i386','amd64') and (p.stem in SOUNDS and p.suffix in ('.wa_','.wav') or p.name in ('shell32.dl_','shell32.dll','txtsetup.sif','explorer.ex_','explorer.exe','main.cp_','main.cpl','timedate.cp_','timedate.cpl','mmsys.cp_','mmsys.cpl','rover.ac_','rover.acs'))
 data=dict(members(source,wanted,'iso9660'))
 architecture=next((a for a in ('amd64','i386') if a+'/txtsetup.sif' in data and any(n.startswith(a+'/xp') for n in data)),None)
 if not architecture:raise ValueError('No supported Windows XP installation layout (I386/AMD64) found')
 sounds=dest/'sounds';theme=dest/'icons';sounds.mkdir();theme.mkdir();written={};origins=[];companion={}
 def save(p,blob):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob);written[str(p.relative_to(dest))]=hashlib.sha256(blob).hexdigest()
 with tempfile.TemporaryDirectory(dir=dest) as tmp:
  tmp=Path(tmp)
  for name,blob in data.items():
   p=PurePosixPath(name)
   if p.parts[0]!=architecture or p.stem not in SOUNDS:continue
   raw=unpack(blob,tmp)
   with wave.open(io.BytesIO(raw)) as audio:
    if audio.getcomptype()!='NONE' or audio.getnchannels() not in (1,2) or not 8000<=audio.getframerate()<=192000 or audio.getsampwidth() not in (1,2,3,4) or not 0<audio.getnframes()<=192000*30:raise ValueError('Unsupported installation WAV')
    if len(audio.readframes(audio.getnframes()))!=audio.getnframes()*audio.getnchannels()*audio.getsampwidth():raise ValueError('Truncated installation WAV')
   save(sounds/('Windows XP '+SOUNDS[p.stem]+'.wav'),raw);origins.append(name)
  rover=next((n for n in (architecture+'/rover.ac_',architecture+'/rover.acs') if n in data),None)
  if rover:
   try:
    from .agent_character import export
    manifest,hashes=export(unpack(data[rover],tmp),dest/'companion')
    written.update({'companion/'+k:v for k,v in hashes.items()});origins.append(rover)
    companion={'available':True,'animations':len(manifest['animations']),'source':rover}
   except (ValueError,UnicodeError,IndexError,OverflowError) as error:
    import shutil
    shutil.rmtree(dest/'companion',ignore_errors=True)
    companion={'available':False,'reason':str(error)}
  shell=next((n for n in (architecture+'/shell32.dl_',architecture+'/shell32.dll') if n in data),None)
  if not shell:raise ValueError('SHELL32 icons missing from ISO')
  icon_names=[];icon_origins={}
  def render(names,pix,source_id):
   for size in (16,24,32,48):
    factor=size/max(pix.get_width(),pix.get_height())
    scaled=pix.scale_simple(max(1,round(pix.get_width()*factor)),max(1,round(pix.get_height()*factor)),GdkPixbuf.InterpType.BILINEAR)
    ok,png=scaled.save_to_bufferv('png',[],[])
    for name in names.split():save(theme/str(size)/(name+'.png'),bytes(png))
   for name in names.split():
    if name not in icon_names:icon_names.append(name)
    icon_origins[name]=source_id
  def read_pix(blob,size):
   stream=Gio.MemoryInputStream.new_from_bytes(__import__('gi').repository.GLib.Bytes.new(blob))
   return GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,size,size,True,None)
  def read_bitmap(blob):
   rgba=bitmap_rgba(blob)
   if rgba:
    w,h,pixels=rgba
    return GdkPixbuf.Pixbuf.new_from_bytes(__import__('gi').repository.GLib.Bytes.new(pixels),GdkPixbuf.Colorspace.RGB,True,8,w,h,w*4)
   stream=Gio.MemoryInputStream.new_from_bytes(__import__('gi').repository.GLib.Bytes.new(blob))
   return GdkPixbuf.Pixbuf.new_from_stream(stream,None).add_alpha(True,255,0,255)
  def render_groups(source_name,mapping):
   groups=icons(unpack(data[source_name],tmp))
   for ident,names in mapping.items():
    if ident not in groups:continue
    # Decode each native resolution separately to retain crisp small icons.
    for size in (16,24,32,48):
     pix=read_pix(ico(groups[ident],size),size);ok,png=pix.save_to_bufferv('png',[],[])
     for name in names.split():save(theme/str(size)/(name+'.png'),bytes(png))
    for name in names.split():
     if name not in icon_names:icon_names.append(name)
     icon_origins[name]={'entry':source_name,'resource':ident,'type':'icon'}
   origins.append(source_name)
  render_groups(shell,ICON_MAP)
  # Shell32's original Explorer toolbar strips, with native 16/24 px frames.
  toolbar={0:'back',1:'forward',5:'cut',6:'copy',7:'paste',8:'undo',9:'redo',17:'search',22:'view',28:'up',31:'new-folder',43:'folders'}
  shell_raw=unpack(data[shell],tmp)
  for resource,tile in ((216,16),(214,24)):
   strip=bitmap(shell_raw,resource)
   if not strip:continue
   pix=read_bitmap(strip)
   if pix.get_height()!=tile or pix.get_width()<47*tile:raise ValueError('Unexpected Explorer toolbar dimensions')
   for index,label in toolbar.items():
    name='mintxp-toolbar-'+label
    for size in ((16,) if tile==16 else (24,32,48)):
     frame=pix.new_subpixbuf(index*tile,0,tile,tile).scale_simple(size,size,GdkPixbuf.InterpType.BILINEAR)
     ok,png=frame.save_to_bufferv('png',[],[]);save(theme/str(size)/(name+'.png'),bytes(png))
    if name not in icon_names:icon_names.append(name)
    icon_origins[name]={'entry':shell,'resource':resource,'frame':index,'type':'bitmap-strip'}

  for stem,mapping in EXTRA_MAP.items():
   source_name=next((n for n in (architecture+'/'+stem+'.cp_',architecture+'/'+stem+'.cpl') if n in data),None)
   if source_name:render_groups(source_name,mapping)
  explorer=next((n for n in (architecture+'/explorer.ex_',architecture+'/explorer.exe') if n in data),None)
  if explorer:
   flag=bitmap(unpack(data[explorer],tmp),143)
   if flag:
    pix=read_bitmap(flag)
    render('mintxp-start start-here',pix,{'entry':explorer,'resource':143,'type':'bitmap'})
    origins.append(explorer)

 if len(list(sounds.glob('*.wav')))<10 or len(icon_names)<10:raise ValueError('Incomplete XP media resources')
 index='[Icon Theme]\nName=Private XP ISO Icons\nInherits=Mint-XP-Experience-Icons,Mint-Y,Adwaita,hicolor\nDirectories=16,24,32,48\n'
 for size in (16,24,32,48):index+=f'\n[{size}]\nSize={size}\nType=Fixed\nContext=Places\n'
 save(theme/'index.theme',index.encode())
 if source.stat().st_size!=before.st_size or source.stat().st_mtime_ns!=before.st_mtime_ns:raise ValueError('ISO changed during import')
 result={'format':1,'architecture':architecture,'sounds':len(list(sounds.glob('*.wav'))),'icons':len(icon_names),'icon_origins':icon_origins,'origin_entries':origins,'files':written,'companion':companion,'private_import':True,'license_notice':'Source rights remain with their owners. Not licensed for redistribution by this importer.'}
 (dest/'report.json').write_text(json.dumps(result,indent=2));return result

def import_iso(engine,path):
 source=Path(path).expanduser().resolve(strict=True)
 parent=engine.state/'imports'
 if parent.is_symlink():raise ValueError('Linked import directory rejected')
 parent.mkdir(mode=0o700,exist_ok=True)
 engine.report('iso',0,None,source.name)
 with tempfile.TemporaryDirectory(prefix='.iso-',dir=parent) as td:
  root=Path(__file__).resolve().parent.parent
  script='import sys,resource;sys.path.insert(0,sys.argv[1]);resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824));resource.setrlimit(resource.RLIMIT_CPU,(60,60));resource.setrlimit(resource.RLIMIT_FSIZE,(41943040,41943040));from mintxp.iso_import import worker;worker(sys.argv[2],sys.argv[3])'
  run=subprocess.run(['/usr/bin/python3','-I','-B','-c',script,str(root),str(source),td],capture_output=True,text=True,timeout=120)
  if run.returncode:raise ValueError('ISO import: '+(run.stderr[-1400:] or 'worker stopped'))
  result=json.loads((Path(td)/'report.json').read_text())
  for name,digest in result['files'].items():
   safe_name(name);p=Path(td)/name
   if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('Import verification failed')
  target=parent/('xp-iso-'+uuid.uuid4().hex);Path(td).rename(target)
 result.update(sound_path=str(target/'sounds'),icon_path=str(target/'icons'),source_name=source.name)
 return result
