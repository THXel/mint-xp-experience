"""Selection-aware XP menus. Actions use GIO associations, never shell commands."""
from xp_locale import t as _xp
from dataclasses import dataclass
import os,shutil,subprocess
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gio,Gdk,Pango
from core import file_for,format_size

@dataclass
class Action:
    label:str
    callback:object=None
    icon:object=None
    enabled:bool=True
    children:object=None

ARCHIVES={'application/zip','application/x-7z-compressed','application/vnd.rar','application/x-rar','application/x-rar-compressed','application/x-tar','application/x-compressed-tar','application/x-bzip-compressed-tar','application/x-xz-compressed-tar','application/x-lzma-compressed-tar','application/gzip','application/x-gzip','application/x-bzip','application/x-bzip2','application/x-xz','application/x-zstd'}
def kind(row):
    if row.get('dir') or row.get('shortcut') or row.get('mountable'):return 'folder'
    mime=row.get('mime') or 'application/octet-stream'
    if mime in ARCHIVES:return 'archive'
    for prefix in ('image','audio','video'):
        if mime.startswith(prefix+'/'):return prefix
    if mime=='application/pdf':return 'pdf'
    if Gio.content_type_is_a(mime,'text/plain'):return 'text'
    if mime.startswith(('application/vnd.oasis.opendocument','application/vnd.openxmlformats-officedocument','application/vnd.ms-')) or mime=='application/msword':return 'document'
    return 'file'

def associated_apps(mime):
    apps=[];seen=set();default=Gio.AppInfo.get_default_for_type(mime,False)
    for app in ([default] if default else [])+Gio.AppInfo.get_all_for_type(mime):
        identity=app.get_id() or app.get_executable()
        if identity in seen or not app.should_show() or not (app.supports_files() or app.supports_uris()):continue
        if identity=='org.mintxp.Explorer.desktop':continue
        seen.add(identity);apps.append(app)
    return apps[:8]

def build_menu(owner,entries):
    menu=Gtk.Menu();menu.get_style_context().add_class('xp-context-menu')
    for entry in entries:
        if entry is None:menu.append(Gtk.SeparatorMenuItem());continue
        if not isinstance(entry,Action):
            title,fn=entry;entry=Action(title,children=fn) if isinstance(fn,list) else Action(title,fn)
        item=Gtk.MenuItem();item.xp_action=entry;box=Gtk.Box(spacing=9)
        image=Gtk.Image();image.set_size_request(18,18)
        if entry.icon:image.set_from_pixbuf(owner.pix(entry.icon,16))
        box.pack_start(image,False,False,0);text=Gtk.Label(label=entry.label,xalign=0);text.set_max_width_chars(48);text.set_ellipsize(Pango.EllipsizeMode.MIDDLE);box.pack_start(text,True,True,0);item.add(box)
        item.set_sensitive(entry.enabled)
        if entry.children is not None:item.set_submenu(build_menu(owner,entry.children))
        elif entry.callback:item.connect('activate',lambda w,f=entry.callback:f())
        menu.append(item)
    return menu

def launch(owner,app,rows):
    try:app.launch([file_for(r['uri']) for r in rows],Gdk.Display.get_default().get_app_launch_context())
    except Exception as error:owner.error(error)

def application_menu(owner,row):
    apps=associated_apps(row.get('mime','application/octet-stream'))
    result=[Action(app.get_display_name(),lambda a=app:launch(owner,a,[row]),app.get_icon()) for app in apps]
    if result:result.append(None)
    result.append(Action(_xp('Andere Anwendung wählen …'),lambda:owner.open_with(row),'application-x-executable'))
    return Action(_xp('Öffnen mit'),icon='application-x-executable',children=result)

def copy_paths(owner,rows):
    Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text('\n'.join(file_for(r['uri']).get_path() or r['uri'] for r in rows),-1)
    owner.status.set_text(f'{len(rows)} Pfad'+('e' if len(rows)!=1 else '')+' kopiert')

def extract_archive(owner,row):
    try:
        binary=shutil.which('file-roller');path=file_for(row['uri']).get_path()
        if not binary or not path:raise ValueError(_xp('Archivverwaltung für diesen Ort nicht verfügbar.'))
        # Ask the native archive manager for its destination dialog; no extract-here/force.
        subprocess.Popen([binary,'--extract','--',path])
    except Exception as error:owner.error(error)

def preview(owner):
    owner.preview_enabled=True;owner.preview_box.show();owner.selected_changed()

def explore(owner,uri):
    owner.navigate(uri)
    if not owner.tree_mode:owner.toggle_tree()

def selection_properties(owner,rows):
    if len(rows)==1:
        from properties import Properties
        owner.properties_dialog=Properties(owner,rows[0]);return
    folders=sum(bool(r['dir']) for r in rows);size=sum(r.get('size',0) for r in rows if not r['dir'])
    owner.info(_xp('Eigenschaften der Auswahl'),_xp('{0} Objekte: {1} Ordner, {2} Dateien\nDateigrößen zusammen: {3}\nOrdnerinhalte sind in dieser Größe nicht enthalten.').format(len(rows), folders, len(rows) - folders, format_size(size)))

def file_entries(owner,rows):
    if not rows:return background_entries(owner)
    if len(rows)==1 and (rows[0].get('shortcut') or rows[0].get('mountable')):
        row=rows[0];return [Action(_xp('Öffnen'),lambda:owner.open_row(row),'network-server'),Action(_xp('In neuem Fenster öffnen'),lambda:owner.app.window(row.get('target') or row['uri']),'window-new'),None,Action(_xp('Mit Server verbinden …'),owner.connect_server,'network-server')]
    trash=owner.uri.startswith('trash:');entries=[]
    if trash:
        entries.append(Action(_xp('Wiederherstellen'),owner.restore_trash,'edit-undo',all(r.get('original') for r in rows)))
    elif len(rows)==1:
        row=rows[0];category=kind(row)
        title,icon={'folder':(_xp('Öffnen'),'folder-open'),'image':(_xp('Bild öffnen'),'image-x-generic'),'audio':('Wiedergeben','media-playback-start'),'video':('Video wiedergeben','media-playback-start'),'pdf':(_xp('PDF öffnen'),'application-pdf'),'text':(_xp('Textdatei öffnen'),'text-x-generic'),'document':(_xp('Dokument öffnen'),'x-office-document'),'archive':(_xp('Archiv öffnen'),'package-x-generic'),'file':(_xp('Öffnen'),'document-open')}[category]
        entries.append(Action(title,lambda:owner.open_row(row),icon))
        if category=='folder':
            entries.extend([Action(_xp('In neuem Fenster öffnen'),lambda:owner.app.window(row['uri']),'window-new'),Action(_xp('Im Explorerbaum öffnen'),lambda:explore(owner,row['uri']),'view-list-tree')])
        else:
            entries.append(application_menu(owner,row))
            entries.append(Action(_xp('Dateivorschau anzeigen'),lambda:preview(owner),'document-preview'))
            editors={'image':('gimp.desktop','Mit GIMP bearbeiten'),'audio':('audacity.desktop','Mit Audacity bearbeiten'),'video':('org.kde.kdenlive.desktop','Mit Kdenlive bearbeiten'),'text':('org.kde.kate.desktop','Mit Kate bearbeiten'),'pdf':('xreader.desktop',_xp('Mit Dokumentenbetrachter öffnen'))}
            if category in editors:
                app_id,title=editors[category];app=next((a for a in associated_apps(row['mime']) if a.get_id()==app_id),None)
                if app:entries.append(Action(title,lambda a=app:launch(owner,a,[row]),app.get_icon()))
            if category=='archive' and file_for(row['uri']).get_path() and shutil.which('file-roller'):
                entries.append(Action('Entpacken …',lambda:extract_archive(owner,row),'package-x-generic'))

        if row.get('link'):
            def target_folder():
                try:
                    f=file_for(row['uri']);info=f.query_info('standard::symlink-target',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,None);target=info.get_symlink_target()
                    if not target:raise ValueError(_xp('Verknüpfungsziel nicht verfügbar.'))
                    import os
                    resolved=file_for(target) if os.path.isabs(target) else f.get_parent().resolve_relative_path(target)
                    owner.app.window((resolved.get_parent() or resolved).get_uri())
                except Exception as e:owner.error(e)
            entries.append(Action(_xp('Ordner des Verknüpfungsziels öffnen'),target_folder,'folder-open'))
    else:entries.append(Action(_xp('{0} Objekte ausgewählt').format(len(rows)),enabled=False))
    entries.append(None)
    if trash:entries += [Action(_xp('Kopieren'),owner.copy,'edit-copy'),Action(_xp('Endgültig löschen …'),owner.permanent_delete,'edit-delete')]
    if not trash:entries += [Action(_xp('Ausschneiden'),lambda:owner.copy(True),'edit-cut'),Action(_xp('Kopieren'),owner.copy,'edit-copy')]
    entries.append(Action(_xp('Pfad kopieren') if len(rows)==1 else 'Pfade kopieren',lambda:copy_paths(owner,rows),'edit-copy'))
    if not trash:
        entries.append(None)
        entries.append(Action(_xp('Umbenennen'),owner.rename,'edit-rename'))
        if len(rows)==1:
            if rows[0]['dir']:entries.append(Action(_xp('Zu Favoriten hinzufügen'),lambda:owner.add_favorite(rows[0]['uri']),'emblem-favorite'))
        entries.append(Action(_xp('In den Papierkorb'),owner.trash,'user-trash'))
        entries.append(Action(_xp('Endgültig löschen …'),owner.permanent_delete,'edit-delete'))
    entries += [None,Action(_xp('Eigenschaften'),lambda:selection_properties(owner,rows),'document-properties')]
    return entries

def background_entries(owner,computer=False):
    if computer:
        return [Action(_xp('Aktualisieren'),owner.reload,'view-refresh'),None,Action('Explorerbaum anzeigen' if not owner.tree_mode else 'Systemaufgaben anzeigen',owner.toggle_tree,'view-list-tree'),Action(_xp('Arbeitsplatz in neuem Fenster'),lambda:owner.app.window('computer:///'),'window-new'),None,Action(_xp('Eigene Dateien'),lambda:owner.navigate(Gio.File.new_for_path(os.path.expanduser('~')).get_uri()),'user-home'),Action(_xp('Netzwerkumgebung'),lambda:owner.navigate('network:///'),'network-workgroup'),None,Action('Systemeinstellungen',lambda:owner.launch_settings(),'preferences-system'),Action('Systemeigenschaften',owner.system_info,'computer')]
    result=[Action(_xp('Ansicht'),icon='view-list-details',children=[Action('Symbole',lambda:owner.set_mode('icons'),'view-grid'),Action(_xp('Details'),lambda:owner.set_mode('details'),'view-list-details'),Action(_xp('Ordnerleiste'),owner.toggle_tree,'view-list-tree'),Action(_xp('Dateivorschau'),owner.toggle_preview,'image-x-generic')]),Action('Symbole anordnen nach',children=[Action(title,lambda k=key:owner.sort_by(k)) for title,key in [('Name','name'),(_xp('Größe'),'size'),('Typ','mime'),(_xp('Geändert am'),'modified')]]),Action(_xp('Aktualisieren'),owner.reload,'view-refresh'),None]
    if not owner.uri.startswith(('trash:','network:')):
        # Avoid a synchronous clipboard roundtrip while constructing the menu.
        result.extend([Action(_xp('Einfügen'),owner.paste,'edit-paste'),Action(_xp('Rückgängig'),owner.undo,'edit-undo',owner.app.undo_history.peek() is not None),None,Action(_xp('Neu'),icon='folder-new',children=[Action(_xp('Ordner'),owner.mkdir,'folder-new'),Action('Textdokument',owner.new_text,'text-x-generic')]),None])
    if owner.uri.startswith('trash:'):result.extend([Action(_xp('Papierkorb leeren …'),owner.empty_trash,'user-trash-full'),None])
    if owner.uri.startswith(('network:','smb:','sftp:','ftp:','ftps:','dav:','davs:')):result.extend([Action(_xp('Mit Server verbinden …'),owner.connect_server,'network-server'),Action(_xp('Verbindung trennen'),owner.disconnect_server,'network-offline'),None])
    result.append(Action(_xp('Suchen …'),owner.recursive_search,'edit-find'));return result
