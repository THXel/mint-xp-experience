import importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from mintxp.engine import Engine,Conflict
from mintxp.lifecycle import uninstall_all,status,diagnostic,export_diagnostic,prepare_rescue
from mintxp.session_settings import validated
from test_engine import FakeSettings
ROOT=Path(__file__).resolve().parent.parent
class Bridge:
    def __init__(self,error=None):self.calls=0;self.error=error
    def present(self):return True
    def undo(self):
        self.calls+=1
        if self.error:raise self.error
class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.home=self.root/'home';self.home.mkdir();self.settings=FakeSettings();self.e=Engine(self.home,self.root/'state',self.settings)
        (self.home/'.config').mkdir();(self.home/'.config/theme').write_bytes(b'original')
        self.e.apply({'files':{'.config/theme':self.e.descriptor(b'XP')},'settings':{'test/theme':"'XP'"},'options':{'gtk':True}},False)
    def tearDown(self):self.tmp.cleanup()
    def test_auth_cancel_preserves_user_installation(self):
        bridge=Bridge(Conflict('cancelled'));before=self.e.read_current()
        with self.assertRaises(Conflict):uninstall_all(self.e,bridge)
        self.assertEqual(bridge.calls,1);self.assertEqual(self.e.read_current(),before);self.assertEqual((self.home/'.config/theme').read_bytes(),b'XP');self.assertEqual(self.e.read('combined-uninstall.json')['phase'],'system-step-not-completed')
    def test_changed_file_blocks_before_admin_step(self):
        (self.home/'.config/theme').write_bytes(b'personal');bridge=Bridge()
        with self.assertRaises(Conflict):uninstall_all(self.e,bridge)
        self.assertEqual(bridge.calls,0);self.assertEqual((self.home/'.config/theme').read_bytes(),b'personal')
    def test_bad_backup_blocks_before_admin_step(self):
        desc=self.e.read('baseline.json')['files']['.config/theme'];(self.e.objects/desc['sha256']).write_bytes(b'bad');bridge=Bridge()
        with self.assertRaises(Conflict):uninstall_all(self.e,bridge)
        self.assertEqual(bridge.calls,0)
    def test_combined_uninstall_and_repeat_are_safe(self):
        bridge=Bridge();uninstall_all(self.e,bridge);uninstall_all(self.e,bridge)
        self.assertFalse(self.e.read_current()['installed']);self.assertEqual((self.home/'.config/theme').read_bytes(),b'original');self.assertEqual(self.e.read('combined-uninstall.json')['phase'],'complete')
    def test_user_failure_after_system_can_resume(self):
        bridge=Bridge();self.settings.fail=True
        with self.assertRaises(OSError):uninstall_all(self.e,bridge)
        self.assertEqual(self.e.read('combined-uninstall.json')['phase'],'system-restored');self.assertTrue(self.e.read_current()['installed']);uninstall_all(self.e,bridge);self.assertFalse(self.e.read_current()['installed'])
    def test_lock_covers_system_step(self):
        engine=self.e
        class Locked(Bridge):
            def undo(inner):
                with self.assertRaises(Conflict):
                    with engine.lock():pass
        uninstall_all(self.e,Locked())
    def test_status_reads_changes_without_adding_backup_objects(self):
        count=len(list(self.e.objects.iterdir()));(self.home/'.config/theme').write_bytes(b'changed');self.settings.values['test/theme']="'personal'"
        report=status(self.e);self.assertEqual(report['changed_file_count'],1);self.assertEqual(report['changed_setting_count'],1);self.assertEqual(len(list(self.e.objects.iterdir())),count)
    def test_diagnostic_allowlist_and_no_overwrite_or_symlink(self):
        secret='PRIVATE-CREDENTIAL-DO-NOT-EXPORT';current=self.e.read_current();current['options']['secret']=secret;self.e.save('current.json',current)
        baseline=self.e.read('baseline.json');baseline['created_at']=secret;self.e.save('baseline.json',baseline);self.e.save('combined-uninstall.json',{'phase':secret})
        target=self.root/'report.json';export_diagnostic(self.e,target,secret);data=target.read_text()
        self.assertNotIn(secret,data);self.assertNotIn(str(self.home),data);self.assertNotIn('.config/theme',data);self.assertEqual(target.stat().st_mode&0o777,0o600)
        with self.assertRaises(FileExistsError):export_diagnostic(self.e,target,'0.1.0-preview.4')
        link=self.root/'link';link.symlink_to(target)
        with self.assertRaises(FileExistsError):export_diagnostic(self.e,link,'0.1.0-preview.4')
        self.assertEqual(target.read_text(),data)
    def test_retained_rescue_runs_without_installed_runtime_or_display(self):
        script=prepare_rescue(self.e,ROOT);env=dict(os.environ,HOME=str(self.home),XDG_STATE_HOME=str(self.root/'empty-state'))
        env.pop('DISPLAY',None);env.pop('WAYLAND_DISPLAY',None);env.pop('PYTHONPATH',None)
        result=subprocess.run([sys.executable,'-B',str(script),'check'],cwd=self.root,env=env,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertNotIn('Gtk',(script.parent/'mintxp/rescue.py').read_text())
        self.assertFalse((self.home/'.local/share/mint-xp-experience').exists())
    def test_rescue_protects_linked_destination(self):
        dest=self.e.state/'rescue';dest.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(Conflict):prepare_rescue(self.e,ROOT)
    def test_welcome_validation(self):
        for val in (float('nan'),float('inf'),True,'3',0,9):
            with self.assertRaises(ValueError):validated({'welcome_duration':val})
        self.assertEqual(validated({'welcome_duration':3,'welcome_fade':False,'welcome_monitors':'primary'}),{'duration':3.,'fade':False,'monitors':'primary'})
