import argparse,json,sys
from .engine import Engine,Conflict
from .lifecycle import status,uninstall_all,export_diagnostic,prepare_rescue
from .components import ROOT
from .components import DEFAULTS,plan,preflight,refresh

def main():
    p=argparse.ArgumentParser(description='Mint XP Experience — reversible user-local theme manager')
    p.add_argument('command',nargs='?',default='gui',choices=['gui','setup','settings','auto-setup','status','verify','plan','install','backup','restore','uninstall','recover','diagnose','rescue','addons','addon-install','addon-remove','addon-recover','addon-verify','addon-open','sound-plan','sound-import','sound-verify','sound-test','sound-remove'])
    p.add_argument('--options',help='Path to a JSON option object');p.add_argument('--snapshot');p.add_argument('--yes',action='store_true')
    p.add_argument('--output',help='New local diagnostic JSON file')
    p.add_argument('--addon',choices=['minesweeper','solitaire','jspaint','space-cadet'])
    p.add_argument('--keep-addons',action='store_true',help='Keep manager-installed games/accessories during uninstall')
    p.add_argument('--source',help='Local WAV folder or ZIP/RAR/7z/TAR archive; :mint: selects existing Mint sounds')
    p.add_argument('--event',default='bell',help='Sound test event ID')
    args=p.parse_args()
    try:
        if args.command in ('gui','setup','settings','auto-setup'):
            from .gui import run
            if args.command=='auto-setup':
                from .first_run import automatic_setup
                raise SystemExit(automatic_setup())
            raise SystemExit(run(None if args.command=='gui' else args.command))
        e=Engine()
        if args.command.startswith('sound-'):
            from . import sounds
            options=dict(DEFAULTS,**e.read_current().get('options',{}))
            if args.source:options['sound_source']=args.source
            if args.command in ('sound-import','sound-remove') and not args.yes:raise Conflict('Review sound-plan first, then use --yes.')
            if args.command=='sound-plan':result=sounds.imported_plan(e,options,reimport=True)['report']
            elif args.command=='sound-import':result=sounds.apply_import(e,options)
            elif args.command=='sound-remove':result=sounds.remove_import(e)
            elif args.command=='sound-test':result=sounds.play_test(e,args.event)
            else:result=sounds.verify(e)
            print(json.dumps(result,ensure_ascii=False,indent=2))
        elif args.command=='addons' or args.command.startswith('addon-'):
            from .addons import Addons
            addons=Addons(e)
            if args.command=='addons':print(json.dumps(addons.status(),ensure_ascii=False,indent=2))
            else:
                if not args.addon:raise Conflict('Use --addon ID')
                action=args.command[6:]
                if action in ('install','remove','recover') and not args.yes:raise Conflict('Review docs/GAMES.md, then use --yes or the graphical assistant.')
                print(getattr(addons,{'open':'launch'}.get(action,action))(args.addon))
        elif args.command=='status':print(json.dumps(status(e),ensure_ascii=False,indent=2))
        elif args.command=='diagnose':
            if not args.output:raise Conflict('Use --output NEW-FILE.json; nothing is uploaded.')
            print(export_diagnostic(e,args.output,(ROOT/'VERSION').read_text().strip()))
        elif args.command=='rescue':print(prepare_rescue(e,ROOT))
        elif args.command=='verify':
            if e.read('pending.json'):raise Conflict('Interrupted operation; run recover')
            if e.read('baseline.json'):e.verify_objects(e.read('baseline.json'))
            errors=e.check(e.read_current(),allow_preferences=True)
            if errors:raise Conflict('\n'.join(errors))
            print('Installation and backup integrity: OK')
        elif args.command in ('plan','install'):
            options=dict(DEFAULTS)
            if args.options:
                with open(args.options) as f:options.update(json.load(f))
            preflight(options);desired=plan(e,options)
            print(json.dumps({'files':len(desired['files']),'settings':desired['settings'],'options':options},ensure_ascii=False,indent=2))
            if args.command=='install':
                if not args.yes:raise Conflict('Review the plan, then use --yes or the graphical assistant.')
                prepare_rescue(e,ROOT);print(e.apply(desired));refresh()
        elif args.command=='backup':print(e.backup())
        elif args.command=='recover':print(e.recover())
        elif args.command=='restore':
            if not args.yes or not args.snapshot:raise Conflict('restore requires --snapshot ID --yes')
            print(e.restore(args.snapshot));refresh()
        elif args.command=='uninstall':
            if not args.yes:raise Conflict('uninstall requires --yes or use the graphical assistant.')
            from .removal import complete
            print(complete(e,not args.keep_addons));refresh()
    except (Exception,KeyboardInterrupt) as error:
        print('Mint XP Experience: '+str(error),file=sys.stderr);raise SystemExit(1)
