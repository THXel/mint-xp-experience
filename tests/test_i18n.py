import json,unittest
from mintxp.i18n import Translator,LANGUAGES,ROOT,system_language
class Languages(unittest.TestCase):
    def test_catalogue_completeness(self):
        base=json.loads((ROOT/'en.json').read_text())
        for lang in LANGUAGES:
            data=json.loads((ROOT/(lang+'.json')).read_text());self.assertEqual(set(base),set(data),lang);self.assertTrue(all(isinstance(v,str) and v for v in data.values()))
    def test_locale_priority(self):
        for env,want in [({'LANG':'de_DE.UTF-8'},'de'),({'LANG':'pt_BR.UTF-8'},'pt'),({'LANG':'zh_TW.UTF-8'},'zh'),({'LANG':'xx_XX','LANGUAGE':'xx:ja'},'ja'),({'LANG':'de_DE','LC_ALL':'fr_FR','LANGUAGE':'es'},'fr'),({'LANG':'de_DE','LC_MESSAGES':'C.UTF-8'},'en'),({},'en')]:self.assertEqual(system_language(env),want)
    def test_manual(self):self.assertEqual(Translator('de')('backup'),'Sicherung erstellen')
