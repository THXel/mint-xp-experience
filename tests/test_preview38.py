"""Do not resurrect old baseline applets on an otherwise unchanged upgrade."""
import os,subprocess,sys,unittest
from mintxp.components import ROOT

class AppletUpgrade(unittest.TestCase):
 def test_upgrade_preserves_absent_menu_and_explicit_restore(self):
  code=r"""
import tempfile
from pathlib import Path
from mintxp.engine import Engine
from mintxp.components import DEFAULTS,COMPONENTS,plan
from mintxp.panel_state import APPLETS,NEXT
from mintxp.tray_plan import original_setting
base=['panel1:left:1:menu@cinnamon.org:29','panel1:center:0:grouped-window-list@cinnamon.org:2','panel1:right:1:systray@cinnamon.org:3']
xp='panel1:left:0:mintxp-menu@mintxp:30'
for explicit in (False,True):
 with tempfile.TemporaryDirectory() as td:
  home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state')
  e.settings.set(APPLETS,e.settings.literal(base));e.settings.set(NEXT,'30')
  previous=base[1:]+[xp]
  options=dict(DEFAULTS,**dict.fromkeys(COMPONENTS,False));options.update(menu=True,disabled_applets=['menu@cinnamon.org:29'] if explicit else [])
  e.apply({'files':{},'settings':{APPLETS:e.settings.literal(previous),NEXT:'31'},'options':options},False)
  desired=original_setting(e,'org.cinnamon','enabled-applets')
  assert (base[0] in desired)==explicit,desired
  # Rechecking the old disabled menu restores it, but an absent unowned menu
  # stays absent. Added custom applets must survive either branch.
  live=previous+['panel1:left:4:custom@user:42'];e.settings.set(APPLETS,e.settings.literal(live));e.settings.set(NEXT,'43')
  options['disabled_applets']=[];e.apply(plan(e,options),False)
  result=e.settings.effective('org.cinnamon','enabled-applets')
  assert (base[0] in result)==explicit,result
  assert live[-1] in result and xp in result,result
  assert len([x for x in result if ':mintxp-menu@mintxp:' in x])==1
  # A second unchanged upgrade must also preserve the user's new applet.
  e.apply(plan(e,options),False)
  assert live[-1] in e.settings.effective('org.cinnamon','enabled-applets')
  # Baseline remains immutable; complete uninstall restores its original menu.
  e.uninstall();result=e.settings.effective('org.cinnamon','enabled-applets')
  assert base[0] in result and live[-1] in result and xp not in result,result
"""
  run=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=dict(os.environ,GSETTINGS_BACKEND='memory'),capture_output=True,text=True)
  self.assertEqual(run.returncode,0,run.stdout+run.stderr)
