import json,os,subprocess,sys,tempfile,unittest,string
from pathlib import Path
from mintxp.components import ROOT
class SharedLocale(unittest.TestCase):
    def test_catalogue_copies_and_template_fields(self):
        for p in (ROOT/'locales/legacy').glob('*.json'):
            data=json.loads(p.read_text())
            for folder in ('xp-explorer/locales','xp-control-panel/locales','menu/5.8/locales'):
                self.assertEqual(data,json.loads((ROOT/'assets'/folder/p.name).read_text()))
            for key,value in data.items():
                source=[f for _,f,_,_ in string.Formatter().parse(key) if f is not None]
                target=[f for _,f,_,_ in string.Formatter().parse(value) if f is not None]
                self.assertEqual(sorted(source),sorted(target),(p.name,key))
    def test_manual_choice_overrides_os_without_translating_user_data(self):
        with tempfile.TemporaryDirectory() as td:
            state=Path(td)/'mint-xp-experience';state.mkdir();pref=state/'preferences.json'
            for language,expected in [('fr','Poste de travail'),('de','Arbeitsplatz'),('en','My Computer'),('ja','マイ コンピューター')]:
                pref.write_text(json.dumps({'language':language}));env=dict(os.environ,XDG_STATE_HOME=td,LC_ALL='C.UTF-8')
                result=subprocess.run([sys.executable,'-B','-c',"from xp_locale import t;print(t('Arbeitsplatz'));print(t('private-file-123.txt'))"],cwd=ROOT/'assets/xp-explorer',env=env,text=True,capture_output=True,check=True)
                self.assertEqual(result.stdout.splitlines(),[expected,'private-file-123.txt'])
            pref.write_text('[]')
            result=subprocess.run([sys.executable,'-B','-c',"from xp_locale import t;print(t('Arbeitsplatz'))"],cwd=ROOT/'assets/xp-explorer',env=env,text=True,capture_output=True,check=True)
            self.assertEqual(result.stdout.strip(),'My Computer')
