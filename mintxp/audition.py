"""Audition an already validated import candidate without changing sound settings."""
import subprocess,tempfile,time
from pathlib import Path

class Audition:
 def __init__(self):self.process=None;self.directory=None;self.started=0
 def stop(self):
  if self.process is not None:
   if self.process.poll() is None:
    self.process.terminate()
    try:self.process.wait(timeout=.3)
    except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
   self.process=None
  if self.directory is not None:self.directory.cleanup();self.directory=None
 def play(self,data):
  self.stop();self.directory=tempfile.TemporaryDirectory(prefix='mintxp-preview-')
  path=Path(self.directory.name)/'preview.wav';path.write_bytes(data)
  try:self.process=subprocess.Popen(['canberra-gtk-play','--file='+str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);self.started=time.monotonic()
  except Exception:self.stop();raise
 def poll(self):
  if self.process is None:return 0
  result=self.process.poll()
  if result is None and time.monotonic()-self.started>30:self.stop();return -1
  if result is not None:self.stop()
  return result
