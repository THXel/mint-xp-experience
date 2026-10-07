"""Bounded local sound sources; archives are decoded in an isolated worker.

No archive paths are extracted to the filesystem. The worker writes numbered
blobs only; its manifest supplies validated relative names for the importer.
"""
import ctypes as C,ctypes.util,json,os,re,stat,subprocess,sys,tempfile
from pathlib import Path,PurePosixPath
ARCHIVES=('.zip','.rar','.7z','.tar','.tar.gz','.tgz','.tar.bz2','.tbz2','.tar.xz','.txz')
MAX_FILE=16*1024*1024
MAX_TOTAL=128*1024*1024
MAX_ENTRIES=4096
MAX_WAVS=512

def safe_name(name):
 # Treat Windows separators as separators too; reject ambiguous/path-like names.
 name=name.replace('\\','/')
 if len(name)>1024 or any(ord(c)<32 for c in name) or name.startswith('/') or re.match(r'^[a-zA-Z]:',name):raise ValueError('Unsafe archive path')
 parts=PurePosixPath(name).parts
 if not parts or '..' in parts:raise ValueError('Unsafe archive path')
 return '/'.join(parts)

def folder_data(source):
 payload={};resolved={};disabled=set();entries=total=0
 for directory,dirs,files in os.walk(source,followlinks=False):
  for name in dirs+files:
   entries+=1
   if entries>MAX_ENTRIES:raise ValueError('Sound folder has too many entries')
   p=Path(directory)/name
   if p.is_symlink() and (not p.resolve().is_relative_to(source) or not p.resolve().is_file()):raise ValueError('External, broken or directory sound symlink: '+str(p))
   if p.is_dir():continue
   if not p.is_file():raise ValueError('Special soundpack file rejected')
   rel=str(p.relative_to(source));safe_name(rel)
   if '\\' in rel:raise ValueError('Unsupported sound filename')
   if p.suffix.lower()=='.disabled' and p.parent.name=='stereo':
    if p.stat().st_size:raise ValueError('Invalid disabled event marker')
    disabled.add(p.stem);continue
   if p.suffix.lower()!='.wav':continue
   size=p.stat().st_size;total+=size
   if size>MAX_FILE or total>MAX_TOTAL or len(payload)>=MAX_WAVS:raise ValueError('Sound import exceeds size limit')
   with p.open('rb') as f:data=f.read(MAX_FILE+1)
   if len(data)!=size:raise ValueError('Sound file changed while importing')
   payload[rel]=data;resolved.setdefault(p.resolve(),rel)
 return payload,resolved,disabled

def _archive_worker(source,destination,media=False):
 limit_entries=16000 if media else MAX_ENTRIES
 limit_files=12000 if media else MAX_WAVS
 library=ctypes.util.find_library('archive')
 if not library:raise ValueError('Archive support requires the Linux Mint libarchive library')
 lib=C.CDLL(library)
 def fn(name,restype,args):
  f=getattr(lib,name);f.restype=restype;f.argtypes=args;return f
 new=fn('archive_read_new',C.c_void_p,[])
 support_filter=fn('archive_read_support_filter_all',C.c_int,[C.c_void_p])
 support_format=fn('archive_read_support_format_all',C.c_int,[C.c_void_p])
 opening=fn('archive_read_open_filename',C.c_int,[C.c_void_p,C.c_char_p,C.c_size_t])
 next_header=fn('archive_read_next_header',C.c_int,[C.c_void_p,C.POINTER(C.c_void_p)])
 pathname=fn('archive_entry_pathname',C.c_char_p,[C.c_void_p])
 size_of=fn('archive_entry_size',C.c_int64,[C.c_void_p])
 type_of=fn('archive_entry_filetype',C.c_uint,[C.c_void_p])
 links=[fn('archive_entry_'+kind,C.c_char_p,[C.c_void_p]) for kind in ('symlink','hardlink')]
 encrypted=fn('archive_entry_is_encrypted',C.c_int,[C.c_void_p])
 data_read=fn('archive_read_data',C.c_ssize_t,[C.c_void_p,C.c_void_p,C.c_size_t])
 skip=fn('archive_read_data_skip',C.c_int,[C.c_void_p])
 error=fn('archive_error_string',C.c_char_p,[C.c_void_p])
 free=fn('archive_read_free',C.c_int,[C.c_void_p])
 handle=new();entry=C.c_void_p();buf=C.create_string_buffer(65536)
 names=set();records=[];disabled=[];count=declared=actual=0
 before=source.stat()
 if not stat.S_ISREG(before.st_mode) or before.st_size>MAX_TOTAL:raise ValueError('Archive is not a regular file or exceeds 128 MiB')
 def check(code):
  if code<0:raise ValueError((error(handle) or b'Archive could not be read').decode('utf-8','replace'))
 try:
  check(support_filter(handle));check(support_format(handle));check(opening(handle,os.fsencode(source),65536))
  while True:
   code=next_header(handle,C.byref(entry))
   if code==1:break
   check(code);count+=1
   if count>limit_entries:raise ValueError('Archive has too many entries')
   raw=pathname(entry)
   if not raw:raise ValueError('Archive entry has no filename')
   if os.fsdecode(raw).rstrip('/')=='.' and type_of(entry)==stat.S_IFDIR:check(skip(handle));continue
   name=safe_name(os.fsdecode(raw))
   if name in names:raise ValueError('Duplicate archive path: '+name)
   names.add(name)
   if encrypted(entry)>0:raise ValueError('Encrypted archives are unsupported; extract the soundpack first')
   if any(f(entry) for f in links):raise ValueError('Archive links are not allowed')
   kind=type_of(entry)
   if kind==stat.S_IFDIR:check(skip(handle));continue
   if kind!=stat.S_IFREG:raise ValueError('Special archive entry rejected')
   size=size_of(entry);declared+=size
   if size<0 or size>MAX_FILE or declared>MAX_TOTAL:raise ValueError('Expanded archive exceeds size limit')
   path=PurePosixPath(name)
   if path.suffix.lower()=='.disabled' and path.parent.name=='stereo':
    if size:raise ValueError('Invalid disabled event marker')
    disabled.append(path.stem)
   wanted=path.suffix.lower() in ('.wav','.png','.svg','.ico','.xpm') or path.name=='index.theme' if media else path.suffix.lower()=='.wav'
   if not wanted:check(skip(handle));continue
   if len(records)>=limit_files:raise ValueError('Archive contains too many WAV files')
   target=destination/(str(len(records))+'.bin');written=0
   with target.open('xb') as out:
    while True:
     n=data_read(handle,buf,len(buf));check(n)
     if not n:break
     written+=n;actual+=n
     if written>MAX_FILE or actual>MAX_TOTAL:raise ValueError('Expanded archive exceeds size limit')
     out.write(buf.raw[:n])
   if written!=size:raise ValueError('Truncated archive member: '+name)
   records.append([name,target.name])
  after=source.stat()
  if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('Archive changed while importing')
  return {'files':records,'disabled':disabled}
 finally:free(handle)

def source_data(source):
 if source.is_dir():return folder_data(source)
 if not source.is_file() or not source.name.lower().endswith(ARCHIVES):raise ValueError('Choose a sound folder or ZIP, RAR, 7z or TAR archive')
 with tempfile.TemporaryDirectory(prefix='mintxp-sounds-') as td:
  try:
   result=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),str(source),td],capture_output=True,text=True,timeout=35)
  except subprocess.TimeoutExpired:raise ValueError('Archive processing timed out; extract a smaller soundpack first') from None
  if result.returncode:raise ValueError('Archive import failed: '+(result.stderr.strip()[-1200:] or 'worker resource limit reached'))
  metadata=json.loads(result.stdout);payload={name:(Path(td)/blob).read_bytes() for name,blob in metadata['files']}
  return payload,{source/name:name for name in payload},set(metadata['disabled'])

if __name__=='__main__':
 import resource
 resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
 resource.setrlimit(resource.RLIMIT_CPU,(20,20))
 resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_FILE,MAX_FILE))
 try:print(json.dumps(_archive_worker(Path(sys.argv[1]),Path(sys.argv[2]))))
 except Exception as exc:print(str(exc),file=sys.stderr);raise SystemExit(1)
