"""Small bookmark editor; removing a bookmark never deletes its target."""
from gi.repository import Gtk,Gdk,Gio
from core import file_for
from xp_locale import t as _xp
class FavoritesWindow(Gtk.Window):
    def __init__(self,owner,store):
        super().__init__(title=_xp('Favoriten verwalten'),transient_for=owner)
        self.alive=True;self.connect('destroy',lambda *_:setattr(self,'alive',False));self.owner=owner;self.store=store;self.set_default_size(640,370)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);box.set_border_width(12);self.add(box)
        self.model=Gtk.ListStore(str,str);self.tree=Gtk.TreeView(model=self.model)
        for i,title in enumerate([_xp('Name'),_xp('Ort')]):
            column=Gtk.TreeViewColumn(title,Gtk.CellRendererText(),text=i);column.set_expand(True);column.set_resizable(True);self.tree.append_column(column)
        scroll=Gtk.ScrolledWindow();scroll.add(self.tree);box.pack_start(scroll,True,True,0)
        line=Gtk.Box(spacing=6);box.add(line)
        for title,action in [(_xp('Umbenennen'),'rename'),(_xp('Entfernen'),'remove'),('↑','up'),('↓','down')]:
            b=Gtk.Button(label=title);b.connect('clicked',lambda _,a=action:self.change(a));line.add(b)
        self.status=Gtk.Label(label=_xp('Nur Verknüpfungen – Dateien bleiben erhalten.'),xalign=0);box.add(self.status)
        self.status.set_text(_xp('Ordner hierher ziehen. Favoriten ziehen, um sie zu sortieren.'))
        self.tree.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,[Gtk.TargetEntry.new('application/x-xp-bookmark',Gtk.TargetFlags.SAME_WIDGET,1)],Gdk.DragAction.MOVE)
        self.tree.enable_model_drag_dest([Gtk.TargetEntry.new('application/x-xp-bookmark',Gtk.TargetFlags.SAME_WIDGET,1),Gtk.TargetEntry.new('text/uri-list',0,2)],Gdk.DragAction.COPY|Gdk.DragAction.MOVE)
        self.tree.connect('drag-data-get',self.drag_get);self.tree.connect('drag-data-received',self.drag_receive)
        self.tree.connect('row-activated',lambda *_:self.open());self.refresh();self.show_all()
    def refresh(self,uri=None):
        self.model.clear()
        for name,target in self.store.entries():
            it=self.model.append([name,target])
            if target==uri:self.tree.get_selection().select_iter(it)
    def open(self):
        m,it=self.tree.get_selection().get_selected()
        if it is not None:self.owner.navigate(m[it][1])
    def change(self,action):
        m,it=self.tree.get_selection().get_selected()
        if it is None:return
        name,uri=m[it];label=None
        if action=='rename':
            label=self.owner.prompt(_xp('Favorit umbenennen'),name)
            if label is None:return
        try:
            self.store.change(uri,'move' if action in ('up','down') else action,label, -1 if action=='up' else 1)
            self.refresh(uri);self.owner.refresh_bookmarks()
        except Exception as e:self.status.set_text(str(e))

    def drag_get(self,tree,context,data,info,stamp):
        m,it=tree.get_selection().get_selected()
        if it is not None:data.set(data.get_target(),8,m[it][1].encode())
    def drag_receive(self,tree,context,x,y,data,info,stamp):
        try:
            hit=tree.get_dest_row_at_pos(x,y);before=None
            if hit:
                path,position=hit;index=path.get_indices()[0]
                if position in (Gtk.TreeViewDropPosition.AFTER,Gtk.TreeViewDropPosition.INTO_OR_AFTER):index+=1
                if index<len(self.model):before=self.model[index][1]
            if info==1:
                uri=bytes(data.get_data()).decode();self.store.change(uri,'before',before);self.refresh(uri);self.owner.refresh_bookmarks();Gtk.drag_finish(context,True,False,stamp)
            else:
                uris=list(data.get_uris() or [])[:100]
                def validate():
                    accepted=[]
                    for uri in uris:
                        f=file_for(uri)
                        if f.get_uri_scheme() not in ('file','smb','sftp','ftp','dav','davs'):raise ValueError(_xp('Dieser Ort ist kein unterstützter Ordner.'))
                        # Remote locations are checked on opening, not while editing favorites.
                        if f.is_native() and f.query_file_type(Gio.FileQueryInfoFlags.NONE,None)!=Gio.FileType.DIRECTORY:raise ValueError(_xp('Bitte nur Ordner zu den Favoriten hinzufügen.'))
                        accepted.append(f.get_uri())
                    return accepted
                def ready(accepted,error):
                    if not self.alive:Gtk.drag_finish(context,False,False,stamp);return
                    try:
                        if error:raise error
                        for uri in accepted:
                            added=self.store.change(uri,'add')
                            if added and before:self.store.change(uri,'before',before)
                        self.refresh();self.owner.refresh_bookmarks();Gtk.drag_finish(context,True,False,stamp)
                    except Exception as e:self.status.set_text(str(e));Gtk.drag_finish(context,False,False,stamp)
                self.owner.spawn(validate,ready)
        except Exception as e:self.status.set_text(str(e));Gtk.drag_finish(context,False,False,stamp)
