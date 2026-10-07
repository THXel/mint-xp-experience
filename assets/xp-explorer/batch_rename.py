"""Preview-only name planning, followed by no-overwrite operations and session undo."""
from pathlib import Path
from gi.repository import Gtk
from core import child_name,file_for
from xp_locale import t as _xp

def plan_names(rows,pattern,start=1,keep_extension=True):
    if not pattern.strip():raise ValueError(_xp('Bitte ein Namensmuster eingeben.'))
    if len(rows)>500:raise ValueError(_xp('Bitte höchstens 500 Einträge gleichzeitig umbenennen.'))
    planned=[];targets=set()
    import string
    for _,field,spec,conversion in string.Formatter().parse(pattern):
        if field is not None and (field not in ('name','n') or conversion or (spec and (field!='n' or spec not in ('02d','03d','04d','05d')))):raise ValueError(_xp('Erlaubte Platzhalter: {name}, {n}, {n:03d}'))
    for number,row in enumerate(rows,start):
        suffix=Path(row['name']).suffix if keep_extension and not row['dir'] else ''
        stem=row['name'][:-len(suffix)] if suffix else row['name']
        name=child_name(pattern.format(name=stem,n=number)+suffix)
        target=file_for(row['uri']).get_parent().get_child(name).get_uri()
        if target in targets:raise ValueError(_xp('Das Muster erzeugt doppelte Namen.'))
        targets.add(target);planned.append((row['uri'],name,target))
    return planned

class RenameDialog(Gtk.Dialog):
    def __init__(self,owner,rows):
        super().__init__(title=_xp('Mehrere Dateien umbenennen'),transient_for=owner,modal=True)
        self.rows=sorted(rows,key=lambda r:r['name'].casefold());self.plan=[];self.set_default_size(650,440);self.add_buttons(_xp('Abbrechen'),Gtk.ResponseType.CANCEL,_xp('Umbenennen'),Gtk.ResponseType.OK)
        box=self.get_content_area();box.set_border_width(14);box.set_spacing(10)
        lab=Gtk.Label(label=_xp('Muster: {name} behält den Namen, {n:03d} fügt eine Nummer ein.'),xalign=0);lab.set_line_wrap(True);box.add(lab)
        self.pattern=Gtk.Entry(text='{name} ({n:03d})');box.add(self.pattern)
        self.keep=Gtk.CheckButton(label=_xp('Dateiendung beibehalten'));self.keep.set_active(True);box.add(self.keep)
        self.model=Gtk.ListStore(str,str);tree=Gtk.TreeView(model=self.model)
        for i,label in enumerate(('Bisheriger Name','Neuer Name')):
            col=Gtk.TreeViewColumn(_xp(label),Gtk.CellRendererText(),text=i);col.set_expand(True);tree.append_column(col)
        scroll=Gtk.ScrolledWindow();scroll.add(tree);box.pack_start(scroll,True,True,0)
        self.status=Gtk.Label(xalign=0);self.status.set_line_wrap(True);box.add(self.status)
        self.pattern.connect('changed',lambda w:self.update());self.keep.connect('toggled',lambda w:self.update());self.update();self.show_all()
    def update(self):
        self.model.clear();self.plan=[]
        try:
            self.plan=plan_names(self.rows,self.pattern.get_text(),keep_extension=self.keep.get_active())
            for row,(_,name,_) in zip(self.rows,self.plan):self.model.append([row['name'],name])
            self.status.set_text(_xp('Vorhandene Dateien werden nicht überschrieben. Strg+Z macht den Vorgang rückgängig.'));self.set_response_sensitive(Gtk.ResponseType.OK,any(a!=c for a,b,c in self.plan))
        except (ValueError,KeyError,IndexError) as e:self.status.set_text(str(e));self.set_response_sensitive(Gtk.ResponseType.OK,False)
