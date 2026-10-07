#!/usr/bin/python3
"""Reproducible, original vector artwork. Art: CC0-1.0; generator: GPL-3.0-or-later."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DEFS='''<defs>
<linearGradient id="gold" x2=".25" y2="1"><stop stop-color="#fff8b8"/><stop offset=".44" stop-color="#ffdf71"/><stop offset="1" stop-color="#df9a28"/></linearGradient>
<linearGradient id="blue" x2=".65" y2="1"><stop stop-color="#b6edff"/><stop offset=".42" stop-color="#4298ec"/><stop offset="1" stop-color="#174aa3"/></linearGradient>
<linearGradient id="metal" x2=".2" y2="1"><stop stop-color="#fff"/><stop offset=".48" stop-color="#e3e8ec"/><stop offset="1" stop-color="#8393a7"/></linearGradient>
<linearGradient id="green" x2=".25" y2="1"><stop stop-color="#d3f594"/><stop offset=".48" stop-color="#79c146"/><stop offset="1" stop-color="#2f7b23"/></linearGradient>
<linearGradient id="red" x2=".2" y2="1"><stop stop-color="#ffd0af"/><stop offset=".42" stop-color="#f67c4c"/><stop offset="1" stop-color="#bb302b"/></linearGradient>
<linearGradient id="paper" x2=".1" y2="1"><stop stop-color="#fff"/><stop offset="1" stop-color="#e7eef9"/></linearGradient>
</defs>'''
def svg(body):return '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'+DEFS+'<ellipse cx="32" cy="57" rx="25" ry="3" fill="#213955" opacity=".16"/>'+body+'</svg>\n'
def folder(badge=''):
 # Own perspective geometry: warm rear tab, paper lining and beveled front flap.
 return '<path d="M8 17L26 12L34 17L54 15L56 43L14 56L8 51Z" fill="#c99539" stroke="#85642c" stroke-width="1.2"/><path d="M10 17L25 14L31 20L53 17L51 42L13 53Z" fill="url(#gold)"/><path d="M14 23L49 20L49 42L14 52Z" fill="#fff9df" stroke="#d8be72"/><path d="M6 30L47 24L59 26L50 51L13 58L9 55Z" fill="url(#gold)" stroke="#9b762f" stroke-width="1.2"/><path d="M8 31L47 26L56 27" fill="none" stroke="#fffde8" stroke-width="2"/><path d="M13 56L49 49L56 29" fill="none" stroke="#d49a27" stroke-width="1.2"/>'+badge

MONITOR='<path d="M26 45L39 42L42 51L23 56L15 52L27 49Z" fill="url(#metal)" stroke="#63708e"/><path d="M8 11L39 5L49 12L49 41L17 50L7 43Z" fill="#8c9ac1" stroke="#596483" stroke-width="1.3"/><path d="M8 11L39 7L40 39L17 46L9 42Z" fill="url(#metal)"/><path d="M13 16L35 12L36 36L15 42Z" fill="#224d8f" stroke="#5d6f98"/><path d="M15 18L33 15L34 34L17 39Z" fill="url(#blue)"/><path d="M16 19L31 16L17 32Z" fill="white" opacity=".27"/><path d="M40 8L47 13V39L41 41Z" fill="#a5b3d5"/><circle cx="34" cy="41" r="1.2" fill="#90dd63"/>'

BIN='<path d="M14 16L19 51Q32 61 46 50L50 16Z" fill="#8ec5e4" fill-opacity=".72" stroke="#658ca9" stroke-width="1.3"/><path d="M18 22L22 48Q28 52 31 51V25Z" fill="#ecfbff" opacity=".6"/><path d="M42 23L40 52L45 48L48 20Z" fill="#427cbb" opacity=".25"/><ellipse cx="32" cy="16" rx="18" ry="6" fill="#eafbff" stroke="#779cbd"/><ellipse cx="32" cy="16" rx="14" ry="3.5" fill="#a8cadb"/><path d="M30 29L24 37L30 36L31 41L38 30L33 33Z M37 42L43 35L38 35L37 30L31 44L35 40Z" fill="#469443" stroke="#fff" stroke-width=".7"/>'

PAGE='<path d="M14 5H39L51 17V56H14Z" fill="url(#paper)" stroke="#768aaa" stroke-width="1.4"/><path d="M39 5V17H51" fill="#cbdcf4" stroke="#768aaa"/><path d="M20 24H43M20 30H43M20 36H36" stroke="#93a7bd" stroke-width="2"/>'
NOTE='<path d="M30 24V43C20 38 17 51 27 51Q35 51 35 44V28L44 26V39C34 34 31 47 40 47Q49 47 49 40V20Z" fill="url(#blue)" stroke="#2157a2"/>'
PHOTO='<rect x="20" y="29" width="30" height="22" fill="#85c6ef" stroke="#3b77aa"/><circle cx="43" cy="35" r="3" fill="#fff6a4"/><path d="M21 49L31 35L41 49L46 41L49 49Z" fill="#579641"/>'
FILM='<rect x="23" y="25" width="28" height="25" rx="1" fill="#415574"/><path d="M31 26V49M43 26V49" stroke="#fff" stroke-width="2" stroke-dasharray="3 3"/><path d="M35 32L41 37L35 42Z" fill="#fff"/>'
BOOK='<rect x="27" y="27" width="20" height="24" rx="2" fill="url(#blue)" stroke="#1c5192"/><path d="M31 28V50M35 34H44M35 39H44" stroke="#e1f4ff" stroke-width="2"/>'
GEAR='<g fill="url(#blue)" stroke="#2b5b95"><path d="M28 17H36L38 24L44 21L50 27L46 33L52 37L49 45L42 44L40 51H32L30 44L24 47L18 41L22 35L16 31L19 23L26 24Z"/><circle cx="34" cy="34" r="7" fill="#e8f4ff"/></g>'
assets={}
def put(context,names,body):
 for name in names.split():assets[(context,name)]=svg(body)
put('places','folder inode-directory',folder())
put('places','folder-open document-open',folder('<path d="M13 33L9 52H51L59 32Z" fill="url(#gold)" stroke="#ad7829"/>'))
for names,badge in [('folder-documents user-documents','<g transform="translate(22 23) scale(.53)">'+PAGE+'</g>'),('folder-music',NOTE),('folder-pictures',PHOTO),('folder-videos',FILM),('folder-download', '<path d="M29 27H38V39H44L34 50L23 39H29Z" fill="url(#green)" stroke="#397c2c"/>'),('folder-templates', '<path d="M23 29H43V49H23Z" fill="url(#paper)" stroke="#728ba9"/><path d="M27 34H39M27 39H39M27 44H35" stroke="#8c9fb7"/>')]:put('places',names,folder(badge))
put('places','user-home folder-home go-home', '<path d="M10 30L32 11L54 30" fill="url(#red)" stroke="#954630" stroke-width="3"/><path d="M16 28L32 16L48 28V54H16Z" fill="url(#gold)" stroke="#a18544"/><path d="M29 38H39V54H29Z" fill="url(#blue)" stroke="#486689"/><rect x="20" y="32" width="6" height="7" fill="#82c8f0" stroke="#6b8393"/>')
put('places','user-trash',BIN)
put('places','user-trash-full', '<path d="M18 25L15 5L29 2L34 23M30 22L33 3L45 7L41 24M38 23L46 10L57 16L45 31" fill="url(#paper)" stroke="#7b8faa"/>'+BIN)
put('devices','computer user-desktop video-display','<path d="M43 15L57 12L61 17V48L48 53L43 49Z" fill="url(#metal)" stroke="#647293"/><path d="M48 22L56 20M48 27L56 25M48 31L56 29" stroke="#6f7fa3" stroke-width="2"/><circle cx="54" cy="44" r="1.5" fill="#67a45e"/>'+MONITOR)
DRIVE='<path d="M11 21H50L59 38V51Q32 59 5 51V38Z" fill="url(#metal)" stroke="#6d7884" stroke-width="1.5"/><path d="M11 21H50L56 38H8Z" fill="url(#paper)" stroke="#939ea9"/><path d="M8 41Q32 46 56 41V49Q32 55 8 49Z" fill="#8d99a7" stroke="#5b6e83"/><path d="M11 43Q31 47 47 44" fill="none" stroke="#d4e1ee"/><circle cx="51" cy="47" r="1.7" fill="#b0e65f"/>'
put('devices','drive-harddisk drive-harddisk-system drive-multidisk',DRIVE)
put('devices','drive-harddisk-usb drive-removable-media media-flash',DRIVE+'<path d="M25 26V35M25 31L20 28V25M25 29L30 26V23M23 28L25 25L27 28" fill="none" stroke="#59728b" stroke-width="1.8"/>')
put('devices','drive-optical media-optical',DRIVE+'<ellipse cx="32" cy="30" rx="13" ry="7" fill="url(#blue)" stroke="#7a94c6"/><path d="M23 26L38 34M39 26L25 34" stroke="#d6f8df" stroke-width="3" opacity=".8"/><ellipse cx="32" cy="30" rx="3" ry="1.8" fill="#f2f5fa" stroke="#65829c"/>')
NETWORK='<path d="M18 35V51H47V35M32 51V57" fill="none" stroke="#5b79a3" stroke-width="3"/><g transform="translate(1 7) scale(.61)">'+MONITOR+'</g><g transform="translate(27 -1) scale(.61)">'+MONITOR+'</g>'
put('places','network-workgroup network-server network-wired network',NETWORK)
put('places','folder-remote folder-publicshare',folder('<g transform="translate(19 20) scale(.65)">'+NETWORK+'</g>'))
put('mimetypes','text-x-generic text-plain unknown application-octet-stream',PAGE)
put('mimetypes','text-x-script application-x-shellscript text-x-python text-x-java text-x-csrc',PAGE+'<path d="M27 38L20 43L27 48M39 38L46 43L39 48M35 36L31 50" fill="none" stroke="#448544" stroke-width="2.5"/>')
put('mimetypes','image-x-generic image-jpeg image-png image-svg+xml',PAGE+PHOTO)
put('mimetypes','audio-x-generic audio-mpeg audio-x-wav',PAGE+NOTE)
put('mimetypes','video-x-generic video-mp4 video-x-matroska',PAGE+FILM)
put('mimetypes','x-office-document application-vnd.oasis.opendocument.text application-msword',PAGE+BOOK)
put('mimetypes','application-pdf',PAGE+'<rect x="18" y="33" width="34" height="18" rx="2" fill="url(#red)" stroke="#ac3b31"/><path d="M24 46V38H29V42H24M33 46V38H37L39 40V44L37 46ZM43 46V38H48M43 42H47" fill="none" stroke="#fff" stroke-width="1.8"/>')
put('mimetypes','x-office-spreadsheet application-vnd.oasis.opendocument.spreadsheet application-vnd.ms-excel',PAGE+'<rect x="20" y="30" width="29" height="22" fill="url(#green)" stroke="#4f7d38"/><path d="M21 37H48M21 44H48M29 31V51M39 31V51" stroke="#f1f8d9"/>')
put('mimetypes','x-office-presentation application-vnd.oasis.opendocument.presentation',PAGE+'<rect x="20" y="29" width="30" height="22" fill="url(#gold)" stroke="#b28a34"/><path d="M25 45V39H30V45M33 45V34H38V45M41 45V37H45V45" fill="url(#red)"/>')
put('mimetypes','package-x-generic application-zip application-x-7z-compressed application-x-rar application-gzip application-x-tar', '<path d="M7 21L32 10L57 21V48L32 58L7 48Z" fill="url(#gold)" stroke="#a37639"/><path d="M7 21L32 32L57 21M32 32V58" fill="none" stroke="#af8544"/><path d="M22 15L46 26V36L38 40V30L15 19Z" fill="#fff4c8" opacity=".8"/>')
put('mimetypes','application-x-executable application-x-desktop', '<rect x="7" y="10" width="50" height="43" rx="3" fill="url(#paper)" stroke="#5d7fbb"/><path d="M8 14Q8 11 12 11H53Q56 11 56 14V21H8Z" fill="url(#blue)"/>'+GEAR)
put('apps','preferences-system preferences-desktop preferences-desktop-theme preferences-desktop-display cinnamon-settings org.mintxp.Experience',MONITOR+'<g transform="translate(24 25) scale(.62)">'+GEAR+'</g>')
put('apps','utilities-terminal terminal', '<rect x="5" y="11" width="54" height="42" rx="3" fill="url(#metal)" stroke="#5c728d"/><rect x="9" y="16" width="46" height="30" fill="#183660"/><path d="M15 24L23 30L15 36M28 37H40" fill="none" stroke="#f8ffff" stroke-width="3"/>')
put('apps','system-file-manager org.mintxp.Explorer',folder())
put('categories','applications-system applications-settings preferences-other',GEAR)
put('categories','applications-office applications-education',PAGE+BOOK)
put('categories','applications-multimedia applications-audio applications-video',FILM+NOTE)
put('categories','applications-graphics',PHOTO+ '<path d="M45 18L51 21L32 46L27 47L28 42Z" fill="url(#gold)" stroke="#82601e"/>')
put('categories','applications-internet',NETWORK)
put('categories','applications-games', '<path d="M10 29Q12 24 19 26L26 29H38L46 26Q53 25 55 32L59 46Q59 55 52 51L40 43H24L12 52Q5 54 6 46Z" fill="url(#metal)" stroke="#667b97"/><path d="M15 33H21V38H26V43H21V48H15V43H10V38H15Z" fill="#5176b0"/><circle cx="45" cy="36" r="3" fill="#71b447"/><circle cx="52" cy="42" r="3" fill="#df6551"/>')
for name,transform in [('go-next',''),('go-previous','translate(64 0) scale(-1 1)'),('go-up','translate(0 64) rotate(-90)'),('go-down','translate(64 0) rotate(90)')]:
 put('actions',name,'<g transform="'+transform+'"><circle cx="32" cy="32" r="25" fill="url(#green)" stroke="#437d2b" stroke-width="1.4"/><path d="M13 27Q18 9 36 10" fill="none" stroke="#edffdb" stroke-width="2" opacity=".8"/><path d="M17 27H33V19L47 32L33 45V37H17Z" fill="#fff" stroke="#4e8c34" stroke-width=".7"/></g>')
put('actions','edit-find system-search', '<circle cx="26" cy="25" r="17" fill="url(#blue)" stroke="#596e8b" stroke-width="4"/><path d="M37 38L54 56" stroke="#647f9e" stroke-width="9"/><path d="M40 40L54 54" stroke="#86a9d6" stroke-width="4"/><path d="M15 24Q15 14 27 13" stroke="#effaff" stroke-width="3" fill="none"/>')
put('actions','edit-copy', '<g transform="translate(-4 -2) scale(.86)">'+PAGE+'</g><g transform="translate(13 12) scale(.84)">'+PAGE+'</g>')
put('actions','edit-paste', '<rect x="10" y="9" width="39" height="45" rx="3" fill="url(#gold)" stroke="#a87e37"/><rect x="20" y="6" width="19" height="8" rx="2" fill="url(#metal)" stroke="#7c8d9d"/><g transform="translate(19 18) scale(.67)">'+PAGE+'</g>')
put('actions','edit-cut', '<path d="M20 40L48 8L31 39L21 8L42 42" fill="url(#metal)" stroke="#7488a0" stroke-width="2"/><circle cx="19" cy="46" r="9" fill="none" stroke="#5485c5" stroke-width="5"/><circle cx="44" cy="46" r="9" fill="none" stroke="#5485c5" stroke-width="5"/><circle cx="30" cy="32" r="2" fill="#45669d"/>')
put('actions','edit-delete window-close', '<path d="M15 10L32 26L49 10L56 17L39 33L55 49L48 56L32 40L16 56L9 49L25 33L8 17Z" fill="url(#red)" stroke="#a34132" stroke-width="1.3"/>')
put('actions','folder-new', folder('<path d="M36 26H44V35H53V43H44V52H36V43H27V35H36Z" fill="url(#green)" stroke="#4d842e"/>'))
put('actions','view-refresh system-reboot', '<path d="M49 22A21 21 0 1 0 49 43L43 38A13 13 0 1 1 44 25L35 27L54 34L56 14Z" fill="url(#blue)" stroke="#3464a5"/>')
put('actions','edit-undo', '<path d="M26 12L6 29L26 45V35H37Q51 35 50 50Q61 22 36 23H26Z" fill="url(#blue)" stroke="#3464a5"/>')
put('actions','document-properties dialog-information', '<circle cx="32" cy="32" r="25" fill="url(#blue)" stroke="#3464a5"/><circle cx="32" cy="20" r="3" fill="white"/><path d="M27 29H34V44H38M27 45H38" fill="none" stroke="white" stroke-width="4"/>')
put('actions','system-shutdown', '<rect x="8" y="8" width="48" height="48" rx="9" fill="url(#red)" stroke="#9b362c"/><path d="M32 16V33M23 23A15 15 0 1 0 41 23" stroke="#fff" fill="none" stroke-width="5"/>')
# Original palette and brush artwork, inspired by classic desktop Paint tools.
put('apps','mintxp-paint', '<path d="M28 9C12 10 5 23 7 38C9 51 23 56 34 52C41 50 43 45 39 40C35 35 43 32 50 33C59 35 60 25 54 17C49 10 38 7 28 9Z" fill="url(#gold)" stroke="#937044" stroke-width="1.5"/><path d="M12 29C13 18 22 12 34 12" fill="none" stroke="#fff9d8" stroke-width="2"/><ellipse cx="25" cy="40" rx="6" ry="7" transform="rotate(-28 25 40)" fill="#fff" stroke="#9c7645" stroke-width="1.5"/><circle cx="19" cy="22" r="4.8" fill="url(#red)" stroke="#a43e36"/><circle cx="32" cy="17" r="4.3" fill="url(#blue)" stroke="#2d5d98"/><circle cx="45" cy="20" r="4.2" fill="url(#green)" stroke="#417333"/><circle cx="13" cy="35" r="3.7" fill="#9265b3" stroke="#634483"/><path d="M59 5Q62 3 61 8L39 42L34 38Z" fill="url(#blue)" stroke="#284e85" stroke-width="1.3"/><path d="M35 36L41 40L36 47L30 43Z" fill="url(#metal)" stroke="#617081"/><path d="M30 42Q21 46 24 57Q36 54 36 47Z" fill="#785238" stroke="#4e372b" stroke-width="1.3"/><path d="M31 46L26 54" stroke="#c5a077" stroke-width="1.8"/>')
# A distinct four-petal emblem, not the Microsoft flag or Mint trademark.
EMBLEM=''.join('<path d="M32 30C15 31 7 21 13 8C27 8 36 16 32 30Z" fill="url(#'+color+')" stroke="#ffffff" stroke-opacity=".7" stroke-width="1" transform="rotate('+str(i*90)+' 32 32)"/>' for i,color in enumerate(('red','green','gold','blue')))+'<circle cx="32" cy="32" r="4" fill="#fffbdc"/>'
put('places','mintxp-start',EMBLEM)
def build():
 base=ROOT/'assets/icons';contexts=sorted(set(c for c,n in assets));base.mkdir(exist_ok=True)
 # Aliases are real files so public archives never depend on external symlinks.
 for (context,name),data in assets.items():
  p=base/'scalable'/context/(name+'.svg');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 import gi
 gi.require_version('GdkPixbuf','2.0');from gi.repository import GdkPixbuf,Gio,GLib
 directories=[]
 for size in (16,24,32,48):
  for context in contexts:directories.append(str(size)+'/'+context)
  for (context,name),data in assets.items():
   stream=Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(data.encode()))
   pix=GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,size,size,True,None)
   path=base/str(size)/context/(name+'.png');path.parent.mkdir(parents=True,exist_ok=True);pix.savev(str(path),'png',[],[])
 directories += ['scalable/'+c for c in contexts]
 text='[Icon Theme]\nName=Mint XP Experience Icons\nComment=Original perspective desktop artwork\nInherits=Mint-Y,Adwaita,hicolor\nDirectories='+','.join(directories)+'\n'
 for directory in directories:
  size,c=directory.split('/');context={'mimetypes':'MimeTypes','places':'Places','devices':'Devices','actions':'Actions','apps':'Applications','categories':'Categories'}[c]
  text+='\n['+directory+']\nSize='+('48' if size=='scalable' else size)+'\nType='+('Scalable\nMinSize=16\nMaxSize=256' if size=='scalable' else 'Fixed')+'\nContext='+context+'\n'
 (base/'index.theme').write_text(text);(base/'LICENSE.txt').write_text('Original Mint XP Experience vector artwork. CC0-1.0.\nDesigned in this project; no Microsoft icon files, Windows logos or third-party application logos are included.\nUncovered application icons are provided by the existing Mint-Y/Adwaita/hicolor themes.\nRebuild from tools/build_icons.py.\n')
 for relative in ('assets/menu/mintxp-start.svg','assets/menu/5.8/mintxp-start.svg'):(ROOT/relative).write_text(svg(EMBLEM))
 print('Generated',len(assets),'original icon names and the bundled Start emblem.')
if __name__=='__main__':build()
