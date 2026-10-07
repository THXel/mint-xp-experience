"""Disposable GUI fixtures for responsive rendering and companion/preferences sync."""
import os,time,threading,unittest
from pathlib import Path
from unittest.mock import patch
import test_preview35_gui as base
from gi.repository import Gio,Gtk,GLib
from search_ui import SearchWindow
from conflicts import ConflictPrompt

@unittest.skipUnless(os.environ.get('GSETTINGS_BACKEND')=='memory' and os.environ.get('DISPLAY'),'isolated graphical session required')
class ExplorerGUI36(unittest.TestCase):
 setUpClass=classmethod(base.ExplorerGUI35.setUpClass.__func__)
 tearDownClass=classmethod(base.ExplorerGUI35.tearDownClass.__func__)
 setUp=base.ExplorerGUI35.setUp
 tearDown=base.ExplorerGUI35.tearDown
 pump=base.ExplorerGUI35.pump
 wait=base.ExplorerGUI35.wait
 def test_companion_preferences_and_restart(self):
  s=SearchWindow(self.w)
  try:
   s.companion.select('none');self.assertEqual(s.mascot.get_active_id(),'none');self.assertEqual(s.companion.timer,0)
   s.mascot.set_active_id('penguin');self.assertEqual(s.companion.choice,'penguin')
   s.companion.enable(False);self.assertFalse(s.animated.get_active());self.assertEqual(s.companion.timer,0)
   s.hidden.set_active(True);s.recursive.set_active(False);s.category.set_active_id('image');s.reset_filters();self.assertFalse(s.hidden.get_active());self.assertTrue(s.recursive.get_active());self.assertEqual(s.category.get_active_id(),'all')
   s.companion.select('none')
  finally:s.destroy()
  s=SearchWindow(self.w)
  try:self.assertEqual(s.mascot.get_active_id(),'none');self.assertEqual(s.companion.get_size_request().height,20);self.assertFalse(s.animated.get_active())
  finally:s.destroy()
 def test_large_folder_yields_and_stale_navigation_is_ignored(self):
  large=self.folder/'large';large.mkdir()
  for i in range(2400):(large/f'fixture-{i:04d}.txt').write_text('fixture')
  ticks=[];timer=GLib.timeout_add(8,lambda:(ticks.append(time.monotonic()),True)[1]);self.w.navigate(large.as_uri())
  try:
   self.wait(lambda:not self.w.directory_loading and len(self.w.store)==2400);self.assertGreater(len(ticks),5)
   self.w.navigate(self.folder.as_uri());self.w.navigate((self.folder/'Downloads').as_uri());self.wait(lambda:not self.w.directory_loading and self.w.uri==(self.folder/'Downloads').as_uri());self.pump(.25);self.assertEqual(len(self.w.store),0);self.assertFalse(self.errors)
  finally:GLib.source_remove(timer)
 def test_conflict_metadata_and_replace_or_merge_permissions(self):
  a=self.folder/'source.txt';b=self.folder/'target.txt';a.write_text('incoming');b.write_text('old')
  cancel=Gio.Cancellable();answers=[]
  def work():answers.append(ConflictPrompt(self.w).choose(a.name,str(b),cancel,source=a.as_uri()))
  t=threading.Thread(target=work,daemon=True);t.start();found=[]
  def dialog():
   found[:]=[d for d in Gtk.Window.list_toplevels() if isinstance(d,Gtk.Dialog) and d.get_transient_for()==self.w]
   return bool(found)
  self.wait(dialog);d=found[0]
  try:
   self.assertTrue(d.get_widget_for_response(3).get_sensitive());self.assertFalse(d.get_widget_for_response(4).get_sensitive())
   def labels(w):
    return [w.get_text()] if isinstance(w,Gtk.Label) else sum((labels(c) for c in w.get_children()),[]) if isinstance(w,Gtk.Container) else []
   text='\n'.join(labels(d));self.assertIn(str(a),text);self.assertIn(str(b),text);d.response(2);self.wait(lambda:not t.is_alive());self.assertEqual(answers,['keep'])
  finally:d.destroy();cancel.cancel()
 def test_destroying_conflict_dialog_releases_worker(self):
  a=self.folder/'a';b=self.folder/'b';a.mkdir();b.mkdir();answers=[];cancel=Gio.Cancellable()
  t=threading.Thread(target=lambda:answers.append(ConflictPrompt(self.w).choose('a',str(b),cancel,source=a.as_uri())),daemon=True);t.start();found=[]
  def dialog():
   found[:]=[d for d in Gtk.Window.list_toplevels() if isinstance(d,Gtk.Dialog) and d.get_transient_for()==self.w];return bool(found)
  self.wait(dialog);d=found[0];self.assertTrue(d.get_widget_for_response(4).get_sensitive());self.assertFalse(d.get_widget_for_response(3).get_sensitive());d.destroy();self.wait(lambda:not t.is_alive());self.assertEqual(answers,['cancel'])
