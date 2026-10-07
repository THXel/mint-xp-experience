"""Portable component plans. No installation side effects here (apart from backup objects)."""
import configparser, json, os, re, subprocess
from pathlib import Path
from .engine import encoded, Conflict
from .session_settings import validated
ROOT=Path(__file__).resolve().parent.parent
THEME='Mint-XP-Experience'
RUNTIME='.local/share/mint-xp-experience'
COMPONENTS=('gtk','shell','cursor','icons','wallpaper','fonts','explorer','control','menu','taskbar','tray','default_manager','sounds','games','welcome_screen')
DEFAULTS={'gtk':True,'shell':True,'cursor':True,'icons':True,'wallpaper':False,'fonts':True,'explorer':True,'control':True,'menu':False,'taskbar':False,'tray':False,'default_manager':False,'sounds':False,'games':False,'font_size':11,'icon_size':32,'language':'auto','sound_theme':'Windows-XP','sound_source':':keep:','sound_preserve':True,'sound_choices':{},'icon_import':'','prefer_local_icons':False,'addon_selection':[],'boot_install':False,'login_install':False,'welcome_screen':False,'welcome_duration':2.6,'welcome_fade':True,'welcome_monitors':'all'}

def desktop(name,script,icon='preferences-desktop-theme',args='',category='Settings;DesktopSettings;',extra=''):
    # Desktop Entry quoted argument syntax is distinct from shell escaping.
    def quote(s):return '"'+str(s).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'
    return ('[Desktop Entry]\nType=Application\nName='+name+'\nExec=/usr/bin/python3 -B '+quote(script)+(' '+args if args else '')+'\nIcon='+icon+'\nTerminal=false\nCategories='+category+'\n'+extra).encode()

def preflight(options):
    if os.geteuid()==0:raise Conflict('Run as your desktop user, not root / sudo.')
    text=Path('/etc/os-release').read_text()
    if 'ID=linuxmint' not in text and 'ID="linuxmint"' not in text:raise Conflict('This preview supports Linux Mint Cinnamon only.')
    if 'VERSION_ID="22.3"' not in text and 'VERSION_ID=22.3' not in text:raise Conflict('This preview requires Linux Mint 22.3.')
    from gi.repository import Gio
    if not Gio.SettingsSchemaSource.get_default().lookup('org.cinnamon',True):raise Conflict('Cinnamon is required.')
    if options.get('menu') or options.get('taskbar') or options.get('tray'):
        version=subprocess.run(['cinnamon','--version'],capture_output=True,text=True,check=True).stdout
        if not re.search(r'\b6\.6\.',version):raise Conflict('Applet patches require Cinnamon 6.6.x. Other versions need compatibility testing.')
    if options.get('default_manager') and not options.get('explorer'):raise Conflict('Select Explorer before making it the default file manager.')

def patch_control(source):
    entry=" ('appearance','Mint XP Experience','Theme, Sprache, Sicherung und Deinstallation','org.mintxp.Experience.desktop'),\n"
    if 'from xp_locale import' in source:entry=entry.replace("'Theme, Sprache, Sicherung und Deinstallation'","_xp('Theme, Sprache, Sicherung und Deinstallation')")
    if 'org.mintxp.Experience.desktop' in source:return source
    source=source.replace('ENTRIES=[\n','ENTRIES=[\n'+entry,1)
    source=source.replace("  path=Path('/usr/share/applications')/desktop", "  path=(Path.home()/'.local/share/applications'/desktop) if desktop=='org.mintxp.Experience.desktop' else Path('/usr/share/applications')/desktop")
    return source

def patch_preferences(source):
    if 'org.mintxp.Experience.desktop' in source:return source
    return source.replace("source=Path('/usr/share/applications')/entry['desktop']", "source=(Path.home()/'.local/share/applications'/entry['desktop']) if entry['desktop']=='org.mintxp.Experience.desktop' else Path('/usr/share/applications')/entry['desktop']")

def plan(engine,options,root=ROOT):
    o=dict(DEFAULTS,**options); session=validated(o);files={}; settings={}; home=engine.home
    def add(rel,data,mode=0o644):
        engine.path(rel);files[rel]=engine.descriptor(data,mode)
        engine.report('prepare',len(files),None,rel)
    def tree(src,dest,local_import=False):
        for p in sorted(src.rglob('*')):
            if p.is_symlink():
                if not local_import or not p.resolve().is_relative_to(src) or not p.resolve().is_file():raise Conflict('External or directory symlink is not allowed: '+str(p))
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc'):
                add(dest+'/'+str(p.relative_to(src)),p.read_bytes(),p.stat().st_mode&0o777)
    def setv(schema,key,value):
        engine.settings.get(schema+'/'+key) # Validate schema + key before any change.
        settings[schema+'/'+key]=engine.settings.literal(value)
    # Self-contained recovery/UI payload. The checkout can be removed after installing.
    for part in ('mintxp','assets','locales','licenses','sources','docs','system'):
        tree(root/part,RUNTIME+'/'+part)
    for name in ('launch.py','VERSION','LICENSE','README.md'):
        add(RUNTIME+'/'+name,(root/name).read_bytes())
    add('.local/share/applications/org.mintxp.Experience.desktop',desktop('Mint XP Experience',home/RUNTIME/'launch.py',extra='Name[de]=Mint XP Experience – Theme-Verwaltung\n'))
    add('.local/bin/mint-xp-experience',('#!/bin/sh\nexec /usr/bin/python3 -B "$HOME/'+RUNTIME+'/launch.py" "$@"\n').encode(),0o755)
    # Install a narrowly scoped entry into the already present XP Control Panel too.
    panel=home/'.local/share/xp-control-panel/panel.py'
    if not o['control'] and panel.is_file():
        add(str(panel.relative_to(home)),patch_control(panel.read_text()).encode())
        prefs=panel.parent/'preferences.py'
        if prefs.is_file():add(str(prefs.relative_to(home)),patch_preferences(prefs.read_text()).encode())
    add('.config/mint-xp-experience/session.json',encoded(session),0o600)
    add('.local/bin/mint-xp-rescue',b'#!/bin/sh\nexec /usr/bin/python3 -B "${XDG_STATE_HOME:-$HOME/.local/state}/mint-xp-experience/rescue/rescue.py" "$@"\n',0o755)
    if o['welcome_screen']:
        tree(root/'assets/session','.local/share/mint-xp-welcome')
        add('.config/autostart/mintxp-welcome.desktop',desktop('Mint XP Welcome',home/'.local/share/mint-xp-welcome/welcome.py',extra='OnlyShowIn=X-Cinnamon;\nX-GNOME-Autostart-enabled=true\nX-GNOME-Autostart-Phase=Applications\nNoDisplay=true\n'))
    if o['gtk']:
        tree(root/'assets/gtk','.themes/'+THEME)
        for schema in ('org.cinnamon.desktop.interface','org.gnome.desktop.interface'):setv(schema,'gtk-theme',THEME)
        setv('org.cinnamon.desktop.wm.preferences','theme',THEME)
        setv('org.cinnamon.desktop.wm.preferences','button-layout',':minimize,maximize,close')
    if o['shell']:
        tree(root/'assets/cinnamon/cinnamon','.themes/'+THEME+'/cinnamon')
        setv('org.cinnamon.theme','name',THEME)
    if o['cursor']:
        tree(root/'assets/cursors','.local/share/icons/'+THEME+'-Cursors')
        for schema in ('org.cinnamon.desktop.interface','org.gnome.desktop.interface'):setv(schema,'cursor-theme',THEME+'-Cursors')
    if o['icons']:
        tree(root/'assets/icons','.local/share/icons/'+THEME+'-Icons')
        for schema in ('org.cinnamon.desktop.interface','org.gnome.desktop.interface'):setv(schema,'icon-theme',THEME+'-Icons')
    if o['wallpaper']:
        tree(root/'assets/wallpapers','.local/share/backgrounds/'+THEME)
        setv('org.cinnamon.desktop.background','picture-uri',(home/'.local/share/backgrounds'/THEME/'Luna-Hills-Photo.png').as_uri())
        setv('org.cinnamon.desktop.background','picture-options','zoom')
    if o['fonts']:
        size=int(o['font_size'])
        if not 9<=size<=18:raise ValueError('Font size must be 9–18')
        for schema in ('org.cinnamon.desktop.interface','org.gnome.desktop.interface'):setv(schema,'font-name',f'Liberation Sans {size}')
        setv('org.cinnamon.desktop.wm.preferences','titlebar-font',f'Liberation Sans Bold {size}')
        setv('org.nemo.desktop','font',f'Liberation Sans {size}')
    if o['explorer']:
        tree(root/'assets/xp-explorer','.local/share/xp-explorer')
        launcher=desktop('My Computer',home/'.local/share/xp-explorer/explorer.py','computer','%U','System;FileTools;FileManager;',extra='Name[de]=Arbeitsplatz\nMimeType=inode/directory;\nStartupWMClass=XP Explorer\n')
        add('.local/share/applications/org.mintxp.Explorer.desktop',desktop('XP Explorer',home/'.local/share/xp-explorer/explorer.py','folder','--tree --home %U','System;FileTools;FileManager;',extra='Name[de]=XP Explorer\nMimeType=inode/directory;\nStartupWMClass=XP Explorer\n'))
        from .integration import desktop_directory,pin_explorer
        folder=desktop_directory(home)
        if folder is not None:add(str((folder/'org.mintxp.Computer.desktop').relative_to(home)),launcher,0o755)
        pin_explorer(engine,settings,root,replace_nemo=o['default_manager'])
    if o['control']:
        tree(root/'assets/xp-control-panel','.local/share/xp-control-panel')
        add('.local/share/xp-control-panel/panel.py',patch_control((root/'assets/xp-control-panel/panel.py').read_text()).encode())
        add('.local/share/xp-control-panel/preferences.py',patch_preferences((root/'assets/xp-control-panel/preferences.py').read_text()).encode())
        add('.local/bin/xp-control-panel',b'#!/bin/sh\nexec /usr/bin/python3 -B "$HOME/.local/share/xp-control-panel/panel.py" "$@"\n',0o755)
        add('.local/share/applications/cinnamon-settings.desktop',desktop('Control Panel',home/'.local/share/xp-control-panel/panel.py','preferences-desktop',extra='Name[de]=Systemsteuerung\nStartupWMClass=XPControlPanel\n'))
    from .tray_plan import original_setting
    applets=original_setting(engine,"org.cinnamon","enabled-applets") if o["menu"] or o["tray"] else None
    if o['menu']:
        # Separate UUID keeps the user's Cinnamenu code and settings intact.
        tree(root/'assets/menu','.local/share/cinnamon/applets/mintxp-menu@mintxp')
    if o['menu'] or o.get('disabled_applets'):
        from .applet_review import configure,XP_MENU
        if applets is None:applets=original_setting(engine,'org.cinnamon','enabled-applets')
        applets,next_id=configure(engine,o,applets,engine.settings.effective('org.cinnamon','next-applet-id'))
        setv('org.cinnamon','enabled-applets',applets);setv('org.cinnamon','next-applet-id',next_id)
        if o['menu']:
            # Avoid stealing the Super key from an explicitly retained menu.
            schema=json.loads((root/'assets/menu/5.8/settings-schema.json').read_text())
            if any('menu' in s.split(':')[3].lower() and s.split(':')[3]!=XP_MENU for s in applets):schema['overlay-key']['default']=''
            add('.local/share/cinnamon/applets/'+XP_MENU+'/5.8/settings-schema.json',encoded(schema))
    if o['tray']:
        from .tray_plan import add_tray
        tree(root/'assets/tray','.local/share/cinnamon/applets/mintxp-tray@mintxp')
        updated,next_id=add_tray(applets,original_setting(engine,'org.cinnamon','next-applet-id'))
        setv('org.cinnamon','enabled-applets',updated)
        setv('org.cinnamon','next-applet-id',next_id)
    if o['taskbar']:
        tree(root/'assets/taskbar','.local/share/cinnamon/applets/grouped-window-list@cinnamon.org')
        size=int(o['icon_size'])
        if not 20<=size<=48:raise ValueError('Icon size must be 20–48')
        # Preserve applet positions, and size the zone that actually contains the
        # task list (a fresh Mint profile places it on the left).
        applets=engine.settings.effective('org.cinnamon','enabled-applets')
        zones={}
        for entry in applets:
            fields=entry.split(':')
            if len(fields)>=4 and fields[3]=='grouped-window-list@cinnamon.org':
                zones.setdefault(fields[0].removeprefix('panel'),set()).add(fields[1])
        if not zones:raise Conflict('Add the grouped window list to a panel first.')
        for key in ('panel-zone-icon-sizes','panel-zone-symbolic-icon-sizes'):
            data=json.loads(engine.settings.effective('org.cinnamon',key))
            for row in data:
                for zone in zones.get(str(row.get('panelId')),()):row[zone]=size
            setv('org.cinnamon',key,json.dumps(data,separators=(',',':')))
    if o['default_manager']:
        # Keep Nemo independently discoverable by its own name after replacing
        # its Files pin. Preserve the system entry's actions and translations.
        nemo=home/'.local/share/applications/nemo.desktop'
        if not nemo.is_file():nemo=Path('/usr/share/applications/nemo.desktop')
        if nemo.is_file():
            cp=configparser.ConfigParser(interpolation=None,strict=False);cp.optionxform=str;cp.read(nemo)
            entry=cp['Desktop Entry'];entry['Name']='Nemo'
            for key in list(entry):
                if key.startswith('Name['):entry[key]='Nemo'
            entry['Keywords']=entry.get('Keywords','')+'nemo;'
            import io
            buf=io.StringIO();cp.write(buf);add('.local/share/applications/nemo.desktop',buf.getvalue().encode())
        from .mime_state import REL,replace,EXPLORER
        p=home/REL
        add(REL,replace(p.read_bytes() if p.exists() else b'',EXPLORER+';'),p.stat().st_mode&0o777 if p.exists() else 0o600)
    if o['sounds'] and o.get('sound_source') not in (':keep:',':builtin:'):
        from .sounds import imported_plan,ensure_ready
        sound=imported_plan(engine,o);ensure_ready(sound['report']);files.update(sound['files']);settings.update(sound['settings'])
    else:
        # Without a selected pack, preserve any existing imported sounds. The
        # discontinued bundled pack is explicitly returned to its saved baseline.
        from .sounds import PREFIX,settings_keys
        current=engine.read_current();old=current.get('options',{})
        if old.get('sounds') and old.get('sound_source')!=':builtin:':
            files.update({k:v for k,v in current['files'].items() if k.startswith(PREFIX)})
            settings.update({k:v for k,v in current['settings'].items() if k in settings_keys()})
            for k in ('sounds','sound_source','sound_theme','sound_preserve','sound_choices'):o[k]=old.get(k,o.get(k))
        else:o['sounds']=False;o['sound_source']=':keep:'
    from .integration import local_icons
    icon_source=(o.get('icon_import') if o.get('icon_mode','imported' if o.get('icon_import') else 'bundled')=='imported' else '') or (local_icons(home) if o.get('prefer_local_icons',True) and o['icons'] else '')
    if o['icons'] and icon_source:
        src=Path(icon_source).expanduser().resolve()
        if not (src/'index.theme').is_file():raise Conflict('Choose an icon theme folder containing index.theme.')
        from .agent_character import checked_files
        for name,blob in checked_files(src.parent/'companion').items():add('.local/share/xp-explorer/companion/'+name,blob)
        # Local assets are copied only into private installation state, never the source package.
        tree(src,'.local/share/icons/'+THEME+'-Imported',local_import=True)
        cp=configparser.ConfigParser(interpolation=None,strict=False);cp.optionxform=str;cp.read(src/'index.theme')
        inherited=cp['Icon Theme'].get('Inherits','').split(',')
        cp['Icon Theme']['Inherits']=','.join(dict.fromkeys([THEME+'-Icons',*[x for x in inherited if x and x!=THEME+'-Imported'],'hicolor']))
        import io
        buf=io.StringIO();cp.write(buf);add('.local/share/icons/'+THEME+'-Imported/index.theme',buf.getvalue().encode())
        for schema in ('org.cinnamon.desktop.interface','org.gnome.desktop.interface'):setv(schema,'icon-theme',THEME+'-Imported')
    # Mascot choice is independent of the active icon theme. Retain an imported
    # companion across icon switches; uninstall still restores all managed files.
    if o['explorer'] or engine.read_current().get('options',{}).get('explorer'):
        for name,desc in engine.read_current().get('files',{}).items():
            if name.startswith('.local/share/xp-explorer/companion/') and name not in files:files[name]=desc
    if o['menu'] or o['games']:
        for p in sorted((root/'assets/menu-integration').iterdir()):
            destination='.config/menus/applications-merged/' if p.suffix=='.menu' else '.local/share/desktop-directories/'
            add(destination+p.name,p.read_bytes())
    if o['games']:
        # Integrate existing games only. Do not bundle third-party binaries or pinball data.
        candidates=[home/'.local/share/flatpak/exports/share/applications/com.github.k4zmu2a.spacecadetpinball.desktop',Path('/var/lib/flatpak/exports/share/applications/com.github.k4zmu2a.spacecadetpinball.desktop')]
        for src in candidates:
            if src.exists():
                cp=configparser.ConfigParser(interpolation=None,strict=False);cp.optionxform=str;cp.read(src)
                cp['Desktop Entry']['Categories']='Game;X-XPCommunity;'
                import io
                buf=io.StringIO();cp.write(buf);add('.local/share/applications/'+src.name,buf.getvalue().encode());break
        # An empty game category is valid on a fresh machine. Optional games
        # are installed separately on the Games and accessories page.
    return {'files':files,'settings':settings,'options':o}

def refresh():
    subprocess.run(['update-desktop-database',str(Path.home()/'.local/share/applications')],capture_output=True)
    # Update visible favourites without restarting Cinnamon or user applications.
    script="(()=>{imports.ui.main.loadTheme();for (const d of imports.ui.appletManager.definitions){if(d.uuid==='grouped-window-list@cinnamon.org' && d.applet){let a=d.applet;if(a.settings?._checkSettings)a.settings._checkSettings();if(a.updateFavorites)a.updateFavorites();}}return true;})()"
    try:subprocess.run(['gdbus','call','--session','--dest','org.Cinnamon','--object-path','/org/Cinnamon','--method','org.Cinnamon.Eval',script],capture_output=True,timeout=5)
    except (OSError,subprocess.TimeoutExpired):pass
    # Replaced JavaScript modules still load consistently after the next login.
