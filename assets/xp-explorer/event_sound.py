"""Emit the standard trash event only after an actually successful empty action."""
from gi.repository import Gio,GLib

def completed_sound(kind,count,failed=False,cancelled=False):
    if kind!='empty-trash' or count<=0 or failed or cancelled:return False
    try:
        if not Gio.Settings.new('org.cinnamon.desktop.sound').get_boolean('event-sounds'):return False
        process=Gio.Subprocess.new(['canberra-gtk-play','--id=trash-empty'],Gio.SubprocessFlags.STDOUT_SILENCE|Gio.SubprocessFlags.STDERR_SILENCE)
        def finished(process,result):
            try:process.wait_check_finish(result)
            except GLib.Error:pass # Optional audio cannot invalidate a successful file action.
        process.wait_check_async(None,finished)
        return True
    except GLib.Error:return False
