import ast,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from mintxp.components import ROOT,plan,DEFAULTS,patch_control,desktop
from mintxp.engine import Engine
class Package(unittest.TestCase):
    def test_python_syntax_and_no_private_paths(self):
        for p in ROOT.rglob('*.py'):
            ast.parse(p.read_text(),str(p))
            self.assertNotIn(str(Path.home())+'/',p.read_text(),str(p))
    def test_control_entry_idempotent(self):
        original=(ROOT/'assets/xp-control-panel/panel.py').read_text();patched=patch_control(original)
        self.assertEqual(patch_control(patched),patched);self.assertIn("Path.home()/'.local/share/applications'",patched)
    def test_desktop_exec_quoting(self):
        data=desktop('Test',Path('/tmp/test " dollar$ tick` percent%/app.py')).decode()
        self.assertIn('\\"',data);self.assertIn('%%',data);self.assertIn('\\$',data)
    def test_full_real_schema_roundtrip_in_memory_backend(self):
        code='''
import os,tempfile
from pathlib import Path
from mintxp.engine import Engine
from mintxp.components import plan,DEFAULTS
with tempfile.TemporaryDirectory() as td:
    home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state')
    o=dict(DEFAULTS);p=plan(e,o);e.apply(p,False)
    assert not e.check(e.read_current())
    o['font_size']=12;p=plan(e,o);e.apply(p,False)
    e.uninstall();assert not e.check(e.read_current())
    assert not list(home.rglob('*')), list(home.rglob('*'))[:10]
    # Installing anew after uninstall must capture the new user's baseline.
    (home/'.config').mkdir();(home/'.config/other').write_text('keep')
    e.apply(plan(e,o),False);e.uninstall();assert (home/'.config/other').read_text()=='keep'
print('Full package install, update, uninstall and reinstall passed')
'''
        env=dict(os.environ,GSETTINGS_BACKEND='memory');r=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=env,text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr+'\n'+r.stdout)
    def test_taskbar_sizes_its_actual_zones(self):
        code="""
import tempfile,json
from pathlib import Path
from mintxp.engine import Engine
from mintxp.components import plan,DEFAULTS
with tempfile.TemporaryDirectory() as td:
 home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state')
 e.settings.set('org.cinnamon/enabled-applets',e.settings.literal(['panel1:left:2:grouped-window-list@cinnamon.org:2','panel2:center:0:grouped-window-list@cinnamon.org:3']))
 original=[{'panelId':1,'left':22,'center':24,'right':16},{'panelId':2,'left':20,'center':24,'right':18}]
 for key in ('panel-zone-icon-sizes','panel-zone-symbolic-icon-sizes'):e.settings.set('org.cinnamon/'+key,e.settings.literal(json.dumps(original)))
 p=plan(e,dict(DEFAULTS,taskbar=True,icon_size=36))
 for key in ('panel-zone-icon-sizes','panel-zone-symbolic-icon-sizes'):
  text=e.settings.GLib.Variant.parse(None,p['settings']['org.cinnamon/'+key],None,None).unpack();rows=json.loads(text)
  assert rows==[dict(original[0],left=36),dict(original[1],center=36)],rows
"""
        r=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=dict(os.environ,GSETTINGS_BACKEND='memory'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_optional_components_with_real_schemas(self):
        code='''
import tempfile,json
from pathlib import Path
from mintxp.engine import Engine
from mintxp.components import plan,DEFAULTS
with tempfile.TemporaryDirectory() as td:
 home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state')
 # Explicit canonical default panel to exercise applet replacement on a fresh profile.
 e.settings.set('org.cinnamon/enabled-applets',e.settings.literal(['panel1:left:0:menu@cinnamon.org:0','panel1:center:0:grouped-window-list@cinnamon.org:1']))
 original=e.settings.get('org.cinnamon/enabled-applets')
 sound=home/'.local/share/sounds/Windows-XP';sound.mkdir(parents=True);(sound/'index.theme').write_text('[Sound Theme]')
 import wave
 with wave.open(str(sound/'Windows XP Ding.wav'),'wb') as wav:
  wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(22050);wav.writeframes(bytes(100))
 options=dict(DEFAULTS,menu=True,taskbar=True,wallpaper=True,sounds=True,default_manager=True)
 p=plan(e,options);e.apply(p,False)
 assert 'mintxp-menu@mintxp' in e.settings.get('org.cinnamon/enabled-applets')
 assert 'org.mintxp.Explorer.desktop' in (home/'.config/mimeapps.list').read_text()
 e.uninstall();assert e.settings.get('org.cinnamon/enabled-applets')==original
 assert (sound/'index.theme').exists()
print('Optional menu/taskbar/sounds/wallpaper/default-file-manager roundtrip passed')
'''
        env=dict(os.environ,GSETTINGS_BACKEND='memory');r=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=env,text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr+'\n'+r.stdout)
