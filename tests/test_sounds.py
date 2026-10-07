import io,json,os,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch
from mintxp.engine import Engine,Conflict
from mintxp.sounds import PREFIX,NAME,ALIASES,CINNAMON,imported_plan,apply_import,remove_import,verify
from mintxp.components import DEFAULTS,ROOT

def audio():
 out=io.BytesIO()
 with wave.open(out,'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(22050);wav.writeframes(b'\0\0'*2205)
 return out.getvalue()
class Settings:
 def __init__(self):self.values={};self.fail=False
 def get(self,key):return self.values.get(key)
 def literal(self,value):return json.dumps(value)
 def effective(self,schema,key):
  raw=self.get(schema+'/'+key)
  return json.loads(raw) if raw is not None else False if key.endswith(('enabled','sounds')) else ''
 def set(self,key,value):
  if self.fail:self.fail=False;raise OSError('settings write failed')
  self.values[key]=value
class Sounds(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);home=self.root/'home';home.mkdir();self.e=Engine(home,self.root/'state',Settings())
  self.source=self.root/'Personal WAVs';self.source.mkdir()
  for name in set(ALIASES.values())|{x[0] for x in CINNAMON.values()}:(self.source/('Windows XP '+name+'.wav')).write_bytes(audio())
  self.o=dict(DEFAULTS,sound_source=str(self.source),sounds=True)
  self.e.apply({'files':{'.config/keep':self.e.descriptor(b'keep')},'settings':{'other/keep':'true'},'options':{}},False)
  self.backup=patch.object(self.e,'safety_snapshot',return_value='test reference');self.backup.start()
 def tearDown(self):self.backup.stop();self.tmp.cleanup()
 def test_private_import_enabled_choices_and_exact_undo(self):
  self.e.settings.set('org.cinnamon.sounds/minimize-file',json.dumps(str(self.source/'Windows XP Minimize.wav')))
  self.e.settings.set('org.cinnamon.sounds/minimize-enabled','false')
  before=dict(self.e.settings.values);original={p.name:p.read_bytes() for p in self.source.iterdir()}
  r=apply_import(self.e,self.o);self.assertTrue((self.e.state/'snapshots'/f"{r['snapshot']}.json").is_file());self.assertEqual(len(r['aliases']),30)
  self.assertFalse(r['cinnamon']['minimize']['enabled']);self.assertTrue(r['cinnamon']['minimize']['preserved']);self.assertEqual(verify(self.e)['integrity'],'OK')
  self.assertEqual(self.e.settings.effective('org.cinnamon.desktop.sound','theme-name'),NAME)
  remove_import(self.e)
  self.assertEqual({k:v for k,v in self.e.settings.values.items() if v is not None},{k:v for k,v in before.items() if v is not None})
  self.assertEqual((self.e.home/'.config/keep').read_bytes(),b'keep');self.assertEqual({p.name:p.read_bytes() for p in self.source.iterdir()},original)
  self.assertFalse(any(p.is_file() for p in (self.e.home/PREFIX).rglob('*')))
 def test_import_again_after_undo_with_remaining_empty_directories(self):
  apply_import(self.e,self.o);remove_import(self.e)
  apply_import(self.e,self.o);self.assertEqual(verify(self.e)['integrity'],'OK')
  remove_import(self.e);self.assertFalse(any(p.is_file() for p in (self.e.home/PREFIX).rglob('*')))
 def test_source_may_disappear_after_import(self):
  apply_import(self.e,self.o)
  for p in self.source.iterdir():p.unlink()
  self.source.rmdir();cached=imported_plan(self.e,self.o)
  self.assertEqual(len(cached['report']['aliases']),30);self.e.apply(dict(cached,options=self.e.read_current()['options']),False)
  self.assertEqual(verify(self.e)['integrity'],'OK')
 def test_internal_aliases_custom_overrides_and_disabled_events(self):
  stereo=self.source/'stereo';stereo.mkdir();(stereo/'dialog-error.wav').symlink_to('../Windows XP Ding.wav');(stereo/'custom-tone.wav').write_bytes(audio());(stereo/'bell.disabled').write_bytes(b'')
  r=imported_plan(self.e,self.o);self.assertEqual(r['report']['aliases']['dialog-error'],'stereo/dialog-error.wav');self.assertIn('custom-tone',r['report']['aliases'])
  self.assertIn(PREFIX+'stereo/bell.disabled',r['files']);self.assertNotIn(PREFIX+'stereo/bell.wav',r['files'])
  self.assertNotIn('Windows XP Ding.wav',r['report']['unassigned_files'])
 def test_external_and_directory_symlinks_rejected(self):
  link=self.source/'unsafe.wav';link.symlink_to(self.root/'outside.wav');(self.root/'outside.wav').write_bytes(audio())
  with self.assertRaises(Conflict):imported_plan(self.e,self.o)
  link.unlink();link.symlink_to(self.source,target_is_directory=True)
  with self.assertRaises(Conflict):imported_plan(self.e,self.o)
 def test_invalid_and_truncated_wav_do_not_change_installation(self):
  before=(self.e.state/'current.json').read_bytes()
  for data in (b'not audio',audio()[:-20]):
   (self.source/'broken.wav').write_bytes(data)
   with self.assertRaises(Conflict):apply_import(self.e,self.o)
   self.assertEqual((self.e.state/'current.json').read_bytes(),before)
 def test_edited_copy_protected_and_failed_settings_rollback(self):
  before=(self.e.state/'current.json').read_bytes();self.e.settings.fail=True
  with self.assertRaises(OSError):apply_import(self.e,self.o)
  self.assertEqual((self.e.state/'current.json').read_bytes(),before);self.assertFalse(self.e.read('pending.json'))
  apply_import(self.e,self.o);p=self.e.home/(PREFIX+'stereo/bell.wav');p.write_bytes(b'edited')
  with self.assertRaises(Conflict):remove_import(self.e)
  self.assertEqual(p.read_bytes(),b'edited')
 def test_reimport_preserves_disabled_current_selection(self):
  apply_import(self.e,self.o)
  # The installer itself records a disabled choice (external edits remain protected).
  current=self.e.read_current();current['settings']['org.cinnamon.sounds/minimize-enabled']='false';self.e.apply(current,False)
  r=apply_import(self.e,self.o);self.assertFalse(r['cinnamon']['minimize']['enabled']);self.assertTrue(r['cinnamon']['minimize']['preserved'])
 def test_unmanaged_destination_protected(self):
  target=self.e.home/PREFIX;target.mkdir(parents=True);(target/'keep').write_text('personal')
  with self.assertRaises(Conflict):apply_import(self.e,self.o)
  self.assertEqual((target/'keep').read_text(),'personal')
 def test_real_cinnamon_schema_roundtrip(self):
  code='''
import tempfile,wave
from pathlib import Path
from unittest.mock import patch
from mintxp.engine import Engine
from mintxp.sounds import ALIASES,CINNAMON,apply_import,remove_import,verify,settings_keys
from mintxp.components import DEFAULTS
with tempfile.TemporaryDirectory() as d:
 root=Path(d);home=root/'home';home.mkdir();source=root/'sounds';source.mkdir();e=Engine(home,root/'state')
 for stem in set(ALIASES.values())|{v[0] for v in CINNAMON.values()}:
  with wave.open(str(source/('Windows XP '+stem+'.wav')),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(22050);w.writeframes(b'\\0\\0'*50)
 e.apply({'files':{},'settings':{},'options':{}},False);before={k:e.settings.get(k) for k in settings_keys()}
 with patch.object(e,'safety_snapshot',return_value='test'):
  apply_import(e,dict(DEFAULTS,sound_source=str(source)));assert verify(e)['integrity']=='OK';remove_import(e)
 assert {k:e.settings.get(k) for k in settings_keys()}==before
'''
  r=subprocess.run([sys.executable,'-B','-c',code],env=dict(os.environ,GSETTINGS_BACKEND='memory'),cwd=ROOT,capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)

class ExplorerSound(unittest.TestCase):
 def test_no_success_tone_for_failure_cancel_empty_or_disabled(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('xp_event_sound',ROOT/'assets/xp-explorer/event_sound.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with patch.object(module.Gio.Settings,'new') as settings,patch.object(module.Gio.Subprocess,'new') as start:
   settings.return_value.get_boolean.return_value=True
   for args in [('empty-trash',0,False,False),('empty-trash',2,True,False),('empty-trash',2,False,True),('trash',2,False,False)]:self.assertFalse(module.completed_sound(*args))
   start.assert_not_called();self.assertTrue(module.completed_sound('empty-trash',2));start.assert_called_once()
   start.reset_mock();settings.return_value.get_boolean.return_value=False;self.assertFalse(module.completed_sound('empty-trash',2));start.assert_not_called()
