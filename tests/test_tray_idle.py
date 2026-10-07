import shutil,subprocess,unittest
from mintxp.components import ROOT
class TrayInactivity(unittest.TestCase):
 def run_js(self,assertions):
  runtime=shutil.which('cjs') or shutil.which('gjs')
  if not runtime:self.skipTest('CJS/GJS not available')
  code='var module={exports:{}};\n'+(ROOT/'assets/tray/idle.js').read_text()+'\nconst Clock=module.exports.IdleCollapse; function check(v){if(!v)throw Error("Inactivity policy failed");}\n'+assertions
  p=subprocess.run([runtime,'-c',code],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
 def test_ten_seconds_and_interaction_restart(self):
  self.run_js('''const c=new Clock(0);check(!c.due(9999,true,false));check(c.due(10000,true,false));
  c.touch(18000);check(!c.due(27999,true,false));check(c.due(28000,true,false));''')
 def test_menu_drag_and_always_open_start_a_fresh_interval(self):
  self.run_js('''const c=new Clock(0);
  for(let now=0;now<=25000;now+=250)check(!c.due(now,true,true));
  check(!c.due(34999,true,false));check(c.due(35000,true,false));
  check(!c.due(80000,false,false));check(!c.due(89999,true,false));check(c.due(90000,true,false));''')
