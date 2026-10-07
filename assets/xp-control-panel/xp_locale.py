"""Shared language preference; explicit catalogue keys never translate user data."""
import json,os
from pathlib import Path
LANGS=('de','en','fr','es','it','pt','nl','pl','tr','ru','uk','zh','ja','ko')
def language():
    try:
        pref=json.loads((Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'mint-xp-experience/preferences.json').read_text())
        chosen=pref.get('language','auto') if isinstance(pref,dict) else 'auto'
        if chosen in LANGS:return chosen
    except (OSError,ValueError,TypeError):pass
    loc=os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG','en')
    if loc in ('C','POSIX') or loc.startswith('C.'):return 'en'
    for item in ([loc] if os.environ.get('LC_ALL') else os.environ.get('LANGUAGE','').split(':')+[loc]):
        code=item.split('.')[0].split('_')[0].split('-')[0].lower()
        if code in LANGS:return code
    return 'en'
LANGUAGE=language()
def read(code):
    # Prefer app-local catalogues: standalone apps also work without the manager.
    p=Path(__file__).resolve().parent/'locales'/(code+'.json')
    try:
        result=json.loads(p.read_text());return result if isinstance(result,dict) else {}
    except (OSError,ValueError):return {}
BASE=read('en');MESSAGES=read(LANGUAGE)
def t(source):return source if LANGUAGE=='de' else MESSAGES.get(source,BASE.get(source,source))
