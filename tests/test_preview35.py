import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'assets/xp-explorer'))
from gi.repository import Gio,GLib
from search_ui import search_names
from batch_rename import plan_names
from bookmark_store import BookmarkStore
from journal import UndoHistory
from replacements import replace,restore,records
from core import file_for
from mintxp.agent_character import Reader,decompress,checked_files
import views

class Explorer35(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name);self.env=patch.dict(os.environ,XP_EXPLORER_STATE_DIR=str(self.p/'state'));self.env.start()
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def test_search_categories_size_date_hidden_and_limit(self):
  (self.p/'document.txt').write_text('abc');(self.p/'picture.png').write_bytes(b'\x89PNG\r\n\x1a\n'+bytes(50));(self.p/'.secret.txt').write_text('x');(self.p/'folder').mkdir()
  def search(**kw):
   out=[];result=search_names(str(self.p),'*',False,Gio.Cancellable(),out.append,**kw);return out,result
  self.assertEqual([r['name'] for r in search(kind='documents')[0]],['document.txt'])
  self.assertEqual([r['name'] for r in search(kind='image')[0]],['picture.png'])
  self.assertEqual([r['name'] for r in search(kind='folders')[0]],['folder'])
  self.assertFalse(search(since=99999999999)[0]);self.assertFalse(search(kind='documents',min_size=20)[0]);self.assertTrue(search(limit=1)[1][2])
 def test_batch_names_keep_extensions_no_duplicate_or_injection(self):
  rows=[dict(name='A.txt',uri=(self.p/'A.txt').as_uri(),dir=False),dict(name='B.pdf',uri=(self.p/'B.pdf').as_uri(),dir=False)]
  self.assertEqual([p[1] for p in plan_names(rows,'Photo {n:03d}')],['Photo 001.txt','Photo 002.pdf'])
  for pattern in ('../{name}','{name.__class__}','{n:99999d}','same'):
   with self.assertRaises(ValueError):plan_names(rows,pattern,keep_extension=False)
 def test_favorite_drag_reorders_and_preserves_unknown_lines(self):
  p=self.p/'bookmarks';p.write_text('# keep\nfile:///a A\nfile:///b B\nfile:///c C\n');b=BookmarkStore(p);b.change('file:///c','before','file:///a')
  self.assertEqual([u for n,u in b.entries()],['file:///c','file:///a','file:///b']);self.assertIn('# keep',p.read_text())
  b.change('file:///c','before',None);self.assertEqual(b.entries()[-1][1],'file:///c')
 def test_zoom_bounds_and_persistence(self):
  views.save('file:///x',dict(zoom=80,mode='details',sort='size'));self.assertEqual(views.get('file:///x')['zoom'],80);self.assertEqual(views.normalize({'zoom':9999})['zoom'],128)
 def test_copy_replace_undo_keeps_source_and_restores_target(self):
  src=self.p/'source';dst=self.p/'target';src.write_text('new');dst.write_text('old');h=UndoHistory();replace(src.as_uri(),dst.as_uri(),Gio.Cancellable(),h)
  self.assertEqual(dst.read_text(),'new');self.assertEqual(src.read_text(),'new');self.assertEqual(len(list(records().glob('*.json'))),1)
  h.undo();self.assertEqual(dst.read_text(),'old');self.assertEqual(src.read_text(),'new');self.assertFalse(list(records().glob('*.json')))
 def test_cut_replace_and_group_undo(self):
  h=UndoHistory()
  with h.batch():
   for i in range(2):
    src=self.p/f's{i}';dst=self.p/f't{i}';src.write_text('new');dst.write_text('old');replace(src.as_uri(),dst.as_uri(),Gio.Cancellable(),h,cut=True)
  h.undo()
  for i in range(2):self.assertEqual((self.p/f's{i}').read_text(),'new');self.assertEqual((self.p/f't{i}').read_text(),'old')
 def test_replace_failure_restores_old_and_protects_modified_files(self):
  src=self.p/'source';dst=self.p/'target';src.write_text('new');dst.write_text('old');h=UndoHistory()
  with patch('replacements.copy_item',side_effect=OSError('disk full')):
   with self.assertRaises(OSError):replace(src.as_uri(),dst.as_uri(),Gio.Cancellable(),h)
  self.assertEqual(dst.read_text(),'old');self.assertFalse(h.items)
  replace(src.as_uri(),dst.as_uri(),Gio.Cancellable(),h);dst.write_text('user edit')
  with self.assertRaises(ValueError):h.undo()
  self.assertEqual(dst.read_text(),'user edit');self.assertEqual(file_for(h.peek()['backup']).load_contents(None)[1],b'old')
 def test_persistent_recovery_after_new_history(self):
  src=self.p/'source';dst=self.p/'target';src.write_text('new');dst.write_text('old');replace(src.as_uri(),dst.as_uri(),Gio.Cancellable(),UndoHistory());record=next(records().glob('*.json'));restore(json.loads(record.read_text()));self.assertEqual(dst.read_text(),'old')
 def test_replace_rejects_self_symlink_and_directory(self):
  src=self.p/'src';src.write_text('new');link=self.p/'link';link.symlink_to(src);folder=self.p/'folder';folder.mkdir()
  for dst in (src,link,folder):
   with self.assertRaises(ValueError):replace(src.as_uri(),dst.as_uri(),Gio.Cancellable(),UndoHistory())
  self.assertEqual(src.read_text(),'new');self.assertFalse(list(records().glob('*.json')))
 def test_decoder_rejects_truncation_and_invalid_backrefs(self):
  with self.assertRaises(ValueError):Reader(b'abc').take(4)
  with self.assertRaises(ValueError):decompress(b'\x00\x01\xff',10)
 def test_manifest_rejects_paths_and_large_dimensions(self):
  folder=self.p/'companion';folder.mkdir();m={'format':1,'width':80,'height':80,'animations':{'RestPose':[['../x.png',20]]}};(folder/'character.json').write_text(json.dumps(m))
  with self.assertRaises(ValueError):checked_files(folder)
  m['width']=9999;(folder/'character.json').write_text(json.dumps(m))
  with self.assertRaises(ValueError):checked_files(folder)
