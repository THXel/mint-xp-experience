#!/usr/bin/python3
"""Read-only prerequisite report. No installation, settings writes or credentials."""
import argparse,json,os,platform,re,shutil,subprocess

def report():
    rows=[]
    def add(name,ok,detail,required=True):rows.append({'check':name,'status':'PASS' if ok else 'FAIL' if required else 'WARN','detail':detail})
    try:release=platform.freedesktop_os_release()
    except OSError:release={}
    add('Linux Mint 22.3',release.get('ID')=='linuxmint' and release.get('VERSION_ID')=='22.3',release.get('PRETTY_NAME','Unknown OS'))
    binary=shutil.which('cinnamon');version='not found'
    if binary:
        try:version=subprocess.run([binary,'--version'],capture_output=True,text=True,timeout=8).stdout.strip()
        except (OSError,subprocess.TimeoutExpired):version='version check failed'
    add('Cinnamon 6.6',bool(re.search(r'\b6\.6\.',version)),version)
    session=os.environ.get('XDG_SESSION_TYPE','unknown');add('X11 desktop session',session=='x11' and bool(os.environ.get('DISPLAY')),session)
    add('Desktop user',os.geteuid()!=0,'non-root' if os.geteuid()!=0 else 'Do not run the user installer with sudo')
    for binary in ('dconf','update-desktop-database','gio','xdg-open','cjs'):
        add(binary,bool(shutil.which(binary)),'available' if shutil.which(binary) else 'missing')
    for ns,version in [('Gtk','3.0'),('Gio','2.0'),('GdkPixbuf','2.0')]:
        try:
            import gi
            gi.require_version(ns,version);__import__('gi.repository',fromlist=[ns]);ok=True
        except (ImportError,ValueError):ok=False
        add(ns+' '+version,ok,'available' if ok else 'missing Python GI namespace')
    for binary in ('pkexec','plymouth','mkinitramfs','lsinitramfs'):
        add('Optional boot/login: '+binary,bool(shutil.which(binary)),'available' if shutil.which(binary) else 'missing; needed only for the optional system appearance',False)
    add('User settings transport',bool(os.environ.get('DBUS_SESSION_BUS_ADDRESS')),'session bus environment present' if os.environ.get('DBUS_SESSION_BUS_ADDRESS') else 'Run inside the logged-in desktop terminal')
    return {'format':1,'read_only':True,'checks':rows,'ready_for_user_install':not any(r['status']=='FAIL' for r in rows),'clean_vm_acceptance':'not_performed'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--json',action='store_true');args=parser.parse_args();data=report()
    if args.json:print(json.dumps(data,indent=2))
    else:
        for row in data['checks']:print(f"{row['status']:4}  {row['check']}: {row['detail']}")
        print('Read-only check; no installation or clean-VM acceptance performed.')
    return 0 if data['ready_for_user_install'] else 1
if __name__=='__main__':raise SystemExit(main())
