import os,sys,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/xp-explorer'))
from gi.repository import Gio
from journal import UndoHistory
from core import move_item,copy_item,listing
from folder_merge import merge
import replacements as r
import search_settings as s
import thumbnail_cache as cache
class Preview36(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name);self.env=patch.dict(os.environ,XP_EXPLORER_STATE_DIR=str(self.p/'state'),XP_EXPLORER_CACHE_DIR=str(self.p/'cache'));self.env.start()
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def test_search_history_bounded_credentials_excluded_and_clear(self):
  for n in range(20):s.remember(str(n),str(self.p/str(n)))
  self.assertEqual(len(s.load()['terms']),12);s.remember('19',str(self.p/'19'));self.assertEqual(s.load()['terms'][0],'19');s.remember('secret','smb://user:password@server/share');self.assertFalse(any('password' in x for x in s.load()['locations']));self.assertEqual(s.path().stat().st_mode&0o777,0o600);s.clear();self.assertFalse(s.load()['terms'])
 def source_target(self):
  a=self.p/'src';b=self.p/'dst';a.mkdir();b.mkdir();(a/'same.txt').write_text('new');(b/'same.txt').write_text('old');(a/'sub').mkdir();(a/'sub/a.txt').write_text('A');(b/'sub').mkdir();(b/'sub/keep.txt').write_text('keep');return a,b
 def test_copy_merge_keeps_unrelated_and_undo_restores_conflicts(self):
  a,b=self.source_target();h=UndoHistory()
  with h.batch():merge(a.as_uri(),b.as_uri(),Gio.Cancellable(),h,lambda *args,**kw:'replace')
  self.assertEqual((b/'same.txt').read_text(),'new');self.assertEqual((b/'sub/a.txt').read_text(),'A');self.assertEqual((b/'sub/keep.txt').read_text(),'keep');h.undo();self.assertEqual((b/'same.txt').read_text(),'old');self.assertFalse((b/'sub/a.txt').exists());self.assertTrue((a/'sub/a.txt').exists())
 def test_cut_merge_recreates_removed_source_directories_on_undo(self):
  a,b=self.source_target();h=UndoHistory()
  with h.batch():merge(a.as_uri(),b.as_uri(),Gio.Cancellable(),h,lambda *args,**kw:'replace',cut=True)
  self.assertFalse(a.exists());h.undo();self.assertEqual((a/'same.txt').read_text(),'new');self.assertEqual((a/'sub/a.txt').read_text(),'A');self.assertEqual((b/'same.txt').read_text(),'old')
 def test_merge_skip_links_and_nested_rejected(self):
  a,b=self.source_target();(a/'link').symlink_to(self.p/'outside',target_is_directory=True);h=UndoHistory()
  with h.batch():self.assertFalse(merge(a.as_uri(),b.as_uri(),Gio.Cancellable(),h,lambda *args,**kw:'skip'))
  self.assertTrue((b/'link').is_symlink());self.assertEqual((b/'same.txt').read_text(),'old')
  with self.assertRaises(ValueError):merge(a.as_uri(),(a/'sub').as_uri(),Gio.Cancellable(),h,lambda *x: 'keep')
 def test_interrupted_install_before_new_file_restores_original(self):
  src=self.p/'s';dst=self.p/'d';src.write_text('new');dst.write_text('old');h=UndoHistory();r.replace(src.as_uri(),dst.as_uri(),Gio.Cancellable(),h);item=h.peek();dst.unlink();item['stamp']=None;item['result_identity']=None;r.write_record(item['record'],item);r.restore(item);self.assertEqual(dst.read_text(),'old')
 def test_restore_resumes_after_staging_or_original_restored(self):
  for before_original in (True,False):
   src=self.p/('s'+str(before_original));dst=self.p/('d'+str(before_original));src.write_text('new');dst.write_text('old');h=UndoHistory();r.replace(src.as_uri(),dst.as_uri(),Gio.Cancellable(),h,cut=True);item=h.peek();backup,target,folder,staged=r.paths(item);move_item(dst.as_uri(),staged.as_uri())
   if not before_original:move_item(backup.as_uri(),dst.as_uri())
   r.restore(item);self.assertEqual(src.read_text(),'new');self.assertEqual(dst.read_text(),'old')
 def test_changed_file_rescue_copy_preserves_both(self):
  src=self.p/'s.txt';dst=self.p/'d.txt';src.write_text('new');dst.write_text('old');h=UndoHistory();r.replace(src.as_uri(),dst.as_uri(),Gio.Cancellable(),h);dst.write_text('user edit');item=h.peek()
  with self.assertRaises(ValueError):r.restore(item)
  recovered=r.rescue_copy(item);from core import file_for
  self.assertEqual(Path(file_for(recovered).get_path()).read_text(),'old');self.assertEqual(dst.read_text(),'user edit');summary=r.summaries()[0];self.assertEqual(summary[1],3);self.assertFalse(summary[4])
 def test_listing_publishes_before_finish(self):
  for n in range(350):(self.p/str(n)).write_text('x')
  batches=[];rows=listing(self.p.as_uri(),on_batch=lambda b:batches.append(b));self.assertEqual([len(b) for b in batches],[150,150,50]);self.assertEqual(len(rows),350)
 def test_cache_reuses_then_invalidates_source(self):
  from gi.repository import GdkPixbuf
  p=self.p/'image.png';pix=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,True,8,16,16);pix.fill(0xff0000ff);pix.savev(str(p),'png',[],[])
  a=cache.load(p.as_uri(),32)
  with patch('thumbnail_cache.load_image',side_effect=AssertionError('cache miss')):self.assertIs(cache.load(p.as_uri(),32),a)
  old=cache.key(p.as_uri(),32);pix.fill(0x00ff00ff);pix.savev(str(p),'png',[],[]);self.assertNotEqual(cache.key(p.as_uri(),32),old);b=cache.load(p.as_uri(),32);self.assertNotEqual(a.get_pixels(),b.get_pixels())
 def test_translation_coverage_and_placeholders(self):
  import string
  root=Path(__file__).resolve().parents[1];keys=json.loads((root/'docs/explorer-preview36-keys.json').read_text());self.assertEqual(len(keys),100)
  def fields(s):return sorted((k,f) for _,k,f,_ in string.Formatter().parse(s) if k is not None)
  for lang in ('en','es','fr','it','ja','ko','nl','pl','pt','ru','tr','uk','zh'):
   catalogue=json.loads((root/'locales/legacy'/f'{lang}.json').read_text())
   for key in keys:self.assertTrue(catalogue.get(key),(lang,key));self.assertEqual(fields(catalogue[key]),fields(key),(lang,key))
   for app in ('xp-explorer','xp-control-panel','menu/5.8'):self.assertEqual(json.loads((root/'assets'/app/'locales'/f'{lang}.json').read_text()),catalogue)
