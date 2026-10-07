"""Resolve files passed by browsers to their containing directory without opening them."""
from pathlib import Path
from core import file_for
from gi.repository import Gio

def browse_target(uri):
    target=file_for(uri)
    # Only native metadata here: remote browsing remains cancellable/asynchronous.
    if target.is_native():
        kind=target.query_file_type(Gio.FileQueryInfoFlags.NONE,None)
        if kind not in (Gio.FileType.DIRECTORY,Gio.FileType.UNKNOWN,Gio.FileType.MOUNTABLE):
            parent=target.get_parent()
            if parent:return parent.get_uri(),target.get_uri()
    return target.get_uri(),None
