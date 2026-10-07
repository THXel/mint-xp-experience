"""Own generated audio fixtures; no Microsoft recordings required."""
import hashlib,io,json,shutil,stat,struct,subprocess,tarfile,unittest,zipfile,zlib
from pathlib import Path
import test_sounds
from test_sounds import audio
from mintxp.engine import Conflict
from mintxp.components import ROOT,DEFAULTS
from mintxp.sounds import imported_plan,apply_import,verify,remove_import,ensure_ready
from mintxp.sound_sources import source_data,MAX_FILE

def rar5(name,data):
 # Stored RAR5 fixture per https://www.rarlab.com/technote.htm.
 def vint(n):
  out=bytearray()
  while n>=128:out.append((n&127)|128);n>>=7
  out.append(n);return bytes(out)
 def header(body):
  raw=vint(len(body))+body;return struct.pack('<I',zlib.crc32(raw))+raw
 filename=name.encode()
 file=b'\x02\x02'+vint(len(data))+b'\x04'+vint(len(data))+vint(0o100644)+struct.pack('<I',zlib.crc32(data))+b'\x00\x01'+vint(len(filename))+filename
 return b'Rar!\x1a\x07\x01\x00'+header(b'\x01\x00\x00')+header(file)+data+header(b'\x05\x00\x00')

class SourceCases(unittest.TestCase):
 setUp=test_sounds.Sounds.setUp
 tearDown=test_sounds.Sounds.tearDown
 def plan(self,path,**options):return imported_plan(self.e,dict(self.o,sound_source=str(path),**options))
 def test_no_implicit_sound_source(self):
  with self.assertRaises(Conflict):imported_plan(self.e,dict(DEFAULTS))
  with self.assertRaises(Conflict):imported_plan(self.e,dict(DEFAULTS,sound_source=':builtin:'))
 def test_zip_tar_rar_nested_import_and_undo(self):
  for suffix in ('.zip','.tar','.tar.gz','.tar.bz2','.tar.xz','.rar'):
   with self.subTest(suffix=suffix):
    p=self.root/('sounds'+suffix);name='Pack/Media/Windows XP Ding.wav';data=audio()
    if suffix=='.zip':
     with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as f:f.writestr(name,data)
    elif suffix=='.rar':
     p.write_bytes(rar5(name,data))
     if shutil.which('unrar'):self.assertEqual(subprocess.run(['unrar','t',str(p)],capture_output=True).returncode,0)
    else:
     with tarfile.open(p,'w:'+{'.tar':'','.tar.gz':'gz','.tar.bz2':'bz2','.tar.xz':'xz'}[suffix]) as f:
      member=tarfile.TarInfo(name);member.size=len(data);f.addfile(member,io.BytesIO(data))
    original=p.read_bytes();result=self.plan(p);self.assertEqual(result['report']['aliases']['bell'],name)
    apply_import(self.e,dict(self.o,sound_source=str(p)),prepared=result);self.assertEqual(verify(self.e)['integrity'],'OK');remove_import(self.e);self.assertEqual(p.read_bytes(),original)
 def test_7z_and_encrypted_zip(self):
  if not shutil.which('7z'):self.skipTest('7z fixture producer unavailable')
  for suffix,password in (('.7z',False),('.zip',True)):
   p=self.root/('fixture'+suffix);args=['7z','a',str(p),str(self.source/'Windows XP Ding.wav')]
   if password:args+=['-pfixture-password']
   self.assertEqual(subprocess.run(args,capture_output=True).returncode,0)
   if password:
    with self.assertRaises(Conflict):self.plan(p)
   else:self.assertIn('bell',self.plan(p)['report']['aliases'])
 def test_ambiguity_requires_choice_and_identical_duplicates_do_not(self):
  sub=self.source/'alternative';sub.mkdir();name='Windows XP Ding.wav';(sub/name).write_bytes(audio())
  self.assertFalse(self.plan(self.source)['report']['ambiguous'])
  other=bytearray(audio());other[-2:]=b'\x01\x00';(sub/name).write_bytes(other)
  result=self.plan(self.source);self.assertIn('stem:Ding',result['report']['ambiguous'])
  before=(self.e.state/'current.json').read_bytes()
  with self.assertRaises(Conflict):apply_import(self.e,self.o)
  self.assertEqual((self.e.state/'current.json').read_bytes(),before)
  result=self.plan(self.source,sound_choices={'stem:Ding':'alternative/'+name});ensure_ready(result['report']);self.assertEqual(result['report']['aliases']['bell'],'alternative/'+name)
 def test_german_names_and_start_vs_startup(self):
  folder=self.root/'Deutsch';folder.mkdir()
  for n in ('Papierkorb leeren','Gerät angeschlossen','Lautstärke','Fenster minimieren','Windows XP Start','Systemstart'):(folder/(n+'.wav')).write_bytes(audio())
  r=self.plan(folder)['report'];self.assertEqual(r['aliases']['trash-empty'],'Papierkorb leeren.wav');self.assertEqual(r['aliases']['device-added'],'Gerät angeschlossen.wav');self.assertEqual(r['aliases']['bell'],'Lautstärke.wav');self.assertEqual(r['aliases']['desktop-login'],'Systemstart.wav');self.assertEqual(r['cinnamon']['switch']['file'],'originals/Windows XP Start.wav')
 def test_unsafe_paths_links_duplicates_and_oversize_rejected(self):
  p=self.root/'bad.zip'
  for name in ('../escape.wav','/absolute.wav','C:\\outside.wav','ok/../../escape.wav'):
   with zipfile.ZipFile(p,'w') as f:f.writestr(name,audio())
   with self.assertRaises(Conflict):self.plan(p)
  with zipfile.ZipFile(p,'w') as f:
   link=zipfile.ZipInfo('Ding.wav');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16;f.writestr(link,'elsewhere')
  with self.assertRaises(Conflict):self.plan(p)
  p=self.root/'bad.tar'
  for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE):
   with tarfile.open(p,'w') as f:
    m=tarfile.TarInfo('Ding.wav');m.type=kind;m.linkname='elsewhere';f.addfile(m)
   with self.assertRaises(Conflict):self.plan(p)
  with tarfile.open(p,'w') as f:
   m=tarfile.TarInfo('Ding.wav');m.size=MAX_FILE+1;f.addfile(m)
  with self.assertRaises(Conflict):self.plan(p)
 def test_archived_source_removal_and_preview_immutable(self):
  p=self.root/'pack.zip'
  with zipfile.ZipFile(p,'w') as f:f.writestr('Windows XP Ding.wav',audio())
  result=self.plan(p);p.unlink();o=dict(self.o,sound_source=str(p));apply_import(self.e,o,prepared=result);self.assertEqual(verify(self.e)['integrity'],'OK');self.assertIn('bell',imported_plan(self.e,o)['report']['aliases'])
