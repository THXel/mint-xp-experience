"""Detect local icon/audio packs in an isolated worker; keep private files private."""
import configparser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
import uuid
import wave
from .sound_sources import ARCHIVES, MAX_FILE, MAX_TOTAL, safe_name, _archive_worker

IMAGE_EXTENSIONS = {'.png', '.svg', '.ico', '.xpm'}
# Plain Windows icon folders get Linux event/icon names, without guessing IDs.
ICON_NAMES = {
    'mycomputer': 'computer user-desktop org.mintxp.Explorer',
    'computer': 'computer user-desktop org.mintxp.Explorer',
    'arbeitsplatz': 'computer user-desktop org.mintxp.Explorer',
    'folder': 'folder inode-directory system-file-manager',
    'ordner': 'folder inode-directory system-file-manager',
    'mydocuments': 'user-home folder-documents', 'eigenedateien': 'user-home folder-documents',
    'recyclebin': 'user-trash', 'recyclebinempty': 'user-trash',
    'papierkorb': 'user-trash', 'recyclebinfull': 'user-trash-full',
    'network': 'network-workgroup network-wired', 'mynetworkplaces': 'network-workgroup network-wired',
    'netzwerkumgebung': 'network-workgroup network-wired',
    'harddisk': 'drive-harddisk', 'harddrive': 'drive-harddisk',
    'localdisk': 'drive-harddisk', 'festplatte': 'drive-harddisk',
    'cdrom': 'drive-optical', 'printer': 'printer', 'drucker': 'printer',
    'controlpanel': 'preferences-system cinnamon-settings',
    'systemsteuerung': 'preferences-system cinnamon-settings',
}


def icon_names(stem):
    key = re.sub(r'[^a-z0-9]', '', stem.casefold())
    aliases = ICON_NAMES.get(key)
    if aliases:
        return aliases.split()
    return [stem] if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@+-]{0,127}', stem) else []


def folder_records(source, destination):
    total = count = 0
    records = []
    for directory, dirs, files in os.walk(source, followlinks=False):
        for name in dirs + files:
            count += 1
            if count > 16000:
                raise ValueError('Media folder has too many entries')
            p = Path(directory) / name
            if p.is_symlink() and (not p.resolve().is_relative_to(source) or not p.resolve().is_file()):
                raise ValueError('External or directory media link rejected')
            if p.is_dir():
                continue
            if not p.is_file():
                raise ValueError('Special media file rejected')
            rel = safe_name(str(p.relative_to(source)))
            if p.suffix.lower() not in IMAGE_EXTENSIONS | {'.wav', '.disabled'} and p.name != 'index.theme':
                continue
            size = p.stat().st_size
            total += size
            if size > MAX_FILE or total > MAX_TOTAL or len(records) >= 12000:
                raise ValueError('Media import exceeds size limit')
            with p.open('rb') as f:
                data = f.read(MAX_FILE + 1)
            if len(data) != size:
                raise ValueError('Media file changed while reading')
            blob = str(len(records)) + '.bin'
            (destination / blob).write_bytes(data)
            records.append([rel, blob])
    return records


def validate_wav(data):
    with wave.open(io.BytesIO(data)) as wav:
        if (wav.getcomptype() != 'NONE' or wav.getnchannels() not in (1, 2)
                or wav.getsampwidth() not in (1, 2, 3, 4)
                or not 8000 <= wav.getframerate() <= 192000 or not wav.getnframes()):
            raise ValueError('Unsupported PCM WAV in media pack')
        if len(wav.readframes(wav.getnframes())) != wav.getnframes()*wav.getnchannels()*wav.getsampwidth():
            raise ValueError('Truncated WAV in media pack')


def decode_image(data, suffix, size=None):
    import gi
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf
    if suffix == '.svg':
        # SVG is untrusted too: refuse entities and references to external files/URLs.
        import xml.etree.ElementTree as ET
        if re.search(br'<!\s*(?:DOCTYPE|ENTITY)', data, re.I):
            raise ValueError('SVG entities are unsupported')
        text = data.decode('utf-8')
        tree = ET.fromstring(text)
        for element in tree.iter():
            if element.tag.split('}')[-1] in ('script', 'foreignObject'):
                raise ValueError('Active SVG content rejected')
            for key, value in element.attrib.items():
                if key.split('}')[-1] in ('href', 'src') and not value.startswith('#'):
                    raise ValueError('External SVG reference rejected')
        text = data.decode('utf-8')
        for match in re.findall(r'url\((.*?)\)', text, re.I):
            if not match.strip(" \t\n\"'").startswith('#'):
                raise ValueError('External SVG reference rejected')
        if '@import' in text.casefold():
            raise ValueError('External SVG style rejected')
    loader = GdkPixbuf.PixbufLoader.new_with_type(suffix.removeprefix('.'))
    def dimensions(l, width, height):
        if width > 4096 or height > 4096 or width * height > 4096**2:
            l.set_size(1, 1)
            dimensions.invalid = True
        elif size:
            l.set_size(max(1, round(size * width/max(width,height))),
                       max(1, round(size * height/max(width,height))))
    dimensions.invalid = False
    loader.connect('size-prepared', dimensions)
    loader.write(data)
    loader.close()
    pix = loader.get_pixbuf()
    if dimensions.invalid or pix is None:
        raise ValueError('Oversized or unreadable icon')
    return pix


def worker(source, dest):
    source, dest = Path(source), Path(dest)
    if source == Path.home() or source == Path('/'):
        raise ValueError('Choose a media pack, not the complete home/filesystem')
    raw = dest / 'raw'
    raw.mkdir()
    disabled=[]
    if source.is_dir():records=folder_records(source, raw)
    else:
        archive=_archive_worker(source,raw,media=True);records=archive['files'];disabled=archive['disabled']
    files = {name: raw / blob for name, blob in records}
    waves = {name: p for name, p in files.items() if PurePosixPath(name).suffix.lower() == '.wav'}
    images = {name: p for name, p in files.items() if PurePosixPath(name).suffix.lower() in IMAGE_EXTENSIONS}
    written = {};output_bytes=0
    def save(name, data):
        nonlocal output_bytes
        output_bytes += len(data)
        if output_bytes > 256*1024*1024 or len(written)>48000:raise ValueError('Converted media size limit')
        safe_name(name)
        p = dest / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        written[name] = hashlib.sha256(data).hexdigest()
    for name,p in files.items():
        rel=PurePosixPath(name)
        if rel.suffix.lower()=='.disabled' and rel.parent.name=='stereo':
            if p.stat().st_size:raise ValueError('Invalid disabled sound marker')
            disabled.append(rel.stem)
    if waves:
        for event in disabled:
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',event):raise ValueError('Invalid disabled sound event')
            save('sounds/stereo/'+event+'.disabled',b'')
    for name, p in waves.items():
        data = p.read_bytes()
        validate_wav(data)
        save('sounds/' + name, data)
    # Confirm actual audio event names, rather than accepting arbitrary music WAVs.
    mapped = 0
    if waves:
        from .engine import Engine
        from .sounds import imported_plan, ALIASES, CINNAMON
        from .components import DEFAULTS
        class NoSettings:
            def get(self, key):return None
            def effective(self, schema, key):return False if key.endswith('enabled') else ''
            def literal(self, value):return json.dumps(value)
        home = dest / 'probe-home'; home.mkdir()
        e = Engine(home, dest/'probe-state', NoSettings())
        report = imported_plan(e, dict(DEFAULTS, sound_source=str(dest/'sounds'), sound_preserve=False))['report']
        mapped = len(report['aliases']) + sum(x['mapped'] for x in report['cinnamon'].values())
        if not mapped and not report['ambiguous']:
            raise ValueError('WAV files found, but no system sounds recognized; use event names such as Notify or Ding')
        import shutil
        shutil.rmtree(home);shutil.rmtree(dest/'probe-state')
    icons_count = 0
    indexes = [n for n in files if PurePosixPath(n).name == 'index.theme']
    themes = []
    for name in indexes:
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        cp.read_string(files[name].read_text())
        if cp.has_section('Icon Theme') and cp['Icon Theme'].get('Directories'):
            themes.append((name, cp))
    if len(themes) > 1:
        raise ValueError('Multiple icon themes found; select one theme folder or archive')
    if themes:
        index, cp = themes[0];base = PurePosixPath(index).parent
        for name, p in images.items():
            path = PurePosixPath(name)
            if not path.is_relative_to(base):continue
            relative = str(path.relative_to(base))
            decode_image(p.read_bytes(), path.suffix.lower())
            save('icons/' + relative, p.read_bytes());icons_count += 1
        # Reject references outside the selected theme; installer supplies fallback icons.
        for key in ('Directories', 'ScaledDirectories'):
            for directory in cp['Icon Theme'].get(key, '').split(','):
                if directory:safe_name(directory)
        if icons_count:save('icons/index.theme', files[index].read_bytes())
    elif images:
        # Loose PNG/ICO/SVG collections become a private freedesktop theme.
        choices = {}
        for name, p in images.items():
            pix = decode_image(p.read_bytes(), PurePosixPath(name).suffix.lower())
            for alias in icon_names(PurePosixPath(name).stem):
                old = choices.get(alias)
                area = pix.get_width()*pix.get_height()
                if old is None or area > old[0]:choices[alias] = (area, p, PurePosixPath(name).suffix.lower())
                elif area == old[0] and p.read_bytes() != old[1].read_bytes():
                    raise ValueError('Different icons share a name; select one variant: ' + alias)
        for alias, (_, p, suffix) in choices.items():
            for size in (16, 24, 32, 48):
                pix = decode_image(p.read_bytes(), suffix, size)
                ok, png = pix.save_to_bufferv('png', [], [])
                if not ok:raise ValueError('Icon conversion failed')
                save('icons/'+str(size)+'/'+alias+'.png', bytes(png))
        icons_count = len(choices)
        if icons_count:
            index = '[Icon Theme]\nName=Private imported icons\nInherits=Mint-XP-Experience-Icons,Mint-Y,Adwaita,hicolor\nDirectories=16,24,32,48\n'
            for size in (16,24,32,48):index += f'\n[{size}]\nSize={size}\nType=Fixed\n'
            save('icons/index.theme', index.encode())
    if not waves and not icons_count:
        raise ValueError('No supported sound or icon pack found')
    import shutil
    shutil.rmtree(raw)
    result = {'sounds':len(waves), 'icons':icons_count, 'mapped_events':mapped,
              'files':written, 'private_import':True, 'source_name':source.name}
    (dest/'report.json').write_text(json.dumps(result, indent=2))
    return result


def import_media(engine, path):
    source = Path(path).expanduser().resolve(strict=True)
    if source.suffix.lower() == '.iso' and source.is_file():
        from .iso_import import import_iso
        return import_iso(engine, source)
    if not source.is_dir() and not (source.is_file() and source.name.lower().endswith(ARCHIVES)):
        raise ValueError('Choose an ISO, folder, ZIP, RAR, 7z or TAR archive')
    parent = engine.state/'imports'
    if parent.is_symlink():raise ValueError('Linked import directory rejected')
    parent.mkdir(mode=0o700, exist_ok=True)
    engine.report('media', 0, None, source.name)
    with tempfile.TemporaryDirectory(prefix='.pack-', dir=parent) as td:
        root = Path(__file__).resolve().parent.parent
        script = ('import sys,resource;sys.path.insert(0,sys.argv[1]);'
                  'resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824));'
                  'resource.setrlimit(resource.RLIMIT_CPU,(90,90));'
                  'resource.setrlimit(resource.RLIMIT_FSIZE,(16777216,16777216));'
                  'from mintxp.media_import import worker;worker(sys.argv[2],sys.argv[3])')
        run = subprocess.run(['/usr/bin/python3','-I','-B','-c',script,str(root),str(source),td],
                             capture_output=True,text=True,timeout=120)
        if run.returncode:raise ValueError('Media import: '+(run.stderr[-1400:] or 'worker stopped'))
        result = json.loads((Path(td)/'report.json').read_text())
        for name, digest in result['files'].items():
            safe_name(name);p=Path(td)/name
            if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
                raise ValueError('Media verification failed')
        target = parent/('media-'+uuid.uuid4().hex);Path(td).rename(target)
    result.update(sound_path=str(target/'sounds') if result['sounds'] else '',
                  icon_path=str(target/'icons') if result['icons'] else '')
    if result['sound_path']:
        from .sounds import imported_plan
        from .components import DEFAULTS
        result['sound_plan']=imported_plan(engine,dict(DEFAULTS,sound_source=result['sound_path'],sound_preserve=False),reimport=True)
    return result
