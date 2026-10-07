"""Bounded ACS 2.x image/animation reader; no scripts, voice or Windows runtime.
Format reference: Remy Lebeau, MSAgent Character Data Specification.
https://uploads.s.zeid.me/ms-agent-format-spec.html
"""
import struct,hashlib,json
from pathlib import Path
class Reader:
 def __init__(self,data,start=0,size=None):self.data=data;self.pos=start;self.end=len(data) if size is None else start+size
 def take(self,n):
  if n<0 or self.pos+n>self.end or self.end>len(self.data):raise ValueError('Truncated character')
  value=self.data[self.pos:self.pos+n];self.pos+=n;return value
 def num(self,f):return struct.unpack('<'+f,self.take(struct.calcsize('<'+f)))[0]
 def text(self):
  n=self.num('I')
  if n>4096:raise ValueError('Character string limit')
  return self.take((n+1)*2)[:-2].decode('utf-16le') if n else ''
 def loc(self):return Reader(self.data,self.num('I'),self.num('I'))
 def count(self,f,limit):
  n=self.num(f)
  if n>limit:raise ValueError('Character count limit')
  return n

def decompress(data,size):
 if not data or data[0]!=0 or not 0<size<=1024*1024:raise ValueError('Invalid image stream')
 bit=8;out=bytearray()
 def read(n):
  nonlocal bit
  if bit+n>len(data)*8:raise ValueError('Truncated image stream')
  v=0
  for i in range(n):v|=((data[bit//8]>>(bit%8))&1)<<i;bit+=1
  return v
 while len(out)<size:
  if not read(1):out.append(read(8));continue
  run=0
  while run<3 and read(1):run+=1
  bits=(6,9,12,20)[run];offset=read(bits)
  if bits==20 and offset==0xfffff:break
  offset+=(1,65,577,4673)[run];ones=0
  while read(1):
   ones+=1
   if ones>11:raise ValueError('Image run limit')
  count=2+(run==3)+(1<<ones)-1+read(ones)
  if offset>len(out) or len(out)+count>size:raise ValueError('Invalid image backreference')
  for _ in range(count):out.append(out[-offset])
 if len(out)!=size:raise ValueError('Image length mismatch')
 return out

def export(data,destination):
 if len(data)>40*1024*1024:raise ValueError('Character size limit')
 r=Reader(data)
 if r.num('I')!=0xabcdabc3:raise ValueError('Unsupported character format')
 ch=r.loc();an=r.loc();im=r.loc();r.loc()
 minor=ch.num('H');major=ch.num('H')
 if major!=2:raise ValueError('Unsupported character version')
 ch.take(24);width=ch.num('H');height=ch.num('H');transparent=ch.num('B');flags=ch.num('I');ch.take(4)
 if not 0<width<=256 or not 0<height<=256:raise ValueError('Character dimensions limit')
 start=ch.pos;palette=None
 # Rover omits voice metadata although its style includes the legacy voice bit.
 for voice in (bool(flags&16),False):
  ch.pos=start
  try:
   if voice:
    ch.take(38)
    if ch.num('B'):ch.take(2);ch.text();ch.take(4);ch.text()
   if flags&512:ch.take(14);ch.text();ch.take(10)
   count=ch.count('I',256)
   if count!=256:continue
   palette=[ch.take(4) for _ in range(count)];break
  except (ValueError,UnicodeError):continue
 if palette is None:raise ValueError('Unsupported character palette')
 images=[]
 for _ in range(im.count('I',5000)):images.append(im.loc());im.take(4)
 animations={}
 for _ in range(an.count('I',300)):name=an.text();animations[name]=an.loc()
 import gi
 gi.require_version("GdkPixbuf","2.0")
 from gi.repository import GdkPixbuf,GLib
 output_bytes=0
 dest=Path(destination);dest.mkdir(parents=True,exist_ok=True);written={};cache={};frames_total=0
 def image(index):
  if index in cache:return cache[index]
  if index>=len(images):raise ValueError('Invalid image index')
  src=images[index];src.take(1);w=src.num('H');h=src.num('H');compressed=src.num('B');blob=src.take(src.count('I',1024*1024))
  if not 0<w<=256 or not 0<h<=256:raise ValueError('Image dimensions limit')
  stride=(w+3)&~3;pixels=decompress(blob,stride*h) if compressed else blob
  if len(pixels)!=stride*h:raise ValueError('Image byte count')
  cache[index]=(w,h,pixels);return cache[index]
 manifest={'format':1,'width':width,'height':height,'animations':{}}
 for name,src in animations.items():
  src.text();src.take(1);src.text();frames=[]
  for _ in range(src.count('H',1000)):
   frames_total+=1
   if frames_total>5000:raise ValueError('Animation frame limit')
   parts=[(src.num('I'),src.num('h'),src.num('h')) for _ in range(src.count('H',20))]
   src.take(2);duration=src.num('H');src.take(2);src.take(src.count('B',8)*4)
   for _ in range(src.count('B',8)):
    src.take(5);region=src.num('B');src.take(8)
    if region:src.take(src.count('I',1024*1024))
   rgba=bytearray(width*height*4)
   for index,x,y in reversed(parts):
    w,h,pixels=image(index)
    for yy in range(h):
     for xx in range(w):
      c=pixels[(h-1-yy)*((w+3)&~3)+xx]
      if c!=transparent and 0<=x+xx<width and 0<=y+yy<height:
       b,g,red,_=palette[c];at=((y+yy)*width+x+xx)*4;rgba[at:at+4]=bytes((red,g,b,255))
   key=hashlib.sha256(rgba).hexdigest()[:24]+'.png'
   if key not in written:
    pix=GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(rgba)),GdkPixbuf.Colorspace.RGB,True,8,width,height,width*4);pix.savev(str(dest/key),'png',[],[]);written[key]=hashlib.sha256((dest/key).read_bytes()).hexdigest()
    output_bytes+=(dest/key).stat().st_size
    if output_bytes>32*1024*1024:raise ValueError('Character output limit')
   frames.append([key,max(20,min(10000,duration*10))])
  if frames:manifest['animations'][name]=frames
 (dest/'character.json').write_text(json.dumps(manifest));written['character.json']=hashlib.sha256((dest/'character.json').read_bytes()).hexdigest()
 return manifest,written


def checked_files(folder):
 """Validate private imported frames before placing them in a managed install."""
 import re
 folder=Path(folder)
 if not folder.exists():return {}
 if folder.is_symlink():raise ValueError('Linked character folder')
 manifest_path=folder/'character.json'
 if manifest_path.is_symlink() or manifest_path.stat().st_size>1024*1024:raise ValueError('Character manifest limit')
 raw=manifest_path.read_bytes();m=json.loads(raw)
 if m.get('format')!=1 or any(type(m.get(k))!=int or not 0<m[k]<=256 for k in ('width','height')):raise ValueError('Character dimensions')
 animations=m.get('animations')
 if not isinstance(animations,dict) or not 0<len(animations)<=300:raise ValueError('Character animations')
 names=set();count=0
 for animation,frames in animations.items():
  if not isinstance(animation,str) or len(animation)>100 or not isinstance(frames,list) or not 0<len(frames)<=1000:raise ValueError('Animation limit')
  for frame in frames:
   if not isinstance(frame,list) or len(frame)!=2:raise ValueError('Invalid frame')
   name,duration=frame
   if not isinstance(name,str) or not re.fullmatch(r'[a-f0-9]{24}\.png',name) or type(duration)!=int or not 20<=duration<=10000:raise ValueError('Invalid frame')
   names.add(name);count+=1
 if count>5000:raise ValueError('Frame limit')
 result={'character.json':raw};total=len(raw)
 for name in names:
  path=folder/name
  if path.is_symlink() or path.stat().st_size>1024*1024:raise ValueError('Frame size limit')
  data=path.read_bytes();total+=len(data)
  if total>32*1024*1024 or data[:8]!=b'\x89PNG\r\n\x1a\n' or data[12:16]!=b'IHDR' or struct.unpack('>II',data[16:24])!=(m['width'],m['height']):raise ValueError('Frame dimensions or total limit')
  result[name]=data
 return result
