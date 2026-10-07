"""Persistent, lazy folder tree. Listing is asynchronous and never follows links recursively."""
from xp_locale import t as _xp
from pathlib import Path
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gio,GLib,GdkPixbuf,Pango
from core import file_for,listing

class FolderTree(Gtk.ScrolledWindow):
    def __init__(self,owner,computer_items):
        super().__init__();self.owner=owner;self.alive=True;self.syncing=False;self.target=None;self.pending={};self.nodes={};self.monitors={};self.timers={};self.dirty=set();self.anchor=None
        self.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
        self.set_min_content_width(180);self.set_propagate_natural_width(False)
        self.model=Gtk.TreeStore(GdkPixbuf.Pixbuf,str,str,int)
        self.tree=Gtk.TreeView(model=self.model);self.tree.set_headers_visible(False);self.tree.set_enable_tree_lines(True);self.tree.set_level_indentation(3)
        self.tree.get_style_context().add_class('xp-folder-tree')
        c=Gtk.TreeViewColumn();p=Gtk.CellRendererPixbuf();c.pack_start(p,False);c.add_attribute(p,'pixbuf',0)
        t=Gtk.CellRendererText();t.set_property('ypad',4);c.pack_start(t,True);c.add_attribute(t,'text',1);self.tree.append_column(c)
        self.tree.set_tooltip_column(1);self.add(self.tree)
        self.add_node(None,'Desktop',Path(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP) or Path.home()).as_uri(),'user-desktop')
        self.home_node=self.add_node(None,_xp('Eigene Dateien'),Path.home().as_uri(),'user-home')
        computer=self.add_node(None,_xp('Arbeitsplatz'),'computer:///','computer',loaded=True)
        self.add_node(computer,_xp('Dateisystem'),'file:///','drive-harddisk')
        self.add_node(None,_xp('Papierkorb'),'trash:///','user-trash')
        self.tree.connect('button-press-event',lambda w,e:self.owner.tree_context(e) if e.button==3 else False)
        self.add_node(None,_xp('Netzwerkumgebung'),'network:///','network-workgroup')
        shortcuts=self.add_node(None,_xp('Favoriten'),'',loaded=True);self.shortcuts=shortcuts
        for name,uri in owner.bookmark_places():
            self.add_node(shortcuts,name,uri,'folder' if uri.startswith('file:') else 'folder-remote')
        self.tree.expand_row(self.model.get_path(shortcuts),False)
        self.tree.connect('row-expanded',lambda w,it,p:self.load(it))
        self.tree.get_selection().connect('changed',self.selected)
        self.connect('destroy',self.destroyed)
        def drives(groups,error):
            if not self.alive:return False
            if not error:
                for group in (_xp('Festplatten'),_xp('Geräte mit Wechselmedien')):
                    for r in groups[group]:
                        if r['uri'] not in self.nodes:self.add_node(computer,r['name'],r['uri'],r['icon'])
            self.tree.expand_row(self.model.get_path(computer),False);self.sync(self.target);return False
        owner.spawn(computer_items,drives)
    def add_node(self,parent,name,uri,icon='folder',loaded=False):
        it=self.model.append(parent,[self.owner.pix(icon,16),name,uri,2 if loaded else 0])
        self.nodes.setdefault(uri,[]).append(it)
        if not loaded:self.model.append(it,[None,'Wird geladen …','',2])
        return it
    def valid(self,it):return self.model.iter_is_valid(it)
    def forget(self,it):
        uri=self.model[it][2]
        child=self.model.iter_children(it)
        while child:
            self.forget(child);child=self.model.iter_next(child)
        if uri in self.nodes:
            self.nodes[uri]=[n for n in self.nodes[uri] if self.valid(n) and self.model.get_path(n)!=self.model.get_path(it)]
            if not self.nodes[uri]:
                self.nodes.pop(uri,None)
                if uri in self.monitors:self.monitors.pop(uri).cancel()
                if uri in self.timers:GLib.source_remove(self.timers.pop(uri))
    def watch(self,uri):
        if uri in self.monitors or not uri:return
        try:
            monitor=file_for(uri).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES,None)
            monitor.connect('changed',lambda m,f,other,event:self.change(uri,f,other,event));self.monitors[uri]=monitor
        except GLib.Error:pass
    def change(self,uri,f,other,event):
        if not self.alive:return
        if other and event==Gio.FileMonitorEvent.RENAMED:self.remap(f.get_uri(),other.get_uri())
        if uri in self.timers:GLib.source_remove(self.timers[uri])
        def refresh():
            self.timers.pop(uri,None)
            if not self.alive:return False
            for it in list(self.nodes.get(uri,[])):
                if self.valid(it):self.load(it,True)
            return False
        self.timers[uri]=GLib.timeout_add(350,refresh)
    def remap(self,old,new):
        oldfile=file_for(old);self.syncing=True
        try:
            for uri in list(self.nodes):
                f=file_for(uri)
                if uri!=old and not f.has_prefix(oldfile):continue
                newuri=new if uri==old else file_for(new).resolve_relative_path(oldfile.get_relative_path(f)).get_uri()
                its=self.nodes.pop(uri)
                for it in its:
                    if self.valid(it):self.model[it][2]=newuri
                    if self.valid(it) and uri==old:self.model[it][1]=file_for(new).get_basename()
                self.nodes.setdefault(newuri,[]).extend(its)
                if uri in self.monitors:self.monitors.pop(uri).cancel();self.watch(newuri)
        finally:self.syncing=False
    def load(self,it,force=False):
        if not self.alive or not self.valid(it):return
        uri=self.model[it][2]
        if not uri or uri=='computer:///':return
        if self.model[it][3]==1:
            if force:self.dirty.add(uri)
            return
        if self.model[it][3]==2 and not force:return
        self.model[it][3]=1;cancel=Gio.Cancellable();self.pending[id(cancel)]=cancel;self.watch(uri)
        def done(rows,error):
            self.pending.pop(id(cancel),None)
            if not self.alive or not self.valid(it):return False
            if self.model[it][2]!=uri:self.model[it][3]=0;self.load(it);return False
            self.syncing=True
            try:
                existing={};child=self.model.iter_children(it)
                while child:
                    existing[self.model[child][2]]=child;child=self.model.iter_next(child)
                wanted={(r.get('target') if r.get('target') and (r.get('shortcut') or r.get('mountable')) else r['uri']):r for r in (rows or []) if r['dir'] or r.get('shortcut') or r.get('mountable')}
                if not error:
                    was_expanded=self.tree.row_expanded(self.model.get_path(it))
                    # Add real rows before removing the placeholder: an empty model collapses GTK rows.
                    for key,r in wanted.items():
                        if key not in existing:self.add_node(it,r['name'],key,r.get('icon') or 'folder')
                    for key,child in existing.items():
                        if key not in wanted:self.forget(child);self.model.remove(child)
                    self.model[it][3]=2
                    if was_expanded and wanted:self.tree.expand_row(self.model.get_path(it),False)
                else:
                    self.model[it][3]=0
                    if not existing:self.model.append(it,[None,_xp('Nicht verfügbar – erneut aufklappen'),'',2])
            finally:self.syncing=False
            if not error:self.sync(self.target)
            if uri in self.dirty:self.dirty.discard(uri);self.load(it,True)
            return False
        self.owner.spawn(lambda:listing(uri,False,cancel),done)
    def sync(self,uri):
        self.target=uri
        if not self.alive or not uri:return
        target=file_for(uri);candidates=[]
        for node_uri,its in self.nodes.items():
            f=file_for(node_uri)
            if node_uri and (target.equal(f) or target.has_prefix(f)):
                candidates.extend((len(node_uri),it) for it in its)
        if not candidates:return
        # Duplicate URIs (home tree / bookmarks / filesystem) must not redirect
        # selection to a different branch. Keep the clicked branch while it fits.
        def belongs(it,root):
            return root is not None and self.valid(root) and self.root_path(it)==self.model.get_path(root).to_string()
        preferred=[pair for pair in candidates if belongs(pair[1],self.anchor)]
        if not preferred and (target.equal(file_for(Path.home().as_uri())) or target.has_prefix(file_for(Path.home().as_uri()))):
            preferred=[pair for pair in candidates if belongs(pair[1],self.home_node)]
        if not preferred:preferred=[pair for pair in candidates if not belongs(pair[1],self.shortcuts)]
        it=max(preferred or candidates,key=lambda pair:pair[0])[1];p=self.model.get_path(it)
        self.syncing=True
        try:
            self.tree.expand_to_path(p)
            if self.model[it][2]==uri:
                selection=self.tree.get_selection()
                if not selection.path_is_selected(p):
                    selection.select_path(p);self.tree.scroll_to_cell(p,None,False,0,0)
            elif self.model[it][3]!=2:
                self.tree.expand_row(p,False);self.load(it)
        finally:self.syncing=False
    def root_path(self,it):
        parent=self.model.iter_parent(it)
        while parent is not None:it=parent;parent=self.model.iter_parent(it)
        return self.model.get_path(it).to_string()
    def reload_bookmarks(self):
        self.syncing=True
        try:
            child=self.model.iter_children(self.shortcuts)
            while child:
                self.forget(child);self.model.remove(child);child=self.model.iter_children(self.shortcuts)
            for name,uri in self.owner.bookmark_places():
                self.add_node(self.shortcuts,name,uri,'folder' if uri.startswith('file:') else 'folder-remote')
        finally:self.syncing=False
        self.sync(self.target)
    def selected(self,selection):
        if self.syncing:return
        if self.owner.busy:self.sync(self.owner.uri);return
        model,it=selection.get_selected()
        if it is not None and model[it][2]:
            self.anchor=self.model.get_iter_from_string(self.root_path(it))
            if model[it][2]!=self.owner.uri:
                self.owner._tree_navigation=True
                try:self.owner.navigate(model[it][2])
                finally:self.owner._tree_navigation=False
    def destroyed(self,*args):
        self.alive=False
        for c in self.pending.values():c.cancel()
        self.pending.clear()
        for m in self.monitors.values():m.cancel()
        for timer in self.timers.values():GLib.source_remove(timer)
        self.monitors.clear();self.timers.clear()
