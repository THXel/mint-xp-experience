"""Once-per-version first-run prompt, always executed as the desktop user."""
import os
from .engine import Engine
from .components import ROOT

def automatic_setup(engine=None):
    if os.geteuid()==0:return 0
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):return 0
    engine=engine or Engine()
    if engine.read_current().get('installed'):return 0
    version=(ROOT/'VERSION').read_text().strip()
    if engine.read('first-run.json',{}).get('version')==version:return 0
    # Mark only after a window was actually activated. Failed graphical startup
    # remains retryable at the next login; manual setup is always available.
    from .gui import Application
    app=Application('setup')
    def activated(application):
        if application.get_windows():engine.save('first-run.json',{'version':version})
    app.connect_after('activate',activated)
    return app.run([])
