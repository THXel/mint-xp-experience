import unittest
from unittest.mock import Mock,patch
from mintxp.install_flow import install

class OverallInstall(unittest.TestCase):
 def run_flow(self,fail=False,desktop_fail=False):
  e=Mock();e.read.return_value=None;e.check.return_value=[];events=[];order=[]
  observer=lambda *args:events.append(args)
  e.progress=observer;e.report=lambda *args:e.progress(*args)
  def repeated_events(stage):
   order.append(stage)
   for phase in ('capture','write','download','verify'):
    for done in (0,1,10):e.report(phase,done,10,stage)
  def desktop(*args):
   repeated_events('desktop')
   if desktop_fail:raise RuntimeError('desktop failed')
   return 'transaction'
  def accessory(key):
   repeated_events(key)
   if fail and key=='minesweeper':raise RuntimeError('download failed')
   return 'OK'
  system=Mock();system.install.side_effect=lambda *args:repeated_events('system') or 'OK'
  addons=Mock();addons.install.side_effect=accessory;e.apply.side_effect=desktop
  with patch('mintxp.install_flow.prepare_rescue'),patch('mintxp.install_flow.plan'),patch('mintxp.install_flow.summary',return_value={}):
   if desktop_fail:
    with self.assertRaisesRegex(RuntimeError,'System undo:'):install(e,{'boot_install':True,'addon_selection':['jspaint']},addons,system)
    result=e.save.call_args.args[1]
   else:result=install(e,{'boot_install':True,'addon_selection':['minesweeper','jspaint','jspaint']},addons,system)
  self.assertIs(e.progress,observer)
  return result,events,order
 def test_overall_never_restarts_and_auth_runs_first(self):
  result,events,order=self.run_flow()
  self.assertEqual(order,['system','desktop','minesweeper','jspaint'])
  self.assertTrue(all(x[0]=='overall' for x in events))
  fractions=[e[1]/e[2] for e in events];self.assertEqual(fractions,sorted(fractions));self.assertEqual(fractions.count(1),1)
  self.assertEqual(result['progress'],{'completed':4,'total':4});self.assertFalse(result['partial'])
 def test_failure_never_reports_full_success(self):
  result,events,order=self.run_flow(fail=True)
  self.assertEqual(order[-1],'jspaint');self.assertTrue(result['partial']);self.assertLess(max(e[1]/e[2] for e in events),1)
  self.assertEqual(result['progress'],{'completed':3,'total':4})
 def test_desktop_failure_retains_system_recovery_details(self):
  result,events,order=self.run_flow(desktop_fail=True)
  self.assertEqual(order,['system','desktop']);self.assertFalse(result['incomplete']);self.assertTrue(result['partial'])
  self.assertEqual([r['ok'] for r in result['steps']],[True,False])
 def test_existing_conflicts_prevent_system_changes(self):
  e=Mock();e.read.return_value=None;e.check.return_value=['changed wallpaper'];system=Mock()
  with self.assertRaisesRegex(Exception,'changed wallpaper'):install(e,{'boot_install':True},Mock(),system)
  system.install.assert_not_called();e.apply.assert_not_called()

 def test_reinstall_does_not_guard_a_completed_old_installation(self):
  e=Mock();e.read.return_value=None;e.read_current.return_value={'installed':False};e.check.side_effect=AssertionError('Retired installation must not guard current preferences');e.progress=None
  with patch('mintxp.install_flow.prepare_rescue'),patch('mintxp.install_flow.plan',return_value={}),patch('mintxp.install_flow.summary',return_value={}):
   install(e,{},Mock(),Mock())
  e.check.assert_not_called();e.safety_snapshot.assert_called_once();e.apply.assert_called_once()
