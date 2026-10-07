"""Installation completion facts from the committed transaction, not the preview."""
from .components import COMPONENTS

def summary(engine,transaction):
 current=engine.read_current();journal=engine.read('history/'+transaction+'.json')
 if not journal or journal.get('action')!='apply' or not current.get('installed'):raise ValueError('No completed installation')
 options=current.get('options',{})
 changed=[k for k in current['settings'] if journal.get('before',{}).get('settings',{}).get(k)!=current['settings'][k]]
 appearance_changed=any(k.startswith(('.themes/','.local/share/cinnamon/applets/','.local/share/icons/')) and journal.get('before',{}).get('files',{}).get(k)!=v for k,v in current['files'].items())
 return {'transaction':transaction,'enabled':[k for k in COMPONENTS if options.get(k)],'disabled':[k for k in COMPONENTS if not options.get(k)],'backup_path':str(engine.state),'relogin_recommended':appearance_changed or any(k.startswith(('org.cinnamon.theme/','org.cinnamon/enabled-applets','org.cinnamon.desktop.interface/')) for k in changed),'system_step_separate':True}
