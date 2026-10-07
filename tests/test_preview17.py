import importlib.util,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from mintxp.components import ROOT
from mintxp.first_run import automatic_setup

class FirstRun(unittest.TestCase):
 def test_no_root_headless_installed_or_repeat_launch(self):
  e=Mock();e.read_current.return_value={'installed':False};e.read.return_value={}
  with patch('mintxp.first_run.os.geteuid',return_value=0):self.assertEqual(automatic_setup(e),0)
  with patch('mintxp.first_run.os.geteuid',return_value=1000):
   with patch.dict(os.environ,{},clear=True):self.assertEqual(automatic_setup(e),0)
   with patch.dict(os.environ,{'DISPLAY':':99'}):
    e.read_current.return_value={'installed':True};self.assertEqual(automatic_setup(e),0)
    e.read_current.return_value={'installed':False};e.read.return_value={'version':(ROOT/'VERSION').read_text().strip()};self.assertEqual(automatic_setup(e),0)
  e.save.assert_not_called()
 def test_only_local_active_graphical_user_sessions(self):
  spec=importlib.util.spec_from_file_location('autostart',ROOT/'tools/session_autostart.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  valid=dict(Active='yes',Remote='no',Type='x11',Class='user',User='1000')
  self.assertTrue(module.eligible(valid))
  for key,value in [('Active','no'),('Remote','yes'),('Type','tty'),('Class','greeter'),('User','0'),('User','bad')]:self.assertFalse(module.eligible(dict(valid,**{key:value})))
 def test_fresh_all_components_without_optional_games_roundtrip(self):
  code='''
import tempfile
from pathlib import Path
from mintxp.components import DEFAULTS,COMPONENTS,plan
from mintxp.engine import Engine
with tempfile.TemporaryDirectory() as td:
 p=Path(td);home=p/'home';home.mkdir();e=Engine(home,p/'state')
 e.settings.set('org.cinnamon/enabled-applets',e.settings.literal(['panel1:left:0:menu@cinnamon.org:0','panel1:center:0:grouped-window-list@cinnamon.org:1','panel1:right:0:systray@cinnamon.org:2']))
 desired=plan(e,dict(DEFAULTS,**dict.fromkeys(COMPONENTS,True)))
 assert any('applications-merged' in name for name in desired['files'])
 e.apply(desired,False);assert not e.check(e.read_current())
 e.uninstall();assert not list(home.rglob('*'))
'''
  p=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=dict(os.environ,GSETTINGS_BACKEND='memory'),capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stdout+p.stderr)
