"""JSON catalogues, OS locale selection, explicit English fallback."""
import json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent/'locales'
LANGUAGES={'de':'Deutsch','en':'English','fr':'Français','es':'Español','it':'Italiano','pt':'Português','nl':'Nederlands','pl':'Polski','tr':'Türkçe','ru':'Русский','uk':'Українська','zh':'简体中文','ja':'日本語','ko':'한국어'}
def system_language(env=None):
    env=os.environ if env is None else env
    # LC_ALL overrides individual locale categories. LANGUAGE contains gettext's
    # preference list; C/POSIX deliberately uses English.
    locale=env.get('LC_ALL') or env.get('LC_MESSAGES') or env.get('LANG') or 'en'
    if locale in ('C','POSIX') or locale.startswith('C.'):return 'en'
    choices=([env['LC_ALL']] if env.get('LC_ALL') else env.get('LANGUAGE','').split(':'))+[locale]
    for choice in choices:
        lang=choice.split('.')[0].split('_')[0].split('-')[0].lower()
        if lang in LANGUAGES:return lang
    return 'en'
class Translator:
    def __init__(self,language=None):
        if language is None:
            try:
                state=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'mint-xp-experience/preferences.json';language=json.loads(state.read_text()).get('language','auto')
            except (OSError,ValueError,TypeError,AttributeError):language='auto'
        self.language=system_language() if language=='auto' else language
        if not isinstance(self.language,str) or self.language not in LANGUAGES:self.language='en'
        self.base=json.loads((ROOT/'en.json').read_text())
        self.messages=json.loads((ROOT/(self.language+'.json')).read_text())
    def __call__(self,key):return self.messages.get(key,self.base.get(key,key))
