#!/usr/bin/python3
"""Best-effort postinst: ask active local users' systemd managers to open setup.

No GUI is run as root. No home files or session scripts are sourced by root.
The systemd user manager supplies its existing graphical session environment.
XDG autostart is the fallback if no suitable session manager is available.
"""
import os,pwd,subprocess

def command(argv):
    return subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=4,check=True).stdout

def eligible(properties):
    return (properties.get('Active')=='yes' and properties.get('Remote')=='no'
            and properties.get('Type') in ('x11','wayland')
            and properties.get('Class')=='user'
            and properties.get('User','').isdigit()
            and int(properties['User'])>=1000)

def main():
    if os.geteuid()!=0:return
    seen=set()
    try:sessions=command(['/usr/bin/loginctl','list-sessions','--no-legend','--no-pager']).splitlines()
    except (OSError,subprocess.SubprocessError):return
    for line in sessions:
        if not line.split():continue
        session=line.split()[0]
        if not session.isalnum():continue
        try:
            data=command(['/usr/bin/loginctl','show-session',session,'--no-pager'])
            props=dict(row.split('=',1) for row in data.splitlines() if '=' in row)
            if not eligible(props):continue
            uid=int(props['User'])
            if uid in seen:continue
            seen.add(uid);user=pwd.getpwuid(uid)
            runtime='/run/user/'+str(uid)
            if os.stat(runtime).st_uid!=uid:continue
            command(['/usr/sbin/runuser','-u',user.pw_name,'--','/usr/bin/env',
                     'XDG_RUNTIME_DIR='+runtime,'DBUS_SESSION_BUS_ADDRESS=unix:path='+runtime+'/bus',
                     '/usr/bin/systemd-run','--user','--collect','--no-block',
                     '--unit=mintxp-first-run','/usr/bin/mint-xp-experience','auto-setup'])
        except (KeyError,OSError,subprocess.SubprocessError):continue
if __name__=='__main__':main()
