"""Cancellable, isolated preview execution. GTK delivery remains on the main loop."""
from xp_locale import t as _xp
import json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
from core import file_for
from comfort import load_image

def generate(uri,mime,cancel):
    path=file_for(uri).get_path()
    if not path:return {'detail':_xp('Inhaltsvorschauen sind derzeit für lokale Dateien verfügbar.')},None
    with tempfile.TemporaryDirectory(prefix='xp-preview-') as directory:
        out=Path(directory)
        if cancel.is_set():return {},None
        process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).with_name('preview_worker.py')),path,mime,str(out)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        deadline=time.monotonic()+12
        try:
            while process.poll() is None:
                if cancel.wait(.04) or time.monotonic()>deadline:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    process.wait();return {'detail':'Vorschau abgebrochen.' if cancel.is_set() else 'Vorschau hat zu lange gedauert.'},None
            if cancel.is_set():return {},None
            if not (out/'result.json').exists():return {'detail':_xp('Für diese Datei konnte keine Vorschau erstellt werden.')},None
            result=json.loads((out/'result.json').read_text());pix=None
            if result.get('image')=='preview.png':pix=load_image((out/'preview.png').as_uri(),300)
            return result,pix
        finally:
            if process.poll() is None:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait()
