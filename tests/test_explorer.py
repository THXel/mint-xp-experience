import tempfile,unittest,uuid,time,os,sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"assets/xp-explorer"))
from pathlib import Path
from core import *
from journal import UndoHistory
from network import server_uri,NetworkActions
from unittest.mock import Mock,patch
class Audit(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory(prefix='xp-audit-',dir=Path.cwd());self.root=Path(self.temp.name)
 def tearDown(self):
  # Only remove trash entries belonging to this test's unique directory.
  for row in (listing('trash:///',True) if os.environ.get('MINTXP_TEST_TRASH')=='1' else []):
   if row.get('original') and str(row['original']).startswith(str(self.root)+'/'):delete_item(row['uri'])
  self.temp.cleanup()
 def test_delete_directory_does_not_follow_symlinks(self):
  protected=self.root/'keep';protected.mkdir();(protected/'file').write_text('keep')
  target=self.root/'delete';target.mkdir();(target/'link').symlink_to(protected,target_is_directory=True);(target/'file').write_text('gone')
  delete_item(str(target));self.assertFalse(target.exists());self.assertEqual((protected/'file').read_text(),'keep')
 def test_delete_root_is_rejected(self):
  for uri in ['file:///','trash:///','network:///','computer:///']:
   with self.assertRaises(ValueError):delete_item(uri)
 @unittest.skipUnless(os.environ.get("MINTXP_TEST_TRASH")=="1", "Needs an explicit desktop GVfs trash test session")
 def test_trash_folder_restore_and_permanent_delete(self):
  p=self.root/'folder';p.mkdir();(p/'file').write_text('restore');uri=trash_with_location(str(p));self.assertTrue(uri)
  j=UndoHistory();self.assertTrue(j.remember(str(p),uri));j.undo();self.assertEqual((p/'file').read_text(),'restore')
  uri=trash_with_location(str(p));delete_item(uri);self.assertFalse(file_for(uri).query_exists(None))
 def test_computer_classifies_optical_usb_and_removable_media(self):
  import explorer
  nodes=[{'name':'sda','type':'disk','model':'Fixed','tran':'sata','rm':False,'children':[{'name':'sda1','fstype':'ext4','mountpoints':['/']}]},
         {'name':'sdb','type':'disk','tran':'usb','rm':False,'children':[{'name':'sdb1','fstype':'ext4','mountpoints':['/media/usb']}]},
         {'name':'mmcblk0','type':'disk','rm':True,'children':[{'name':'mmcblk0p1','fstype':'vfat','mountpoints':['/media/card']}]},
         {'name':'sr0','type':'rom','tran':'ata','rm':True,'fstype':'iso9660','mountpoints':['/media/disc']}]
  with patch('explorer.subprocess.check_output',return_value=__import__('json').dumps({'blockdevices':nodes}).encode()),patch('explorer.usage',return_value=None),patch('explorer.bookmarks',return_value=[]):
   groups=explorer.computer_items()
  disks=groups[explorer._xp('Festplatten')];media=groups[explorer._xp('Geräte mit Wechselmedien')]
  self.assertEqual([r['uri'] for r in disks],['file:///'])
  self.assertEqual({r['uri'] for r in media},{'file:///media/usb','file:///media/card','file:///media/disc'})
  self.assertEqual(next(r['icon'] for r in media if r['uri'].endswith('/disc')),'drive-optical')
 def test_copy_batch_undo(self):
  j=UndoHistory()
  with j.batch():
   for name in ('one','two'):
    p=self.root/name;p.write_text(name);j.remember_created(p.as_uri())
  self.assertEqual(len(j.items),1);j.undo();self.assertFalse((self.root/'one').exists());self.assertFalse((self.root/'two').exists())
 def test_batch_changed_file_stops_all_undo(self):
  j=UndoHistory()
  with j.batch():
   for name in ('one','two'):
    p=self.root/name;p.write_text(name);j.remember_created(p.as_uri())
  (self.root/'one').write_text('new data')
  with self.assertRaises(ValueError):j.undo()
  self.assertTrue((self.root/'two').exists())
 def test_rename_after_batch_undo_chain(self):
  j=UndoHistory()
  with j.batch():
   for name in ('one','two'):
    p=self.root/name;p.write_text(name);j.remember_created(p.as_uri())
  before=j.prepare((self.root/'two').as_uri());new=rename_item(str(self.root/'two'),'three');j.remember((self.root/'two').as_uri(),new,before=before)
  j.undo();j.undo();self.assertFalse((self.root/'one').exists())
 @unittest.skipUnless(os.environ.get("MINTXP_TEST_TRASH")=="1", "Needs an explicit desktop GVfs trash test session")
 def test_restored_file_undo_returns_to_trash(self):
  p=self.root/'restored';p.write_text('keep');uri=trash_with_location(p.as_uri());move_item(uri,p.as_uri())
  j=UndoHistory();self.assertTrue(j.remember_created(p.as_uri(),kind='restored'));j.undo();self.assertFalse(p.exists())
  end=time.monotonic()+2
  while not any(r.get('original')==str(p) for r in listing('trash:///',True)) and time.monotonic()<end:time.sleep(.05)
  self.assertTrue(any(r.get('original')==str(p) for r in listing('trash:///',True)))
 @unittest.skipUnless(os.environ.get("MINTXP_TEST_TRASH")=="1", "Needs an explicit desktop GVfs trash test session")
 def test_fast_retrash_finds_same_reused_uri(self):
  p=self.root/'fast';p.write_text('keep');uri=trash_with_location(p.as_uri());move_item(uri,p.as_uri());again=trash_with_location(p.as_uri());self.assertTrue(again);self.assertEqual(file_for(again).load_contents(None)[1],b'keep')
 def test_mount_navigation_race_ignores_old_callback(self):
  owner=Mock();owner.generation=1;owner.mount_generation=None;owner.nav_cancel=Gio.Cancellable();owner.alive=True
  first,second=Mock(),Mock()
  with patch('network.Gtk.MountOperation'),patch('network.Gio.File.new_for_uri',side_effect=[first,second]):
   NetworkActions.mount_location(owner,'smb://first/share');old_done=first.mount_enclosing_volume.call_args.args[-1]
   owner.nav_cancel.cancel();owner.nav_cancel=Gio.Cancellable();owner.generation=2
   NetworkActions.mount_location(owner,'smb://second/share');new_done=second.mount_enclosing_volume.call_args.args[-1]
   old_done(first,None);self.assertEqual(owner.mount_generation,2);owner.navigate.assert_not_called()
   new_done(second,None);owner.navigate.assert_called_once_with('smb://second/share',False,_mount_retry=True)
 def test_server_uri_and_credentials(self):
  self.assertEqual(server_uri(r'\\server\freigabe\Ein Ordner'),'smb://server/freigabe/Ein%20Ordner')
  self.assertEqual(server_uri('sftp://user@server:2222/path'),'sftp://user@server:2222/path')
  for value in ('smb://user:test-password@server/share','file:///etc','smb://','sftp://server:99999/','smb://server/path?query=x'):
   with self.assertRaises(ValueError):server_uri(value)
if __name__=='__main__':unittest.main(verbosity=2)

class LauncherRouting(unittest.TestCase):
 def test_home_fallback_and_explicit_paths(self):
  import explorer
  class Options:
   def contains(self,key):return key in ('tree','home')
  command=Mock();command.get_options_dict.return_value=Options();command.get_arguments.return_value=['explorer','--tree','--home']
  app=Mock();explorer.Application.do_command_line(app,command)
  app.window.assert_called_once_with(Path.home().as_uri(),True)
  app.reset_mock();command.get_arguments.return_value=['explorer','--tree','--home','/tmp/chosen folder']
  command.create_file_for_arg.return_value.get_uri.return_value='file:///tmp/chosen%20folder'
  explorer.Application.do_command_line(app,command);app.window.assert_called_once_with('file:///tmp/chosen%20folder',True)
  app.reset_mock();command.get_arguments.return_value=['explorer','--tree','--home','--','--home']
  explorer.Application.do_command_line(app,command);command.create_file_for_arg.assert_called_with('--home')
