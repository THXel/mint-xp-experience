import hashlib,io,json,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from mintxp.addons import Addons,DOWNLOADS,download,unpack,safe_url
from mintxp.flatpak_addons import FlatpakAddons
from mintxp.engine import Engine,Conflict
from test_engine import FakeSettings

def archive(path,entries):
 with tarfile.open(path,'w:gz') as tar:
  for name,data,link in entries:
   info=tarfile.TarInfo(name)
   if link is not None:info.type=tarfile.SYMTYPE;info.linkname=link;tar.addfile(info)
   else:info.size=len(data);tar.addfile(info,io.BytesIO(data))

class Downloads(unittest.TestCase):
 def test_exact_digest_and_progress(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'cache').mkdir();(p/'cache/a').write_bytes(b'hello');events=[]
   spec={'url':'https://github.com/a/b','size':5,'sha256':hashlib.sha256(b'hello').hexdigest()}
   download(spec,p/'a',lambda *e:events.append(e),p/'cache');self.assertEqual((p/'a').read_bytes(),b'hello');self.assertEqual(events[-1][1:3],(5,5))
 def test_hash_failure_and_oversize_leave_no_download(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'cache').mkdir();(p/'cache/a').write_bytes(b'hello')
   for size in (4,5,6):
    with self.assertRaises(Conflict):download({'url':'https://github.com/a/b','size':size,'sha256':'0'*64},p/'a',cache=p/'cache')
    self.assertFalse((p/'a').exists())
 def test_untrusted_hosts_and_cleartext_rejected(self):
  for url in ('http://github.com/a','https://example.org/a','https://github.com@evil.org/a','https://github.com:4433/a'):
   with self.assertRaises(Conflict):safe_url(url)
 def test_archive_traversal_and_external_links_rejected_before_write(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)
   for name,link in [('root/../../escape',None),('/tmp/escape',None),('root/escape','../../escape')]:
    archive(p/'a.tgz',[('root/first',b'ok',None),(name,b'bad',link)])
    with self.assertRaises(Conflict):unpack(p/'a.tgz',p/'out')
    self.assertFalse((p/'out/root/first').exists())
 def test_internal_file_link_materialized_without_symlinks(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);archive(p/'a.tgz',[('root/lib/real',b'x',None),('root/bin/link',b'','../lib/real')]);out=unpack(p/'a.tgz',p/'out')
   self.assertEqual((out/'bin/link').read_bytes(),b'x');self.assertFalse((out/'bin/link').is_symlink())
 def test_link_cycles_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);archive(p/'a.tgz',[('root/a',b'','b'),('root/b',b'','a')])
   with self.assertRaises(Conflict):unpack(p/'a.tgz',p/'out')

class LocalAddons(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.home=self.base/'home';self.home.mkdir()
  self.e=Engine(self.home,self.base/'state',FakeSettings());self.a=Addons(self.e,cache=self.base/'cache');(self.base/'cache').mkdir()
  self.patcher=patch.object(self.a.flatpak,'status',return_value={'space-cadet':{'state':'absent'}});self.patcher.start()
 def tearDown(self):self.patcher.stop();self.temp.cleanup()
 def install_fixture(self):
  file=self.base/'cache/jspaint.tar.gz';archive(file,[('root/index.html',b'<title>fixture</title>',None),('root/LICENSE.txt',b'test',None)])
  spec={'url':'https://github.com/a/b','sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'size':file.stat().st_size}
  with patch.dict(DOWNLOADS,{'jspaint.tar.gz':spec}),patch.object(self.a,'preflight'):
   return self.a.install('jspaint')
 def test_install_remove_preserves_saved_data_theme_and_unrelated_files(self):
  self.e.apply({'files':{'.config/theme':self.e.descriptor(b'theme')},'settings':{}},False)
  baseline=(self.e.state/'baseline.json').read_bytes();current=(self.e.state/'current.json').read_bytes()
  save=self.home/'.local/share/mintxp-addon-data/jspaint/drawing.png';save.parent.mkdir(parents=True);save.write_bytes(b'keep')
  self.install_fixture();self.assertEqual(self.a.status()['jspaint']['state'],'managed');self.assertEqual(self.a.verify('jspaint'),'OK')
  self.a.remove('jspaint');self.assertEqual(save.read_bytes(),b'keep');self.assertEqual((self.e.state/'baseline.json').read_bytes(),baseline);self.assertEqual((self.e.state/'current.json').read_bytes(),current)
  self.assertFalse((self.home/'.local/share/applications/mintxp-addon-jspaint.desktop').exists())
 def test_paint_launcher_and_window_share_bundled_palette_icon(self):
  self.install_fixture()
  from gi.repository import Gio
  p=self.home/'.local/share/applications/mintxp-addon-jspaint.desktop'
  info=Gio.DesktopAppInfo.new_from_filename(str(p));self.assertIsNotNone(info)
  self.assertIn('Utility;',info.get_categories());self.assertIn('Graphics',info.get_categories().split(';'));self.assertEqual(info.get_name(),'Paint - JS Paint')
  icon=self.home/'.local/share/mintxp-addons/jspaint/icon.svg'
  self.assertTrue(icon.is_file());self.assertIn(str(icon),info.get_icon().to_string())
  self.a.remove('jspaint');self.assertFalse(icon.exists())
 def test_existing_legacy_application_is_not_claimed_or_removed(self):
  path=self.home/'.local/share/applications/xp-community-minesweeper.desktop';path.parent.mkdir(parents=True);path.write_text('[Desktop Entry]\nName=Existing')
  self.a.install('minesweeper');self.assertEqual(self.a.status()['minesweeper']['state'],'external')
  with self.assertRaises(Conflict):self.a.remove('minesweeper')
  self.assertEqual(path.read_text(),'[Desktop Entry]\nName=Existing')
 def test_modified_managed_files_block_removal(self):
  self.install_fixture();file=self.home/'.local/share/mintxp-addons/jspaint/web/index.html';file.write_text('user edited')
  with self.assertRaises(Conflict):self.a.remove('jspaint')
  self.assertEqual(file.read_text(),'user edited')
 def test_failed_install_does_not_modify_theme_or_create_launcher(self):
  with patch.object(self.a,'preflight'),patch('mintxp.addons.download',side_effect=Conflict('bad hash')):
   with self.assertRaises(Conflict):self.a.install('jspaint')
  self.assertFalse((self.home/'.local/share/applications/mintxp-addon-jspaint.desktop').exists());self.assertFalse(self.e.read_current()['installed'])
 def test_untracked_directory_is_protected(self):
  path=self.home/'.local/share/mintxp-addons/jspaint/notes';path.parent.mkdir(parents=True);path.write_text('keep')
  with patch.object(self.a,'preflight'):
   with self.assertRaises(Conflict):self.a.install('jspaint')
  self.assertEqual(path.read_text(),'keep')

class Flatpaks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name);(p/'home').mkdir();self.e=Engine(p/'home',p/'state',FakeSettings());self.scopes=[];self.calls=[];self.fail=False
  self.a=FlatpakAddons(self.e,self.runner)
 def tearDown(self):self.tmp.cleanup()
 def runner(self,args,progress=False):
  self.calls.append(args);app='com.github.k4zmu2a.spacecadetpinball'
  if args[0]=='list':return ''.join(app+'\t'+s+'\n' for s in self.scopes)
  if args[0]=='remotes':return 'flathub\thttps://dl.flathub.org/repo/\n'
  if args[0]=='install':
   self.scopes.append('user')
   if self.fail:raise Conflict('interrupted')
  if args[0]=='uninstall':self.scopes.remove('user')
  if args[0]=='info':return 'a'*64
  return ''
 def test_existing_system_flatpak_unchanged(self):
  self.scopes=['system'];self.a.install('space-cadet')
  with self.assertRaises(Conflict):self.a.remove('space-cadet')
  self.assertFalse(any(c[0] in ('install','uninstall') for c in self.calls));self.assertEqual(self.scopes,['system'])
 def test_new_flatpak_removed_without_data_or_dependency_purge(self):
  self.a.install('space-cadet');self.a.remove('space-cadet');self.assertEqual(self.scopes,[])
  cmd=next(c for c in self.calls if c[0]=='uninstall');self.assertIn('--user',cmd);self.assertNotIn('--delete-data',cmd);self.assertNotIn('--unused',cmd)
 def test_failed_external_operation_reconciliation_protects_application(self):
  self.fail=True
  with self.assertRaises(Conflict):self.a.install('space-cadet')
  with self.assertRaises(Conflict):self.a.remove('space-cadet')
  self.a.reconcile('space-cadet');self.assertEqual(self.a.status()['space-cadet']['state'],'external');self.assertEqual(self.scopes,['user'])

 def test_empty_user_remote_list_with_blank_line(self):
  created=[]
  def runner(args,progress=False):
   if args[0]=='remotes':return 'flathub\thttps://dl.flathub.org/repo/\n' if created else '\n'
   if args[0]=='remote-add':created.append(args);return ''
   if args[0]=='list' and not self.scopes:return '\n'
   return self.runner(args,progress)
  self.a.runner=runner;self.a.install('space-cadet')
  self.assertEqual(len(created),1);self.assertEqual(self.scopes,['user'])
  self.assertEqual(created[0][-1],'https://dl.flathub.org/repo/flathub.flatpakrepo')
