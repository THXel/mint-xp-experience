import io,struct,tempfile,unittest,wave,subprocess,shutil,json
from pathlib import Path
from unittest.mock import Mock
from mintxp.pe_icons import icons,ico
from mintxp.iso_import import members,import_iso,ICON_MAP,SOUNDS
from mintxp.engine import Engine

def pe_fixture(bits=64,cycle=False):
 # Original synthetic 16x16 bitmap, never Windows artwork.
 image=struct.pack('<IiiHHIIiiII',40,16,32,1,32,0,1024,0,0,0,0)+bytes([80,130,210,255])*256+bytes(64)
 resource=bytearray()
 def reserve(n):off=len(resource);resource.extend(bytes(n));return off
 def directory(entries):
  off=reserve(16+len(entries)*8);struct.pack_into('<HH',resource,off+12,0,len(entries))
  for i,(name,child) in enumerate(entries):struct.pack_into('<II',resource,off+16+8*i,name,child)
  return off
 root=directory([(3,0),(14,0)]);types={}
 for kind,ids in [(3,[1]),(14,list(ICON_MAP))]:
  off=directory([(i,0) for i in ids]);types[kind]=off
  for n,i in enumerate(ids):
   language=directory([(1033,0)]);d=reserve(16);struct.pack_into('<I',resource,off+20+8*n,language|0x80000000);struct.pack_into('<I',resource,language+20,d)
   data=image if kind==3 else struct.pack('<HHHBBBBHHIH',0,1,1,16,16,0,0,1,32,len(image),1)
   payload=reserve(len(data));resource[payload:]=data;struct.pack_into('<IIII',resource,d,0x1000+payload,len(data),0,0)
 for n,kind in enumerate((3,14)):struct.pack_into('<I',resource,root+20+n*8,types[kind]|0x80000000)
 if cycle:struct.pack_into('<I',resource,20,0x80000000)
 pe=0x80;optional_size=240 if bits==64 else 224;header=bytearray(0x200);header[:2]=b'MZ';struct.pack_into('<I',header,0x3c,pe);header[pe:pe+4]=b'PE\0\0';struct.pack_into('<H',header,pe+6,1);struct.pack_into('<H',header,pe+20,optional_size);optional=pe+24;struct.pack_into('<H',header,optional,0x20b if bits==64 else 0x10b);directory=optional+(112 if bits==64 else 96);struct.pack_into('<II',header,directory+16,0x1000,len(resource));section=optional+optional_size;struct.pack_into('<III',header,section+12,0x1000,len(resource),0x200)
 return bytes(header+resource)

class PEBounds(unittest.TestCase):
 def test_pe32_and_pe64(self):
  for bits in (32,64):
   groups=icons(pe_fixture(bits));self.assertEqual(set(groups),set(ICON_MAP));data=ico(groups[16]);self.assertEqual(data[:6],b'\0\0\1\0\1\0');self.assertEqual(struct.unpack_from('<I',data,18)[0],22)
 def test_cyclic_resource_tree_rejected(self):
  with self.assertRaisesRegex(ValueError,'Cyclic'):icons(pe_fixture(cycle=True))
 def test_truncated_and_non_pe_rejected(self):
  for data in (b'',b'MZ',pe_fixture()[:-30]):
   with self.assertRaises(ValueError):icons(data)

@unittest.skipUnless(shutil.which('genisoimage'),'ISO test builder unavailable')
class ISOImport(unittest.TestCase):
 def test_synthetic_iso_import_is_private_and_does_not_apply_settings(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);media=root/'media/AMD64';media.mkdir(parents=True);(media/'TXTSETUP.SIF').write_text('[SourceDisksFiles]\n');(media/'SHELL32.DLL').write_bytes(pe_fixture())
   bio=io.BytesIO()
   with wave.open(bio,'wb') as wav:wav.setparams((1,2,22050,0,'NONE','not compressed'));wav.writeframes(bytes(100))
   for stem in SOUNDS:(media/(stem+'.WAV')).write_bytes(bio.getvalue())
   source=root/'fixture.iso';subprocess.run(['genisoimage','-quiet','-R','-o',str(source),str(media.parent)],check=True)
   home=root/'home';home.mkdir();settings=Mock();e=Engine(home,root/'state',settings);r=import_iso(e,source)
   settings.set.assert_not_called();self.assertFalse(e.read_current().get('installed'));self.assertEqual(r['sounds'],26);self.assertEqual(r['icons'],len(set(' '.join(ICON_MAP.values()).split())))
   self.assertTrue(Path(r['icon_path']).is_relative_to(e.state/'imports'));self.assertTrue((Path(r['icon_path'])/'48/computer.png').is_file());self.assertEqual((Path(r['sound_path'])/'Windows XP Startup.wav').read_bytes(),bio.getvalue())
   self.assertFalse(list((e.state/'imports').glob('.iso-*')))
 def test_unsupported_iso_does_not_leave_partial_import(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'bad.iso';source.write_bytes(bytes(40000));home=root/'home';home.mkdir();e=Engine(home,root/'state',Mock())
   with self.assertRaises(ValueError):import_iso(e,source)
   self.assertEqual(list((e.state/'imports').iterdir()),[])
