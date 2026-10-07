import json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from mintxp.engine import Engine,Conflict
from mintxp.install_flow import install
class Settings:
 def effective(self,schema,key):
  if key=='picture-uri':return self.wallpaper.as_uri()
  return 'shared-reference-fixture'
class ReferenceTests(unittest.TestCase):
 def fixture(self,root):
  home=root/'home';home.mkdir();theme=home/'.themes/shared-reference-fixture';theme.mkdir(parents=True)
  (theme/'real.png').write_bytes(b'pixels');(theme/'alias.png').symlink_to('real.png')
  settings=Settings();settings.wallpaper=theme/'alias.png';return Engine(home,root/'state',settings),theme
 def test_shared_theme_and_nested_wallpaper_copied_once_with_links(self):
  with tempfile.TemporaryDirectory() as td:
   e,theme=self.fixture(Path(td))
   with patch('mintxp.engine.subprocess.run',return_value=subprocess.CompletedProcess([],0,stdout=b'')):
    backup=Path(e.safety_snapshot())
   report=json.loads((backup/'report.json').read_text());self.assertTrue(all(r['saved'] for r in report))
   self.assertEqual(sum(r['path']==str(theme) for r in report),1)
   self.assertFalse(any(r['path']==str(theme/'alias.png') for r in report))
   copy=backup/'files'/str(theme).lstrip('/');self.assertEqual((copy/'real.png').read_bytes(),b'pixels');self.assertTrue((copy/'alias.png').is_symlink());self.assertEqual(os.readlink(copy/'alias.png'),'real.png')
 def test_duplicate_root_symlink_is_preserved(self):
  with tempfile.TemporaryDirectory() as td:
   e,theme=self.fixture(Path(td));target=theme.with_name('actual');theme.rename(target);theme.symlink_to(target.name);e.settings.wallpaper=Path(td)/'wallpaper.png';e.settings.wallpaper.write_bytes(b'wallpaper')
   with patch('mintxp.engine.subprocess.run',return_value=subprocess.CompletedProcess([],0,stdout=b'')):
    backup=Path(e.safety_snapshot())
   copied=backup/'files'/str(theme).lstrip('/');self.assertTrue(copied.is_symlink());self.assertEqual(os.readlink(copied),target.name)
 def test_real_copy_failure_still_blocks_installation(self):
  with tempfile.TemporaryDirectory() as td:
   e,theme=self.fixture(Path(td))
   with patch('mintxp.engine.subprocess.run',return_value=subprocess.CompletedProcess([],0,stdout=b'')),patch('mintxp.engine.shutil.copytree',side_effect=PermissionError('unreadable fixture')):
    with self.assertRaisesRegex(Conflict,'Reference backup incomplete'):e.safety_snapshot()
   self.assertFalse(e.read_current()['installed'])
 def test_backup_failure_happens_before_privileged_changes(self):
  e=Mock();e.progress=None;e.read.return_value=None;e.check.return_value=[];e.safety_snapshot.side_effect=Conflict('backup incomplete');system=Mock()
  with patch('mintxp.install_flow.plan'),patch('mintxp.install_flow.prepare_rescue'):
   with self.assertRaisesRegex(Conflict,'backup incomplete'):install(e,{'boot_install':True},Mock(),system)
  system.install.assert_not_called();e.apply.assert_not_called()
 def test_completed_reference_is_not_repeated_after_system_install(self):
  e=Mock();e.progress=None;e.read.return_value=None;e.check.return_value=[];events=[];e.safety_snapshot.side_effect=lambda:events.append('backup');system=Mock();system.install.side_effect=lambda *args:events.append('system') or 'OK'
  e.apply.side_effect=lambda target,reference:events.append(('desktop',reference)) or 'tx'
  with patch('mintxp.install_flow.plan'),patch('mintxp.install_flow.prepare_rescue'),patch('mintxp.install_flow.summary',return_value={}):install(e,{'boot_install':True},Mock(),system)
  self.assertEqual(events,['backup','system',('desktop',False)])
