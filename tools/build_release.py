#!/usr/bin/python3
"""Build an allowlisted source release; never collect private state/backups."""
import hashlib,tarfile,io
from pathlib import Path
root=Path(__file__).resolve().parent.parent
allowed=('mintxp','assets','locales','licenses','sources','docs','tests','tools','system','.github')
files=[root/name for name in ('launch.py','VERSION','LICENSE','README.md','.gitignore','install.sh','verify.sh','restore.sh')]
for name in allowed:
 files.extend(p for p in (root/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc'))
for p in files:
 if p.is_symlink():raise SystemExit('Unexpected symlink: '+str(p))
 if p.suffix in ('.py','.js','.json','.md','.css','.desktop'):
  text=p.read_text()
  if str(Path.home())+'/' in text or ('192.'+'168.') in text:raise SystemExit('Private data candidate: '+str(p))
# Sounds are private imports only; no audio is distributed.
if any(p.suffix.lower() in ('.wav','.ogg','.mp3','.flac','.oga') for p in files):
 raise SystemExit('Unexpected audio payload in release')
manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(root))+'\n' for p in sorted(files))
(root/'MANIFEST.sha256').write_text(manifest);files.append(root/'MANIFEST.sha256')
name='mint-xp-experience-'+(root/'VERSION').read_text().strip();out=root/'dist';out.mkdir(exist_ok=True)
archive=out/(name+'.tar.gz')
with tarfile.open(archive,'w:gz') as tar:
 for p in sorted(files):
  info=tar.gettarinfo(str(p),arcname=name+'/'+str(p.relative_to(root)));info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
  tar.addfile(info,io.BytesIO(p.read_bytes()))
(out/'SHA256SUMS').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print(archive);print(str(len(files))+' reviewed source files; no private runtime state included.')
