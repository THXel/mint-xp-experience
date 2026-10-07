import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from mintxp.engine import Engine,Conflict
from mintxp import mime_state as m
from test_engine import FakeSettings
class MimePreferences(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.home=self.root/'home';self.home.mkdir();self.e=Engine(self.home,self.root/'state',FakeSettings());self.p=self.home/m.REL;self.p.parent.mkdir()
 def tearDown(self):self.tmp.cleanup()
 def install(self):
  data=self.p.read_bytes() if self.p.exists() else b''
  plan={'files':{m.REL:self.e.descriptor(m.replace(data,m.EXPLORER+';'),0o600),'.config/xp':self.e.descriptor(b'xp')},'settings':{},'options':{'default_manager':True}}
  self.e.apply(plan,False);return plan
 def test_original_defaults_comments_and_mode_roundtrip(self):
  original=b'# my preferences\n[Default Applications]\ninode/directory=nemo.desktop;\ntext/plain=editor.desktop;\n';self.p.write_bytes(original);self.p.chmod(0o600)
  self.install();self.e.uninstall();self.assertEqual(self.p.read_bytes(),original);self.assertEqual(self.p.stat().st_mode&0o777,0o600)
 def test_new_file_removed_when_no_personal_data_added(self):
  self.install();self.e.uninstall();self.assertFalse(self.p.exists())
 def test_later_unrelated_changes_survive_update_and_uninstall(self):
  self.p.write_text('[Default Applications]\ninode/directory=nemo.desktop;\ntext/plain=old.desktop;\n');plan=self.install()
  self.p.write_text(self.p.read_text().replace('old.desktop','new.desktop')+'\n[Added Associations]\napplication/pdf=reader.desktop;\n')
  self.assertFalse(self.e.check(self.e.read_current(),allow_preferences=True));self.e.apply(plan,False);self.e.uninstall()
  self.assertEqual(m.directory(self.p.read_bytes()),'nemo.desktop;');self.assertIn('text/plain=new.desktop;',self.p.read_text());self.assertIn('application/pdf=reader.desktop;',self.p.read_text())
 def test_user_folder_choice_survives_media_update_and_uninstall(self):
  self.install();self.p.write_bytes(m.replace(self.p.read_bytes(),'other.desktop;'));self.e.apply(self.e.read_current(),False);self.e.uninstall();self.assertEqual(m.directory(self.p.read_bytes()),'other.desktop;')
 def test_user_removed_file_is_preserved(self):
  self.install();self.p.unlink();self.e.uninstall();self.assertFalse(self.p.exists())
 def test_external_data_in_created_file_survives_uninstall(self):
  self.install();self.p.write_text(self.p.read_text()+'text/plain=editor.desktop;\n');self.e.uninstall();self.assertIsNone(m.directory(self.p.read_bytes()));self.assertIn('editor.desktop',self.p.read_text())
 def test_duplicate_entries_and_symlinks_still_block(self):
  self.install();self.p.write_text('[Default Applications]\ninode/directory=a;\ninode/directory=b;\n')
  with self.assertRaises(Conflict):self.e.uninstall()
  self.assertTrue((self.home/'.config/xp').exists());self.p.unlink();other=self.home/'other';other.write_text('untouched');self.p.symlink_to(other)
  with self.assertRaises(Conflict):self.e.uninstall()
  self.assertEqual(other.read_text(),'untouched')
 def test_restore_keeps_later_personal_associations(self):
  self.install()
  with patch.object(self.e,'safety_snapshot',return_value='fixture'):name=self.e.backup(reason='media')
  self.p.write_text(self.p.read_text()+'text/plain=editor.desktop;\n');self.e.restore(name);self.assertIn('editor.desktop',self.p.read_text());self.assertEqual(self.e.read('snapshots/'+name+'.json')['reason'],'media')
 def test_failure_rolls_back_exact_actual_file(self):
  self.install();self.p.write_text(self.p.read_text()+'text/plain=editor.desktop;\n');before=self.p.read_bytes();plan=self.e.read_current();plan['settings']={'test/theme':"'new'"};self.e.settings.fail=True
  with self.assertRaises(OSError):self.e.apply(plan,False)
  self.assertEqual(self.p.read_bytes(),before);self.assertIsNone(self.e.read('pending.json'))

 def test_later_user_choice_can_be_explicitly_replaced_again(self):
  self.install();self.p.write_bytes(m.replace(self.p.read_bytes(),'other.desktop;'));self.e.apply(self.e.read_current(),False)
  self.assertTrue(self.e.read_current()['mime_user_choice']);self.install();self.assertEqual(m.directory(self.p.read_bytes()),m.EXPLORER+';')
 def test_concurrent_change_during_capture_blocks_before_write(self):
  self.install();capture=self.e.capture
  def changed(target):
   self.p.write_text(self.p.read_text()+'text/plain=concurrent.desktop;\n');return capture(target)
  with patch.object(self.e,'capture',side_effect=changed):
   with self.assertRaisesRegex(Conflict,'during review'):self.e.uninstall()
  self.assertTrue(self.e.read_current()['installed']);self.assertIn('concurrent.desktop',self.p.read_text())

 def test_duplicate_unrelated_application_entries_are_preserved_verbatim(self):
  self.install();self.p.write_text(self.p.read_text()+'x-scheme-handler/example=one.desktop;\nx-scheme-handler/example=two.desktop;\n')
  self.e.uninstall();self.assertIn('x-scheme-handler/example=one.desktop;\nx-scheme-handler/example=two.desktop;\n',self.p.read_text())
