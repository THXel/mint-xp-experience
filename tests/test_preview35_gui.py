"""Targeted GUI checks use disposable files, private bookmarks and memory settings."""
import os,sys,tempfile,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/xp-explorer'))
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gio,GLib
import explorer
from journal import UndoHistory
from bookmark_store import BookmarkStore
from search_ui import SearchWindow

@unittest.skipUnless(os.environ.get('GSETTINGS_BACKEND')=='memory' and os.environ.get('DISPLAY'),'isolated graphical session required')
class ExplorerGUI35(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.app=Gtk.Application(application_id='org.mintxp.ExplorerTest.x'+uuid.uuid4().hex,flags=Gio.ApplicationFlags.NON_UNIQUE);cls.app.register(None);cls.app.hold()
 @classmethod
 def tearDownClass(cls):cls.app.release()
 def pump(self,seconds=.1):
  until=time.monotonic()+seconds
  while time.monotonic()<until:
   while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
   time.sleep(.005)
 def wait(self,predicate):
  until=time.monotonic()+6
  while not predicate() and time.monotonic()<until:self.pump(.03)
  self.assertTrue(predicate())
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.folder=self.base/'home';self.folder.mkdir();(self.folder/'Downloads').mkdir()
  for i in range(90):(self.folder/f'Test {i:03d}.txt').write_text('example')
  self.env=patch.dict(os.environ,HOME=str(self.folder),XP_EXPLORER_STATE_DIR=str(self.base/'state'));self.env.start()
  self.bookmark=patch.object(explorer,'bookmark_store',BookmarkStore(self.base/'bookmarks'));self.bookmark.start()
  self.computer=patch.object(explorer,'computer_items',return_value={explorer._xp('Festplatten'):[],explorer._xp('Geräte mit Wechselmedien'):[]});self.computer.start()
  self.app.undo_history=UndoHistory();self.app.clip_uris=[]
  self.w=explorer.Explorer(self.app,self.folder.as_uri());self.errors=[];self.w.error=self.errors.append;self.w.info=lambda *args:self.errors.append(args);self.wait(lambda:len(self.w.rows)==91)
 def tearDown(self):
  self.w.destroy();self.pump();self.computer.stop();self.bookmark.stop();self.env.stop();self.tmp.cleanup()
 def test_history_and_zoom_preserve_multiple_selection(self):
  selected={(self.folder/f'Test {n:03d}.txt').as_uri() for n in (60,61)};self.w.select_uris(selected);self.w.icon_scroll.get_vadjustment().set_value(200);self.pump();offset=self.w.icon_scroll.get_vadjustment().get_value()
  self.w.navigate((self.folder/'Downloads').as_uri());self.wait(lambda:not self.w.rows and self.w.content.get_visible_child_name()=='icons');self.w.travel(-1);self.wait(lambda:len(self.w.rows)==91);self.pump()
  self.assertEqual({r['uri'] for r in self.w.selected()},selected);self.assertAlmostEqual(self.w.icon_scroll.get_vadjustment().get_value(),offset,delta=3)
  self.w.zoom(32);self.assertEqual(len(self.w.selected()),2)
 def test_explicit_navigation_does_not_select_duplicate_favorite_branch(self):
  uri=(self.folder/'Downloads').as_uri();explorer.bookmark_store.change(uri,'add');self.w.refresh_bookmarks();self.w.toggle_tree();self.w.folder_pane.anchor=self.w.folder_pane.shortcuts;self.w.navigate(uri)
  def selected_home():
   model,it=self.w.folder_pane.tree.get_selection().get_selected()
   return it is not None and model[it][2]==uri and self.w.folder_pane.root_path(it)==self.w.folder_pane.model.get_path(self.w.folder_pane.home_node).to_string()
  self.wait(selected_home)
 def test_batch_rename_and_ctrl_z_backend(self):
  selected={(self.folder/f'Test {n:03d}.txt').as_uri() for n in (1,2)};self.w.select_uris(selected)
  def accept():
   for d in Gtk.Window.list_toplevels():
    if d.get_transient_for()==self.w and isinstance(d,Gtk.Dialog):d.response(Gtk.ResponseType.OK)
   return False
  GLib.idle_add(accept);self.w.rename();self.wait(lambda:not self.w.busy)
  self.assertTrue((self.folder/'Test 001 (001).txt').exists());self.assertTrue((self.folder/'Test 002 (002).txt').exists());self.w.undo();self.wait(lambda:not self.w.busy);self.assertTrue((self.folder/'Test 001.txt').exists());self.assertFalse(self.errors)
 def test_search_restart_filter_and_containing_folder(self):
  s=SearchWindow(self.w)
  try:
   s.entry.set_text('Test');s.category.set_active_id('documents');s.start();s.entry.set_text('Test 001');s.start();self.wait(lambda:not s.stop_button.get_sensitive());self.assertEqual(len(s.store),1)
   s.tree.get_selection().select_path(Gtk.TreePath.new_from_indices([0]));s.open(True)
   self.wait(lambda:not self.w.directory_loading and len(self.w.rows)==91)
   self.assertEqual(self.w.uri,self.folder.as_uri());self.assertFalse(s.active)
   self.assertEqual({r['uri'] for r in self.w.selected()},{(self.folder/'Test 001.txt').as_uri()})
   s.companion.enable(False);self.assertEqual(s.companion.timer,0)
   self.w.saved_geometry=dict(x=0,y=0,width=800,height=600);self.w.save_geometry()
   from comfort import read_state
   self.assertFalse(read_state()['search_animation'])
  finally:s.destroy()
 def test_failed_transfer_retry_does_not_repeat_success(self):
  first=(self.folder/'Test 001.txt').as_uri();second=(self.folder/'Test 002.txt').as_uri();calls=[]
  def action(uri,cancel):
   calls.append(uri)
   if uri==first and calls.count(first)==1:raise OSError('temporary fixture error')
  with patch.object(Gtk.MessageDialog,'run',return_value=Gtk.ResponseType.OK):
   self.w.operation('Fixture transfer',[first,second],action,kind='copy');self.wait(lambda:not self.w.busy)
  self.assertEqual(calls.count(first),2);self.assertEqual(calls.count(second),1);self.assertFalse(self.errors)
