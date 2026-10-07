import json,string,unittest
from mintxp.i18n import ROOT,LANGUAGES

class MediaTranslations(unittest.TestCase):
 def test_new_media_flow_translated_in_every_supported_language(self):
  base=json.loads((ROOT/'en.json').read_text())
  keys=('media_welcome_notice','media_rights','media_file','media_folder','media_without_iso',
        'media_choose','media_required','media_pending','media_builtin_ready','media_current_ready',
        'media_ready_summary','media_continue','media_detected','media_ask_sounds','media_ask_icons',
        'media_current','media_selected','media_same','media_pending_short','media_scope','restore_scope','conflict_help','overview','settings_overview','open_icons','open_sounds','component_notice','apply_component_changes','media_steps','media_selection_only','icon_selection','no_icon_pack','install_icons','install_media','install_sounds','media_setup_hint','sound_apply_hint','icons_apply_notice',
        'media_yes','media_no','sound_mint','progress_media','install_all','install_selected')
  for lang in LANGUAGES:
   data=json.loads((ROOT/(lang+'.json')).read_text())
   for key in keys:
    self.assertTrue(data.get(key),(lang,key))
    if lang!='en':self.assertNotEqual(data[key],base[key],(lang,key))
 def test_all_catalogue_placeholders_preserved(self):
  fmt=string.Formatter();base=json.loads((ROOT/'en.json').read_text())
  fields=lambda value:sorted(f for _,f,_,_ in fmt.parse(value) if f is not None)
  for lang in LANGUAGES:
   data=json.loads((ROOT/(lang+'.json')).read_text())
   for key,value in base.items():self.assertEqual(fields(value),fields(data[key]),(lang,key))
