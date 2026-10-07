"""Server URI validation and native GVfs authentication. Never store credentials in URLs."""
from xp_locale import t as _xp
from urllib.parse import urlsplit,urlunsplit,quote,unquote
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gio,Gtk,GLib
NETWORK_SCHEMES={'smb','sftp','ftp','ftps','dav','davs','afp','nfs'}

def server_uri(text):
    text=text.strip()
    if text.startswith('\\\\'):text='smb://'+text[2:].replace('\\','/')
    elif '://' not in text:text='smb://'+text
    u=urlsplit(text)
    if u.scheme not in NETWORK_SCHEMES or not u.hostname or any(c.isspace() for c in u.netloc):raise ValueError(_xp('Bitte eine Serveradresse eingeben, z. B. smb://server/freigabe oder sftp://server.'))
    if u.password is not None:raise ValueError(_xp('Passwörter bitte nur im Anmeldedialog eingeben, nicht in der Adresse.'))
    if u.query or u.fragment:raise ValueError(_xp('Diese Serveradresse darf keine Suchparameter oder Fragmente enthalten.'))
    if u.port is not None and not 1<=u.port<=65535:raise ValueError(_xp('Ungültiger Port.'))
    return urlunsplit((u.scheme,u.netloc,quote(unquote(u.path or '/'),safe='/@:+'),'', ''))

def cancelled(error):return isinstance(error,GLib.Error) and any(error.matches(Gio.io_error_quark(),code) for code in (Gio.IOErrorEnum.CANCELLED,Gio.IOErrorEnum.FAILED_HANDLED))

class NetworkActions:
    def connect_server(self):
        if self.busy:return
        d=Gtk.Dialog(title=_xp('Mit Server verbinden'),transient_for=self,modal=True)
        d.add_buttons(_xp('Abbrechen'),Gtk.ResponseType.CANCEL,'Verbinden',Gtk.ResponseType.OK);d.set_default_response(Gtk.ResponseType.OK)
        box=d.get_content_area();box.set_border_width(18);box.set_spacing(12)
        text=Gtk.Label(label='Serveradresse (SMB, SFTP, FTP oder WebDAV)\nBeispiel: smb://server/freigabe\nBenutzername und Passwort werden bei Bedarf separat abgefragt.',xalign=0);text.set_line_wrap(True);box.add(text)
        entry=Gtk.Entry();entry.set_width_chars(48);entry.set_placeholder_text('smb://server/freigabe');entry.set_activates_default(True);box.add(entry)
        error=Gtk.Label(xalign=0);error.set_line_wrap(True);box.add(error);d.show_all();entry.grab_focus()
        while d.run()==Gtk.ResponseType.OK:
            try:uri=server_uri(entry.get_text());break
            except ValueError as e:error.set_text(str(e))
        else:d.destroy();return
        d.destroy();self.navigate(uri)
    def mount_location(self,uri,mountable=False):
        generation=self.generation
        if getattr(self,'mount_generation',None)==generation:return
        self.mount_generation=generation;self.mount_attempted=True
        cancel=self.nav_cancel or Gio.Cancellable()
        op=Gtk.MountOperation(parent=self);op.set_password_save(Gio.PasswordSave.FOR_SESSION)
        self.mount_operation=op;self.status.set_text(_xp('Netzwerkverbindung wird hergestellt …'))
        def done(f,res):
            if getattr(self,'mount_generation',None)==generation:
                self.mount_generation=None;self.mount_operation=None
            target=uri
            try:
                if mountable:target=f.mount_mountable_finish(res).get_uri()
                else:f.mount_enclosing_volume_finish(res)
            except GLib.Error as e:
                if not self.alive or generation!=self.generation:return
                if e.matches(Gio.io_error_quark(),Gio.IOErrorEnum.ALREADY_MOUNTED):pass
                elif cancelled(e):self.status.set_text('Verbindung abgebrochen.');self.message.set_text(_xp('Verbindung abgebrochen. Über „Mit Server verbinden“ erneut versuchen.'));return
                else:self.status.set_text(_xp('Verbindung nicht hergestellt.'));self.error(e);return
            if self.alive and generation==self.generation:self.navigate(target,False,_mount_retry=True)
        try:
            f=Gio.File.new_for_uri(uri)
            if mountable:f.mount_mountable(Gio.MountMountFlags.NONE,op,cancel,done)
            else:f.mount_enclosing_volume(Gio.MountMountFlags.NONE,op,cancel,done)
        except Exception as e:
            if self.mount_generation==generation:self.mount_generation=None;self.mount_operation=None
            self.error(e)
    def disconnect_server(self,uri=None):
        if self.busy:return
        target=Gio.File.new_for_uri(uri or self.uri)
        def found(f,res):
            try:
                mount=f.find_enclosing_mount_finish(res)
                if not mount.can_unmount():raise ValueError(_xp('Diese Verbindung lässt sich nicht trennen.'))
            except Exception as e:self.error(e);return
            if not self.alive:return
            if not self.confirm('Netzwerkverbindung trennen?', _xp('Bitte vorher geöffnete Dateien auf dieser Freigabe schließen.')):return
            op=Gtk.MountOperation(parent=self)
            def done(m,res):
                try:m.unmount_with_operation_finish(res)
                except Exception as e:
                    if self.alive and not cancelled(e):self.error(e)
                    return
                if self.alive:self.navigate('network:///')
            mount.unmount_with_operation(Gio.MountUnmountFlags.NONE,op,None,done)
        target.find_enclosing_mount_async(GLib.PRIORITY_DEFAULT,None,found)
