import subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from mintxp.audition import Audition
from mintxp.completion import summary
from mintxp.engine import Engine
from test_sounds import Settings

class Completion(unittest.TestCase):
 def test_committed_selection_backup_and_relogin(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'home').mkdir();e=Engine(p/'home',p/'state',Settings())
   plan={'files':{},'settings':{'org.cinnamon.theme/name':'"Theme"'},'options':{'shell':True}}
   tx=e.apply(plan,False);r=summary(e,tx);self.assertEqual(r['enabled'],['shell']);self.assertIn('sounds',r['disabled']);self.assertEqual(r['backup_path'],str(e.state));self.assertTrue(r['relogin_recommended'])
   tx=e.apply(plan,False);self.assertFalse(summary(e,tx)['relogin_recommended'])
   tx=e.uninstall()
   with self.assertRaises(ValueError):summary(e,tx)
 def test_applet_file_update_recommends_relogin(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'home').mkdir();e=Engine(p/'home',p/'state',Settings());plan={'files':{'.local/share/cinnamon/applets/demo/applet.js':e.descriptor(b'first')},'settings':{},'options':{'menu':True}}
   tx=e.apply(plan,False);self.assertTrue(summary(e,tx)['relogin_recommended'])
   tx=e.apply(plan,False);self.assertFalse(summary(e,tx)['relogin_recommended'])
   plan['files']['.local/share/cinnamon/applets/demo/applet.js']=e.descriptor(b'updated');tx=e.apply(plan,False);self.assertTrue(summary(e,tx)['relogin_recommended'])
 def test_failed_transaction_has_no_success_summary(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'home').mkdir();e=Engine(p/'home',p/'state',Settings())
   with self.assertRaises(ValueError):summary(e,'missing')

class SoundPreview(unittest.TestCase):
 def test_switch_cancel_cleanup_and_no_settings_write(self):
  proc=Mock();proc.poll.return_value=None
  with patch('mintxp.audition.subprocess.Popen',return_value=proc) as popen:
   a=Audition();a.play(b'validated PCM fixture');first=Path(a.directory.name);self.assertTrue(first.is_dir());self.assertIsNone(a.poll());a.play(b'second');self.assertFalse(first.exists());proc.terminate.assert_called_once();second=Path(a.directory.name);a.stop();self.assertFalse(second.exists());self.assertIsNone(a.process);self.assertEqual(popen.call_args.args[0][0],'canberra-gtk-play')
 def test_playback_failure_cleans_temporary_data(self):
  with patch('mintxp.audition.subprocess.Popen',side_effect=OSError('missing')):
   a=Audition()
   with self.assertRaises(OSError):a.play(b'data')
   self.assertIsNone(a.directory)
