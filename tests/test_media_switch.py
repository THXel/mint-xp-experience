import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from mintxp.engine import Engine
from mintxp.components import plan,DEFAULTS,COMPONENTS
from mintxp.media_settings import apply
from mintxp.sounds import settings_keys,apply_import
from test_sounds import Settings,audio
class MediaSwitch(unittest.TestCase):
 def test_default_and_all_components_do_not_change_sounds_without_media(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);home=root/'home';home.mkdir();e=Engine(home,root/'state',Settings())
   e.settings.set('org.cinnamon.desktop.sound/theme-name','"personal"')
   options=dict(DEFAULTS,**dict.fromkeys(COMPONENTS,False));options.update(sounds=True,sound_source=':keep:')
   target=plan(e,options)
   self.assertFalse(settings_keys() & target['settings'].keys());self.assertFalse(any(k.startswith('.local/share/sounds/') for k in target['files']))
   self.assertFalse(target['options']['sounds'])
 def test_later_import_and_both_icon_directions_preserve_other_components(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);home=root/'home';home.mkdir();e=Engine(home,root/'state',Settings())
   icons=root/'icons';icons.mkdir();(icons/'index.theme').write_text('[Icon Theme]\nName=Private\nDirectories=32/places\n[32/places]\nSize=32\nContext=Places\n');(icons/'32/places').mkdir(parents=True);(icons/'32/places/folder.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
   sounds=root/'sounds';sounds.mkdir();(sounds/'Windows XP Ding.wav').write_bytes(audio())
   e.apply({'files':{'.config/keep':e.descriptor(b'untouched')},'settings':{'other/value':'"personal"'},'options':dict(DEFAULTS)},False)
   options=dict(DEFAULTS,icon_import=str(icons),icon_mode='imported',sound_source=str(sounds),sounds=True,disabled_applets=['Cinnamenu@json:15'],reviewed_applets=['panel1:left:0:Cinnamenu@json:15'])
   current=e.read_current();current['options'].update(disabled_applets=options['disabled_applets'],reviewed_applets=options['reviewed_applets']);e.save('current.json',current)
   e.settings.set('org.cinnamon/enabled-applets',json.dumps(['panel1:left:0:mintxp-menu@mintxp:32']))
   panel_before=e.settings.get('org.cinnamon/enabled-applets')
   with patch.object(e,'safety_snapshot',return_value='fixture'):
    apply(e,options);self.assertEqual(e.settings.effective('org.cinnamon.desktop.interface','icon-theme'),'Mint-XP-Experience-Imported')
    before={k:e.settings.get(k) for k in settings_keys()}
    apply(e,dict(options,icon_mode='bundled',sound_source=':keep:',sounds=False));self.assertEqual(e.settings.effective('org.cinnamon.desktop.interface','icon-theme'),'Mint-XP-Experience-Icons')
    self.assertEqual(before,{k:e.settings.get(k) for k in settings_keys()});self.assertEqual(e.read_current()['options']['icon_import'],str(icons))
    apply(e,dict(options,sound_source=':keep:',sounds=False));self.assertEqual(e.settings.effective('org.cinnamon.desktop.interface','icon-theme'),'Mint-XP-Experience-Imported')
   self.assertEqual((home/'.config/keep').read_bytes(),b'untouched');self.assertEqual(e.settings.get('other/value'),'"personal"');self.assertTrue((icons/'index.theme').exists())
   self.assertEqual(e.settings.get('org.cinnamon/enabled-applets'),panel_before)
   self.assertEqual(e.read_current()['options']['disabled_applets'],options['disabled_applets'])

 def test_retired_luna_restores_original_sound_settings(self):
  from mintxp.media_settings import retire_luna
  import copy
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);home=root/'home';home.mkdir();e=Engine(home,root/'state',Settings())
   key='org.cinnamon.desktop.sound/theme-name';e.settings.set(key,'"personal"')
   runtime='.local/share/mint-xp-experience/assets/sounds/luna/test.wav';active='.local/share/sounds/Mint-XP-Experience-Sounds/test.wav'
   e.apply({'files':{runtime:e.descriptor(audio()),active:e.descriptor(audio())},'settings':{key:'"Luna"'},'options':dict(DEFAULTS,sounds=True,sound_source=':builtin:')},False)
   target=copy.deepcopy(e.read_current());self.assertTrue(retire_luna(target));e.apply(target,False)
   self.assertEqual(e.settings.get(key),'"personal"');self.assertFalse((home/runtime).exists());self.assertFalse((home/active).exists())
   self.assertFalse(retire_luna(target))
