import json,tempfile,unittest
from pathlib import Path
from mintxp.engine import Engine,Conflict
from mintxp.panel_state import APPLETS,NEXT,equivalent
from test_sounds import Settings
class PanelPreferences(unittest.TestCase):
 def test_json_spacing_is_not_a_conflict(self):
  self.assertTrue(equivalent('org.cinnamon/panel-zone-symbolic-icon-sizes',repr('[{"panelId":1,"left":32}]'),repr('[{"panelId": 1, "left": 32}]')))
 def test_uninstall_preserves_moved_recreated_and_added_applets(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);h=root/'home';h.mkdir();s=Settings();e=Engine(h,root/'state',s)
   original=['panel1:left:0:Cinnamenu@json:15','panel1:right:1:calendar@cinnamon.org:13'];s.set(APPLETS,s.literal(original));s.set(NEXT,'28')
   e.apply({'files':{},'settings':{APPLETS:s.literal(original+['panel1:right:0:mintxp-tray@mintxp:28']),NEXT:'29'},'options':{}},False)
   current=['panel1:left:1:Cinnamenu@json:31','panel1:right:4:calendar@cinnamon.org:13','panel1:right:8:mintxp-tray@mintxp:28','panel1:center:0:custom@user:35'];s.set(APPLETS,s.literal(current));s.set(NEXT,'36')
   self.assertFalse(e.check(e.read_current(),True))
   from mintxp.lifecycle import status
   self.assertEqual(status(e)['changed_setting_count'],0);e.uninstall()
   self.assertEqual(s.effective('org.cinnamon','enabled-applets'),[x for x in current if 'mintxp-tray' not in x]);self.assertEqual(s.effective('org.cinnamon','next-applet-id'),36)
 def test_native_menu_uuid_restored_with_current_instance(self):
  from mintxp.panel_state import applets_merge
  self.assertEqual(applets_merge(['panel1:left:0:Cinnamenu@json:0'],['panel1:left:2:Cinnamenu@json:9'],['panel1:left:0:menu@cinnamon.org:0']),['panel1:left:2:menu@cinnamon.org:9'])
 def test_unrelated_setting_and_malformed_panel_remain_protected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);h=root/'home';h.mkdir();s=Settings();e=Engine(h,root/'state',s)
   record={'files':{},'settings':{APPLETS:s.literal([]),'other/theme':'"before"'},'options':{}}
   e.apply(record,False);s.set(APPLETS,'"broken"');s.set('other/theme','"personal"')
   with self.assertRaises(Conflict):e.uninstall()
