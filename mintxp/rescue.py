"""Text-console recovery: no GTK and no dependency on the installed theme runtime."""
import argparse,json,os
from pathlib import Path
from .engine import Engine,Conflict
from .lifecycle import status,uninstall_all

def main():
    p=argparse.ArgumentParser(description='Mint XP rescue — retained backups, no graphical desktop required')
    p.add_argument('action',nargs='?',default='check',choices=['check','recover','restore','uninstall']);p.add_argument('--snapshot');p.add_argument('--yes',action='store_true');args=p.parse_args()
    try:
        if os.geteuid()==0:raise Conflict('Run this as your own desktop user, without sudo. Only the system step requests sudo/polkit.')
        bus=Path('/run/user')/str(os.getuid())/'bus'
        if not os.environ.get('DBUS_SESSION_BUS_ADDRESS') and bus.exists():os.environ['DBUS_SESSION_BUS_ADDRESS']='unix:path='+str(bus)
        e=Engine()
        if args.action=='check':
            report=status(e)
            if e.read('baseline.json'):e.verify_objects(e.read('baseline.json'))
            print(json.dumps(report,indent=2))
            if report['pending'] or report['changed_file_count'] or report['changed_setting_count']:raise Conflict('Changes or an interrupted operation require review before recovery.')
            print('Actions: recover --yes | restore --snapshot ID --yes | uninstall --yes')
            for item in sorted((e.state/'snapshots').glob('*.json'),reverse=True):print('Snapshot:',item.stem)
            return
        if not args.yes:raise Conflict('Review check first. A modifying action requires --yes.')
        if args.action=='recover':print(e.recover())
        elif args.action=='restore':
            if not args.snapshot:raise Conflict('Supply --snapshot ID.')
            print(e.restore(args.snapshot))
        else:print(uninstall_all(e))
    except (Exception,KeyboardInterrupt) as exc:p.exit(1,'Mint XP rescue: '+str(exc)+'\n')
if __name__=='__main__':main()
