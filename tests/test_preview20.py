import unittest,wave,struct,json,hashlib
from mintxp.components import ROOT
class OriginalAssets(unittest.TestCase):
 def test_no_bundled_audio(self):
  self.assertFalse(list((ROOT/'assets').rglob('*.wav')))

 def test_native_size_icons_present(self):
  for size in (16,24,32,48):
   for context,name in [('places','folder'),('places','user-trash'),('devices','computer'),('apps','mintxp-paint')]:self.assertTrue((ROOT/'assets/icons'/str(size)/context/(name+'.png')).is_file())

 def test_deselected_icons_do_not_apply_remembered_import(self):
  import tempfile
  from pathlib import Path
  from mintxp.engine import Engine
  from mintxp.components import plan,DEFAULTS,COMPONENTS
  from test_engine import FakeSettings
  with tempfile.TemporaryDirectory() as td:
   home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state',FakeSettings())
   options=dict(DEFAULTS,**dict.fromkeys(COMPONENTS,False));options['icon_import']=str(home/'unavailable-previous-import')
   result=plan(e,options)
   self.assertFalse(any('icon-theme' in k for k in result['settings']))
   self.assertFalse(any(k.startswith('.local/share/icons/Mint-XP-Experience-Imported') for k in result['files']))
