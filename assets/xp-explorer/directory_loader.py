"""Bounded producer/consumer directory listing; late generations cannot change UI."""
import queue,threading
from gi.repository import GLib
from core import listing

def start(uri,hidden,cancel,valid,batch,finished):
    messages=queue.Queue(maxsize=4)
    def put(kind,value):
        while not cancel.is_cancelled():
            try:messages.put((kind,value),timeout=.1);return
            except queue.Full:pass
    def work():
        try:rows=listing(uri,hidden,cancel,on_batch=lambda rows:put('batch',rows));put('done',(rows,None))
        except Exception as e:put('done',(None,e))
    def poll():
        if not valid():cancel.cancel();return False
        if cancel.is_cancelled():finished(None,RuntimeError('Cancelled'));return False
        try:kind,value=messages.get_nowait()
        except queue.Empty:return True
        if kind=='batch':batch(value);return True
        finished(*value);return False
    GLib.timeout_add(16,poll);threading.Thread(target=work,daemon=True,name='xp-directory').start()
