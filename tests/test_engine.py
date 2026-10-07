import json,os,tempfile,unittest
from pathlib import Path
from mintxp.engine import Engine,Conflict

class FakeSettings:
    def __init__(self):self.values={};self.fail=False
    def get(self,key):return self.values.get(key)
    def set(self,key,val):
        if self.fail:self.fail=False;raise OSError('simulated settings failure')
        self.values[key]=val
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)/'home';self.home.mkdir();self.fake=FakeSettings()
        self.e=Engine(self.home,Path(self.tmp.name)/'state',self.fake)
        for path in ('.local/share','.themes','.config','.local/bin'): (self.home/path).mkdir(parents=True,exist_ok=True)
    def tearDown(self):self.tmp.cleanup()
    def plan(self,text=b'new'):
        return {'files':{'.config/theme':self.e.descriptor(text,0o640),'.local/share/xp/new':self.e.descriptor(b'asset')},'settings':{'test/theme':"'XP'"},'options':{'gtk':True}}
    def test_existing_and_absent_roundtrip_modes_and_defaults(self):
        p=self.home/'.config/theme';p.write_bytes(b'old');p.chmod(0o600)
        self.e.apply(self.plan(),False);self.assertEqual(self.fake.get('test/theme'),"'XP'")
        self.e.uninstall();self.assertEqual(p.read_bytes(),b'old');self.assertEqual(p.stat().st_mode&0o777,0o600)
        self.assertFalse((self.home/'.local/share/xp').exists());self.assertIsNone(self.fake.get('test/theme'))
    def test_later_edit_blocks_entire_uninstall(self):
        self.e.apply(self.plan(),False);p=self.home/'.config/theme';p.write_bytes(b'personal')
        with self.assertRaises(Conflict):self.e.uninstall()
        self.assertTrue((self.home/'.local/share/xp/new').exists());self.assertEqual(self.fake.get('test/theme'),"'XP'")
    def test_updates_never_replace_original(self):
        p=self.home/'.config/theme';p.write_bytes(b'original')
        self.e.apply(self.plan(),False);self.e.apply(self.plan(b'updated'),False);self.e.uninstall();self.assertEqual(p.read_bytes(),b'original')
    def test_deselect_component_restores_just_that_component(self):
        self.e.apply(self.plan(),False);plan=self.plan();del plan['files']['.config/theme'];self.e.apply(plan,False)
        self.assertFalse((self.home/'.config/theme').exists());self.assertTrue((self.home/'.local/share/xp/new').exists())
    def test_failure_after_files_restores_before_state(self):
        p=self.home/'.config/theme';p.write_bytes(b'original');self.fake.fail=True
        with self.assertRaises(OSError):self.e.apply(self.plan(),False)
        self.assertEqual(p.read_bytes(),b'original');self.assertFalse(self.e.read('pending.json'));self.assertFalse(self.e.read_current()['installed'])
    def test_symlink_parent_and_traversal_blocked(self):
        (self.home/'.config/link').symlink_to(self.home/'.local/share',target_is_directory=True)
        for path in ('.config/link/file','../../etc/shadow','/etc/passwd','.config/../file'):
            with self.assertRaises(Conflict):self.e.path(path)
    def test_backup_tampering_blocks_uninstall_before_mutation(self):
        p=self.home/'.config/theme';p.write_bytes(b'original');self.e.apply(self.plan(),False)
        desc=self.e.read('baseline.json')['files']['.config/theme'];(self.e.objects/desc['sha256']).write_bytes(b'broken')
        with self.assertRaises(Conflict):self.e.uninstall()
        self.assertEqual(p.read_bytes(),b'new')
    def test_unrelated_file_is_preserved(self):
        self.e.apply(self.plan(),False);p=self.home/'.local/share/xp/user';p.write_text('keep');self.e.uninstall();self.assertEqual(p.read_text(),'keep')
    def test_crash_recovery_accepts_mixed_before_after(self):
        target=self.plan();before=self.e.capture(target)
        self.e.save('pending.json',{'before':before,'target':target,'previous':self.e.read_current(),'created_dirs':[]})
        self.e.write_record({'files':target['files'],'settings':{}});self.e.recover();self.assertFalse((self.home/'.config/theme').exists())
    def test_crash_recovery_rejects_foreign_change(self):
        target=self.plan();before=self.e.capture(target)
        self.e.save('pending.json',{'before':before,'target':target,'previous':self.e.read_current(),'created_dirs':[]})
        (self.home/'.config/theme').write_bytes(b'foreign')
        with self.assertRaises(Conflict):self.e.recover()
        self.assertEqual((self.home/'.config/theme').read_bytes(),b'foreign')
    def test_exclusive_lock(self):
        with self.e.lock():
            with self.assertRaises(Conflict):
                with self.e.lock():pass
    def test_snapshot_restore_keeps_baseline(self):
        self.e.apply(self.plan(),False);snapshot=self.e.capture(self.e.read_current());snapshot.update(options={},installed=True)
        self.e.save('snapshots/20261004T120000Z-abcdef.json',snapshot);self.e.apply(self.plan(b'v2'),False)
        self.e.restore('20261004T120000Z-abcdef');self.assertEqual((self.home/'.config/theme').read_bytes(),b'new');self.e.uninstall();self.assertFalse((self.home/'.config/theme').exists())
    def test_failed_update_does_not_claim_new_originals(self):
        self.e.apply(self.plan(),False)
        p=self.home/'.config/newly-managed';p.write_bytes(b'original-A')
        desired=self.plan();desired['files']['.config/newly-managed']=self.e.descriptor(b'XP')
        self.fake.fail=True
        with self.assertRaises(OSError):self.e.apply(desired,False)
        self.assertNotIn('.config/newly-managed',self.e.read('baseline.json')['files'])
        p.write_bytes(b'personal-B');self.e.apply(desired,False);self.e.uninstall();self.assertEqual(p.read_bytes(),b'personal-B')
