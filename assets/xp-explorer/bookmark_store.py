"""GTK bookmarks shared with Nemo; optimistic writes preserve concurrent edits."""
from pathlib import Path
from gi.repository import Gio,GLib
from core import file_for
class BookmarkStore:
    def __init__(self,path=None):self.path=Path(path) if path else Path.home()/'.config/gtk-3.0/bookmarks'
    def read(self):
        try:
            _,data,etag=Gio.File.new_for_path(str(self.path)).load_contents(None)
            return data.decode('utf-8'),etag
        except GLib.Error as e:
            if e.matches(Gio.io_error_quark(),Gio.IOErrorEnum.NOT_FOUND):return '',None
            raise
    @staticmethod
    def uri(line):
        first=line.split(' ',1)[0]
        return file_for(first).get_uri() if '://' in first else None
    def entries(self):
        result=[]
        for line in self.read()[0].splitlines():
            uri=self.uri(line)
            if uri:
                label=line.split(' ',1)[1] if ' ' in line else file_for(uri).get_basename() or uri
                result.append((label,uri))
        return result
    def change(self,uri,action,label=None,step=0):
        uri=file_for(uri).get_uri()
        if any(c in uri for c in '\r\n\x00'):raise ValueError('Invalid bookmark URI')
        if label is not None and (not label.strip() or any(c in label for c in '\r\n\x00')):raise ValueError('Invalid bookmark name')
        text,etag=self.read();lines=text.splitlines();indices=[i for i,line in enumerate(lines) if self.uri(line)==uri]
        if action=='add':
            if indices:return False
            lines.append(uri+' '+(label or file_for(uri).get_basename() or uri))
        elif action=='remove':lines=[line for line in lines if self.uri(line)!=uri]
        elif action=='rename':
            for i in indices:lines[i]=uri+' '+label.strip()
        elif action=='move':
            if not indices:return False
            order=[i for i,line in enumerate(lines) if self.uri(line)];pos=order.index(indices[0]);target=pos+step
            if not 0<=target<len(order):return False
            a,b=order[pos],order[target];lines[a],lines[b]=lines[b],lines[a]
        elif action=='before':
            if not indices:return False
            if label==uri:return False
            moving=lines[indices[0]];lines=[line for line in lines if self.uri(line)!=uri]
            at=next((i for i,line in enumerate(lines) if label is not None and self.uri(line)==label),len(lines));lines.insert(at,moving)
        else:raise ValueError('Unknown bookmark action')
        data=('\n'.join(lines)+'\n' if lines else '').encode();f=Gio.File.new_for_path(str(self.path))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if etag is None:
            stream=f.create(Gio.FileCreateFlags.PRIVATE,None)
            try:stream.write_all(data,None)
            finally:stream.close(None)
        else:f.replace_contents(data,etag,False,Gio.FileCreateFlags.NONE,None)
        return True
