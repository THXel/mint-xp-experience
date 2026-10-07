import importlib.util,json,shlex,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('system_shutdown',ROOT/'system/shutdown.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class ShutdownTests(unittest.TestCase):
 def test_kernel_options_preserved(self):
  value=s.commandline('quiet splash root=UUID=test ro "a=b c" plymouth.splash=old')
  self.assertEqual(shlex.split(value),['quiet','splash','root=UUID=test','ro','a=b c','plymouth.splash=mint-xp-shutdown'])
 def test_native_renderer_and_boot_is_separate(self):
  import configparser
  c=configparser.ConfigParser();c.read(ROOT/'assets/shutdown/mint-xp-shutdown.plymouth')
  self.assertEqual(c['Plymouth Theme']['ModuleName'],'two-step');self.assertEqual(c['shutdown']['UseAnimation'],'false')
  self.assertTrue((ROOT/'assets/shutdown/background.png').is_file());self.assertNotIn('shutdown-splash',(ROOT/'assets/boot/mint-xp-experience.plymouth').read_text())
 def test_shutdown_journal_roundtrip_and_conflicts(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);theme=root/'theme';helper=root/'lib/helper.py';state=root/'state'
   with patch.object(s,'STATE',state),patch.object(s,'THEME',theme),patch.object(s,'HELPER',helper),patch.object(s,'DROPINS',[]),patch.object(s.subprocess,'run'):
    helper.parent.mkdir();helper.write_text('prior')
    previous=os.umask(0o077)
    try:s.apply(ROOT)
    finally:os.umask(previous)
    self.assertEqual(theme.stat().st_mode&0o777,0o755)
    record=json.loads((state/'state.json').read_text());self.assertEqual(record['status'],'applied')
    s.apply(ROOT);file=theme/'background.png';saved=file.read_bytes();file.write_bytes(b'private change')
    with self.assertRaises(RuntimeError):s.undo()
    self.assertEqual(file.read_bytes(),b'private change');file.write_bytes(saved);s.undo();self.assertEqual(helper.read_text(),'prior');self.assertFalse(theme.exists());s.undo()
 def test_failed_write_rolls_back(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);real=s.write;counter=[0]
   def broken(p,data,mode=0o644):
    if p.parent==root/'theme':
     counter[0]+=1
     if counter[0]==2:raise OSError('simulated failure')
    return real(p,data,mode)
   with patch.object(s,'STATE',root/'state'),patch.object(s,'THEME',root/'theme'),patch.object(s,'HELPER',root/'helper'),patch.object(s,'DROPINS',[]),patch.object(s.subprocess,'run'),patch.object(s,'write',broken):
    with self.assertRaises(OSError):s.apply(ROOT)
    self.assertFalse((root/'theme').exists());self.assertEqual(json.loads((root/'state/state.json').read_text())['status'],'restored')
