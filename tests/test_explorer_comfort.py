import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/xp-explorer'))
from bookmark_store import BookmarkStore
from core import file_for
from search_ui import search_names
from gi.repository import Gio,GLib
class ComfortTests(unittest.TestCase):
 def test_bookmarks_preserve_shared_entries_and_order(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bookmarks';p.write_text('smb://example.invalid/share Existing name\nfile:///tmp/other Other\n')
   b=BookmarkStore(p);self.assertTrue(b.change('file:///tmp/new','add','New'));self.assertFalse(b.change('file:///tmp/new','add'))
   b.change('file:///tmp/new','rename','Label only');b.change('file:///tmp/new','move',step=-1)
   self.assertEqual(b.entries(),[('Existing name',file_for('smb://example.invalid/share').get_uri()),('Label only','file:///tmp/new'),('Other','file:///tmp/other')])
   b.change('file:///tmp/new','remove');self.assertEqual(p.read_text(),'smb://example.invalid/share Existing name\nfile:///tmp/other Other\n')
 def test_bookmarks_protect_concurrent_edit(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bookmarks';p.write_text('file:///tmp/old Old\n');b=BookmarkStore(p);old=b.read();p.write_text('file:///tmp/external External change\n')
   with patch.object(b,'read',return_value=old):
    with self.assertRaises(GLib.Error):b.change('file:///tmp/old','rename','New')
   self.assertEqual(p.read_text(),'file:///tmp/external External change\n')
 def test_bookmarks_new_file_race_is_not_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bookmarks';b=BookmarkStore(p);p.write_text('file:///tmp/external External\n')
   with patch.object(b,'read',return_value=('',None)):
    with self.assertRaises(GLib.Error):b.change('file:///tmp/new','add')
   self.assertIn('external',p.read_text())
 def test_bookmark_label_cannot_inject_another_entry(self):
  with tempfile.TemporaryDirectory() as d:
   b=BookmarkStore(Path(d)/'bookmarks')
   with self.assertRaises(ValueError):b.change('file:///tmp/new','add','Name\nfile:///etc')
 def test_search_globs_subfolders_and_symlinks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'Report.PDF').write_text('one');(p/'sub').mkdir();(p/'sub/Report.txt').write_text('two');(p/'sub/loop').symlink_to(p,target_is_directory=True);(p/'.secret.pdf').write_text('hidden')
   rows=[];search_names(str(p),'*.pdf',False,Gio.Cancellable(),rows.append);self.assertEqual([r['name'] for r in rows],['Report.PDF'])
   rows=[];search_names(str(p),'report',False,Gio.Cancellable(),rows.append,recursive=False);self.assertEqual(len(rows),1)
   rows=[];search_names(str(p),'report',False,Gio.Cancellable(),rows.append);self.assertEqual(len(rows),2)
   c=Gio.Cancellable();c.cancel()
   with self.assertRaises(GLib.Error):search_names(str(p),'report',False,c,rows.append)
