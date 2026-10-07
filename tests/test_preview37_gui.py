"""Search is embedded: navigation, cancellation and hidden selection isolation."""
import os,time,unittest
from unittest.mock import patch
import test_preview35_gui as base
from gi.repository import Gtk,Gdk,GLib

@unittest.skipUnless(os.environ.get('DISPLAY') and os.environ.get('GSETTINGS_BACKEND')=='memory','isolated graphical session required')
class EmbeddedSearch(unittest.TestCase):
 setUpClass=classmethod(base.ExplorerGUI35.setUpClass.__func__)
 tearDownClass=classmethod(base.ExplorerGUI35.tearDownClass.__func__)
 setUp=base.ExplorerGUI35.setUp
 tearDown=base.ExplorerGUI35.tearDown
 pump=base.ExplorerGUI35.pump
 wait=base.ExplorerGUI35.wait
 def test_toolbar_embeds_and_restores_folder_selection(self):
  chosen=(self.folder/'Test 003.txt').as_uri();self.w.select_uris({chosen});before=len([w for w in Gtk.Window.list_toplevels() if w.get_visible() and w.get_window_type()==Gtk.WindowType.TOPLEVEL]);self.w.search_btn.clicked();s=self.w.search_window;self.pump()
  self.assertEqual(len([w for w in Gtk.Window.list_toplevels() if w.get_visible() and w.get_window_type()==Gtk.WindowType.TOPLEVEL]),before);self.assertFalse(isinstance(s,Gtk.Window));self.assertEqual(self.w.side_stack.get_visible_child_name(),'search');self.assertEqual(self.w.content.get_visible_child_name(),'search');self.assertEqual(s.cards.get_visible_child_name(),'welcome');self.assertFalse(self.w.selected())
  s.choose_category('documents');s.entry.set_text('Test 003');s.start();self.wait(lambda:not s.stop_button.get_sensitive());self.assertEqual(len(s.store),1);self.w.search_btn.clicked();self.wait(lambda:not self.w.directory_loading);self.assertFalse(s.active);self.assertEqual({r['uri'] for r in self.w.selected()},{chosen})
 def test_folder_button_and_back_restore_in_same_window(self):
  self.w.recursive_search();self.w.toggle_tree();self.wait(lambda:not self.w.directory_loading);self.assertTrue(self.w.tree_mode);self.assertEqual(self.w.side_stack.get_visible_child_name(),'folders');self.w.recursive_search();self.w.travel(-1);self.wait(lambda:not self.w.directory_loading);self.assertEqual(self.w.uri,self.folder.as_uri());self.assertEqual(self.w.side_stack.get_visible_child_name(),'folders')
 def test_containing_folder_reveals_nested_result_without_new_window(self):
  p=self.folder/'Downloads/Needle.txt';p.write_text('fixture');self.w.recursive_search();s=self.w.search_window;s.entry.set_text('Needle');s.start();self.wait(lambda:not s.stop_button.get_sensitive());s.tree.get_selection().select_path(Gtk.TreePath.new_from_indices([0]))
  with patch.object(self.app,'window',create=True,side_effect=AssertionError('No additional explorer allowed')):s.open(True)
  self.wait(lambda:not self.w.directory_loading);self.assertEqual(self.w.uri,p.parent.as_uri());self.assertEqual({r['uri'] for r in self.w.selected()},{p.as_uri()})
 def test_navigation_cancels_old_search_and_rebinds_location(self):
  self.w.recursive_search();s=self.w.search_window;s.start();self.w.navigate((self.folder/'Downloads').as_uri());self.wait(lambda:not self.w.directory_loading);self.pump(.3);self.assertFalse(s.active);self.assertNotEqual(self.w.content.get_visible_child_name(),'search');self.w.recursive_search();self.assertEqual(s.root,(self.folder/'Downloads').as_uri());self.assertEqual(len(s.store),0)
 def test_escape_stops_then_closes_search_without_file_action(self):
  self.w.select_uris({(self.folder/'Test 001.txt').as_uri()});self.w.recursive_search();s=self.w.search_window;s.choose_category('all');s.start();e=Gdk.Event.new(Gdk.EventType.KEY_PRESS);e.keyval=Gdk.KEY_Escape;e.state=Gdk.ModifierType(0);self.w.key(self.w,e);self.wait(lambda:not s.stop_button.get_sensitive());self.assertTrue(s.active)
  self.w.key(self.w,e);self.wait(lambda:not self.w.directory_loading);self.assertFalse(s.active);self.assertTrue((self.folder/'Test 001.txt').exists())
 def test_background_render_does_not_replace_search_results(self):
  self.w.recursive_search();self.w.render_files();self.w.search.set_text('unrelated');self.pump(.3);self.assertEqual(self.w.content.get_visible_child_name(),'search');self.w.search_window.destroy();self.w.recursive_search();self.assertTrue(self.w.search_active())
