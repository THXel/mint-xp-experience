#!/usr/bin/python3
import sys,re
from pathlib import Path
sys.dont_write_bytecode=True
# User-local recovery stays usable after removing the DEB. While it is installed,
# route this managed launcher through the current system package for updates.
_here=Path(__file__).resolve().parent
_system=Path('/usr/share/mint-xp-experience')
def _version(path):
 try:
  match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)-preview\.(\d+)',(path/'VERSION').read_text().strip())
  return tuple(map(int,match.groups())) if match else ()
 except OSError:return ()
# A newer locally applied manager must not be downgraded by an older DEB.
if _here==Path.home()/'.local/share/mint-xp-experience' and (_system/'launch.py').is_file() and _version(_system)>=_version(_here):
 sys.path.insert(0,str(_system))
from mintxp.cli import main
if __name__=='__main__':main()
