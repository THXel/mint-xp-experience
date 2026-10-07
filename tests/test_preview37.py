import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/xp-explorer'))
from gi.repository import Gio
from search_ui import search_names
class Search37(unittest.TestCase):
 def test_combined_media_category(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'picture.png').write_bytes(b'\x89PNG\r\n\x1a\n'+bytes(50));(p/'note.txt').write_text('fixture');(p/'folder').mkdir();rows=[]
   search_names(p.as_uri(),'*',False,Gio.Cancellable(),rows.append,kind='media');self.assertEqual([r['name'] for r in rows],['picture.png'])
 def test_new_labels_are_translated_and_shared(self):
  root=Path(__file__).resolve().parents[1];keys=json.loads((root/'docs/explorer-preview37-keys.json').read_text())
  for lang in ('en','fr','es','it','pt','nl','pl','tr','ru','uk','zh','ja','ko'):
   c=json.loads((root/'locales/legacy'/f'{lang}.json').read_text())
   for key in keys:self.assertTrue(c.get(key),(lang,key))
   for app in ('xp-explorer','xp-control-panel','menu/5.8'):self.assertEqual(c,json.loads((root/'assets'/app/'locales'/f'{lang}.json').read_text()))
