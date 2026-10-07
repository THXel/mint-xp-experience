"""A completed uninstall relinquishes ownership; active installs stay guarded."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reinstall_appearance',ROOT/'system/appearance.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class ReinstallTests(unittest.TestCase):
 def fixture(self,root):
  state=root/'state';state.mkdir();conf=root/'slick-greeter.conf';conf.write_text('[Greeter]\nbackground=original.png\nshow-a11y=true\n')
  return state,conf
 def apply_fixture(self,root,state,conf):
  from contextlib import ExitStack
  stack=ExitStack();self.addCleanup(stack.close)
  for name,value in {'STATE':state,'CONF':conf,'LOGIN':root/'login','ART':root/'art','THEME':root/'boot'}.items():stack.enter_context(patch.object(a,name,value))
  stack.enter_context(patch.object(a,'objects',return_value={root/'login/gtk-3.0/gtk.css':b'/* test */',root/'art/login.png':b'fixture'}))
  stack.enter_context(patch.object(a,'run'))
  stack.enter_context(patch.object(a.shutil,'disk_usage',return_value=type('Space',(),{'free':10**10})()))
  real=Path.read_text
  stack.enter_context(patch.object(Path,'read_text',lambda p,*args,**kwargs:'ID=linuxmint\nVERSION_ID="22.3"\n' if str(p)=='/etc/os-release' else real(p,*args,**kwargs)))
  return stack
 def test_reinstall_snapshots_current_config_and_preserves_historical_backup(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state,conf=self.fixture(root)
   with self.apply_fixture(root,state,conf):
    first=conf.read_bytes();a.apply(False,True);a.undo()
    changed=b'[Greeter]\nbackground=new-mint.png\nshow-a11y=false\n';conf.write_bytes(changed)
    a.undo();self.assertEqual(conf.read_bytes(),changed)
    a.apply(False,True)
    self.assertIn('show-a11y = true',conf.read_text())
    s=a.state();record=next(r for r in s['files'] if r['path']==str(conf))
    self.assertEqual((state/'backup'/record['backup']).read_bytes(),changed)
    retired=next((state/'retired').iterdir());old=json.loads((retired/'state.json').read_text());r=next(r for r in old['files'] if r['path']==str(conf));self.assertEqual((retired/'backup'/r['backup']).read_bytes(),first)
    a.undo();self.assertEqual(conf.read_bytes(),changed)
 def test_active_install_still_protects_edits(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state,conf=self.fixture(root)
   with self.apply_fixture(root,state,conf):
    a.apply(False,True);conf.write_bytes(b'personal edit')
    with self.assertRaisesRegex(RuntimeError,'later change'):a.apply(False,True)
    with self.assertRaisesRegex(RuntimeError,'later change'):a.undo()
    self.assertEqual(conf.read_bytes(),b'personal edit');self.assertFalse((state/'retired').exists())
 def test_damaged_completed_backup_is_not_discarded(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state,conf=self.fixture(root)
   with self.apply_fixture(root,state,conf):
    a.apply(False,True);a.undo();s=a.state();r=next(r for r in s['files'] if r['before'] is not None);(state/'backup'/r['backup']).write_bytes(b'damaged')
    with self.assertRaisesRegex(RuntimeError,'Damaged backup'):a.apply(False,True)
    self.assertTrue((state/'state.json').exists());self.assertFalse((state/'retired').exists())
 def test_interrupted_journal_is_not_retired(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state,conf=self.fixture(root)
   with self.apply_fixture(root,state,conf):
    for status in ('installing','restoring'):
     a.save({'status':status})
     with self.assertRaisesRegex(RuntimeError,'interrupted'):a.apply(False,True)
     self.assertTrue((state/'state.json').exists());self.assertFalse((state/'retired').exists())
 def test_fresh_install_still_rejects_symlink(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state,conf=self.fixture(root)
   with self.apply_fixture(root,state,conf):
    a.apply(False,True);a.undo();target=root/'private';target.write_text('[Greeter]\n');conf.unlink();conf.symlink_to(target)
    with self.assertRaisesRegex(RuntimeError,'Linked destination'):a.apply(False,True)
    self.assertEqual(target.read_text(),'[Greeter]\n')
