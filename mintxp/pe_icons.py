"""Read bounded PE icon resources as data; never load or execute the binary.

Format: learn.microsoft.com/windows/win32/debug/pe-format and
learn.microsoft.com/windows/win32/menurc/resource-file-formats.
"""
import struct

def resources(data,kinds=(3,14)):
 def take(offset,size):
  if offset<0 or size<0 or offset+size>len(data):raise ValueError('Truncated PE resource')
  return data[offset:offset+size]
 def u16(o):return struct.unpack('<H',take(o,2))[0]
 def u32(o):return struct.unpack('<I',take(o,4))[0]
 if len(data)>40*1024*1024 or take(0,2)!=b'MZ':raise ValueError('Not a supported PE file')
 pe=u32(0x3c)
 if take(pe,4)!=b'PE\0\0':raise ValueError('Invalid PE signature')
 count=u16(pe+6);optional=pe+24;size=u16(pe+20);magic=u16(optional)
 if count>96 or magic not in (0x10b,0x20b):raise ValueError('Invalid PE sections')
 directory=optional+(96 if magic==0x10b else 112)
 if directory+24>optional+size:raise ValueError('Missing resource directory')
 rva=u32(directory+16);resource_size=u32(directory+20);sections=[]
 if resource_size>32*1024*1024:raise ValueError('Oversized resource directory')
 for i in range(count):
  s=optional+size+i*40;sections.append((u32(s+12),u32(s+16),u32(s+20)))
 def offset(address,length):
  for virtual,raw_size,raw in sections:
   if virtual<=address and address+length<=virtual+raw_size:return raw+address-virtual
  raise ValueError('Resource outside raw section')
 base=offset(rva,resource_size);take(base,resource_size)
 def resource(rel,length):
  if rel<0 or rel+length>resource_size:raise ValueError('Resource directory bounds')
  return base+rel
 found={};visited=set();nodes=[0]
 def walk(rel,path):
  if len(path)>3 or rel in visited:raise ValueError('Cyclic resource directory')
  visited.add(rel);p=resource(rel,16);n=u16(p+12)+u16(p+14);nodes[0]+=n
  if n>4096 or nodes[0]>20000:raise ValueError('Too many PE resources')
  resource(rel+16,8*n)
  for i in range(n):
   name=u32(p+16+8*i);child=u32(p+20+8*i)
   if name&0x80000000:continue
   ids=path+(name,)
   if len(ids)==1 and name not in kinds:continue
   if child&0x80000000:walk(child&0x7fffffff,ids)
   else:
    q=resource(child,16);length=u32(q+4)
    if len(ids)!=3 or length>4*1024*1024:raise ValueError('Invalid icon resource')
    found[ids]=take(offset(u32(q),length),length)
 walk(0,())
 return found

def icons(data):
 found=resources(data)
 groups={}
 for (kind,ident,lang),group in sorted(found.items(),key=lambda x:(x[0][2]!=1033,x[0])):
  if kind!=14 or ident in groups:continue
  if len(group)<6:raise ValueError('Truncated icon group')
  reserved,typ,n=struct.unpack_from('<HHH',group)
  if reserved or typ!=1 or not 0<n<=128 or len(group)<6+n*14:raise ValueError('Invalid icon group')
  images=[]
  for i in range(n):
   entry=group[6+i*14:20+i*14];rid=struct.unpack_from('<H',entry,12)[0]
   raw=found.get((3,rid,lang))
   if raw is None:raw=next((v for (t,j,l),v in found.items() if t==3 and j==rid),None)
   if raw is None:raise ValueError('Missing icon bitmap')
   if struct.unpack_from('<I',entry,8)[0]!=len(raw):raise ValueError('Invalid icon length')
   images.append((entry[:8],raw))
  groups[ident]=images
 return groups

def ico(images,size=48):
 # Prefer an exact native size and highest colour depth; otherwise nearest larger.
 entry,raw=min(images,key=lambda item:((item[0][0] or 256)!=size,(item[0][0] or 256)<size,abs((item[0][0] or 256)-size),-struct.unpack_from('<H',item[0],6)[0]))
 return struct.pack('<HHH',0,1,1)+entry+struct.pack('<II',len(raw),22)+raw


def bitmap(data,ident):
 """Convert a bounded Windows DIB resource to BMP for the image decoder."""
 found=resources(data,(2,))
 candidates=sorted(((lang,raw) for (kind,key,lang),raw in found.items() if key==ident),key=lambda x:x[0]!=1033)
 if not candidates:return None
 raw=candidates[0][1]
 if len(raw)<40:raise ValueError('Truncated bitmap')
 header,w,h,planes,bits,compression,_,_,_,colours,_=struct.unpack_from('<IiiHHIIiiII',raw)
 if header not in (40,108,124) or planes!=1 or bits not in (1,4,8,16,24,32) or compression not in (0,3) or not 0<w<=4096 or not 0<abs(h)<=4096:raise ValueError('Unsupported bitmap')
 palette=(colours or 2**bits) if bits<=8 else colours
 if palette>256:raise ValueError('Invalid bitmap palette')
 offset=14+header+4*palette+(12 if compression==3 and header==40 else 0)
 if offset>=14+len(raw):raise ValueError('Truncated bitmap pixels')
 return b'BM'+struct.pack('<IHHI',len(raw)+14,0,0,offset)+raw


def bitmap_rgba(bmp):
 """Retain straight alpha in XP's 32-bit BI_RGB DIBs (BMP loaders drop it)."""
 if len(bmp)<54 or bmp[:2]!=b'BM':raise ValueError('Invalid BMP')
 offset=struct.unpack_from('<I',bmp,10)[0]
 header,w,h,planes,bits,compression=struct.unpack_from('<IiiHHI',bmp,14)
 if header!=40 or planes!=1 or bits!=32 or compression!=0:return None
 if not 0<w<=4096 or not 0<abs(h)<=4096 or offset<54 or offset+w*abs(h)*4>len(bmp):raise ValueError('Invalid alpha bitmap bounds')
 raw=bmp[offset:offset+w*abs(h)*4]
 # Legacy 32-bit bitmaps can leave the reserved alpha channel entirely zero.
 if not any(raw[3::4]):return None
 rgba=bytearray(len(raw));stride=w*4
 for y in range(abs(h)):
  row=(abs(h)-1-y if h>0 else y)*stride
  for x in range(w):
   b,g,r,a=raw[row+x*4:row+x*4+4];i=y*stride+x*4
   rgba[i:i+4]=bytes((r,g,b,a))
 return w,abs(h),bytes(rgba)
