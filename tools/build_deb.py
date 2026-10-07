#!/usr/bin/python3
"""Build a root-owned DEB from the audited source archive, with an optional user-session first-run prompt."""
import gzip,hashlib,os,re,shutil,subprocess,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def build():
 subprocess.run(['/usr/bin/python3','-B',str(ROOT/'tools/build_release.py')],check=True)
 upstream=(ROOT/'VERSION').read_text().strip()
 if not re.fullmatch(r'\d+\.\d+\.\d+-preview\.\d+',upstream):raise ValueError('Expected preview version')
 version=upstream.replace('-preview.','~preview.');archive=ROOT/'dist'/('mint-xp-experience-'+upstream+'.tar.gz')
 with tempfile.TemporaryDirectory(prefix='mintxp-deb-') as td:
  stage=Path(td);payload=stage/'usr/share/mint-xp-experience';payload.mkdir(parents=True)
  with tarfile.open(archive) as source:
   prefix='mint-xp-experience-'+upstream+'/'
   for member in source:
    name=member.name.removeprefix(prefix)
    if member.name==name or not member.isfile() or Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unexpected release entry')
    target=payload/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.extractfile(member).read());target.chmod(0o755 if member.mode&0o111 else 0o644)
  def write(name,data,mode=0o644):
   p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data.encode() if isinstance(data,str) else data);p.chmod(mode)
  write('usr/bin/mint-xp-experience','#!/bin/sh\nexec /usr/bin/python3 -B /usr/share/mint-xp-experience/launch.py "$@"\n',0o755)
  write('usr/share/applications/org.mintxp.Experience.desktop','[Desktop Entry]\nType=Application\nName=Mint XP Experience\nName[de]=Mint XP Experience – Einrichtung\nComment=Set up, back up and restore the XP-style desktop\nComment[de]=XP-Desktop einrichten, sichern und zurücksetzen\nExec=/usr/bin/mint-xp-experience\nIcon=preferences-desktop-theme\nTerminal=false\nCategories=Settings;DesktopSettings;\nStartupNotify=true\n')
  write('etc/xdg/autostart/mintxp-first-run.desktop','[Desktop Entry]\nType=Application\nName=Mint XP Experience setup\nExec=/usr/bin/mint-xp-experience auto-setup\nIcon=preferences-desktop-theme\nTerminal=false\nOnlyShowIn=X-Cinnamon;\nX-GNOME-Autostart-Delay=5\n')
  write('DEBIAN/postinst','#!/bin/sh\nset -e\nif [ "$1" = configure ]; then\n  /usr/bin/python3 -I -B /usr/share/mint-xp-experience/tools/session_autostart.py || true\nfi\nexit 0\n',0o755)
  size=sum(p.stat().st_size for p in (stage/'usr').rglob('*') if p.is_file())
  write('DEBIAN/control',f'''Package: mint-xp-experience
Version: {version}
Section: x11
Priority: optional
Architecture: all
Maintainer: Mint XP Experience contributors <noreply@example.invalid>
Installed-Size: {(size+1023)//1024}
Depends: python3 (>= 3.12), python3-gi, python3-cairo, python3-gi-cairo, gir1.2-gtk-3.0, gir1.2-gdkpixbuf-2.0, cinnamon (>= 6.6), cinnamon-desktop-data, nemo, dconf-cli, libglib2.0-bin, desktop-file-utils, xdg-utils, flatpak, gir1.2-webkit2-4.1, fonts-liberation, gnome-session-canberra, libarchive13t64 | libarchive13
Recommends: gvfs-backends
Suggests: policykit-1, lightdm-settings
Description: Reversible XP-style desktop setup for Linux Mint 22.3 Cinnamon
 Installs the setup assistant without applying a theme automatically.
 Start Mint XP Experience as your desktop user to choose components and
 create a backup before applying changes. Boot/login appearance is optional.
 Restore the desktop in the assistant before removing this application.
 This preview has no affiliation with Microsoft or Linux Mint.
''')
  write('usr/share/doc/mint-xp-experience/copyright', '''Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Mint XP Experience
Source: Source is included in /usr/share/mint-xp-experience
Disclaimer: Preview; upstream artwork provenance limitations are documented
 in /usr/share/mint-xp-experience/docs/SOURCES.md and docs/GAMES.md.

Files: *
Copyright: Respective authors; see retained source notices and docs/SOURCES.md
License: Various
 This is an aggregation. Original manager/Explorer code: GPL-3.0-or-later.
 Inherited theme, cursor, menu and taskbar modules retain their GPL notices.
 Original icons and wallpapers: CC0-1.0.
 Emoji keywords: MIT. Full licence texts and credits accompany the sources
 under /usr/share/mint-xp-experience/licenses and the respective asset folders.
''')
  changelog=f'mint-xp-experience ({version}) unstable; urgency=medium\n\n  * Separate setup wizard, safe language switching and first-run launch.\n\n -- Mint XP Experience contributors <noreply@example.invalid>  Sun, 04 Oct 2026 12:00:00 +0000\n'
  write('usr/share/doc/mint-xp-experience/changelog.Debian.gz',gzip.compress(changelog.encode(),mtime=0))
  files=sorted(p for folder in ('usr','etc') for p in (stage/folder).rglob('*') if p.is_file())
  write('DEBIAN/conffiles','/etc/xdg/autostart/mintxp-first-run.desktop\n')
  write('DEBIAN/md5sums',''.join(hashlib.md5(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(stage))+'\n' for p in files))
  for p in stage.rglob('*'):os.utime(p,(0,0))
  output=ROOT/'dist'/f'mint-xp-experience_{version}_all.deb'
  subprocess.run(['dpkg-deb','--root-owner-group','-Zxz','--build',str(stage),str(output)],env=dict(os.environ,SOURCE_DATE_EPOCH='0'),check=True)
 sums=ROOT/'dist/SHA256SUMS';sums.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in (archive,output)))
 print(output)
 return output
if __name__=='__main__':build()
