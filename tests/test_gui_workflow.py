"""Run with GSETTINGS_BACKEND=memory on a graphical session; never touch host settings."""
import os,json,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
import gi
gi.require_version('Gtk','3.0');from gi.repository import Gtk,Gio
from mintxp.gui import Window
from mintxp.engine import Engine
from mintxp.components import DEFAULTS
from test_sounds import audio

@unittest.skipUnless(os.environ.get('GSETTINGS_BACKEND')=='memory' and os.environ.get('DISPLAY'),'isolated graphical session required')
class Workflow(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.app=Gtk.Application(application_id='org.mintxp.WorkflowTest.x'+uuid.uuid4().hex,flags=Gio.ApplicationFlags.NON_UNIQUE);cls.app.register(None)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.home=self.root/'home';self.home.mkdir();self.e=Engine(self.home,self.root/'state')
  self.w=None
  self.backup=patch.object(self.e,'safety_snapshot',return_value='test-reference');self.backup.start()
 def tearDown(self):
  if self.w:self.w.destroy()
  self.backup.stop();self.tmp.cleanup()
 def install_record(self):
  options=dict(DEFAULTS,disabled_applets=['Cinnamenu@json:15'])
  self.e.apply({'files':{'.config/preserve':self.e.descriptor(b'personal')},'settings':{},'options':options},False)
 def window(self,mode=None):
  self.w=Window(self.app,self.e,mode);return self.w
 def synchronous(self):
  def run(fn,refresh_after=False,complete=None,quiet=False):
   result=fn()
   if complete:complete(result)
  self.w.run_job=run
 def sources(self):
  icons=self.root/'icons';icons.mkdir();(icons/'32/places').mkdir(parents=True);(icons/'index.theme').write_text('[Icon Theme]\nName=Test\nDirectories=32/places\n[32/places]\nSize=32\nContext=Places\n');(icons/'32/places/folder.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
  sound=self.root/'sounds';sound.mkdir();(sound/'Windows XP Ding.wav').write_bytes(audio());return icons,sound
 def test_first_install_immediately_exposes_settings_actions(self):
  w=self.window();self.assertEqual(w.mode,'setup');self.assertFalse(w.icons_apply_button.get_sensitive());self.assertFalse(w.sound_apply_button.get_sensitive())
  self.install_record();w.show_completion({'enabled':['icons'],'disabled':[],'backup_path':'test','transaction':'fixture','relogin_recommended':False})
  self.assertEqual(w.mode,'settings');self.assertTrue(w.icons_apply_button.get_sensitive());self.assertTrue(w.media_apply_button.get_visible());self.assertFalse(w.install_all_button.get_visible());self.assertIsNotNone(w.stack.get_child_by_name('components'))
 def test_existing_install_overrides_stale_setup_launch(self):
  self.install_record();w=self.window('setup');self.assertEqual(w.mode,'settings');self.assertTrue(w.icons_apply_button.get_sensitive())
 def test_actual_icons_then_sound_apply_without_reinstallation_and_undo(self):
  self.install_record();w=self.window();self.synchronous();icons,sound=self.sources();w.icons.set_text(str(icons));w.icon_mode.set_active_id('imported');w.set_sound_source(str(sound));w.sound_pack.set_active_id('custom')
  with patch.object(w,'message',return_value=True),patch.object(w,'apply_options',side_effect=AssertionError('No full installation allowed')):
   w.icons_apply_button.clicked();self.assertEqual(self.e.settings.effective('org.cinnamon.desktop.interface','icon-theme'),'Mint-XP-Experience-Imported');self.assertFalse(self.e.read_current()['options']['sounds'])
   w.sound_apply_button.clicked();self.assertTrue(self.e.read_current()['options']['sounds']);self.assertEqual(self.e.read_current()['options']['disabled_applets'],['Cinnamenu@json:15'])
   w.sound_action('remove');self.assertFalse(self.e.read_current()['options']['sounds'])
  self.assertEqual((self.home/'.config/preserve').read_bytes(),b'personal');self.e.uninstall();self.assertFalse(self.e.read_current()['installed'])
 def test_cancel_apply_keeps_installation_unchanged(self):
  self.install_record();w=self.window();self.synchronous();before=self.e.read_current()
  with patch.object(w,'message',return_value=False),patch.object(w,'run_job') as worker:w.icons_apply_button.clicked();worker.assert_not_called()
  self.assertEqual(self.e.read_current(),before)
 def test_sound_keep_disables_install_until_sound_selected(self):
  self.install_record();w=self.window();self.assertFalse(w.sound_apply_button.get_sensitive());w.sound_pack.set_active_id('mint');self.assertTrue(w.sound_apply_button.get_sensitive());w.sound_pack.set_active_id('keep');self.assertFalse(w.sound_apply_button.get_sensitive())

 def test_import_selection_is_explicit_and_language_preserves_it(self):
  self.install_record();w=self.window();icons,sound=self.sources();before=self.e.read_current()
  with patch('mintxp.gui_media.Gtk.MessageDialog',side_effect=AssertionError('No second-pack prompt in settings')):
   w.media_imported({'icon_path':str(icons),'icons':1})
  self.assertEqual(self.e.read_current(),before);self.assertEqual(w.icon_mode.get_active_id(),'imported');self.assertFalse(w.media_apply_button.get_sensitive())
  w.media_imported({'sound_path':str(sound),'sounds':1});self.assertTrue(w.media_apply_button.get_sensitive())
  w.stack.set_visible_child_name('media_page');w.language.set_active_id('de')
  from gi.repository import GLib
  while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
  self.assertEqual(w.stack.get_visible_child_name(),'media_page');self.assertEqual(w.icons.get_text(),str(icons));self.assertEqual(w.sound_source.get_text(),str(sound));self.assertTrue(w.icons_apply_button.get_sensitive());self.assertTrue(w.media_apply_button.get_sensitive())

 def test_media_status_and_scope_are_shown_before_applying(self):
  from mintxp.gui_status import refresh
  self.install_record();w=self.window();self.synchronous();icons,sounds=self.sources()
  w.icons.set_text(str(icons));w.icon_mode.set_active_id('imported')
  self.assertIn(w.t('media_pending_short'),w.media_state_labels[0].get_text())
  with patch.object(w,'message',return_value=False) as dialog:w.icons_apply_button.clicked()
  self.assertIn(w.t('media_scope'),dialog.call_args.args[1]);self.assertIn(w.t('sound_keep'),dialog.call_args.args[1])
  with patch.object(w,'message',return_value=True):w.icons_apply_button.clicked()
  refresh(w);self.assertIn(w.t('media_same'),w.media_state_labels[0].get_text())
 def test_backup_label_uses_reason_and_restore_describes_scope(self):
  self.install_record();w=self.window();name=self.e.backup(reason='media');w.reload_backups();self.assertIn(w.t('media_page'),w.backups.get_active_text())
  with patch.object(w,'message',return_value=False) as dialog,patch.object(w,'run_job') as worker:
   w.restore();worker.assert_not_called();self.assertIn(w.t('restore_scope'),dialog.call_args.args[1])
