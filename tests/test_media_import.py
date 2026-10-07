import base64,io,json,tarfile,tempfile,unittest,wave,zipfile
from pathlib import Path
from unittest.mock import Mock,patch
from mintxp.engine import Engine
from mintxp.media_import import import_media
from mintxp.sounds import imported_plan,apply_import,remove_import,verify
from mintxp.components import DEFAULTS,ROOT
from test_sounds import audio,Settings

PNG=(ROOT/'assets/icons/32/devices/computer.png').read_bytes()

class MediaPacks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.home=self.root/'home';self.home.mkdir();self.e=Engine(self.home,self.root/'state',Settings())
 def tearDown(self):self.tmp.cleanup()
 def archive(self,entries):
  p=self.root/'pack.zip'
  with zipfile.ZipFile(p,'w') as f:
   for name,data in entries.items():f.writestr(name,data)
  return p
 def test_sound_only_icon_only_and_mixed_nested_archives(self):
  for entries,counts in [({'Pack/Windows XP Ding.wav':audio()},(1,0)),({'Icons/My Computer.png':PNG},(0,3)),({'Pack/Windows XP Ding.wav':audio(),'Pack/Icons/My Computer.png':PNG},(1,3))]:
   result=import_media(self.e,self.archive(entries));self.assertEqual((result['sounds'],result['icons']),counts)
   self.assertEqual(bool(result['sound_path']),bool(counts[0]));self.assertEqual(bool(result['icon_path']),bool(counts[1]))
   self.assertFalse(self.e.read_current().get('installed'))
   if counts[0]:self.assertIn('bell',imported_plan(self.e,dict(DEFAULTS,sound_source=result['sound_path']))['report']['aliases'])
   if counts[1]:self.assertTrue((Path(result['icon_path'])/'32/computer.png').exists())
 def test_theme_folder_recognized_and_original_unchanged(self):
  folder=self.root/'Theme';(folder/'32/devices').mkdir(parents=True)
  index=b'[Icon Theme]\nName=Test\nDirectories=32/devices\n\n[32/devices]\nSize=32\nType=Fixed\n'
  (folder/'index.theme').write_bytes(index);(folder/'32/devices/computer.png').write_bytes(PNG)
  result=import_media(self.e,folder);self.assertEqual(result['icons'],1);self.assertEqual((folder/'index.theme').read_bytes(),index)
  self.assertEqual((Path(result['icon_path'])/'32/devices/computer.png').read_bytes(),PNG)
 def test_malformed_unknown_audio_and_traversal_leave_no_import(self):
  for entries in ({'../Ding.wav':audio()},{'Ding.wav':b'bad'},{'music.wav':audio()},{'Computer.png':b'not png'},{'readme.txt':b'no media'}):
   with self.assertRaises(ValueError):import_media(self.e,self.archive(entries))
   self.assertEqual(list((self.e.state/'imports').iterdir()),[])
 def test_external_svg_reference_and_links_rejected(self):
  data=b'<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><image href="file:///etc/passwd"/></svg>'
  with self.assertRaises(ValueError):import_media(self.e,self.archive({'Computer.svg':data}))
  folder=self.root/'unsafe';folder.mkdir();(folder/'Computer.png').symlink_to('/etc/passwd')
  with self.assertRaises(ValueError):import_media(self.e,folder)
 def test_disabled_sound_markers_survive_guided_import(self):
  result=import_media(self.e,self.archive({'Windows XP Ding.wav':audio(),'Pack/stereo/bell.disabled':b''}))
  self.assertIn('bell',result['sound_plan']['report']['disabled_events'])
  self.assertNotIn('bell',result['sound_plan']['report']['aliases'])
 def test_svg_disguised_as_png_is_rejected(self):
  data=b'<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><image href="file:///etc/passwd"/></svg>'
  with self.assertRaises(ValueError):import_media(self.e,self.archive({'computer.png':data}))
 def test_ico_and_tar_import(self):
  from test_iso_import import pe_fixture
  from mintxp.pe_icons import icons,ico
  payload=ico(icons(pe_fixture())[16]);p=self.root/'icons.tar.gz'
  with tarfile.open(p,'w:gz') as f:
   info=tarfile.TarInfo('My Computer.ico');info.size=len(payload);f.addfile(info,io.BytesIO(payload))
  result=import_media(self.e,p);self.assertEqual(result['icons'],3)
 def test_duplicate_variants_do_not_silently_pick_one(self):
  data=(ROOT/'assets/icons/32/places/folder.png').read_bytes()
  with self.assertRaises(ValueError):import_media(self.e,self.archive({'A/computer.png':PNG,'B/computer.png':data}))

class MintSounds(unittest.TestCase):
 def test_mint_plan_apply_and_exact_undo(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);home=root/'home';home.mkdir();e=Engine(home,root/'state',Settings())
   e.settings.set('org.cinnamon.desktop.sound/theme-name','"Before"')
   e.apply({'files':{'.config/keep':e.descriptor(b'keep')},'settings':{},'options':{}},False)
   before=dict(e.settings.values)
   # Test state transitions with temporary media; Ubuntu CI has no Mint artwork.
   from mintxp.sounds import CINNAMON
   art=root/'MintSounds';art.mkdir();theme=root/'LinuxMint';theme.mkdir()
   (theme/'index.theme').write_text('[Sound Theme]\nName=LinuxMint\n')
   for event in (*CINNAMON,'volume','trash'):
    (art/(event+('.ogg' if event=='logout' else '.oga'))).write_bytes(audio())
   with patch.object(e,'safety_snapshot',return_value='test'),patch('mintxp.mint_sounds.ART',art),patch('mintxp.mint_sounds.THEME',theme):
    source=root/'Sounds';source.mkdir();(source/'Windows XP Ding.wav').write_bytes(audio())
    apply_import(e,dict(DEFAULTS,sound_source=str(source),sounds=True))
    result=apply_import(e,dict(DEFAULTS,sound_source=':mint:'))
    self.assertEqual(result['pack'],'mint');self.assertEqual(verify(e)['integrity'],'OK')
    self.assertEqual(e.settings.effective('org.cinnamon.desktop.sound','theme-name'),'LinuxMint')
    self.assertFalse((home/'.local/share/sounds/Mint-XP-Experience-Sounds/stereo/bell.wav').exists())
    self.assertTrue(Path(result['preview_files']['bell']).is_file())
    remove_import(e)
   self.assertEqual({k:v for k,v in e.settings.values.items() if v is not None},before)
   self.assertEqual((home/'.config/keep').read_bytes(),b'keep')
