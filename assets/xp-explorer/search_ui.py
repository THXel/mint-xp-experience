"""Cancellable recursive filename search; never follow directory symlinks."""
from xp_locale import t as _xp
import threading,queue,fnmatch,time,datetime
from search_companion import Companion
import search_settings
import gi
gi.require_version("Gtk","3.0")
from gi.repository import Gtk,Gio,GLib
from core import file_for,format_size

def search_names(root,term,hidden,cancel,emit,limit=5000,recursive=True,kind="all",min_size=0,max_size=None,since=0,progress=None):
    pending=[file_for(root)];count=0;errors=0;visited=0;term=term.casefold()
    while pending:
        cancel.set_error_if_cancelled();directory=pending.pop();enum=None
        try:
            if progress:progress(directory.get_parse_name())
            enum=directory.enumerate_children('standard::name,standard::display-name,standard::type,standard::is-symlink,standard::is-hidden,standard::content-type,standard::size,time::modified',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,cancel)
            while True:
                cancel.set_error_if_cancelled();info=enum.next_file(cancel)
                if info is None:break
                if not hidden and (info.get_is_hidden() or info.get_name().startswith('.')):continue
                f=directory.get_child(info.get_name());isdir=info.get_file_type()==Gio.FileType.DIRECTORY;visited+=1
                mime=info.get_content_type() or 'application/octet-stream';size=info.get_size();modified=info.get_attribute_uint64('time::modified')
                category=(kind=='all' or kind=='folders' and isdir or kind in ('image','audio','video') and mime.startswith(kind+'/') or kind=='media' and mime.split('/')[0] in ('image','audio','video') or kind=='documents' and (mime.startswith('text/') or any(x in mime for x in ('pdf','officedocument','opendocument','msword','vnd.ms-','rtf'))))
                matches_filter=category and size>=min_size and (max_size is None or size<=max_size) and modified>=since
                if matches_filter and (fnmatch.fnmatchcase(info.get_display_name().casefold(),term) if any(c in term for c in '*?[') else term in info.get_display_name().casefold()):
                    emit(dict(uri=f.get_uri(),name=info.get_display_name(),dir=isdir,mountable=False,mime=mime,size=size,modified=modified,parent=directory.get_parse_name()));count+=1
                    if count>=limit:return count,errors,True,visited
                if recursive and isdir and not info.get_is_symlink():pending.append(f)
        except GLib.Error:
            cancel.set_error_if_cancelled();errors+=1
        finally:
            if enum:enum.close(None)
    return count,errors,False,visited

class SearchPanel:
    """Two embedded widgets: the left companion pane and the right result pane."""
    def __init__(self,owner):
        self.owner=owner;self.cancel=None;self.alive=True;self.active=False;self.token=0;self.bound_uri=None
        self.page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);self.page.get_style_context().add_class('xp-search-pane')
        header=Gtk.Box(spacing=6);header.get_style_context().add_class('xp-search-header');self.page.pack_start(header,False,False,0)
        header.pack_start(Gtk.Label(label=_xp('Suchassistent'),xalign=0),True,True,0)
        close=Gtk.Button(label='×');close.set_tooltip_text(_xp('Schließen'));close.connect('clicked',lambda *_:self.hide());header.pack_end(close,False,False,0)
        scrollside=Gtk.ScrolledWindow();scrollside.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);self.page.pack_start(scrollside,True,True,0)
        sidebar=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0);sidebar.set_border_width(12);sidebar.get_style_context().add_class('xp-search-blue');scrollside.add(sidebar)
        self.cards=Gtk.Stack();self.cards.set_homogeneous(False);self.cards.set_transition_type(Gtk.StackTransitionType.CROSSFADE);self.cards.set_transition_duration(140);self.cards.get_style_context().add_class('xp-search-card');sidebar.pack_start(self.cards,False,False,0)
        welcome=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);self.cards.add_named(welcome,'welcome')
        welcome.add(self.caption('Wonach soll gesucht werden?',True))
        for kind,title in [('media','Bilder, Musik oder Videos'),('documents','Dokumente'),('all','Alle Dateien und Ordner'),('folders','Nur Ordner')]:
            welcome.add(self.link(title,lambda k=kind:self.choose_category(k)))
        welcome.add(self.link('Netzwerkumgebung',lambda:self.owner.navigate('network:///'),'network-workgroup'))
        form=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5);self.cards.add_named(form,'form')
        self.criteria_heading=self.caption('Suche nach einem oder mehreren Kriterien.',True);form.add(self.criteria_heading);form.add(self.caption('Dateiname oder Teil des Namens:'))
        self.entry=Gtk.Entry();self.entry.set_placeholder_text(_xp('Name oder Muster, z. B. *.pdf'));form.add(self.history_entry(self.entry,'terms'));self.entry.connect('activate',lambda *_:self.start())
        self.category=Gtk.ComboBoxText()
        for key,title in [('all','Alle Dateien und Ordner'),('media','Bilder, Musik oder Videos'),('image','Bilder'),('audio','Musik'),('video','Videos'),('documents','Dokumente'),('folders','Nur Ordner')]:self.category.append(key,_xp(title))
        self.category.set_active_id('all');self.category.set_no_show_all(True);form.add(self.category)
        root=owner.uri if owner.uri not in ('computer:///','network:///','trash:///') else GLib.get_home_dir();self.root=file_for(root).get_uri()
        form.add(self.caption('Suchen in:'));self.location=Gtk.Entry(text=file_for(root).get_parse_name());form.add(self.history_entry(self.location,'locations'));form.add(self.link('Ordner auswählen …',self.choose_folder,'folder'))
        self.date=Gtk.ComboBoxText()
        for key,title in [('0','Beliebiger Zeitpunkt'),('1','Heute'),('7','Letzte 7 Tage'),('30','Letzte 30 Tage')]:self.date.append(key,_xp(title))
        self.date.set_active_id('0');self.section(form,'Wann wurde die Datei geändert?',self.date)
        self.size=Gtk.ComboBoxText()
        for key,title in [('all','Beliebige Größe'),('small','Klein (bis 1 MB)'),('medium','Mittel (1–100 MB)'),('large','Groß (ab 100 MB)')]:self.size.append(key,_xp(title))
        self.size.set_active_id('all');self.section(form,'Wie groß ist die Datei?',self.size)
        options=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=7);self.section(form,'Weitere Suchoptionen',options)
        self.hidden=Gtk.CheckButton(label=_xp('Versteckte Dateien einschließen'));self.hidden.get_child().set_line_wrap(True);self.hidden.get_child().set_max_width_chars(26);options.add(self.hidden)
        self.recursive=Gtk.CheckButton(label=_xp('Unterordner durchsuchen'));self.recursive.set_active(True);options.add(self.recursive)
        reset=Gtk.Button(label=_xp('Filter zurücksetzen'));reset.connect('clicked',lambda *_:self.reset_filters());options.add(reset)
        form.add(self.link('Andere Suchoptionen',lambda:self.cards.set_visible_child_name('welcome')))
        line=Gtk.Box(spacing=8);form.add(line);self.start_button=Gtk.Button(label=_xp('Suchen'));self.start_button.connect('clicked',lambda *_:self.start());line.pack_end(self.start_button,False,False,0)
        self.stop_button=Gtk.Button(label=_xp('Abbrechen'));self.stop_button.connect('clicked',lambda *_:self.cancel.cancel() if self.cancel else None);line.pack_start(self.stop_button,False,False,0)
        tail=Gtk.DrawingArea();tail.set_size_request(-1,18)
        def draw_tail(w,c):
            c.move_to(22,0);c.line_to(42,17);c.line_to(39,0);c.set_source_rgb(.84,.875,.969);c.fill_preserve();c.set_source_rgb(1,1,1);c.set_line_width(1);c.stroke();return False
        tail.connect('draw',draw_tail);sidebar.pack_start(tail,False,False,0)
        self.companion=Companion();sidebar.pack_start(self.companion,False,False,0)
        preferences=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);self.section(sidebar,'Einstellungen ändern',preferences)
        self.mascot=Gtk.ComboBoxText()
        for key,title in [('auto','Automatisch'),('penguin','Pinguin'),('none','Ohne Begleiter')]+([('dog','Hund (aus eigener ISO)')] if self.companion.animations else []):self.mascot.append(key,_xp(title))
        self.mascot.set_active_id(self.companion.choice);self.mascot.connect('changed',lambda w:self.companion.select(w.get_active_id()));preferences.add(self.mascot)
        self.animated=Gtk.CheckButton(label=_xp('Suchbegleiter animieren'));self.animated.set_active(self.companion.animate);self.animated.connect('toggled',lambda w:self.companion.enable(w.get_active()));preferences.add(self.animated)
        clear=Gtk.Button(label=_xp('Suchverlauf löschen'));clear.connect('clicked',lambda *_:search_settings.clear());preferences.add(clear)
        def sync_preferences():self.mascot.set_active_id(self.companion.choice);self.animated.set_active(self.companion.animate)
        self.companion.on_preferences=sync_preferences
        self.results=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0);self.results.get_style_context().add_class('xp-search-results')
        from gi.repository import GdkPixbuf
        self.store=Gtk.ListStore(str,str,object,str,str,GdkPixbuf.Pixbuf,str);self.tree=Gtk.TreeView(model=self.store)
        namecol=Gtk.TreeViewColumn(_xp('Name'));pic=Gtk.CellRendererPixbuf();namecol.pack_start(pic,False);namecol.add_attribute(pic,'pixbuf',5);text=Gtk.CellRendererText();namecol.pack_start(text,True);namecol.add_attribute(text,'text',0);namecol.set_resizable(True);namecol.set_sort_column_id(0);self.tree.append_column(namecol)
        for i,title in [(1,'In Ordner'),(3,'Größe'),(6,'Typ'),(4,'Geändert am')]:
            cell=Gtk.CellRendererText();cell.set_property('ellipsize',3);col=Gtk.TreeViewColumn(_xp(title),cell,text=i);col.set_resizable(True);col.set_expand(i==1);col.set_sizing(Gtk.TreeViewColumnSizing.FIXED);col.set_fixed_width(180 if i==1 else 110);col.set_sort_column_id(i);self.tree.append_column(col)
        for col,key in ((3,'size'),(4,'modified')):self.store.set_sort_func(col,lambda m,a,b,k=key:(m[a][2][k]>m[b][2][k])-(m[a][2][k]<m[b][2][k]))
        self.tree.connect('row-activated',lambda *_:self.open(False));self.tree.connect('button-press-event',self.context)
        self.result_stack=Gtk.Stack();self.result_stack.set_homogeneous(False);scroll=Gtk.ScrolledWindow();scroll.add(self.tree);self.result_stack.add_named(scroll,'results')
        emptybox=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);emptybox.set_border_width(20);self.empty=Gtk.Label(label=_xp('Wähle links deine Suchoptionen und klicke auf „Suchen“.'),xalign=0,yalign=0);self.empty.set_line_wrap(True);emptybox.pack_start(self.empty,False,False,0);overlay=Gtk.Overlay();overlay.add(emptybox);watermark=Gtk.DrawingArea();watermark.set_size_request(180,180);watermark.set_halign(Gtk.Align.END);watermark.set_valign(Gtk.Align.END);watermark.set_margin_end(24);watermark.set_margin_bottom(24)
        def magnifier(w,c):
            c.set_source_rgba(.52,.60,.72,.10);c.set_line_width(9);c.arc(105,66,45,0,6.2831853);c.stroke();c.set_line_width(17);c.set_line_cap(1);c.move_to(70,102);c.line_to(27,150);c.stroke();return False
        watermark.connect('draw',magnifier);overlay.add_overlay(watermark);overlay.set_overlay_pass_through(watermark,True);self.result_stack.add_named(overlay,'empty');self.results.pack_start(self.result_stack,True,True,0)
        actions=Gtk.Box(spacing=8);self.actions=actions;actions.set_no_show_all(True);actions.set_border_width(8);self.results.pack_end(actions,False,False,0)
        for title,parent in [('Öffnen',False),('Enthaltenden Ordner öffnen',True)]:
            button=Gtk.Button(label=_xp(title));button.connect('clicked',lambda w,p=parent:self.open(p));button.show();button.set_sensitive(False);actions.add(button)
        self.tree.get_selection().connect('changed',lambda selection:[b.set_sensitive(selection.get_selected()[1] is not None) for b in actions.get_children()])
        self.status=owner.status;owner.side_stack.add_named(self.page,'search');owner.content.add_named(self.results,'search');owner.search_window=self
        self.page.show_all();self.results.show_all();self.cards.set_visible_child_name('welcome');self.result_stack.set_visible_child_name('empty');self.stop_button.set_sensitive(False);self.present()
    def caption(self,title,bold=False):
        label=Gtk.Label(label=_xp(title),xalign=0);label.set_line_wrap(True);label.set_max_width_chars(27)
        if bold:label.get_style_context().add_class('xp-search-heading')
        return label
    def link(self,title,action,icon='go-next'):
        b=Gtk.Button();b.set_relief(Gtk.ReliefStyle.NONE);b.get_style_context().add_class('xp-search-link');row=Gtk.Box(spacing=6);row.pack_start(Gtk.Image.new_from_pixbuf(self.owner.pix(icon,16)),False,False,0);row.pack_start(self.caption(title),True,True,0);b.add(row);b.connect('clicked',lambda *_:action());return b
    def section(self,box,title,child):
        expander=Gtk.Expander();expander.set_label_widget(self.caption(title,True));expander.get_style_context().add_class('xp-search-section');expander.add(child);box.pack_start(expander,False,False,0);return expander
    def choose_category(self,kind):self.criteria_heading.set_text(_xp({'media':'Bilder, Musik oder Videos','documents':'Dokumente','folders':'Nur Ordner'}.get(kind,'Alle Dateien und Ordner')));self.category.set_visible(kind=='media');self.category.set_active_id(kind);self.cards.set_visible_child_name('form');self.entry.grab_focus()
    def present(self):
        if self.active:
            if self.cards.get_visible_child_name()=='welcome':self.choose_category('all')
            else:self.entry.grab_focus()
            return
        w=self.owner;w.capture_position();self.saved_width=w.split.get_position();self.saved_preview=w.preview_box.get_visible();self.saved_back=w.back_btn.get_sensitive()
        if self.bound_uri!=w.uri:
            self.bound_uri=w.uri;self.saved_status=None;self.root=file_for(w.uri if w.uri not in ('computer:///','trash:///','network:///') else GLib.get_home_dir()).get_uri();self.location.set_text(file_for(self.root).get_parse_name());self.store.clear();self.actions.hide();self.result_stack.set_visible_child_name('empty');self.empty.set_text(_xp('Wähle links deine Suchoptionen und klicke auf „Suchen“.'))
        w.generation+=1;w.render_generation+=1
        if w.nav_cancel:w.nav_cancel.cancel()
        if w.monitor:w.monitor.cancel();w.monitor=None
        if w.reload_timer:GLib.source_remove(w.reload_timer);w.reload_timer=None
        w.directory_loading=False;self.active=True;w.preview_box.hide();w.searchrow.hide();w.side_stack.set_visible_child_full('search',Gtk.StackTransitionType.SLIDE_LEFT);w.split.set_position(285);w.content.set_visible_child_name('search');w.search_btn.get_style_context().add_class('xp-search-active');w.address.set_text(_xp('Suchergebnisse'));w.set_title(_xp('Suchergebnisse')+' – XP Explorer');w.back_btn.set_sensitive(True)
        self.status.set_text(getattr(self,'saved_status',None) or _xp('Bereit · Namenssuche, keine Dateiinhalte'));self.menu_states=[(item,item.get_sensitive()) for item in w.folder_actions+w.search_inactive_tools]
        for item,_ in self.menu_states:item.set_sensitive(False)
    def hide(self,reload=True):
        if not self.active:return
        self.saved_status=(_xp('Suche abgebrochen.')+_xp(' · {0} Treffer').format(len(self.store))) if self.stop_button.get_sensitive() else self.status.get_text()
        self.active=False;self.token+=1
        if self.cancel:self.cancel.cancel()
        self.stop_button.set_sensitive(False);self.companion.set_state('idle');w=self.owner
        for item,state in self.menu_states:item.set_sensitive(state)
        w.side_stack.set_visible_child_full('folders' if w.tree_mode else 'tasks',Gtk.StackTransitionType.SLIDE_RIGHT);w.split.set_position(self.saved_width);w.preview_box.set_visible(self.saved_preview);w.search_btn.get_style_context().remove_class('xp-search-active');w.back_btn.set_sensitive(self.saved_back)
        w.content.set_visible_child_name('computer' if w.uri=='computer:///' else w.mode)
        if reload and w.alive:w.navigate(w.uri,False)
    def destroy(self):
        self.hide(False);self.alive=False;self.token+=1
        if self.cancel:self.cancel.cancel()
        self.page.destroy();self.results.destroy()
    def history_entry(self,entry,key):
        line=Gtk.Box(spacing=3);line.pack_start(entry,True,True,0);button=Gtk.MenuButton(label='▾');button.set_tooltip_text(_xp('Letzte Suchbegriffe') if key=='terms' else _xp('Letzte Suchorte'));line.pack_end(button,False,False,0);menu=Gtk.Menu();button.set_popup(menu)
        def populate(*args):
            for child in menu.get_children():child.destroy()
            for value in search_settings.load()[key]:
                item=Gtk.MenuItem(label=value);item.connect('activate',lambda w,v=value:entry.set_text(v));menu.add(item)
            menu.add(Gtk.SeparatorMenuItem());clear=Gtk.MenuItem(label=_xp('Suchverlauf löschen'));clear.connect('activate',lambda w:search_settings.clear());menu.add(clear);menu.show_all()
        menu.connect('show',populate);return line
    def reset_filters(self):
        self.category.set_active_id('all');self.date.set_active_id('0');self.size.set_active_id('all');self.hidden.set_active(False);self.recursive.set_active(True)
    def choose_folder(self,*args):
        d=Gtk.FileChooserDialog(title=_xp('Suchen in:'),transient_for=self.owner,action=Gtk.FileChooserAction.SELECT_FOLDER)
        d.add_buttons(_xp('Abbrechen'),Gtk.ResponseType.CANCEL,_xp('Auswählen'),Gtk.ResponseType.OK);d.set_uri(self.root)
        if d.run()==Gtk.ResponseType.OK:self.location.set_text(file_for(d.get_uri()).get_parse_name())
        d.destroy()
    def context(self,tree,event):
        if event.button!=3:return False
        hit=tree.get_path_at_pos(int(event.x),int(event.y))
        if not hit:return False
        tree.get_selection().select_path(hit[0]);menu=Gtk.Menu()
        for label,parent in [('Öffnen',False),('Enthaltenden Ordner öffnen',True)]:
            item=Gtk.MenuItem(label=_xp(label));item.connect('activate',lambda w,p=parent:self.open(p));menu.add(item)
        menu.show_all();menu.popup_at_pointer(event);self.context_menu=menu;return True
    def key(self,w,e):
        from gi.repository import Gdk
        if Gdk.keyval_name(e.keyval)=='Escape':
            if self.stop_button.get_sensitive() and self.cancel:self.cancel.cancel()
            else:self.hide()
            return True
        return False
    def open(self,parent):
        model,it=self.tree.get_selection().get_selected()
        if it is None:return
        row=dict(model[it][2])
        if parent:
            folder=file_for(row['uri']).get_parent()
            if folder:self.owner.navigate(folder.get_uri(),select_uri=row['uri'])
        elif row['dir']:self.owner.navigate(row['uri'])
        else:self.owner.open_row(row)
    def start(self):
        if not self.active:self.present()
        self.cards.set_visible_child_name('form')
        term=self.entry.get_text().strip()
        if not term:term='*'
        location=self.location.get_text().strip()
        if not location:self.status.set_text(_xp('Bitte einen Suchordner auswählen.'));return
        self.root=file_for(location).get_uri();self.actions.show()
        try:search_settings.remember(term,location)
        except OSError:pass
        if self.cancel:self.cancel.cancel()
        self.token+=1;token=self.token;cancel=Gio.Cancellable();self.cancel=cancel;messages=queue.Queue(maxsize=512);self.store.clear();self.result_stack.set_visible_child_name('results');self.companion.set_state('searching');self.status.set_text(_xp('Suche läuft …'));self.stop_button.set_sensitive(True)
        hidden=self.hidden.get_active();recursive=self.recursive.get_active();root=self.root;kind=self.category.get_active_id()
        bounds={'all':(0,None),'small':(0,1024**2),'medium':(1024**2,100*1024**2),'large':(100*1024**2,None)};min_size,max_size=bounds[self.size.get_active_id()];days=int(self.date.get_active_id());since=time.time()-days*86400 if days else 0
        if days==1:since=datetime.datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
        def emit(row):
            while True:
                cancel.set_error_if_cancelled()
                try:messages.put(('row',row),timeout=.1);return
                except queue.Full:pass
        progress_state={'path':'','time':0}
        def progress(path):progress_state['path']=path
        def worker():
            try:result=search_names(root,term,hidden,cancel,emit,recursive=recursive,kind=kind,min_size=min_size,max_size=max_size,since=since,progress=progress);ending=('done',result)
            except Exception as e:ending=('error',_xp('Suche abgebrochen.') if cancel.is_cancelled() else str(e))
            while self.alive and token==self.token:
                try:messages.put(ending,timeout=.1);break
                except queue.Full:pass
        def poll():
            if not self.alive or token!=self.token:return False
            if progress_state['path'] and time.monotonic()-progress_state['time']>.2:
                self.status.set_text(_xp('Suche in: {0} · {1} Treffer').format(progress_state['path'],len(self.store)));progress_state['time']=time.monotonic()
            for _ in range(150):
                try:kind,value=messages.get_nowait()
                except queue.Empty:return True
                if kind=='row':self.store.append([value['name'],value['parent'],value,'' if value['dir'] else format_size(value['size']),datetime.datetime.fromtimestamp(value['modified']).strftime('%d.%m.%Y %H:%M') if value['modified'] else '',self.owner.pix('folder' if value['dir'] else Gio.content_type_get_icon(value['mime']),16),_xp('Dateiordner') if value['dir'] else (Gio.content_type_get_description(value['mime']) or value['mime'])])
                else:
                    self.stop_button.set_sensitive(False);self.companion.set_state('found' if len(self.store) else 'empty')
                    if not len(self.store):self.actions.hide();self.empty.set_text(_xp('Keine Treffer. Versuche einen anderen Namen oder weniger Filter.'));self.result_stack.set_visible_child_name('empty')
                    if kind=='error':
                        self.status.set_text(value+_xp(' · {0} Treffer').format(len(self.store)))
                        if not len(self.store):self.actions.hide();self.empty.set_text(value)
                    else:
                        n,errors,limited,visited=value;self.status.set_text(_xp('{0} Treffer · {1} Ordner nicht lesbar').format(n, errors)+(_xp(' · Grenze von 5000 Treffern erreicht') if limited else ''))
                    return False
            return True
        GLib.timeout_add(80,poll);threading.Thread(target=worker,daemon=True).start()
    def closed(self,*args):
        self.alive=False
        if self.cancel:self.cancel.cancel()

# Compatibility for callers; this is an embedded controller, never a Gtk.Window.
SearchWindow=SearchPanel
