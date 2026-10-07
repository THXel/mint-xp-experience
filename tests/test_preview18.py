import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from mintxp.engine import Engine,Settings,Conflict
from mintxp.integration import desktop_directory,local_icons,pin_explorer,EXPLORER
from mintxp.components import ROOT

class Integration(unittest.TestCase):
 def test_pins_field_restore_preserves_other_applet_changes(self):
  with tempfile.TemporaryDirectory() as td:
   home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state');key='mintxp-pins/2';p=e.settings.pins_path(key);p.parent.mkdir(parents=True)
   original=['browser.desktop','nemo.desktop'];p.write_text(json.dumps({'pinned-apps':{'type':'generic','value':original},'other':{'value':1}}))
   target={'files':{},'settings':{key:e.settings.literal([EXPLORER,*original])},'options':{}}
   e.apply(target,False);data=json.loads(p.read_text());data['other']['value']=2;p.write_text(json.dumps(data));self.assertFalse(e.check(e.read_current()));e.uninstall();self.assertEqual(json.loads(p.read_text())['pinned-apps']['value'],original);self.assertEqual(json.loads(p.read_text())['other']['value'],2)
 def test_replace_nemo_pin_keeps_nemo_and_other_favourites(self):
  e=Mock();e.settings.effective.return_value=['panel1:left:1:grouped-window-list@cinnamon.org:2']
  e.settings.get.return_value=repr(['browser.desktop','nemo.desktop',EXPLORER,'terminal.desktop'])
  e.settings.literal.side_effect=lambda value:value
  settings={};pin_explorer(e,settings,ROOT,replace_nemo=True)
  self.assertEqual(settings['mintxp-pins/2'],[EXPLORER,'browser.desktop','terminal.desktop'])
  settings={};pin_explorer(e,settings,ROOT,replace_nemo=False)
  self.assertIn('nemo.desktop',settings['mintxp-pins/2'])
 def test_later_pin_change_is_protected(self):
  with tempfile.TemporaryDirectory() as td:
   home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state');key='mintxp-pins/3';p=e.settings.pins_path(key)
   e.apply({'files':{},'settings':{key:e.settings.literal([EXPLORER])},'options':{}},False)
   data=json.loads(p.read_text());data['pinned-apps']['value']=['custom.desktop'];p.write_text(json.dumps(data))
   with self.assertRaises(Conflict):e.uninstall()
 def test_localised_desktop_and_narrow_shortcut_scope(self):
  with tempfile.TemporaryDirectory() as td:
   home=Path(td)/'home';home.mkdir();(home/'Bureau').mkdir();(home/'.config').mkdir();(home/'.config/user-dirs.dirs').write_text('XDG_DESKTOP_DIR="$HOME/Bureau"\n')
   self.assertEqual(desktop_directory(home),home/'Bureau');e=Engine(home,Path(td)/'state');rel='Bureau/org.mintxp.Computer.desktop';e.apply({'files':{rel:e.descriptor(b'launcher',0o755)},'settings':{},'options':{}},False);e.uninstall();self.assertTrue((home/'Bureau').is_dir());self.assertFalse((home/rel).exists())
   with self.assertRaises(Conflict):e.path('Bureau/private.txt')
   (home/'.config/user-dirs.dirs').write_text('XDG_DESKTOP_DIR="/tmp"\n');self.assertIsNone(desktop_directory(home))
 def test_original_local_pack_preferred_without_network(self):
  with tempfile.TemporaryDirectory() as td:
   home=Path(td);self.assertEqual(local_icons(home),'');p=home/'.local/share/icons/XP-Icons-Mint';p.mkdir(parents=True);(p/'index.theme').write_text('[Icon Theme]');self.assertEqual(local_icons(home),str(p))

 def test_plan_uses_local_icons_and_fallback(self):
  from mintxp.components import plan,DEFAULTS,COMPONENTS
  with tempfile.TemporaryDirectory() as td:
   home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state')
   p=home/'.local/share/icons/XP-Icons-Mint';p.mkdir(parents=True);(p/'index.theme').write_text('[Icon Theme]\nName=Local XP\nDirectories=icons\n');(p/'icons').mkdir();(p/'icons/example.svg').write_text('<svg/>')
   options=dict(DEFAULTS,**dict.fromkeys(COMPONENTS,False));options['icons']=True;options['prefer_local_icons']=True
   result=plan(e,options);theme=e.data(result['files']['.local/share/icons/Mint-XP-Experience-Imported/index.theme']).decode()
   self.assertIn('Inherits=Mint-XP-Experience-Icons',theme.replace(' = ','='))
   self.assertIn('Mint-XP-Experience-Imported',result['settings']['org.cinnamon.desktop.interface/icon-theme'])
   options['prefer_local_icons']=False;result=plan(e,options);self.assertNotIn('.local/share/icons/Mint-XP-Experience-Imported/index.theme',result['files'])

class CombinedInstall(unittest.TestCase):
 def test_download_failure_does_not_skip_other_games_or_boot(self):
  from mintxp.install_flow import install
  e=Mock();e.read.return_value=None;e.check.return_value=[];e.apply.return_value='transaction';addons=Mock();addons.install.side_effect=[RuntimeError('offline'),'installed'];system=Mock();system.install.return_value='verified'
  with patch('mintxp.install_flow.prepare_rescue'),patch('mintxp.install_flow.plan'),patch('mintxp.install_flow.summary',return_value={'transaction':'transaction'}):
   result=install(e,{'addon_selection':['minesweeper','jspaint'],'boot_install':True},addons,system)
  self.assertTrue(result['partial']);self.assertEqual([r['ok'] for r in result['steps']],[True,False,True]);self.assertFalse(result['incomplete']);system.install.assert_called_once_with(True,False)
 def test_cancelled_system_prompt_stops_before_desktop_and_games(self):
  from mintxp.install_flow import install
  e=Mock();e.read.return_value=None;e.check.return_value=[];system=Mock();system.install.side_effect=RuntimeError('cancelled');addons=Mock()
  with patch('mintxp.install_flow.prepare_rescue'),patch('mintxp.install_flow.plan'):
   with self.assertRaisesRegex(RuntimeError,'cancelled'):install(e,{'boot_install':True,'addon_selection':['jspaint']},addons,system)
  e.apply.assert_not_called();addons.install.assert_not_called()
