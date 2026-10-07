"""GIO removable-media actions; capability gated, never forced."""
from xp_locale import t as _xp
import gi
gi.require_version("Gtk","3.0")
from gi.repository import Gio,Gtk

def removal_action(mount):
    drive=mount.get_drive()
    if drive and drive.can_stop():return drive,'stop','stop_finish','Sicher entfernen'
    if not mount.get_root().is_native() and mount.can_unmount():return mount,'unmount_with_operation','unmount_with_operation_finish',_xp('Verbindung trennen')
    if mount.can_eject():return mount,'eject_with_operation','eject_with_operation_finish',_xp('Auswerfen')
    if drive and drive.can_eject():return drive,'eject_with_operation','eject_with_operation_finish',_xp('Auswerfen')
    if drive and drive.is_media_removable() and mount.can_unmount():return mount,'unmount_with_operation','unmount_with_operation_finish',_xp('Aushängen')
    return None

class Devices:
    def __init__(self,owner):
        self.owner=owner;self.monitor=Gio.VolumeMonitor.get();self.active=False;self.cancel=Gio.Cancellable()
        self.signals=[self.monitor.connect(n,self.changed) for n in ('mount-added','mount-removed','volume-added','volume-removed','volume-changed')]
    def changed(self,*args):
        if self.owner.alive and self.owner.uri=='computer:///' and not self.active:self.owner.changed()
    def enrich(self,groups):
        mounts={m.get_root().get_uri():m for m in self.monitor.get_mounts()}
        for items in groups.values():
            for item in items:
                if item['uri'] in mounts:item['mount']=mounts[item['uri']]
        seen={item.get('uri') for items in groups.values() for item in items}
        for uri,mount in mounts.items():
            if not mount.get_root().is_native() and uri not in seen:
                groups[_xp('Netzwerk')].append(dict(name=mount.get_name(),uri=uri,icon=mount.get_icon(),sub='Verbunden',mount=mount))
        for volume in self.monitor.get_volumes():
            if not volume.get_mount() and volume.can_mount():
                drive=volume.get_drive();group=_xp('Netzwerk') if drive is None else _xp('Geräte mit Wechselmedien') if drive.is_removable() or drive.can_stop() else _xp('Festplatten')
                groups[group].append(dict(name=volume.get_name(),uri='',icon=volume.get_icon(),sub=_xp('Nicht eingebunden – Doppelklick zum Öffnen'),volume_object=volume))
        return groups
    def open(self,item):
        if self.active or self.owner.busy:return
        if item.get('uri'):self.owner.navigate(item['uri']);return
        volume=item.get('volume_object')
        if volume and volume.can_mount():self.run(volume,'mount','mount_finish',True)
    def remove(self,item):
        if self.active or self.owner.busy:return
        mount=item.get('mount');action=removal_action(mount) if mount else None
        if not action:return
        d=Gtk.MessageDialog(transient_for=self.owner,modal=True,message_type=Gtk.MessageType.QUESTION,buttons=Gtk.ButtonsType.OK_CANCEL,text=f'„{item["name"]}“ sicher entfernen?');d.format_secondary_text(_xp('Bitte vorher geöffnete Dateien auf diesem Laufwerk schließen.'));answer=d.run();d.destroy()
        if answer==Gtk.ResponseType.OK:self.run(*action[:3])
    def run(self,obj,method,finish,open_after=False):
        self.active=True;self.owner.busy=True;self.owner.status.set_text(_xp('Laufwerksaktion läuft …'));operation=Gtk.MountOperation(parent=self.owner)
        def done(source,result):
            self.active=False;self.owner.busy=False
            try:
                getattr(source,finish)(result)
                if not self.owner.alive:return
                mount=source.get_mount() if open_after else None
                if mount:self.owner.navigate(mount.get_root().get_uri())
                else:self.owner.reload()
            except Exception as e:
                if self.owner.alive:self.owner.error(e)
        try:getattr(obj,method)(Gio.MountMountFlags.NONE if method=='mount' else Gio.MountUnmountFlags.NONE,operation,self.cancel,done)
        except Exception as e:self.active=False;self.owner.busy=False;self.owner.error(e)
    def close(self):
        self.cancel.cancel()
        for handler in self.signals:self.monitor.disconnect(handler)
