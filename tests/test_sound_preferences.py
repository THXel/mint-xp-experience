import copy
from unittest.mock import patch
import unittest, test_engine
from mintxp.engine import Conflict

class SoundPreferenceTests(unittest.TestCase):
    setUp=test_engine.RecoveryTests.setUp
    tearDown=test_engine.RecoveryTests.tearDown
    plan=test_engine.RecoveryTests.plan
    keys=('org.cinnamon.desktop.sound/event-sounds','org.gnome.desktop.sound/event-sounds')
    def setup_muted(self):
        plan=self.plan();plan['settings'].update({k:'true' for k in self.keys})
        self.e.apply(plan,False)
        self.base=copy.deepcopy(self.e.read('baseline.json'))
        for k in self.keys:self.fake.set(k,'false')
        return plan
    def test_muted_update_keeps_choice_and_original_baseline(self):
        plan=self.setup_muted();self.assertEqual(len(self.e.check(self.e.read_current())),2)
        self.assertEqual(self.e.check(self.e.read_current(),allow_preferences=True),[])
        tx=self.e.apply(plan,False)
        for k in self.keys:self.assertEqual(self.fake.get(k),'false')
        self.assertEqual(self.e.read('baseline.json'),self.base)
        self.assertEqual(self.e.read('history/'+tx+'.json')['before']['settings'][self.keys[0]],'false')
    def test_muted_uninstall_and_restore(self):
        self.setup_muted()
        with patch.object(self.e,'safety_snapshot'):name=self.e.backup()
        self.e.uninstall()
        for k in self.keys:self.assertIsNone(self.fake.get(k))
        self.e.restore(name)
        for k in self.keys:self.assertEqual(self.fake.get(k),'false')
        self.assertEqual(self.e.read('baseline.json'),self.base)
    def test_muted_still_blocks_file_and_theme_tampering(self):
        self.setup_muted();self.fake.set('test/theme',"'custom'")
        with self.assertRaises(Conflict):self.e.uninstall()
        self.fake.set('test/theme',"'XP'");(self.home/'.config/theme').write_text('personal')
        with self.assertRaises(Conflict):self.e.uninstall()
    def test_failed_update_restores_muted_state(self):
        plan=self.setup_muted();self.fake.fail=True
        with self.assertRaises(OSError):self.e.apply(plan,False)
        for k in self.keys:self.assertEqual(self.fake.get(k),'false')
        self.assertFalse(self.e.read('pending.json'))
