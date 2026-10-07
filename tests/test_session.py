import configparser,importlib.util,tempfile,unittest,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('appearance',ROOT/'system/appearance.py');appearance=importlib.util.module_from_spec(spec);spec.loader.exec_module(appearance)
class SessionTests(unittest.TestCase):
 def test_greeter_preserves_unrelated_values(self):
  value=appearance.config('[Greeter]\nshow-a11y=true\nicon-theme-name=custom\n','Greeter',{'background':'test.png'})
  c=configparser.ConfigParser();c.read_string(value.decode());self.assertEqual(c['Greeter']['icon-theme-name'],'custom');self.assertEqual(c['Greeter']['show-a11y'],'true')
 def test_boot_uses_native_dialog_renderer(self):
  c=configparser.ConfigParser();c.read(ROOT/'assets/boot/mint-xp-experience.plymouth');self.assertEqual(c['Plymouth Theme']['ModuleName'],'two-step');self.assertIn('updates',c)
  frames=list((ROOT/'assets/boot').glob('throbber-*.png'));self.assertEqual(len(frames),48);self.assertGreater(len({p.read_bytes() for p in frames}),30)
 def test_user_install_welcome_roundtrip(self):
  from mintxp.engine import Engine
  from mintxp.components import plan,DEFAULTS
  from test_engine import FakeSettings
  with tempfile.TemporaryDirectory() as td:
   home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state',FakeSettings());o={k:False for k,v in DEFAULTS.items() if isinstance(v,bool)};o['welcome_screen']=True;e.apply(plan(e,o),False)
   p=home/'.config/autostart/mintxp-welcome.desktop';self.assertTrue(p.exists());self.assertIn('NoDisplay=true',p.read_text());self.assertTrue((home/'.local/share/mint-xp-welcome/welcome.py').exists());e.uninstall();self.assertFalse(p.exists())
 def test_system_restore_protects_later_edits(self):
  old_state=appearance.STATE
  try:
   with tempfile.TemporaryDirectory() as td:
    root=Path(td);appearance.STATE=root/'state';appearance.STATE.mkdir();(appearance.STATE/'backup').mkdir();p=root/'config';p.write_bytes(b'after');(appearance.STATE/'backup/0').write_bytes(b'before')
    r={'path':str(p),'backup':'0','before':hashlib.sha256(b'before').hexdigest(),'after':hashlib.sha256(b'after').hexdigest(),'mode':0o640};s={'status':'applied','files':[r],'boot':False,'created_dirs':[]};appearance.save(s)
    p.write_bytes(b'later')
    with self.assertRaises(RuntimeError):appearance.undo()
    self.assertEqual(p.read_bytes(),b'later');p.write_bytes(b'after');appearance.undo();self.assertEqual(p.read_bytes(),b'before');self.assertEqual(p.stat().st_mode&0o777,0o640);appearance.undo()
  finally:appearance.STATE=old_state
