#!/usr/bin/python3
"""XP-style file manager for Cinnamon. Native GTK/GIO, no shell file operations."""
from xp_locale import t as _xp
import datetime,json,os,platform,subprocess,sys,threading,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from sidebar import FolderTree
from comfort import read_state,write_state,clamp_geometry,load_image
from journal import UndoHistory
from properties import Properties
from transfer_ui import TransferDialog
from dragdrop import DragDrop
import views
import directory_loader
from thumbnail_cache import load as cached_image
from file_actions import FileActions
from event_sound import completed_sound
from network import NetworkActions,server_uri,NETWORK_SCHEMES
from navigation import browse_target
from capacity import usage,CapacityBar
import context_menu as context_actions
from preview import generate as generate_preview
from conflicts import ConflictPrompt,transfer_resolved
from search_ui import SearchWindow
from devices import Devices,removal_action
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk,Gio,GLib,GdkPixbuf,Pango
from core import file_for,listing,copy_item,move_item,new_folder,rename_item,trash_item,format_size,transfer_size
BASE=Path(__file__).resolve().parent
COMPUTER='computer:///'

def esc(s):return GLib.markup_escape_text(str(s))
def label(text='',cls=None):
    w=Gtk.Label(label=text,xalign=0);w.set_line_wrap(True)
    if cls:w.get_style_context().add_class(cls)
    return w

from bookmark_store import BookmarkStore
bookmark_store=BookmarkStore()
def bookmarks():return bookmark_store.entries()

def computer_items():
    groups={_xp('Dateien auf diesem Computer'):[],_xp('Festplatten'):[],_xp('Geräte mit Wechselmedien'):[],_xp('Netzwerk'):[]}
    home=Path.home();groups[_xp('Dateien auf diesem Computer')].append(dict(name=_xp('Eigene Dateien'),uri=home.as_uri(),icon='user-home',sub=str(home)))
    docs=GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
    if docs:groups[_xp('Dateien auf diesem Computer')].append(dict(name=_xp('Eigene Dokumente'),uri=Path(docs).as_uri(),icon='folder-documents',sub=docs))
    seen=set()
    try:
        data=json.loads(subprocess.check_output(['lsblk','-J','-b','-o','NAME,TYPE,SIZE,LABEL,MOUNTPOINTS,FSTYPE,TRAN,MODEL,RM'],timeout=8))
        def walk(node,model='',transport='',removable=False,optical=False):
            model=node.get('model') or model;transport=node.get('tran') or transport
            removable=removable or bool(node.get('rm'));optical=optical or node.get('type')=='rom'
            if node.get('fstype') and node.get('fstype')!='swap':
                for mount in node.get('mountpoints') or []:
                    if not mount or not mount.startswith('/') or mount.startswith('/boot') or mount in seen:continue
                    seen.add(mount)
                    name=node.get('label') or (_xp('Lokaler Datenträger') if mount=='/' else _xp('Benutzerdaten') if mount=='/home' else model or node['name'])
                    stats=usage(mount)
                    sub=_xp('{0} frei von {1}').format(format_size(stats['free']), format_size(stats['total'])) if stats else _xp('Belegung nicht verfügbar')
                    group=_xp('Geräte mit Wechselmedien') if removable or optical or transport=='usb' else _xp('Festplatten')
                    groups[group].append(dict(name=name,uri=Path(mount).as_uri(),icon='drive-optical' if optical else 'drive-harddisk-usb' if transport=='usb' else 'drive-removable-media' if removable else 'drive-harddisk',sub=sub+'\n'+mount,tooltip=model,capacity=stats))
            for child in node.get('children',[]):walk(child,model,transport,removable,optical)
        for node in data['blockdevices']:walk(node)
    except Exception:pass
    if '/' not in seen:
        stats=usage('/');sub=_xp('{0} frei von {1}\n/').format(format_size(stats['free']), format_size(stats['total'])) if stats else _xp('Belegung nicht verfügbar\n/')
        groups[_xp('Festplatten')].append(dict(name=_xp('Dateisystem'),uri='file:///',icon='drive-harddisk',sub=sub,capacity=stats))
    groups[_xp('Netzwerk')].append(dict(name=_xp('Netzwerkumgebung'),uri='network:///',icon='network-workgroup',sub=_xp('Netzwerk durchsuchen')))
    for name,uri in bookmarks():
        if not uri.startswith('file:'):groups[_xp('Netzwerk')].append(dict(name=name,uri=uri,icon='folder-remote',sub=_xp('Netzwerkverbindung')))
    return groups

class Explorer(FileActions,NetworkActions,Gtk.ApplicationWindow):
    def __init__(self,app,uri=COMPUTER):
        super().__init__(application=app,title=_xp('Arbeitsplatz'))
        self.app=app;self.set_wmclass('xp-explorer','XP Explorer');self.set_icon_name('folder')
        self.set_default_size(1100,750);self.set_position(Gtk.WindowPosition.CENTER)
        self.get_style_context().add_class('xp-explorer')
        self.alive=True;self.render_generation=0;self.preview_generation=0;self.preview_enabled=False
        self.image_pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='xp-images');self.image_jobs=[];self.preview_job=None;self.preview_cancel=None;self.preview_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='xp-preview')
        self.saved_geometry=None;self.was_maximized=False;self.restore_geometry()
        self.connect('configure-event',self.geometry_changed);self.connect('window-state-event',self.window_state_changed)
        self.view_config=dict(views.DEFAULT);self.view_loading=False;self.computer_selection=None;self.transfer_dialog=None;self.dragging=False
        self.positions={};self.uri=None;self.history=[];self.index=-1;self.generation=0;self.rows=[];self.hidden=False;self.mode='icons';self.busy=False;self.cancel=None;self.nav_cancel=None;self.monitor=None;self.reload_timer=None;self.pixcache={};self.tree_mode=False
        self.connect('delete-event',self.on_close);self.connect('destroy',self.on_destroy);self.connect('key-press-event',self.key)
        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);self.add(outer)
        self.folder_actions=[];self.menu=Gtk.MenuBar();outer.pack_start(self.menu,False,False,0);self.make_menus()
        bar=Gtk.Box(spacing=4);bar.get_style_context().add_class('xp-toolbar');outer.pack_start(bar,False,False,0)
        self.back_btn=self.tool(bar,'go-previous',_xp('Zurück'),lambda:self.travel(-1));self.forward_btn=self.tool(bar,'go-next','',lambda:self.travel(1));self.tool(bar,'go-up','',self.up)
        bar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL),False,False,5)
        self.search_btn=self.tool(bar,'edit-find',_xp('Suchen'),lambda:self.recursive_search(True));self.tool(bar,'folder',_xp('Ordner'),self.toggle_tree)
        self.search_inactive_tools=[self.tool(bar,'image-x-generic',_xp('Vorschau'),self.toggle_preview),self.tool(bar,'view-list',_xp('Ansicht'),self.toggle_view),self.tool(bar,'edit-undo',_xp('Rückgängig'),self.undo)];self.tool(bar,'view-refresh','',self.reload)
        if Gtk.IconTheme.get_default().has_icon('mintxp-start'):
            brand=Gtk.Image.new_from_pixbuf(self.pix('mintxp-start',24))
        else:
            brand=label('XP', 'xp-brand');brand.set_xalign(1)
        bar.pack_end(brand,False,False,12)
        address=Gtk.Box(spacing=7);address.get_style_context().add_class('xp-address');outer.pack_start(address,False,False,0)
        address.pack_start(label(_xp('Adresse:')),False,False,0);self.address=Gtk.Entry();address.pack_start(self.address,True,True,0);self.address.connect('activate',lambda e:self.navigate_entry())
        self.tool(address,'go-next',_xp('Wechseln zu'),self.navigate_entry,20)
        self.searchrow=Gtk.Box(spacing=8);self.searchrow.set_border_width(7);self.search=Gtk.SearchEntry();self.search.set_placeholder_text(_xp('Namen im aktuellen Ordner filtern …'));self.search.connect('search-changed',lambda e:self.render_files());self.searchrow.pack_start(self.search,True,True,0);outer.pack_start(self.searchrow,False,False,0);self.tool(self.searchrow,'edit-find','Unterordner durchsuchen',self.recursive_search,20)
        split=Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL);self.split=split;outer.pack_start(split,True,True,0)
        self.side_stack=Gtk.Stack();self.side_stack.set_homogeneous(False);self.side_stack.set_transition_duration(280);self.side_stack.set_size_request(235,-1)
        taskpage=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);taskpage.get_style_context().add_class('xp-task-pane')
        self.explorer_button=self.side_switch(_xp('Explorer öffnen'),'go-next');taskpage.pack_start(self.explorer_button,False,False,0)
        self.side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=13)
        sidescroll=Gtk.ScrolledWindow();sidescroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);sidescroll.add(self.side);taskpage.pack_start(sidescroll,True,True,0)
        self.side_stack.add_named(taskpage,'tasks')
        treepage=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);treepage.get_style_context().add_class('xp-tree-pane')
        self.standard_button=self.side_switch(_xp('Standardansicht'),'go-previous');treepage.pack_start(self.standard_button,False,False,0)
        self.folder_pane=FolderTree(self,computer_items);treepage.pack_start(self.folder_pane,True,True,0);self.side_stack.add_named(treepage,'folders')
        split.pack1(self.side_stack,False,False)
        right=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL);split.pack2(right,True,False);split.set_position(235)
        self.content=Gtk.Stack();self.content.set_homogeneous(False);self.content.set_transition_type(Gtk.StackTransitionType.NONE);right.pack_start(self.content,True,True,0)
        self.preview_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);self.preview_box.get_style_context().add_class('xp-preview');self.preview_box.set_size_request(300,-1)
        self.preview_box.pack_start(label(_xp('Dateivorschau'),'xp-card-heading'),False,False,0);self.preview_image=Gtk.Image();self.preview_box.pack_start(self.preview_image,False,False,0)
        self.preview_text=label(_xp('Eine Datei auswählen.'));self.preview_text.set_max_width_chars(32);self.preview_text.set_selectable(True);self.preview_box.pack_start(self.preview_text,False,False,0)
        self.preview_excerpt=Gtk.TextView();self.preview_excerpt.set_editable(False);self.preview_excerpt.set_cursor_visible(False);self.preview_excerpt.set_monospace(True);self.preview_excerpt.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);self.preview_excerpt.set_left_margin(7);self.preview_excerpt.set_right_margin(7)
        self.preview_scroll=Gtk.ScrolledWindow();self.preview_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.preview_scroll.set_min_content_height(100);self.preview_scroll.add(self.preview_excerpt);self.preview_box.pack_start(self.preview_scroll,True,True,0);right.pack_end(self.preview_box,False,False,0)
        self.computer_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=22);self.computer_box.set_border_width(20);self.computer_box.get_style_context().add_class('xp-main')
        background=Gtk.EventBox();background.get_style_context().add_class('xp-workarea');background.add(self.computer_box);background.add_events(Gdk.EventMask.BUTTON_PRESS_MASK);background.connect('button-press-event',self.computer_background_context);self.computer_background=background;sc=Gtk.ScrolledWindow();sc.add(background);self.content.add_named(sc,'computer')
        self.store=Gtk.ListStore(GdkPixbuf.Pixbuf,str,str,str,str,object)
        self.iconview=Gtk.IconView.new_with_model(self.store);self.iconview.set_pixbuf_column(0);self.iconview.set_text_column(1);self.iconview.set_item_width(125);self.iconview.set_margin(15);self.iconview.set_row_spacing(18);self.iconview.set_column_spacing(12);self.iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.iconview.connect('item-activated',lambda w,p:self.open_row(self.store[p][5]));self.iconview.connect('selection-changed',lambda w:self.selected_changed());self.iconview.connect('button-press-event',self.context)
        sc=Gtk.ScrolledWindow();self.icon_scroll=sc;sc.add(self.iconview);self.content.add_named(sc,'icons')
        self.tree=Gtk.TreeView(model=self.store);self.tree.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE);self.tree.get_selection().connect('changed',lambda s:self.selected_changed());self.tree.connect('row-activated',lambda w,p,c:self.open_row(self.store[p][5]));self.tree.connect('button-press-event',self.context)
        c=Gtk.TreeViewColumn('Name');p=Gtk.CellRendererPixbuf();p.set_fixed_size(28,28);c.pack_start(p,False);c.add_attribute(p,'pixbuf',0);txt=Gtk.CellRendererText();c.pack_start(txt,True);c.add_attribute(txt,'text',1);c.set_expand(True);c.set_resizable(True);c.set_sizing(Gtk.TreeViewColumnSizing.FIXED);c.set_fixed_width(300);self.tree.append_column(c)
        for n,title in [(2,_xp('Größe')),(3,'Typ'),(4,_xp('Geändert am'))]:
            c=Gtk.TreeViewColumn(title,Gtk.CellRendererText(),text=n);c.set_resizable(True);c.set_sizing(Gtk.TreeViewColumnSizing.FIXED);c.set_fixed_width(150);self.tree.append_column(c)
        for column,key in zip(self.tree.get_columns(),('name','size','mime','modified')):
            column.set_clickable(True);column.connect('clicked',lambda c,k=key:self.sort_by(k))
        self.dragdrop=DragDrop(self)
        sc=Gtk.ScrolledWindow();self.detail_scroll=sc;sc.add(self.tree);self.content.add_named(sc,'details')
        self.message=label('');self.message.set_margin_start(24);self.message.set_margin_end(24);self.content.add_named(self.message,'message')
        foot=Gtk.Box(spacing=12);foot.set_border_width(5);self.status=label('Bereit');self.status.set_line_wrap(False);self.status.set_ellipsize(Pango.EllipsizeMode.MIDDLE);foot.pack_start(self.status,True,True,0);zoom=Gtk.Box(spacing=2);foot.pack_start(zoom,False,False,0)
        for text,step in [('−',-16),('+',16)]:
            b=Gtk.Button(label=text);b.set_tooltip_text(_xp('Symbolgröße ändern (Strg +/−)'));b.connect('clicked',lambda w,n=step:self.zoom(n));zoom.add(b);self.search_inactive_tools.append(b)
        self.progress=Gtk.ProgressBar();self.progress.set_size_request(160,-1);foot.pack_start(self.progress,False,False,0);self.stop=Gtk.Button(label=_xp('Abbrechen'));self.stop.connect('clicked',lambda b:self.cancel.cancel() if self.cancel else None);foot.pack_start(self.stop,False,False,0);outer.pack_end(foot,False,False,0)
        self.devices=Devices(self)
        self.watch_bookmarks();self.show_all();self.preview_box.hide();self.searchrow.hide();self.progress.hide();self.stop.hide();self.navigate(uri)
    def tool(self,box,icon,text,action,size=24):
        b=Gtk.Button();b.set_relief(Gtk.ReliefStyle.NONE);inner=Gtk.Box(spacing=5)
        toolbar={'go-previous':'back','go-next':'forward','go-up':'up','edit-find':'search','folder':'folders','view-list':'view','edit-undo':'undo'}
        themed='mintxp-toolbar-'+toolbar[icon] if icon in toolbar else icon
        selected=themed if Gtk.IconTheme.get_default().has_icon(themed) else icon
        pix=self.pix(selected,size);img=Gtk.Image.new_from_pixbuf(pix);inner.pack_start(img,False,False,0)
        def sensitivity(button,*args):
            shown=pix
            if not button.get_sensitive():
                shown=pix.copy();pix.saturate_and_pixelate(shown,0.0,False)
            img.set_from_pixbuf(shown)
        b.connect('notify::sensitive',sensitivity)
        if text:inner.pack_start(label(text),False,False,0)
        b.add(inner);b.set_tooltip_text(text or {'go-up':'Eine Ebene nach oben','go-next':_xp('Vorwärts'),'view-refresh':_xp('Aktualisieren')}.get(icon,icon));b.connect('clicked',lambda w:action());box.pack_start(b,False,False,0);return b
    def pix(self,icon,size=48):
        key=(icon.to_string() if isinstance(icon,Gio.Icon) else str(icon),size)
        if key not in self.pixcache:
            try:
                theme=Gtk.IconTheme.get_default();flags=Gtk.IconLookupFlags.FORCE_SIZE|Gtk.IconLookupFlags.FORCE_REGULAR
                info=theme.lookup_by_gicon(icon,size,flags) if isinstance(icon,Gio.Icon) else theme.lookup_icon(icon or 'text-x-generic',size,flags)
                self.pixcache[key]=info.load_icon() if info else theme.load_icon('text-x-generic',size,flags)
            except Exception:self.pixcache[key]=None
        return self.pixcache[key]
    def make_menus(self):
        groups=[(_xp('Datei'),[(_xp('Neues Fenster'),lambda:self.app.window(self.uri)),(_xp('Neuer Ordner'),self.mkdir),(_xp('Umbenennen'),self.rename),(_xp('Löschen (Entf)'),self.delete_selected),(_xp('Endgültig löschen (Umschalt+Entf)'),self.permanent_delete),(_xp('Papierkorb leeren …'),self.empty_trash),(_xp('Aus Papierkorb wiederherstellen'),self.restore_trash),(_xp('Eigenschaften'),self.properties),(_xp('Schließen'),self.close)]),(_xp('Bearbeiten'),[(_xp('Rückgängig (Strg+Z)'),self.undo),(_xp('Ausschneiden'),lambda:self.copy(True)),(_xp('Kopieren'),self.copy),(_xp('Einfügen'),self.paste),(_xp('Alles auswählen'),self.select_all)]),(_xp('Ansicht'),[(_xp('Symbole / Details'),self.toggle_view),(_xp('Ordnerleiste'),self.toggle_tree),(_xp('Ordner filtern (Strg+Umschalt+F)'),self.toggle_search),(_xp('Dateivorschau'),self.toggle_preview),(_xp('Versteckte Dateien'),self.toggle_hidden),(_xp('Aktualisieren'),self.reload),(_xp('Nach Name sortieren'),lambda:self.sort_by('name')),(_xp('Nach Größe sortieren'),lambda:self.sort_by('size')),('Nach Typ sortieren',lambda:self.sort_by('mime')),('Nach Datum sortieren',lambda:self.sort_by('modified'))]),(_xp('Favoriten'),[]),(_xp('Extras'),[(_xp('Mit Server verbinden …'),self.connect_server),('Netzwerkverbindung trennen',self.disconnect_server),(_xp('Ersetzte Dateien wiederherstellen'),self.recover_replacements),(_xp('In Nemo öffnen'),self.open_nemo),(_xp('Systemsteuerung'),self.launch_settings)]),(_xp('Hilfe'),[(_xp('Über XP Explorer'),self.about)])]
        for title,entries in groups:
            parent=Gtk.MenuItem(label=title);menu=Gtk.Menu();parent.set_submenu(menu);self.menu.append(parent)
            if title==_xp('Favoriten'):
                self.favorites_menu=menu;menu.connect('show',lambda *_:self.populate_favorites())
            for name,fn in entries:
                item=Gtk.MenuItem(label=name);item.connect('activate',lambda w,f=fn:f());menu.append(item)
                if (title==_xp('Datei') and name not in (_xp('Neues Fenster'),_xp('Eigenschaften'),_xp('Schließen'))) or (title==_xp('Bearbeiten') and name!=_xp('Kopieren')) or (title==_xp('Ansicht') and name not in (_xp('Ordnerleiste'),_xp('Ordner filtern (Strg+Umschalt+F)'))):self.folder_actions.append(item)
    def populate_favorites(self):
        menu=self.favorites_menu
        for child in menu.get_children():child.destroy()
        entries=[(_xp('Diesen Ordner zu Favoriten hinzufügen'),self.add_favorite),(_xp('Favoriten verwalten'),self.manage_favorites)]
        for title,fn in entries:
            item=Gtk.MenuItem(label=title);item.connect('activate',lambda _,f=fn:f());menu.append(item)
            if fn==self.add_favorite:item.set_sensitive(self.uri not in (COMPUTER,'trash:///','network:///'))
        menu.append(Gtk.SeparatorMenuItem())
        for name,uri in bookmarks():
            item=Gtk.MenuItem(label=name);item.connect('activate',lambda _,u=uri:self.navigate(u));menu.append(item)
        menu.show_all()
    def add_favorite(self,uri=None):
        uri=uri or self.uri
        if uri in (COMPUTER,'trash:///','network:///'):return
        try:
            added=bookmark_store.change(uri,'add')
            self.status.set_text(_xp('Favorit hinzugefügt.') if added else _xp('Dieser Ordner ist bereits ein Favorit.'));self.refresh_bookmarks()
        except Exception as e:self.error(e)
    def manage_favorites(self):
        from favorites_ui import FavoritesWindow
        if getattr(self,'favorites_window',None) and self.favorites_window.get_visible():self.favorites_window.present();return
        self.favorites_window=FavoritesWindow(self,bookmark_store)
    def refresh_bookmarks(self):
        if self.alive:self.folder_pane.reload_bookmarks()
    def watch_bookmarks(self):
        self.bookmarks_monitor=None;self.bookmarks_timer=None
        bookmark_store.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            self.bookmarks_monitor=Gio.File.new_for_path(str(bookmark_store.path.parent)).monitor_directory(Gio.FileMonitorFlags.NONE,None)
            def changed(m,f,other,event):
                if f.get_basename()!=bookmark_store.path.name and (not other or other.get_basename()!=bookmark_store.path.name):return
                if self.bookmarks_timer:GLib.source_remove(self.bookmarks_timer)
                def refresh():
                    self.bookmarks_timer=None;self.refresh_bookmarks();return False
                self.bookmarks_timer=GLib.timeout_add(150,refresh)
            self.bookmarks_monitor.connect('changed',changed)
        except GLib.Error:pass
    def spawn(self,work,callback):
        def run():
            try:value,error=work(),None
            except Exception as e:value,error=None,e
            GLib.idle_add(callback,value,error)
        threading.Thread(target=run,daemon=True).start()
    def navigate_entry(self):
        text=self.address.get_text().strip()
        if self.search_active() and text==_xp('Suchergebnisse'):return
        if text.startswith('\\\\'):
            try:self.navigate(server_uri(text))
            except ValueError as e:self.error(e)
        elif text in (_xp('Arbeitsplatz'),'Computer'):self.navigate(COMPUTER)
        elif text:
            if '://' in text and text.split('://',1)[0] in NETWORK_SCHEMES:
                try:self.navigate(server_uri(text))
                except ValueError as e:self.error(e)
                return
            if '://' not in text and not text.startswith(('/','~')) and self.uri!=COMPUTER:
                self.navigate(file_for(self.uri).resolve_relative_path(text).get_uri())
            else:self.navigate(file_for(text).get_uri())
    def search_active(self):return bool(getattr(self,'search_window',None) and self.search_window.active)
    def navigate(self,uri,history=True,select_uri=None,_mount_retry=False):
        if self.busy:return
        if self.search_active():self.search_window.hide(False)
        if file_for(uri).get_uri_scheme() in NETWORK_SCHEMES:
            try:uri=server_uri(uri)
            except ValueError as e:self.error(e);return
        if self.reload_timer:GLib.source_remove(self.reload_timer);self.reload_timer=None
        uri,reveal=browse_target(uri);select_uri=select_uri or reveal
        if select_uri and file_for(select_uri).get_basename().startswith("."):self.hidden=True
        self.capture_position()
        uri=file_for(uri).get_uri();self.generation+=1;self.render_generation+=1;generation=self.generation;self.directory_loading=uri!=COMPUTER
        if self.nav_cancel:self.nav_cancel.cancel()
        self.nav_cancel=Gio.Cancellable();cancel=self.nav_cancel
        if not _mount_retry:self.mount_attempted=False
        if self.monitor:self.monitor.cancel();self.monitor=None
        if self.uri!=uri:
            self.save_view();self.view_config=views.get(uri);self.mode=self.view_config['mode'];self.view_loading=True
            for column,width,key in zip(self.tree.get_columns(),self.view_config['columns'],('name','size','mime','modified')):
                column.set_fixed_width(width);column.set_sort_indicator(key==self.view_config['sort']);column.set_sort_order(Gtk.SortType.DESCENDING if self.view_config['descending'] else Gtk.SortType.ASCENDING)
            self.view_loading=False
        self.uri=uri;self.rows=[];self.store.clear();self.preview_generation+=1
        if hasattr(self,'preview_image'):self.update_preview([])
        if history:
            if self.index<0 or self.history[self.index]!=uri:self.history=self.history[:self.index+1]+[uri];self.index=len(self.history)-1
        self.back_btn.set_sensitive(self.index>0);self.forward_btn.set_sensitive(self.index<len(self.history)-1)
        self.address.set_text(_xp('Arbeitsplatz') if uri==COMPUTER else file_for(uri).get_parse_name());self.search.set_text('');self.status.set_text(_xp('Inhalt wird geladen …'));self.message.set_text(_xp('Inhalt wird geladen …'));self.content.set_visible_child_name('message');self.build_side()
        if self.tree_mode:
            if not getattr(self,'_tree_navigation',False):self.folder_pane.anchor=None
            self.folder_pane.sync(uri)
        def done(value,error):
            if not self.alive or generation!=self.generation:return False
            self.directory_loading=False
            if error:
                if isinstance(error,GLib.Error) and error.matches(Gio.io_error_quark(),Gio.IOErrorEnum.NOT_MOUNTED) and not self.mount_attempted:self.mount(uri);return False
                if isinstance(error,GLib.Error) and error.matches(Gio.io_error_quark(),Gio.IOErrorEnum.NOT_DIRECTORY):
                    parent=file_for(uri).get_parent()
                    if parent:
                        if self.index>=0:self.history[self.index]=parent.get_uri()
                        self.navigate(parent.get_uri(),False,select_uri=uri);return False
                self.message.set_text(_xp('Dieser Ort konnte nicht geöffnet werden.\n\n')+str(error));self.status.set_text(_xp('Nicht geöffnet – Zurück oder einen anderen Ort wählen'));return False
            if uri==COMPUTER:self.render_computer(value)
            else:
                self.rows=value;self.render_files()
                if select_uri:
                    if not self.reveal_selection(select_uri):self.pending_reveal=(generation,select_uri)
                elif len(self.store)<len(self.rows):self.pending_position=generation
                else:self.restore_position(generation)
                try:
                    self.monitor=file_for(uri).monitor_directory(Gio.FileMonitorFlags.NONE,None);self.monitor.connect('changed',self.changed)
                except GLib.Error:pass
            self.set_title(_xp('Arbeitsplatz') if uri==COMPUTER else (file_for(uri).get_basename() or '/')+' – XP Explorer');return False
        if uri==COMPUTER:self.spawn(computer_items,done)
        else:
            partial=[]
            def batch(rows):
                partial.extend(rows)
                if len(partial)<=150:
                    self.rows=list(partial);self.render_files()
                self.status.set_text(_xp('{0} Einträge geladen …').format(len(partial)))
            directory_loader.start(uri,self.hidden,cancel,lambda:self.alive and generation==self.generation,batch,done)
    def reveal_selection(self,uri):
        self.iconview.unselect_all();self.tree.get_selection().unselect_all()
        for row in self.store:
            if file_for(row[5]['uri']).equal(file_for(uri)):
                path=row.path
                if self.mode=='icons':
                    self.iconview.select_path(path);self.iconview.set_cursor(path,None,False)
                    self.iconview.scroll_to_path(path,True,.5,.5);self.iconview.grab_focus()
                else:
                    self.tree.set_cursor(path);self.tree.get_selection().select_path(path)
                    self.tree.scroll_to_cell(path,None,True,.5,0);self.tree.grab_focus()
                self.selected_changed();return True
        return False
    def changed(self,*args):
        if self.reload_timer:GLib.source_remove(self.reload_timer)
        self.reload_timer=GLib.timeout_add(700,self.monitor_reload)
    def monitor_reload(self):
        self.reload_timer=None
        if self.dragging or any(isinstance(d,Gtk.Dialog) and d.get_transient_for()==self and d.get_visible() for d in Gtk.Window.list_toplevels()) or (getattr(self,'context_menu',None) and self.context_menu.get_visible()):self.reload_timer=GLib.timeout_add(350,self.monitor_reload)
        elif not self.busy:self.reload()
        return False
    def reload(self):
        if self.search_active():self.search_window.start();return
        if self.uri:
            self.navigate(self.uri,False)
        for it in list(self.folder_pane.nodes.get(self.uri,[])):
            if self.folder_pane.valid(it):self.folder_pane.load(it,True)
    def travel(self,step):
        if self.search_active() and step<0:self.search_window.hide();return
        idx=self.index+step
        if not self.busy and 0<=idx<len(self.history):self.index=idx;self.navigate(self.history[idx],False)
    def up(self):
        if self.uri==COMPUTER:return
        p=file_for(self.uri).get_parent();self.navigate(p.get_uri() if p else COMPUTER)
    def card(self,title,links):
        card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);card.get_style_context().add_class('xp-card');head=label(title,'xp-card-heading');card.pack_start(head,False,False,0)
        body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3);body.get_style_context().add_class('xp-card-body');card.pack_start(body,False,False,0)
        for name,icon,fn in links:
            b=Gtk.Button();b.set_relief(Gtk.ReliefStyle.NONE);b.get_style_context().add_class('xp-task-link');row=Gtk.Box(spacing=7);row.pack_start(Gtk.Image.new_from_pixbuf(self.pix(icon,16)),False,False,0);txt=label(name);txt.set_max_width_chars(23);row.pack_start(txt,True,True,0);b.add(row);b.connect('clicked',lambda w,f=fn:f());body.pack_start(b,False,False,0)
            if name in (_xp('Papierkorb'),_xp('Netzwerkumgebung')):
                uri='trash:///' if name==_xp('Papierkorb') else 'network:///'
                b.connect('button-press-event',lambda w,e,u=uri:self.place_context(u,e) if e.button==3 else False)
        self.side.pack_start(card,False,False,0);return body
    def build_side(self):
        for w in self.side.get_children():w.destroy()
        if self.uri==COMPUTER:
            self.card(_xp('Systemaufgaben'),[(_xp('Systeminformationen'),'computer',self.system_info),(_xp('Systemsteuerung'),'preferences-system',self.launch_settings)])
        elif self.uri.startswith('trash:'):
            self.card('Papierkorbaufgaben',[('Wiederherstellen','edit-undo',self.restore_trash),(_xp('Endgültig löschen'),'edit-delete',self.permanent_delete),(_xp('Papierkorb leeren …'),'user-trash-full',self.empty_trash)])
        else:
            self.card(_xp('Datei- und Ordneraufgaben'),[(_xp('Neuen Ordner erstellen'),'folder-new',self.mkdir),(_xp('Kopieren'),'edit-copy',self.copy),(_xp('Ausschneiden'),'edit-cut',lambda:self.copy(True)),(_xp('Einfügen'),'edit-paste',self.paste),(_xp('Umbenennen'),'edit-rename',self.rename),(_xp('Rückgängig'),'edit-undo',self.undo),(_xp('In den Papierkorb'),'user-trash',self.trash)])
        if self.uri.startswith(('network:','smb:','sftp:','ftp:','ftps:','dav:','davs:','afp:','nfs:')):
            self.card('Netzwerkaufgaben',[(_xp('Mit Server verbinden …'),'network-server',self.connect_server),(_xp('Verbindung trennen'),'network-offline',self.disconnect_server)])
        self.card(_xp('Andere Orte'),[(_xp('Arbeitsplatz'),'computer',lambda:self.navigate(COMPUTER)),(_xp('Eigene Dateien'),'user-home',lambda:self.navigate(Path.home().as_uri())),(_xp('Netzwerkumgebung'),'network-workgroup',lambda:self.navigate('network:///')),(_xp('Papierkorb'),'user-trash',lambda:self.navigate('trash:///'))])
        body=self.card(_xp('Details'),[]);self.detail_label=label(_xp('Wähle einen Eintrag aus.'));self.detail_label.set_max_width_chars(25);body.pack_start(self.detail_label,False,False,0);self.side.show_all()
    def bookmark_places(self):return bookmarks()
    def side_switch(self,text,icon):
        b=Gtk.Button();b.get_style_context().add_class('xp-side-switch');row=Gtk.Box(spacing=8)
        row.pack_start(Gtk.Image.new_from_pixbuf(self.pix(icon,16)),False,False,0);row.pack_start(label(text),False,False,0)
        b.add(row);b.connect('clicked',lambda w:self.toggle_tree());return b
    def render_computer(self,groups):
        groups=self.devices.enrich(groups)
        for w in self.computer_box.get_children():w.destroy()
        count=0;self.computer_selection=None;self.computer_grids=[]
        for title,items in groups.items():
            if not items:continue
            section=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=9);section.get_style_context().add_class('xp-computer-section');self.computer_box.pack_start(section,False,False,0)
            header=Gtk.Box(spacing=9);header.pack_start(Gtk.Image.new_from_pixbuf(self.pix({_xp('Dateien auf diesem Computer'):'user-home',_xp('Festplatten'):'drive-harddisk',_xp('Geräte mit Wechselmedien'):'drive-removable-media',_xp('Netzwerk'):'network-workgroup'}.get(title,'folder'),24)),False,False,0);head=label({_xp('Dateien auf diesem Computer'):_xp('Persönliche Ordner'),_xp('Festplatten'):_xp('Interne Laufwerke'),_xp('Geräte mit Wechselmedien'):_xp('Externe Laufwerke und Wechselmedien'),_xp('Netzwerk'):_xp('Netzwerk und Freigaben')}.get(title,title),'xp-group-heading');header.pack_start(head,True,True,0);section.pack_start(header,False,False,0)
            grid=Gtk.FlowBox();grid.set_selection_mode(Gtk.SelectionMode.SINGLE);grid.set_activate_on_single_click(False);grid.set_min_children_per_line(1);grid.set_max_children_per_line(3);grid.set_column_spacing(16);grid.set_row_spacing(10);grid.set_homogeneous(True)
            for item in items:
                row=Gtk.Box(spacing=10);row.set_border_width(7);row.set_size_request(205,68);row.pack_start(Gtk.Image.new_from_pixbuf(self.pix(item['icon'],48)),False,False,0);text=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3)
                name=label(item['name'],'xp-drive-name');name.set_max_width_chars(25);text.pack_start(name,False,False,0)
                if title in (_xp('Festplatten'),_xp('Geräte mit Wechselmedien')):
                    stats=item.get('capacity');tip=(_xp('{0:.0%} belegt · {1} belegt · {2} verfügbar · {3} gesamt').format(stats['fraction'], format_size(stats['used']), format_size(stats['free']), format_size(stats['total'])) if stats else (_xp('Nicht eingehängt – Belegung erst nach dem Öffnen verfügbar') if item.get('volume_object') else _xp('Belegung nicht verfügbar')))
                    bar=CapacityBar(stats,tip);text.pack_start(bar,False,False,3)
                sub=label(item['sub'],'xp-drive-sub');sub.set_max_width_chars(28);text.pack_start(sub,False,False,0);row.pack_start(text,True,True,0);grid.add(row);child=row.get_parent();child.item=item;child.set_tooltip_text(item.get('tooltip','')+'\n'+item['uri']);count+=1
                child.connect('button-press-event',self.computer_context)
            grid.connect('button-press-event',self.computer_background_context)
            self.computer_grids.append(grid);grid.connect('selected-children-changed',self.computer_selected)
            grid.connect('child-activated',lambda w,c:self.devices.open(c.item));section.pack_start(grid,False,False,0)
        self.computer_box.show_all();self.content.set_visible_child_name('computer');self.status.set_text(_xp('{0} Orte – Doppelklick zum Öffnen').format(count))
    def render_files(self):
        if self.uri==COMPUTER or self.search_active():return
        selected={r['uri'] for r in self.selected()};self.render_generation+=1;render_id=self.render_generation
        size=self.view_config.get('zoom',48);self.iconview.set_item_width(max(125,size+50))
        for job in self.image_jobs:job.cancel()
        self.image_jobs=[]
        term=self.search.get_text().casefold();rows=views.sorted_rows([r for r in self.rows if term in r['name'].casefold()],self.view_config['sort'],self.view_config['descending']);self.store.clear();self.store.set_sort_column_id(Gtk.TREE_SORTABLE_UNSORTED_SORT_COLUMN_ID,Gtk.SortType.ASCENDING)
        self.content.set_visible_child_name(self.mode);cursor=[0]
        def append_chunk():
            if not self.alive or render_id!=self.render_generation:return False
            started=time.monotonic();count=0
            while cursor[0]<len(rows) and count<150 and time.monotonic()-started<.012:
                row_index=cursor[0];r=rows[row_index];cursor[0]+=1;count+=1
                kind=_xp('Dateiordner') if r['dir'] else Gio.content_type_get_description(r['mime']) or _xp('Datei');date=datetime.datetime.fromtimestamp(r['modified']).strftime('%d.%m.%Y %H:%M') if r['modified'] else ''
                it=self.store.append([self.pix(r['icon'],24 if self.mode=='details' else size),r['name'],'' if r['dir'] else format_size(r['size']),kind,date,r])
                if r['uri'] in selected:
                    path=self.store.get_path(it);self.iconview.select_path(path);self.tree.get_selection().select_path(path)
                if row_index<256 and self.mode=='icons' and r['mime'].startswith('image/') and r['uri'].startswith('file:'):
                    ref=Gtk.TreeRowReference.new(self.store,self.store.get_path(it))
                    def ready(pix,ref=ref,rid=render_id):
                        if self.alive and rid==self.render_generation and ref.valid() and pix:self.store[ref.get_path()][0]=pix
                    self.queue_image(r['uri'],size,ready)
            pending=cursor[0]<len(rows)
            self.status.set_text(_xp('{0} von {1} Einträgen angezeigt …').format(cursor[0],len(rows)) if pending else _xp('{0} Objekte').format(len(rows))+(_xp(' (gefiltert)') if term else ''))
            if not pending:
                self.selected_changed()
                reveal=getattr(self,'pending_reveal',None)
                if reveal and reveal[0]==self.generation:self.pending_reveal=None;self.reveal_selection(reveal[1])
                restore=getattr(self,'pending_position',None)
                if restore==self.generation:self.pending_position=None;self.restore_position(restore)
            return pending
        if append_chunk():GLib.timeout_add(16,append_chunk)
    def select_uris(self,uris):
        self.iconview.unselect_all();self.tree.get_selection().unselect_all()
        for row in self.store:
            if row[5]['uri'] in uris:
                self.iconview.select_path(row.path);self.tree.get_selection().select_path(row.path)
    def capture_position(self):
        if self.search_active():return
        if not self.uri or self.uri==COMPUTER or self.content.get_visible_child_name()=='message':return
        scroll=self.icon_scroll if self.mode=='icons' else self.detail_scroll
        self.positions.pop(self.uri,None);self.positions[self.uri]=([r['uri'] for r in self.selected()],scroll.get_vadjustment().get_value())
        if len(self.positions)>100:self.positions.pop(next(iter(self.positions)))
    def restore_position(self,generation):
        saved=self.positions.get(self.uri)
        if not saved:return
        self.select_uris(saved[0])
        def restore():
            if self.alive and generation==self.generation:
                adj=(self.icon_scroll if self.mode=='icons' else self.detail_scroll).get_vadjustment();adj.set_value(min(saved[1],max(0,adj.get_upper()-adj.get_page_size())))
            return False
        GLib.timeout_add(50,restore)
    def zoom(self,step):
        if self.uri==COMPUTER or self.search_active():return
        self.capture_position();self.view_config['zoom']=max(32,min(128,self.view_config.get('zoom',48)+step));self.save_view();self.render_files()
    def selected(self):
        if self.search_active():
            m,it=self.search_window.tree.get_selection().get_selected()
            return [m[it][2]] if it is not None else []
        if self.uri==COMPUTER:return [dict(self.computer_selection,dir=True,mime='inode/directory',size=0,modified=0,volume=bool(self.computer_selection.get('mount')) or str(self.computer_selection.get('icon','')).startswith('drive-'))] if self.computer_selection else []
        paths=self.iconview.get_selected_items() if self.mode=='icons' else self.tree.get_selection().get_selected_rows()[1]
        return [self.store[p][5] for p in paths]
    def selected_changed(self):
        rows=self.selected()
        self.update_preview(rows)
        if hasattr(self,'detail_label') and not self.tree_mode:
            if len(rows)==1:
                r=rows[0];self.detail_label.set_text(r['name']+'\n\n'+(_xp('Dateiordner') if r['dir'] else format_size(r['size'])))
            else:self.detail_label.set_text(_xp('{0} Objekte ausgewählt').format(len(rows)) if rows else _xp('Wähle einen Eintrag aus.'))
    def queue_image(self,uri,size,callback,preview=False):
        if preview:
            if self.preview_job:self.preview_job.cancel()
            job=self.preview_pool.submit(load_image,uri,size);self.preview_job=job
        else:
            job=self.image_pool.submit(cached_image,uri,size);self.image_jobs.append(job)
        def completed(future):
            if future.cancelled():return
            try:pix=future.result()
            except Exception:pix=None
            def deliver():
                if self.alive:callback(pix)
                return False
            GLib.idle_add(deliver)
        job.add_done_callback(completed)
    def update_preview(self,rows):
        self.preview_generation+=1;token=self.preview_generation;self.preview_image.clear();self.preview_excerpt.get_buffer().set_text('');self.preview_scroll.hide()
        if self.preview_cancel:self.preview_cancel.set()
        if self.preview_job:self.preview_job.cancel()
        if not self.preview_enabled:return
        if len(rows)!=1 or rows[0].get('dir'):
            self.preview_text.set_text(_xp('Eine Datei auswählen.') if len(rows)<2 else _xp('{0} Objekte ausgewählt. Für eine Vorschau eine einzelne Datei wählen.').format(len(rows)));return
        r=rows[0];self.preview_text.set_text(r['name']+_xp('\n\nVorschau wird geladen …'));cancel=threading.Event();self.preview_cancel=cancel
        job=self.preview_pool.submit(generate_preview,r['uri'],r['mime'],cancel);self.preview_job=job
        def completed(future):
            if future.cancelled():return
            try:result,pix=future.result()
            except Exception:result,pix={'detail':_xp('Keine Vorschau verfügbar.')},None
            def deliver():
                if not self.alive or token!=self.preview_generation or cancel.is_set():return False
                if pix:self.preview_image.set_from_pixbuf(pix)
                self.preview_text.set_text(r['name']+'\n'+format_size(r['size'])+'\n\n'+result.get('detail',''))
                text=result.get('text','');self.preview_excerpt.get_buffer().set_text(text);self.preview_scroll.set_visible(bool(text));self.preview_scroll.get_vadjustment().set_value(0)
                return False
            GLib.idle_add(deliver)
        job.add_done_callback(completed)
    def restore_geometry(self):
        state=read_state();display=Gdk.Display.get_default();areas=[]
        for i in range(display.get_n_monitors()):
            r=display.get_monitor(i).get_workarea();areas.append((r.x,r.y,r.width,r.height))
        rect=clamp_geometry(state,areas) if areas else None
        if rect:
            x,y,w,h=rect;self.set_position(Gtk.WindowPosition.NONE);self.set_default_size(w,h);self.move(x,y);self.saved_geometry=dict(x=x,y=y,width=w,height=h)
        if state.get('maximized') is True:self.maximize();self.was_maximized=True
    def geometry_changed(self,*args):
        if not self.was_maximized and not self.is_maximized():
            x,y=self.get_position();w,h=self.get_size();self.saved_geometry=dict(x=x,y=y,width=w,height=h)
        return False
    def window_state_changed(self,w,event):
        self.was_maximized=bool(event.new_window_state&Gdk.WindowState.MAXIMIZED)
        return False
    def save_geometry(self):
        if self.saved_geometry:
            try:write_state(dict(read_state(),**self.saved_geometry,maximized=self.was_maximized))
            except OSError as e:print(_xp('Fensterzustand konnte nicht gespeichert werden:'),e,file=sys.stderr)
    def open_row(self,r):
        if self.busy:return
        if r.get('target') and (r.get('shortcut') or r.get('mountable')):self.navigate(r['target'])
        elif r.get('mountable'):self.mount_location(r['uri'],True)
        elif r['dir']:self.navigate(r['uri'])
        else:
            try:
                app=Gio.AppInfo.get_default_for_type(r['mime'],False)
                if app:app.launch([file_for(r['uri'])],Gdk.Display.get_default().get_app_launch_context())
                else:self.open_with(r)
            except Exception as e:self.error(e)
    def mount(self,uri):self.mount_location(uri)
    def open_with(self,r):
        d=Gtk.AppChooserDialog(content_type=r['mime'],transient_for=self,modal=True)
        if d.run()==Gtk.ResponseType.OK:
            try:d.get_app_info().launch([file_for(r['uri'])],None)
            except Exception as e:self.error(e)
        d.destroy()
    def select_all(self):
        if self.mode=='icons':self.iconview.select_all()
        else:self.tree.get_selection().select_all()
    def toggle_view(self):self.mode='details' if self.mode=='icons' else 'icons';self.view_config['mode']=self.mode;self.save_view();self.render_files()
    def toggle_hidden(self):self.hidden=not self.hidden;self.reload()
    def toggle_tree(self):
        if self.search_active():self.search_window.hide();self.tree_mode=False
        self.tree_mode=not self.tree_mode
        self.side_stack.set_visible_child_full('folders' if self.tree_mode else 'tasks',Gtk.StackTransitionType.SLIDE_LEFT if self.tree_mode else Gtk.StackTransitionType.SLIDE_RIGHT)
        if self.tree_mode:self.folder_pane.sync(self.uri)
    def toggle_preview(self):
        self.preview_enabled=not self.preview_enabled;self.preview_box.set_visible(self.preview_enabled);self.selected_changed()
    def recursive_search(self,toggle=False):
        if self.busy:return
        if getattr(self,'search_window',None) and self.search_window.alive:
            if toggle and self.search_active():self.search_window.hide()
            else:self.search_window.present()
        else:self.search_window=SearchWindow(self)
    def toggle_search(self):
        if self.search_active():self.search_window.hide()
        visible=not self.searchrow.get_visible();self.searchrow.set_visible(visible)
        if visible:self.search.grab_focus()
        else:self.search.set_text('');(self.iconview if self.mode=='icons' else self.tree).grab_focus()
    def xp_menu(self,entries):return context_actions.build_menu(self,entries)
    def show_context_menu(self,entries,event=None):
        if hasattr(self,'context_menu'):self.context_menu.destroy()
        self.context_menu=self.xp_menu(entries);self.context_menu.show_all()
        if event:self.context_menu.popup_at_pointer(event)
        else:
            widget=self.computer_background if self.uri==COMPUTER else self.iconview if self.mode=='icons' else self.tree
            self.context_menu.popup_at_widget(widget,Gdk.Gravity.NORTH_WEST,Gdk.Gravity.NORTH_WEST,Gtk.get_current_event())
        return True
    def computer_background_context(self,widget,event):
        if event.button!=3:return False
        if self.busy:return True
        if isinstance(widget,Gtk.FlowBox):
            child=widget.get_child_at_pos(int(event.x),int(event.y))
            if child:return self.computer_context(child,event)
        for grid in self.computer_grids:grid.unselect_all()
        self.computer_selection=None;self.selected_changed()
        return self.show_context_menu(context_actions.background_entries(self,True),event)
    def keyboard_context(self):
        if self.busy:return True
        if self.uri==COMPUTER:
            if self.computer_selection:return self.show_context_menu(self.computer_entries(self.computer_selection))
            return self.show_context_menu(context_actions.background_entries(self,True))
        return self.show_context_menu(context_actions.file_entries(self,self.selected()))
    def launch_settings(self):
        try:subprocess.Popen([str(Path.home()/'.local/bin/xp-control-panel')])
        except Exception as error:self.error(error)
    def set_mode(self,mode):
        self.mode=mode;self.view_config['mode']=mode;self.save_view();self.render_files()
    def context(self,w,event):
        if event.button!=3:return False
        if self.busy:return True
        p=w.get_path_at_pos(int(event.x),int(event.y))
        if p:
            if w==self.tree:p=p[0]
            if w==self.iconview and not w.path_is_selected(p):w.unselect_all();w.select_path(p)
            elif w==self.tree and not w.get_selection().path_is_selected(p):w.get_selection().unselect_all();w.get_selection().select_path(p)
        elif w==self.iconview:w.unselect_all()
        else:w.get_selection().unselect_all()
        return self.show_context_menu(context_actions.file_entries(self,self.selected()),event)
    def new_text(self):
        if self.busy or self.uri==COMPUTER or self.uri.startswith('trash:'):return
        name=self.prompt('Neues Textdokument','Neues Textdokument.txt')
        if name is None:return
        try:
            from core import child_name
            target=file_for(self.uri).get_child(child_name(name));stream=target.create(Gio.FileCreateFlags.NONE,None);stream.close(None);self.app.undo_history.remember_created(target.get_uri());self.navigate(self.uri,False,select_uri=target.get_uri())
        except Exception as e:self.error(e)
    def prompt(self,title,value='',select_end=-1):
        d=Gtk.Dialog(title=title,transient_for=self,modal=True);d.add_buttons(_xp('Abbrechen'),Gtk.ResponseType.CANCEL,_xp('OK'),Gtk.ResponseType.OK);d.set_default_response(Gtk.ResponseType.OK);e=Gtk.Entry(text=value);e.set_activates_default(True);e.set_margin_top(15);e.set_margin_bottom(15);e.set_margin_start(15);e.set_margin_end(15);d.get_content_area().add(e);d.show_all();e.select_region(0,select_end);answer=e.get_text() if d.run()==Gtk.ResponseType.OK else None;d.destroy();return answer
    def mkdir(self):
        if self.busy or self.uri==COMPUTER or self.uri.startswith(('trash:','network:')):return
        name=self.prompt(_xp('Neuen Ordner erstellen'),_xp('Neuer Ordner'))
        if name is not None:
            try:
                created=new_folder(self.uri,name);self.app.undo_history.remember_created(created);self.navigate(self.uri,False,select_uri=created)
            except Exception as e:self.error(e)
    def rename(self):
        rows=self.selected()
        if len(rows)>1 and not self.busy and self.uri!=COMPUTER and not self.uri.startswith('trash:'):
            self.rename_many(rows);return
        if self.busy or len(rows)!=1 or self.uri==COMPUTER or self.uri.startswith('trash:') or rows[0].get('shortcut') or rows[0].get('mountable'):return
        old=rows[0]['name'];suffix=Path(old).suffix if not rows[0]['dir'] else ''
        name=self.prompt(_xp('Umbenennen'),old,len(old)-len(suffix) if suffix else -1)
        if name is not None and name!=rows[0]['name']:
            def perform(uri,cancel):
                before=self.app.undo_history.prepare(uri,cancel);new=rename_item(uri,name);self.app.undo_history.remember(uri,new,cancel,before);self.rename_target=new
            self.operation(_xp('Umbenennen …'),[rows[0]['uri']],perform,completion=lambda ok:self.navigate(self.uri,False,select_uri=self.rename_target) if ok else None,kind='rename')
    def rename_many(self,rows):
        if any(r.get('shortcut') or r.get('mountable') for r in rows):return
        from batch_rename import RenameDialog
        d=RenameDialog(self,rows);response=d.run();plan=list(d.plan);d.destroy()
        if response!=Gtk.ResponseType.OK:return
        names={old:name for old,name,new in plan if old!=new};checked=[False]
        def perform(uri,cancel):
            if not checked[0]:
                for old,name,new in plan:
                    if old!=new and file_for(new).query_exists(cancel):raise FileExistsError(_xp('Der Name existiert bereits: ')+file_for(new).get_parse_name())
                checked[0]=True
            before=self.app.undo_history.prepare(uri,cancel);new=rename_item(uri,names[uri]);self.app.undo_history.remember(uri,new,cancel,before)
        self.operation(_xp('Umbenennen …'),list(names),perform,kind='rename')
    def undo(self):
        if self.busy:return
        item=self.app.undo_history.peek()
        if not item:self.info(_xp('Rückgängig'),_xp('Noch kein rückgängig machbarer Dateivorgang in dieser Sitzung.'));return
        self.operation(_xp('Wird rückgängig gemacht …'),[item['new']],lambda uri,c:self.app.undo_history.undo(c),kind='undo')
    def copy(self,cut=False):
        rows=self.selected()
        if not rows or self.busy or self.uri==COMPUTER or (cut and self.uri.startswith('trash:')):return
        self.app.own_clipboard([r['uri'] for r in rows],cut);self.status.set_text(f'{len(rows)} Objekte zum '+('Verschieben' if cut else _xp('Kopieren'))+' vorgemerkt')
    def clipboard_items(self):
        cb=Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD);data=cb.wait_for_contents(Gdk.Atom.intern('x-special/gnome-copied-files',False))
        if data and data.get_data():
            parts=bytes(data.get_data()).decode('utf-8','replace').splitlines()
            if parts and parts[0] in ('copy','cut'):return [u for u in parts[1:] if '://' in u],parts[0]=='cut'
        uris=cb.wait_for_uris()
        if uris:return list(uris),False
        text=cb.wait_for_text()
        if text==self.app.clip_text:return list(self.app.clip_uris),self.app.clip_cut
        return [],False
    def operation(self,title,items,fn,cut=False,copy_progress=False,completion=None,kind='copy'):
        if self.busy:return
        self.busy=True;self.cancel=Gio.Cancellable();cancel=self.cancel;self.progress.set_fraction(0);self.progress.show();self.stop.show();self.status.set_text(title)
        self.progress.set_show_text(True);self.progress.set_text('Vorbereitung …');self.last_progress=None
        done_items=[];skipped_items=[];failed_items=[];mailbox={'sample':None};started=[None]
        self.transfer_dialog=TransferDialog(self,title,cancel,kind)
        def tick():
            sample=mailbox['sample']
            if sample:
                name,current,total,index=sample;self.last_progress=sample
                elapsed=time.monotonic()-started[0] if started[0] else 0
                if copy_progress and total:
                    self.progress.set_fraction(min(1,current/total));self.progress.set_text(f'{min(100,int(100*current/total))} %')
                    rate=current/elapsed if elapsed>=.5 else 0
                    suffix=f' · {format_size(int(rate))}/s · ca. {max(0,int((total-current)/rate))} s verbleibend' if rate>0 and current<total else ''
                    self.status.set_text(f'{name} · {index}/{len(items)} · {format_size(current)} / {format_size(total)}'+suffix)
                else:
                    self.progress.set_fraction(len(done_items)/max(1,len(items)));self.progress.set_text(f'{len(done_items)}/{len(items)}')
                    self.status.set_text(f'{title} {name} · {index}/{len(items)}')
            else:self.progress.pulse()
            if self.transfer_dialog:
                fraction=self.progress.get_fraction() if sample else None
                self.transfer_dialog.update(sample[0] if sample else _xp('Dateien werden vorbereitet …'),fraction,self.status.get_text(),self.progress.get_text() or '')
            return self.busy
        timer=GLib.timeout_add(150,tick)
        def work():
            sizes=[];size_errors={}
            for item in items:
                try:sizes.append(transfer_size(item,cancel) if copy_progress else 0)
                except Exception as e:
                    cancel.set_error_if_cancelled();sizes.append(0);size_errors[item]=e
            total=sum(sizes);completed=0;started[0]=time.monotonic()
            with self.app.undo_history.batch():
                for index,item in enumerate(items,1):
                    if cancel.is_cancelled():raise RuntimeError('Vorgang abgebrochen.')
                    name=file_for(item).get_basename();mailbox['sample']=(name,completed,total,index)
                    def report(name,current):mailbox['sample']=(name,completed+current,total,index)
                    try:
                        if item in size_errors:raise size_errors[item]
                        result=fn(item,cancel,report) if copy_progress else fn(item,cancel)
                        (skipped_items if result is False else done_items).append(item)
                    except Exception as e:
                        if cancel.is_cancelled() or kind not in ('copy','move'):raise
                        failed_items.append((item,str(e)))
                    completed+=sizes[index-1];mailbox['sample']=(name,completed,total,index)
            return len(done_items)
        def done(value,error):
            GLib.source_remove(timer)
            if not self.alive:return False
            tick();self.busy=False;self.progress.hide();self.stop.hide()
            if self.transfer_dialog:self.transfer_dialog.destroy();self.transfer_dialog=None
            if cut:
                remaining=[u for u in self.app.clip_uris if u not in done_items]
                if self.app.clip_owner_is_current():self.app.own_clipboard(remaining,True)
            self.reload()
            if completion:completion(error is None and not failed_items)
            completed_sound(kind,len(done_items),error is not None or bool(skipped_items) or bool(failed_items),cancel.is_cancelled())
            if failed_items and not cancel.is_cancelled():
                d=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.WARNING,buttons=Gtk.ButtonsType.NONE,text=_xp('Einige Dateien konnten nicht übertragen werden.'))
                d.format_secondary_text('\n\n'.join(file_for(uri).get_parse_name()+': '+message for uri,message in failed_items[:5]));d.add_buttons(_xp('Schließen'),Gtk.ResponseType.CLOSE,_xp('Nur fehlgeschlagene erneut versuchen'),Gtk.ResponseType.OK);r=d.run();d.destroy()
                if r==Gtk.ResponseType.OK:self.operation(title,[u for u,e in failed_items],fn,cut,copy_progress,completion,kind)
            elif error:self.error(_xp('{0} von {1} Objekten abgeschlossen.\n\n{2}').format(len(done_items), len(items), error))
            elif skipped_items:self.info(_xp('Dateivorgang abgeschlossen'),_xp('{0} abgeschlossen, {1} übersprungen. Die vorhandenen Dateien bleiben erhalten.').format(len(done_items), len(skipped_items)))
            return False
        self.spawn(work,done)
    def paste(self):
        if self.busy or self.uri==COMPUTER or self.uri.startswith('trash:'):return
        uris,cut=self.clipboard_items()
        if uris:self.transfer(uris,self.uri,cut)
    def transfer(self,uris,destination,cut=False,completion=None):
        if self.busy:
            if completion:completion(False)
            return
        uris=list(dict.fromkeys(uris));dest=file_for(destination)
        # Parent + child selections would otherwise move/copy the same payload twice.
        uris=[u for u in uris if not any(u!=v and file_for(u).has_prefix(file_for(v)) for v in uris)]
        conflicts=ConflictPrompt(self)
        def perform(uri,cancel,progress=None):
            def write(target):
                if cut:
                    before=self.app.undo_history.prepare(uri,cancel);result=move_item(uri,target,cancel);self.app.undo_history.remember(uri,result,cancel,before)
                else:
                    result=copy_item(uri,target,cancel,progress);self.app.undo_history.remember_created(result,cancel)
            from replacements import replace
            from folder_merge import merge
            return transfer_resolved(uri,destination,cancel,write,lambda name,path,c:conflicts.choose(name,path,c,source=uri),lambda target:replace(uri,target,cancel,self.app.undo_history,cut,progress),lambda target:merge(uri,target,cancel,self.app.undo_history,conflicts.choose,cut,progress))
        self.operation(_xp('Dateien werden ')+('verschoben …' if cut else 'kopiert …'),uris,perform,cut,not cut,completion,kind='move' if cut else 'copy')
    def trash(self):
        rows=self.selected()
        if self.busy or not rows or self.uri==COMPUTER or self.uri.startswith('trash:'):return
        d=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.QUESTION,buttons=Gtk.ButtonsType.OK_CANCEL,text=_xp('{0} ausgewählte Objekte in den Papierkorb verschieben?').format(len(rows)));response=d.run();d.destroy()
        if response==Gtk.ResponseType.OK:self.operation(_xp('In den Papierkorb …'),[r['uri'] for r in rows],self.trash_recorded,kind='trash')
    def restore_trash(self):
        rows=self.selected()
        if self.busy or not rows or not self.uri.startswith('trash:'):return
        if any(not r.get('original') for r in rows):self.error(_xp('Der ursprüngliche Ort ist nicht verfügbar.'));return
        targets={r['uri']:r['original'] for r in rows}
        def perform(uri,c):
            result=move_item(uri,targets[uri],c);self.app.undo_history.discard_uri(uri);self.app.undo_history.remember_created(result,c,kind='restored')
        self.operation('Wird wiederhergestellt …',list(targets),perform,kind='restore')
    def properties(self):
        rows=self.selected()
        if len(rows)==1:self.properties_dialog=Properties(self,rows[0])
    def computer_selected(self,grid):
        children=grid.get_selected_children()
        if not children:return
        for other in self.computer_grids:
            if other is not grid:other.unselect_all()
        self.computer_selection=children[0].item;self.selected_changed()
    def computer_entries(self,place):
        A=context_actions.Action
        entries=[A(_xp('Öffnen') if place.get('uri') else _xp('Einbinden und öffnen'),lambda:self.devices.open(place),place.get('icon'))]
        if place.get('uri'):entries += [A(_xp('In neuem Fenster öffnen'),lambda:self.app.window(place['uri']),'window-new'),A(_xp('Im Explorerbaum öffnen'),lambda:context_actions.explore(self,place['uri']),'view-list-tree')]
        mount=place.get('mount');action=removal_action(mount) if mount else None
        if action:entries += [None,A(action[3],lambda:self.devices.remove(place),'media-eject')]
        if place.get('uri'):
            row=dict(place,dir=True,mime='inode/directory',size=0,volume=bool(mount) or str(place.get('icon','')).startswith('drive-'))
            entries += [None,A(_xp('Pfad kopieren'),lambda:context_actions.copy_paths(self,[row]),'edit-copy'),A(_xp('Eigenschaften'),lambda:context_actions.selection_properties(self,[row]),'document-properties')]
        return entries
    def computer_context(self,child,event):
        if event.button!=3:return False
        if self.busy:return True
        child.get_parent().select_child(child)
        return self.show_context_menu(self.computer_entries(child.item),event)
    def save_view(self):
        if self.uri and self.uri!=COMPUTER and not self.view_loading:
            self.view_config['mode']=self.mode
            if self.mode=='details':self.view_config['columns']=[max(60,min(900,c.get_width() or c.get_fixed_width())) for c in self.tree.get_columns()]
            try:views.save(self.uri,self.view_config)
            except OSError as e:print(_xp('Ordneransicht konnte nicht gespeichert werden:'),e,file=sys.stderr)
    def sort_by(self,key):
        self.view_config['descending']=not self.view_config['descending'] if self.view_config['sort']==key else False
        self.view_config['sort']=key
        for c,k in zip(self.tree.get_columns(),('name','size','mime','modified')):
            c.set_sort_indicator(k==key);c.set_sort_order(Gtk.SortType.DESCENDING if self.view_config['descending'] else Gtk.SortType.ASCENDING)
        self.save_view();self.render_files()
    def recover_replacements(self):
        if not self.busy:
            from replacements import show_recovery
            show_recovery(self)
    def open_nemo(self):subprocess.Popen(['nemo','--no-desktop',self.uri or COMPUTER])
    def system_info(self):self.info('Systemeigenschaften',platform.node()+'\n'+platform.system()+' '+platform.release()+'\n\n'+platform.machine())
    def about(self):self.info('XP Explorer','XP Explorer für Linux Mint\nVersion 1.7\n\nEigener GTK/GIO-Dateimanager im XP-Stil.\nNemo bleibt unter Extras erreichbar.\n\nKopieren, Verschieben, Umbenennen und Papierkorb.\nEndgültiges Löschen nur nach Bestätigung. Ersetzen lokaler Dateien ist mit Sicherung möglich. Sicherungen stehen unter Extras zur Verfügung.')
    def info(self,title,text):
        d=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.CLOSE,text=title);d.format_secondary_text(str(text));d.run();d.destroy()
    def error(self,error):self.info(_xp('Vorgang nicht abgeschlossen'),str(error))
    def key(self,w,e):
        name=Gdk.keyval_name(e.keyval);ctrl=bool(e.state&Gdk.ModifierType.CONTROL_MASK);alt=bool(e.state&Gdk.ModifierType.MOD1_MASK)
        focus=self.get_focus()
        if name=='F3':self.recursive_search();return True
        if self.search_active() and name=='Escape':
            s=self.search_window
            if s.stop_button.get_sensitive() and s.cancel:s.cancel.cancel()
            else:s.hide()
            return True
        if ctrl and name in ('plus','equal','KP_Add','minus','KP_Subtract') and not isinstance(focus,(Gtk.Entry,Gtk.TextView)):
            self.zoom(-16 if name in ('minus','KP_Subtract') else 16);return True
        if ctrl and name.lower()=='l':self.address.grab_focus();self.address.select_region(0,-1);return True
        if ctrl and name.lower()=='f':
            self.toggle_search() if e.state&Gdk.ModifierType.SHIFT_MASK else self.recursive_search();return True
        if name=='Escape' and focus==self.search:self.toggle_search();return True
        if isinstance(focus,(Gtk.Entry,Gtk.TextView)):return False
        if self.search_active():
            if ctrl and name.lower()=='w':self.close();return True
            if name=='F5':self.search_window.start();return True
            if alt and name=='Left':self.search_window.hide();return True
            if alt and name=='Up':self.up();return True
            if ctrl and name.lower()=='c':
                m,it=self.search_window.tree.get_selection().get_selected()
                if it is not None:self.app.own_clipboard([m[it][2]['uri']],False)
                return True
            if name in ('Delete','F2') or ctrl and name.lower() in ('v','x','z','n'):return True
            return False
        if name=='Menu' or (name=='F10' and e.state&Gdk.ModifierType.SHIFT_MASK):return self.tree_context() if focus==self.folder_pane.tree else self.keyboard_context()
        if focus==self.folder_pane.tree:
            if name=='Menu' or (name=='F10' and e.state&Gdk.ModifierType.SHIFT_MASK):return self.tree_context()
            if name in ('Delete','F2') or (ctrl and name.lower() in ('c','x','v','z','a')):return False
        if ctrl and e.state&Gdk.ModifierType.SHIFT_MASK and name.lower()=='n':self.mkdir();return True
        if ctrl:
            fn={'c':self.copy,'x':lambda:self.copy(True),'v':self.paste,'a':self.select_all,'w':self.close,'h':self.toggle_hidden,'f':self.recursive_search,'d':self.add_favorite,'z':self.undo,'n':lambda:self.app.window(self.uri),'r':self.reload}.get(name.lower())
            if fn:fn();return True
        if alt and name in ('Left','Right','Up'):
            self.travel(-1) if name=='Left' else self.travel(1) if name=='Right' else self.up();return True
        if alt and name in ('Return','KP_Enter'):self.properties();return True
        if name=='Escape':
            if self.busy and self.cancel:self.cancel.cancel()
            elif self.searchrow.get_visible():self.search.set_text('');self.searchrow.hide()
            elif self.nav_cancel:self.nav_cancel.cancel()
            return True
        fn={'F3':self.recursive_search,'F5':self.reload,'F2':self.rename,'Delete':lambda:self.delete_selected(bool(e.state&Gdk.ModifierType.SHIFT_MASK)),'BackSpace':self.up}.get(name)
        if fn:fn();return True
        return False
    def on_close(self,*args):
        if self.busy:self.info(_xp('Dateivorgang läuft'),_xp('Bitte den Vorgang abschließen lassen oder über „Abbrechen“ stoppen.'));return True
        self.save_view();self.save_geometry();return False
    def on_destroy(self,*args):
        if getattr(self,'bookmarks_monitor',None):self.bookmarks_monitor.cancel()
        if getattr(self,'bookmarks_timer',None):GLib.source_remove(self.bookmarks_timer)
        for name in ('search_window','favorites_window'):
            child=getattr(self,name,None)
            if child:child.destroy()
        if self.preview_cancel:self.preview_cancel.set()
        self.alive=False;self.devices.close();self.image_pool.shutdown(wait=False,cancel_futures=True);self.preview_pool.shutdown(wait=False,cancel_futures=True)
        self.generation+=1
        if self.nav_cancel:self.nav_cancel.cancel()
        if self.monitor:self.monitor.cancel()
        if self.reload_timer:GLib.source_remove(self.reload_timer);self.reload_timer=None

class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.mintxp.Explorer',flags=Gio.ApplicationFlags.HANDLES_OPEN|Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.add_main_option('home',0,GLib.OptionFlags.NONE,GLib.OptionArg.NONE,'Open the personal folder when no location is supplied',None)
        self.add_main_option('tree',0,GLib.OptionFlags.NONE,GLib.OptionArg.NONE,'Open the Explorer folder tree',None)
        self.undo_history=UndoHistory()
        self.clip_text=None;self.clip_uris=[];self.clip_cut=False
    def do_startup(self):
        Gtk.Application.do_startup(self);css=Gtk.CssProvider();css.load_from_path(str(BASE/'style.css'));Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    def own_clipboard(self,uris,cut):
        self.clip_uris=list(uris);self.clip_cut=cut;self.clip_text='\n'.join(uris)
        if not hasattr(self,'clip_owner'):
            self.clip_owner=Gtk.Invisible();self.clip_owner.realize()
            for idx,name in enumerate(['x-special/gnome-copied-files','text/uri-list','UTF8_STRING','text/plain;charset=utf-8']):
                Gtk.selection_add_target(self.clip_owner,Gdk.SELECTION_CLIPBOARD,Gdk.Atom.intern(name,False),idx)
            self.clip_owner.connect('selection-get',self.selection_get)
        if not Gtk.selection_owner_set(self.clip_owner,Gdk.SELECTION_CLIPBOARD,Gdk.CURRENT_TIME):
            Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(self.clip_text,-1)
    def clip_owner_is_current(self):
        return hasattr(self,'clip_owner') and Gdk.selection_owner_get(Gdk.SELECTION_CLIPBOARD)==self.clip_owner.get_window()
    def selection_get(self,widget,data,info,timestamp):
        text=(('cut' if self.clip_cut else 'copy')+'\n'+'\n'.join(self.clip_uris)) if info==0 else '\r\n'.join(self.clip_uris)+'\r\n'
        data.set(data.get_target(),8,text.encode('utf-8'))
    def window(self,uri=COMPUTER,tree=False):
        w=Explorer(self,uri or COMPUTER)
        if tree:w.toggle_tree()
        w.present();return w
    def do_command_line(self,command):
        options=command.get_options_dict();tree=options.contains('tree');home=options.contains('home')
        paths=[];literal=False
        for arg in command.get_arguments()[1:]:
            if arg=='--' and not literal:literal=True
            elif arg=='--tree' and not literal:tree=True
            elif arg=='--home' and not literal:home=True
            else:paths.append(arg)
        if paths:
            for path in paths:self.window(command.create_file_for_arg(path).get_uri(),tree)
        else:self.window(Path.home().as_uri() if home else COMPUTER,tree)
        return 0
    def do_activate(self):self.window()
    def do_open(self,files,n_files,hint):
        for f in files:self.window(f.get_uri(),hint=='tree')
if __name__=='__main__':raise SystemExit(Application().run(sys.argv))
