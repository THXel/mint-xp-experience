"""Native URI drag-and-drop. Destination owns moves; source deletion is never requested."""
from xp_locale import t as _xp
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk
from core import file_for
class DragDrop:
    def __init__(self,owner):
        self.owner=owner;self.source_uris=[];self.targets=[Gtk.TargetEntry.new('text/uri-list',0,0)]
        for w in (owner.iconview,owner.tree,owner.folder_pane.tree):
            w.drag_dest_set(Gtk.DestDefaults(0),self.targets,Gdk.DragAction.COPY|Gdk.DragAction.MOVE)
            w.connect('drag-motion',self.motion);w.connect('drag-leave',self.leave);w.connect('drag-drop',self.drop);w.connect('drag-data-received',self.received)
        for w in (owner.iconview,owner.tree):
            w.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,self.targets,Gdk.DragAction.COPY|Gdk.DragAction.MOVE)
            w.connect('drag-begin',self.begin);w.connect('drag-end',self.end);w.connect('drag-data-get',self.provide);w.drag_source_set_icon_name('text-x-generic')
    def destination(self,w,x,y):
        o=self.owner
        if w==o.iconview:
            p=w.get_path_at_pos(x,y)
            if p and o.store[p][5]['dir']:return o.store[p][5]['uri'],p
        else:
            hit=w.get_path_at_pos(x,y);p=hit[0] if hit else None
            if w==o.folder_pane.tree:return (w.get_model()[p][2],p) if p and w.get_model()[p][2] not in ('','computer:///') else (None,None)
            if p and o.store[p][5]['dir']:return o.store[p][5]['uri'],p
        return (o.uri,None) if o.uri and o.uri!='computer:///' and not o.uri.startswith('trash:') else (None,None)
    def action(self,w,ctx):
        device=ctx.get_device();state=w.get_window().get_device_position(device)[3] if device else Gdk.ModifierType(0)
        desired=Gdk.DragAction.MOVE if state&Gdk.ModifierType.SHIFT_MASK else Gdk.DragAction.COPY
        return desired if ctx.get_actions()&desired else Gdk.DragAction(0)
    def motion(self,w,ctx,x,y,timestamp):
        uri,p=self.destination(w,x,y);action=self.action(w,ctx) if uri and not self.owner.busy else Gdk.DragAction(0)
        Gdk.drag_status(ctx,action,timestamp)
        if w==self.owner.iconview:w.set_drag_dest_item(p,Gtk.IconViewDropPosition.DROP_INTO)
        else:w.set_drag_dest_row(p,Gtk.TreeViewDropPosition.INTO_OR_AFTER)
        if action:self.owner.status.set_text(('Verschieben nach: ' if action==Gdk.DragAction.MOVE else _xp('Kopieren nach: '))+file_for(uri).get_parse_name()+' · Umschalt = Verschieben')
        return True
    def leave(self,w,ctx,timestamp):
        if w==self.owner.iconview:w.set_drag_dest_item(None,Gtk.IconViewDropPosition.NO_DROP)
        else:w.set_drag_dest_row(None,Gtk.TreeViewDropPosition.BEFORE)
    def drop(self,w,ctx,x,y,timestamp):
        uri,p=self.destination(w,x,y)
        if not uri or self.owner.busy:return False
        target=w.drag_dest_find_target(ctx,None)
        if target==Gdk.Atom.intern('NONE',False):return False
        w.drag_get_data(ctx,target,timestamp);return True
    def begin(self,w,ctx):
        self.source_uris=[r['uri'] for r in self.owner.selected()];self.owner.dragging=True
    def end(self,w,ctx):self.owner.dragging=False;self.source_uris=[]
    def provide(self,w,ctx,data,info,timestamp):data.set_uris(self.source_uris)
    def received(self,w,ctx,x,y,data,info,timestamp):
        uri,p=self.destination(w,x,y);uris=data.get_uris() or []
        self.leave(w,ctx,timestamp)
        if not uri or not uris or self.owner.busy:Gtk.drag_finish(ctx,False,False,timestamp);return
        cut=ctx.get_selected_action()==Gdk.DragAction.MOVE
        self.owner.transfer(uris,uri,cut)
        # Accept the drop now, without asking the source to delete anything. Long copies
        # continue in the transfer dialog instead of holding the desktop drag grab.
        Gtk.drag_finish(ctx,True,False,timestamp)
