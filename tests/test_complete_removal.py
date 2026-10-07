import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from mintxp.engine import Engine,Conflict
from mintxp.removal import complete
from test_engine import FakeSettings
class Apps:
 def __init__(self,fail=False):self.removed=[];self.fail=fail
 def status(self):return {'owned':{'state':'managed','name':'Owned'},'external':{'state':'external','name':'External'}}
 def verify(self,key):
  if self.fail:raise Conflict('changed accessory')
 def remove(self,key):self.removed.append(key)
class Bridge:
 def __init__(self):self.calls=0
 def present(self):return True
 def undo(self):self.calls+=1
class CompleteRemoval(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();r=Path(self.tmp.name);h=r/'home';h.mkdir();self.e=Engine(h,r/'state',FakeSettings());self.e.apply({'files':{'.config/xp':self.e.descriptor(b'xp')},'settings':{},'options':{}},False)
 def tearDown(self):self.tmp.cleanup()
 def test_owned_only_removed_after_restore(self):
  apps=Apps();bridge=Bridge()
  with patch.object(self.e,'safety_snapshot',return_value='fixture'):complete(self.e,addons=apps,bridge=bridge)
  self.assertEqual(apps.removed,['owned']);self.assertFalse(self.e.read_current()['installed']);self.assertEqual(bridge.calls,1)
 def test_accessory_conflict_precedes_admin_and_desktop(self):
  apps=Apps(True);bridge=Bridge()
  with self.assertRaises(Conflict):complete(self.e,addons=apps,bridge=bridge)
  self.assertTrue(self.e.read_current()['installed']);self.assertEqual(bridge.calls,0);self.assertFalse(apps.removed)
 def test_accessories_can_be_kept(self):
  apps=Apps(True);bridge=Bridge()
  with patch.object(self.e,'safety_snapshot',return_value='fixture'):complete(self.e,False,apps,bridge)
  self.assertFalse(apps.removed);self.assertFalse(self.e.read_current()['installed'])
