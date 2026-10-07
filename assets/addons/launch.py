#!/usr/bin/python3
"""Keep saved games/drawings outside all managed program files."""
import json,os,sys
from pathlib import Path
base=Path(__file__).resolve().parent
app=json.loads((base/'application.json').read_text());key=app['id']
if key not in ('minesweeper','solitaire','jspaint'):raise SystemExit('Unknown add-on')
data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'mintxp-addon-data'/key
data.mkdir(parents=True,exist_ok=True,mode=0o700);os.chdir(data)
if key=='solitaire':
 cmd=[str(base/'java/bin/java'),'-Djava.util.prefs.userRoot='+str(data/'preferences'),'-jar',str(base/'Solitaire.jar')]
 os.execv(cmd[0],cmd)
else:
 from webapp import run
 run(base,data,app)
