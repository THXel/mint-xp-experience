"""Explicit permanent deletion and trash tasks; UI always confirms irreversible actions."""
from xp_locale import t as _xp
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gio
from core import file_for,listing,delete_item,trash_with_location

class FileActions:
    def confirm(self,title,detail=''):
        d=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.WARNING,buttons=Gtk.ButtonsType.OK_CANCEL,text=title)
        d.format_secondary_text(detail);d.set_default_response(Gtk.ResponseType.CANCEL)
        response=d.run();d.destroy();return response==Gtk.ResponseType.OK
    def delete_selected(self,permanent=False):
        if permanent or self.uri.startswith('trash:'):self.permanent_delete()
        else:self.trash()
    def permanent_delete(self):
        rows=self.selected()
        if self.busy or not rows or self.uri=='computer:///' or any(r.get('mountable') or r.get('shortcut') for r in rows):return
        uris=[r['uri'] for r in rows]
        if self.confirm(_xp('{0} ausgewählte Objekte endgültig löschen?').format(len(uris)), _xp('Dies kann nicht rückgängig gemacht werden.\n\n')+'\n'.join(r['name'] for r in rows[:8])):
            self.operation(_xp('Wird endgültig gelöscht …'),uris,self.delete_recorded,kind='delete')
    def empty_trash(self):
        if self.busy:return
        self.busy=True
        def ready(rows,error):
            self.busy=False
            if not self.alive:return False
            if error:self.error(error);return False
            if not rows:self.info(_xp('Papierkorb'),_xp('Der Papierkorb ist bereits leer.'));return False
            # Use exactly the reviewed list: new arrivals during the dialog are excluded.
            if self.confirm(_xp('Papierkorb vollständig leeren?'),_xp('{0} Objekte werden endgültig gelöscht. Dies kann nicht rückgängig gemacht werden.').format(len(rows))):
                self.operation(_xp('Papierkorb wird geleert …'),[r['uri'] for r in rows],self.delete_recorded,kind='empty-trash')
            return False
        self.spawn(lambda:listing('trash:///',True),ready)
    def delete_recorded(self,uri,cancel):
        delete_item(uri,cancel);self.app.undo_history.discard_uri(uri)
    def trash_recorded(self,uri,cancel):
        before=self.app.undo_history.prepare(uri,cancel)
        target=trash_with_location(uri,cancel)
        if target:self.app.undo_history.remember(uri,target,cancel,before)
    def place_context(self,uri,event=None):
        import context_menu as ctx
        A=ctx.Action
        entries=[A(_xp('Öffnen'),lambda:self.navigate(uri),'folder-open')]
        if uri=='trash:///':entries += [None,A(_xp('Papierkorb leeren …'),self.empty_trash,'user-trash-full')]
        if uri=='network:///':entries += [None,A(_xp('Mit Server verbinden …'),self.connect_server,'network-server')]
        return self.show_context_menu(entries,event)
    def tree_context(self,event=None):
        pane=self.folder_pane
        if event:
            hit=pane.tree.get_path_at_pos(int(event.x),int(event.y))
            if not hit:return False
            pane.syncing=True
            try:pane.tree.get_selection().select_path(hit[0])
            finally:pane.syncing=False
        model,it=pane.tree.get_selection().get_selected()
        if it is None:return False
        uri=model[it][2]
        return self.place_context(uri,event) if uri else False
