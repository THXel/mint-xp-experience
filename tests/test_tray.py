import os,subprocess,sys,unittest
from mintxp.tray_plan import add_tray,UUID
from mintxp.engine import Conflict
from mintxp.components import ROOT
class Tray(unittest.TestCase):
    def test_keeps_existing_positions_and_avoids_ids(self):
        before=['panel1:left:0:menu@cinnamon.org:4','panel1:right:0:xapp-status@cinnamon.org:23','panel1:right:4:calendar@cinnamon.org:9']
        after,n=add_tray(before,12)
        self.assertEqual(after[:-1],before);self.assertEqual(after[-1],f'panel1:right:-1:{UUID}:24');self.assertEqual(n,25)
        self.assertEqual(add_tray(after,n),(after,n))
    def test_ambiguous_panel_is_rejected(self):
        with self.assertRaises(Conflict):add_tray(['panel1:right:0:xapp-status@cinnamon.org:1','panel2:right:0:systray@cinnamon.org:2'],3)
    def test_shared_menu_tray_roundtrip(self):
        code='''
import tempfile
from pathlib import Path
from mintxp.engine import Engine
from mintxp.components import plan,DEFAULTS,COMPONENTS
with tempfile.TemporaryDirectory() as td:
 home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state')
 initial=['panel1:left:0:menu@cinnamon.org:0','panel1:right:0:xapp-status@cinnamon.org:1']
 e.settings.set('org.cinnamon/enabled-applets',e.settings.literal(initial));e.settings.set('org.cinnamon/next-applet-id','7')
 o=dict(DEFAULTS,**{k:False for k in COMPONENTS})
 for menu,tray in [(True,True),(True,False),(False,True),(False,False),(True,True)]:
  e.apply(plan(e,dict(o,menu=menu,tray=tray)),False)
  current=e.settings.effective('org.cinnamon','enabled-applets')
  assert any(':mintxp-menu@mintxp:' in x for x in current)==menu,current
  assert any(':mintxp-tray@mintxp:' in x for x in current)==tray,current
  assert initial[1] in current
  assert e.settings.effective('org.cinnamon','next-applet-id')>max(int(x.split(':')[4]) for x in current)
  assert not e.check(e.read_current())
 e.uninstall()
 assert e.settings.effective('org.cinnamon','enabled-applets')==initial
 assert e.settings.effective('org.cinnamon','next-applet-id')==7
 assert not list(home.rglob('*'))
'''
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=dict(os.environ,GSETTINGS_BACKEND='memory'),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_order_policy_survives_missing_apps_and_pid_changes(self):
        import shutil
        js=shutil.which('cjs') or shutil.which('gjs')
        if not js:self.skipTest('CJS/GJS not available')
        logic=(ROOT/'assets/tray/logic.js').read_text()
        script='var module={exports:{}};\n'+logic+'''
const p=module.exports;function check(x){if(!x)throw Error('tray order invariant');}
const order=p.movedOrder(['offline','b','a'],['a','b','new'],'new','b');
check(JSON.stringify(order)===JSON.stringify(['offline','new','b','a']));
check(JSON.stringify(p.ordered([{key:'a'},{key:'new'},{key:'b'}],order).map(i=>i.key))==='["new","b","a"]');
check(p.stableName('org.freedesktop.statusnotifieritem-10-1','app')===p.stableName('org.freedesktop.statusnotifieritem-900-2','app'));
check(!p.shouldCollapse('nyxie',['nyxie'],false,false,false));
check(p.shouldCollapse('nyxie',[],false,false,false));
check(!p.shouldCollapse('nyxie',[],true,false,false));
'''
        result=subprocess.run([js,'-c',script],text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
