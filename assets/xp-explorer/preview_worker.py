"""Bounded local-file preview worker. No macros, extraction, or file execution."""
from xp_locale import t as _xp
import json,os,resource,stat,subprocess,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
MAX_TEXT=12000
TEXT_EXT={'.txt','.md','.rst','.log','.csv','.tsv','.json','.xml','.yaml','.yml','.toml','.ini','.conf','.cfg','.py','.js','.ts','.css','.html','.sh','.c','.cpp','.h','.rs','.java','.sql','.desktop','.svg'}

def run(args,out=None):
    with open(out,'wb') if out else open(os.devnull,'wb') as stream:
        subprocess.run(args,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.DEVNULL,check=True,timeout=7,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))

def xml_member(z,name):
    info=z.getinfo(name)
    if info.file_size>2*1024*1024 or info.file_size>max(1,info.compress_size)*150:raise ValueError(_xp('Dokumentteil zu groß für die Vorschau.'))
    data=z.read(info)
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError(_xp('XML-Deklaration wird nicht für Vorschauen verarbeitet.'))
    return ET.fromstring(data)
def localtag(tag):return tag.rsplit('}',1)[-1]
def paragraphs(root):
    output=[]
    for node in root.iter():
        if localtag(node.tag) in ('p','h'):
            text=''.join(node.itertext()).strip()
            if text:output.append(text)
            if len(output)>=150 or sum(map(len,output))>=MAX_TEXT:break
    return '\n\n'.join(output)[:MAX_TEXT]

def document(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)>10000:raise ValueError(_xp('Zu viele Dokumentteile für die Vorschau.'))
        ext=path.suffix.lower()
        if ext=='.docx':return 'Word-Dokument · Textauszug',paragraphs(xml_member(z,'word/document.xml'))
        if ext in ('.odt','.ods','.odp'):return 'OpenDocument · Textauszug',paragraphs(xml_member(z,'content.xml'))
        if ext=='.pptx':
            return _xp('Präsentation · Text der ersten Folie'),paragraphs(xml_member(z,'ppt/slides/slide1.xml'))
        if ext=='.xlsx':
            strings=[]
            if 'xl/sharedStrings.xml' in names:
                strings=[''.join(n.itertext()) for n in xml_member(z,'xl/sharedStrings.xml')]
            # sheet1 is explicitly named; do not claim workbook display order.
            root=xml_member(z,'xl/worksheets/sheet1.xml');lines=[]
            for row in [n for n in root.iter() if localtag(n.tag)=='row'][:30]:
                cells=[]
                for cell in list(row)[:20]:
                    val=next((n.text or '' for n in cell if localtag(n.tag)=='v'),'')
                    if cell.get('t')=='s':val=strings[int(val)] if val.isdigit() and int(val)<len(strings) else ''
                    elif cell.get('t')=='inlineStr':val=''.join(cell.itertext())
                    cells.append(cell.get('r','')+': '+val)
                lines.append(' | '.join(cells))
            return 'Tabelle · sheet1, bis zu 30 Zeilen (gespeicherte Werte)', '\n'.join(lines)[:MAX_TEXT]
    return '', ''

def render(path,mime,out):
    path=Path(path);st=path.stat()
    if not stat.S_ISREG(st.st_mode):return {'detail':_xp('Für diesen Eintrag ist keine Dateivorschau verfügbar.')}
    size=st.st_size;ext=path.suffix.lower();result={'detail':'','text':'','image':None}
    if mime.startswith('image/'):
        if size>50*1024*1024:raise ValueError(_xp('Bild zu groß für die Vorschau (maximal 50 MB).'))
        import gi;gi.require_version('GdkPixbuf','2.0');from gi.repository import GdkPixbuf
        info,w,h=GdkPixbuf.Pixbuf.get_file_info(str(path))
        if not info or w*h>40_000_000:raise ValueError(_xp('Bildformat oder Bildgröße nicht für die Vorschau geeignet.'))
        GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path),270,300,True).savev(str(out/'preview.png'),'png',[],[])
        result.update(image='preview.png',detail=f'Bild · {w} × {h} Pixel')
    elif mime=='application/pdf' or ext=='.pdf':
        if size>100*1024*1024:raise ValueError(_xp('PDF zu groß für die Vorschau (maximal 100 MB).'))
        run(['/usr/bin/pdftoppm','-f','1','-l','1','-singlefile','-scale-to','300','-png',str(path),str(out/'preview')])
        result.update(image='preview.png',detail='PDF · erste Seite')
        try:
            run(['/usr/bin/pdftotext','-f','1','-l','1',str(path),str(out/'pdf.txt')]);result['text']=(out/'pdf.txt').read_text(errors='replace')[:MAX_TEXT]
        except Exception:pass
    elif ext in ('.docx','.odt','.ods','.odp','.pptx','.xlsx'):
        if size>100*1024*1024:raise ValueError(_xp('Dokument zu groß für die Vorschau (maximal 100 MB).'))
        detail,text=document(path);result.update(detail=detail+_xp('\nOhne Originallayout; keine Makros oder Formeln ausgeführt.'),text=text or 'Kein gespeicherter Text gefunden.')
    elif mime.startswith(('audio/','video/')):
        run(['/usr/bin/ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_entries','format=duration,format_name:format_tags=title,artist,album:stream=codec_type,codec_name,width,height,sample_rate,channels','-of','json',str(path)],out/'media.json')
        data=json.loads((out/'media.json').read_text());fmt=data.get('format',{});lines=[]
        try:
            seconds=int(float(fmt['duration']));lines.append(f'Dauer: {seconds//60}:{seconds%60:02d}')
        except (KeyError,ValueError,OverflowError):pass
        for key,title in [('title','Titel'),('artist','Interpret'),('album','Album')]:
            value=fmt.get('tags',{}).get(key)
            if value:lines.append(f'{title}: {str(value)[:300]}')
        for stream in data.get('streams',[])[:5]:
            if stream.get('codec_type')=='video':lines.append(f"Video: {stream.get('codec_name','')} · {stream.get('width','?')} × {stream.get('height','?')}")
            elif stream.get('codec_type')=='audio':lines.append(_xp('Audio: {0} · {1} Hz · {2} Kanäle').format(stream.get('codec_name', ''), stream.get('sample_rate', '?'), stream.get('channels', '?')))
        result.update(detail='Medieninformationen · keine automatische Wiedergabe',text='\n'.join(lines) or _xp('Keine Medieninformationen verfügbar.'))
        if mime.startswith('video/'):
            try:
                run(['/usr/bin/ffmpeg','-nostdin','-v','error','-protocol_whitelist','file,pipe','-threads','1','-i',str(path),'-frames:v','1','-vf','scale=270:220:force_original_aspect_ratio=decrease','-threads','1','-y',str(out/'preview.png')]);result['image']='preview.png'
            except Exception:result['detail']+=_xp('\nKein Standbild verfügbar.')
    elif ext=='.zip' or mime=='application/zip':
        if size>100*1024*1024:raise ValueError(_xp('Archiv zu groß für die Vorschau (maximal 100 MB).'))
        with zipfile.ZipFile(path) as z:
            entries=z.infolist();result.update(detail=_xp('ZIP-Archiv · {0} Einträge · nichts entpackt').format(len(entries)),text='\n'.join(i.filename[:180] for i in entries[:80])+(_xp('\n… weitere Einträge') if len(entries)>80 else ''))
    elif mime.startswith('text/') or ext in TEXT_EXT or mime in ('application/json','application/xml','application/javascript'):
        with path.open('rb') as f:raw=f.read(65536)
        if raw.startswith((b'\xff\xfe',b'\xfe\xff')):encoding='utf-16'
        else:
            if b'\0' in raw:raise ValueError(_xp('Binärdaten: keine Textvorschau.'))
            try:raw.decode('utf-8-sig');encoding='utf-8-sig'
            except UnicodeDecodeError:encoding='cp1252'
        text=raw.decode(encoding,errors='replace');short=size>len(raw) or len(text)>MAX_TEXT
        result.update(detail='Textauszug'+(_xp(' · gekürzt') if short else '')+' · '+encoding,text=text[:MAX_TEXT])
    else:result['detail']=_xp('Für dieses Format gibt es noch keine Inhaltsvorschau.\nMit „Öffnen mit“ kannst du eine passende Anwendung wählen.')
    return result

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_CPU,(12,12));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024**2,4*1024**2))
    out=Path(sys.argv[3])
    try:result=render(sys.argv[1],sys.argv[2],out)
    except FileNotFoundError:result={'detail':_xp('Datei oder benötigtes Vorschauprogramm nicht verfügbar.')}
    except Exception as e:result={'detail':_xp('Keine Vorschau verfügbar. ')+(str(e)[:180] if isinstance(e,ValueError) else _xp('Die Datei ist beschädigt, geschützt oder für die Vorschau zu aufwendig.'))}
    if result.get('text'):
        result['text']=''.join(c for c in result['text'].replace('\x0c','\n') if ord(c)>=32 or c in '\n\t')[:MAX_TEXT].rstrip()
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False))
