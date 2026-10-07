"""Reviewed desktop + accessories + optional privileged appearance workflow.

Each stage keeps its independent backup/journal. Authentication happens before
desktop changes or downloads. Overall progress counts completed stages only.
"""
import subprocess
from .components import ROOT,plan
from .lifecycle import prepare_rescue
from .completion import summary
from .addons import Addons,CATALOG

class SystemInstaller:
    def install(self,boot,login):
        command=['/usr/bin/pkexec','--disable-internal-agent','/usr/bin/python3','-I','-B',str(ROOT/'system/appearance.py'),'apply']
        if boot:command.append('--boot')
        if login:command.append('--login')
        result=subprocess.run(command,capture_output=True,text=True)
        if result.returncode in (126,127):raise RuntimeError('Administrator authentication cancelled; boot/login installation not completed.')
        if result.returncode:raise RuntimeError((result.stderr or result.stdout or 'System installation failed')[-1600:])
        return result.stdout[-1600:].strip() or 'OK'

class OverallProgress:
    """Substeps may reset their counters; the overall completed count never does."""
    def __init__(self,engine,total):
        self.engine=engine;self.observer=engine.progress;self.total=total;self.done=0;self.stage='prepare'
    def report(self,phase='prepare',done=0,total=None,detail=''):
        if self.observer:
            try:self.observer('overall',self.done,self.total,{'stage':self.stage,'phase':phase,'done':done,'total':total,'detail':str(detail)})
            except Exception:pass # Observers must not affect the transaction.
    def start(self,stage):self.stage=stage;self.report(stage)
    def completed(self):self.done+=1;self.report(self.stage)

def install(engine,options,addons=None,system=None):
    chosen=options.get('addon_selection',[])
    if not isinstance(chosen,list) or any(k not in CATALOG for k in chosen):raise ValueError('Unknown accessory selection')
    chosen=list(dict.fromkeys(chosen));privileged=bool(options.get('boot_install') or options.get('login_install'))
    progress=OverallProgress(engine,1+len(chosen)+int(privileged));engine.progress=progress.report
    results=[];result={'steps':results,'incomplete':True,'partial':True}
    def save():
        result['progress']={'completed':progress.done,'total':progress.total}
        engine.save('setup-result.json',result)
    try:
        progress.start('prepare')
        # Build the plan and recovery files without applying desktop settings.
        # Catch existing user modifications before asking for system changes.
        from .engine import Conflict
        if engine.read('pending.json'):raise Conflict('An interrupted operation needs recovery.')
        current=engine.read_current()
        errors=engine.check(current,allow_preferences=True) if current.get('installed') else []
        if errors:raise Conflict('Changes protected:\n'+'\n'.join(errors))
        from .applet_review import check_review
        check_review(engine,options)
        prepare_rescue(engine,ROOT);target=plan(engine,options)
        # Finish the read-only baseline snapshot before changing boot/login.
        # Per-file transactional backups are still taken by Engine.apply.
        reference_ready=not engine.read('baseline.json') or not engine.read_current().get('installed')
        if reference_ready:engine.safety_snapshot()
        if privileged:
            progress.start('system')
            try:detail=(system or SystemInstaller()).install(bool(options.get('boot_install')),bool(options.get('login_install')))
            except Exception as error:
                results.append({'key':'system','name':'Boot / Login','ok':False,'detail':str(error)})
                result['incomplete']=False;save();raise
            results.append({'key':'system','name':'Boot / Login','ok':True,'detail':detail});progress.completed();save()
        progress.start('desktop')
        try:
            check_review(engine,options)
            transaction=engine.apply(target,not reference_ready);result.update(summary(engine,transaction))
        except Exception as error:
            results.append({'key':'desktop','name':'Desktop','ok':False,'detail':str(error)})
            result['incomplete']=False;save()
            if privileged:
                raise RuntimeError(str(error)+'\nBoot/login was already installed and is backed up. System undo: pkexec python3 -I -B /var/lib/mint-xp-experience-system/appearance.py undo') from error
            raise
        progress.completed();save();addons=addons or Addons(engine)
        for key in chosen:
            progress.start('addons');engine.report('addons',0,None,CATALOG[key]['name'])
            try:detail=str(addons.install(key));ok=True
            except Exception as error:detail=str(error);ok=False
            results.append({'key':key,'name':CATALOG[key]['name'],'ok':ok,'detail':detail})
            if ok:progress.completed()
            save()
        result.update(incomplete=False,partial=any(not s['ok'] for s in results));save()
        return result
    finally:engine.progress=progress.observer
