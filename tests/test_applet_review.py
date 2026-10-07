import os,sys,subprocess,json,tempfile,unittest
from pathlib import Path
from mintxp.applet_review import inventory,configure,check_review,XP_MENU
from mintxp.engine import Engine,Conflict
from mintxp.components import ROOT
from test_sounds import Settings
class AppletReview(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name);home=root/'home';home.mkdir();self.e=Engine(home,root/'state',Settings())
  self.initial=['panel1:left:0:Cinnamenu@json:15','panel1:right:0:monitor@custom:20','panel1:right:1:calendar@cinnamon.org:21']
  self.e.settings.set('org.cinnamon/enabled-applets',json.dumps(self.initial));self.e.settings.set('org.cinnamon/next-applet-id','22')
 def tearDown(self):self.temp.cleanup()
 def test_inventory_distinguishes_unverified_and_menu(self):
  rows=inventory(self.e,{'menu':True});self.assertEqual([r['id'] for r in rows],['Cinnamenu@json:15','monitor@custom:20']);self.assertEqual(rows[0]['reason'],'applet_menu_reason');self.assertEqual(rows[1]['reason'],'applet_custom_reason')
 def test_keep_all_does_not_replace_existing_menu(self):
  entries,n=configure(self.e,{'menu':True},self.initial,22);self.assertEqual(entries[:-1],self.initial);self.assertIn(XP_MENU,entries[-1]);self.assertEqual(n,23)
 def test_disable_selection_keeps_unselected_and_rejects_forged(self):
  entries,n=configure(self.e,{'menu':True,'disabled_applets':['monitor@custom:20']},self.initial,22);self.assertIn(self.initial[0],entries);self.assertNotIn(self.initial[1],entries)
  with self.assertRaises(Conflict):configure(self.e,{'menu':True,'disabled_applets':['calendar@cinnamon.org:21']},self.initial,22)
 def test_review_detects_panel_changes_before_install(self):
  options={'reviewed_applets':self.initial};check_review(self.e,options);self.e.settings.set('org.cinnamon/enabled-applets','[]')
  with self.assertRaises(Conflict):check_review(self.e,options)
 def test_restoring_disabled_applet_does_not_duplicate_manual_readdition(self):
  from mintxp.panel_state import applets_merge
  self.assertEqual(applets_merge(['panel1:left:0:'+XP_MENU+':22'],['panel1:left:0:'+XP_MENU+':22','panel1:right:8:monitor@custom:30'],['panel1:right:0:monitor@custom:20']),['panel1:right:8:monitor@custom:30'])
 def test_real_schema_disable_restore_and_original_menu_files_preserved(self):
  code='''
from pathlib import Path
import tempfile,json
from mintxp.engine import Engine
from mintxp.components import plan,DEFAULTS,COMPONENTS
from mintxp.applet_review import XP_MENU
with tempfile.TemporaryDirectory() as td:
 home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state')
 old=home/'.local/share/cinnamon/applets/Cinnamenu@json/applet.js';old.parent.mkdir(parents=True);old.write_text('personal menu code')
 config=home/'.config/cinnamon/spices/Cinnamenu@json/15.json';config.parent.mkdir(parents=True);config.write_text('personal preferences')
 before=['panel1:left:0:Cinnamenu@json:15','panel1:right:0:monitor@custom:20','panel1:right:1:calendar@cinnamon.org:21']
 e.settings.set('org.cinnamon/enabled-applets',e.settings.literal(before));e.settings.set('org.cinnamon/next-applet-id','22')
 o=dict(DEFAULTS,**dict.fromkeys(COMPONENTS,False));o.update(menu=True,disabled_applets=['Cinnamenu@json:15','monitor@custom:20'])
 target=plan(e,o);assert str(old.relative_to(home)) not in target['files'];e.apply(target,False)
 live=e.settings.effective('org.cinnamon','enabled-applets');assert before[0] not in live and before[1] not in live and before[2] in live
 assert any(XP_MENU in entry for entry in live)
 # Add a user applet after installation: rollback must retain it too.
 e.settings.set('org.cinnamon/enabled-applets',e.settings.literal(live+['panel1:right:9:extra@user:30']))
 e.settings.set('org.cinnamon/next-applet-id','31')
 e.uninstall();restored=e.settings.effective('org.cinnamon','enabled-applets')
 assert all(entry in restored for entry in before),restored
 assert 'panel1:right:9:extra@user:30' in restored
 assert not any(XP_MENU in entry for entry in restored)
 assert old.read_text()=='personal menu code' and config.read_text()=='personal preferences'
 assert not e.check(e.read_current())
 # A fresh install must use the panel configured AFTER uninstall, not an old baseline.
 fresh=['panel1:left:0:menu@cinnamon.org:40','panel1:right:1:calendar@cinnamon.org:21']
 e.settings.set('org.cinnamon/enabled-applets',e.settings.literal(fresh));e.settings.set('org.cinnamon/next-applet-id','41')
 o['disabled_applets']=[];target=plan(e,o)
 from gi.repository import GLib
 intended=GLib.Variant.parse(None,target['settings']['org.cinnamon/enabled-applets'],None,None).unpack()
 assert fresh[0] in intended and not any('Cinnamenu@json' in x for x in intended),intended
 e.apply(target,False);e.uninstall();assert e.settings.effective('org.cinnamon','enabled-applets')==fresh
'''
  result=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=dict(os.environ,GSETTINGS_BACKEND='memory'),capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
