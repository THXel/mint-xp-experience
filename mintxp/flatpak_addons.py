"""Opt-in Flathub accessories; never remove pre-existing apps or application data.

Theme restore and add-on removal are deliberately separate operations. No Flatpak
payload or upstream game artwork is included in the source release.
"""
import json, os, shutil, subprocess
from pathlib import Path
from .engine import Conflict

CATALOG = {
    'space-cadet': {'name':'3D Pinball (Flatpak)', 'id':'com.github.k4zmu2a.spacecadetpinball',
        'license':'MIT (engine); original game data downloaded separately',
        'url':'https://github.com/k4zmu2a/SpaceCadetPinball', 'kind':'game'},
}
EXTERNAL = {}
TRUSTED_REMOTE = 'https://dl.flathub.org/repo/'

class FlatpakAddons:
    def __init__(self, engine, runner=None):
        self.engine=engine
        self.runner=runner or self._run

    def _run(self, args, progress=False):
        # argv only; no shell or password handling. Flatpak performs signed OSTree verification.
        command=['flatpak',*args]
        if not progress:
            result=subprocess.run(command,capture_output=True,text=True,timeout=60)
            if result.returncode:raise Conflict(result.stderr.strip() or 'Flatpak query failed')
            return result.stdout
        env=dict(os.environ,TERM='dumb',LC_ALL='C.UTF-8')
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env)
        tail=[]
        try:
            for line in process.stdout:
                line=line.strip()
                if line:
                    tail.append(line);tail=tail[-15:]
                    # Unknown totals pulse; never infer overall progress from a single runtime.
                    self.engine.report('addons',0,None,line[:400])
            if process.wait():raise Conflict('\n'.join(tail) or 'Flatpak operation failed')
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            raise
        finally:process.stdout.close()
        return '\n'.join(tail)

    def records(self):
        return self.engine.read('addons.json',{})

    def inventory(self):
        if self.runner==self._run and not shutil.which('flatpak'):
            raise Conflict('Flatpak is not installed. Install Flatpak using the Mint software manager.')
        result={}
        for line in self.runner(['list','--app','--columns=application,installation']).splitlines():
            if not line.strip():continue
            parts=line.split('\t')
            if len(parts)!=2 or not all(parts):raise Conflict('Unexpected Flatpak inventory; no changes made.')
            result.setdefault(parts[0],[]).append(parts[1])
        return result

    def desktop(self, name):
        for directory in (self.engine.home/'.local/share/applications',Path('/usr/local/share/applications'),Path('/usr/share/applications')):
            path=directory/name
            if path.is_file():return str(path)
        return None

    def status(self):
        inventory=self.inventory();records=self.records();result={}
        for key,item in CATALOG.items():
            native=self.desktop(item['id']+'.desktop')
            # Native distribution package desktop names can differ from Flatpak IDs.
            native=native or self.desktop(item['id']+'.desktop')
            scopes=inventory.get(item['id'],[]);record=records.get(key,{})
            if record.get('state') in ('installing','removing','uncertain'):state='interrupted'
            elif record.get('state')=='installed' and 'user' in scopes:state='managed'
            elif scopes or native:state='external'
            else:state='absent'
            result[key]=dict(item,state=state,scopes=scopes,desktop=native)
        for key,item in EXTERNAL.items():
            native=self.desktop(item['desktop']) if item.get('desktop') else None
            scopes=inventory.get(item.get('id'),[])
            result[key]=dict(item,state='external' if native or scopes else 'manual',scopes=scopes,desktop=native)
        return result

    def ensure_remote(self):
        remotes={}
        for line in self.runner(['remotes','--user','--columns=name,url']).splitlines():
            if not line.strip():continue
            parts=line.split('\t')
            if len(parts)!=2:raise Conflict('Unexpected Flatpak remote list')
            remotes[parts[0]]=parts[1]
        if 'flathub' in remotes:
            if remotes['flathub'].rstrip('/') != TRUSTED_REMOTE.rstrip('/'):
                raise Conflict('The user remote named flathub has a different URL; no changes made.')
        else:
            self.runner(['remote-add','--user','--if-not-exists','flathub','https://dl.flathub.org/repo/flathub.flatpakrepo'],True)
            # Check even after --if-not-exists, in case another process created it.
            self.ensure_remote()

    def install(self,key):
        if key not in CATALOG:raise Conflict('This entry has no automatic installer.')
        with self.engine.lock():
            status=self.status()[key]
            if status['state'] in ('managed','external'):return 'Already installed; unchanged.'
            if status['state']=='interrupted':raise Conflict('Reconcile the interrupted operation first.')
            self.ensure_remote()
            # A fresh query before taking ownership protects existing user/system installations.
            if self.status()[key]['state']!='absent':return 'Already installed; unchanged.'
            records=self.records();record={'id':CATALOG[key]['id'],'state':'installing','scope':'user'}
            records[key]=record;self.engine.save('addons.json',records)
            try:
                self.engine.report('addons',0,None,CATALOG[key]['name'])
                self.runner(['install','--user','--noninteractive','--assumeyes','flathub',record['id']],True)
                if 'user' not in self.inventory().get(record['id'],[]):raise Conflict('Installation could not be verified.')
                record.update(state='installed',commit=self.runner(['info','--user','--show-commit',record['id']]).strip())
                self.engine.save('addons.json',records)
            except BaseException:
                # An interrupted external package operation is not safely attributable.
                # Never auto-delete a possibly shared/external installation.
                record['state']='uncertain';self.engine.save('addons.json',records);raise
        return CATALOG[key]['name']+' — installed'

    def remove(self,key):
        if key not in CATALOG:raise Conflict('External applications are protected.')
        with self.engine.lock():
            records=self.records();record=records.get(key,{})
            if record.get('state')!='installed':raise Conflict('Only a verified installation made by this manager can be removed.')
            if record.get('id')!=CATALOG[key]['id'] or record.get('scope')!='user':raise Conflict('Invalid add-on ownership record.')
            record['state']='removing';self.engine.save('addons.json',records)
            try:
                if 'user' in self.inventory().get(record['id'],[]):
                    # No --delete-data, --unused, system scope, wildcard or dependency purge.
                    self.runner(['uninstall','--user','--noninteractive','--assumeyes',record['id']],True)
                if 'user' in self.inventory().get(record['id'],[]):raise Conflict('Removal could not be verified.')
                records.pop(key);self.engine.save('addons.json',records)
            except BaseException:
                record['state']='uncertain';self.engine.save('addons.json',records);raise
        return CATALOG[key]['name']+' — removed; application data retained'

    def reconcile(self,key):
        if key not in CATALOG:raise Conflict('Unknown add-on')
        with self.engine.lock():
            records=self.records();record=records.get(key,{})
            if record.get('state') not in ('installing','removing','uncertain'):raise Conflict('No interrupted operation for this add-on.')
            # Confirm inventory is readable before changing the record. Installed apps
            # become external/protected; there is no destructive guess about ownership.
            self.inventory();records.pop(key);self.engine.save('addons.json',records)
        return 'Reconciled. Any existing application and its data were preserved.'

    def launch(self,key):
        entry=self.status()[key]
        if entry['state'] not in ('managed','external'):raise Conflict('Application is not installed.')
        if entry.get('id') and entry['scopes']:
            scope='--user' if 'user' in entry['scopes'] else '--system'
            if scope=='--system' and 'system' not in entry['scopes']:raise Conflict('Open this application from its installed desktop launcher.')
            subprocess.Popen(['flatpak','run',scope,entry['id']],start_new_session=True)
        elif entry['desktop']:
            import gi
            from gi.repository import Gio
            app=Gio.DesktopAppInfo.new_from_filename(entry['desktop'])
            if not app or not app.launch([],None):raise Conflict('Could not open the installed launcher.')
