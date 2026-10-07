"""Local WebKit 4.1 host for upstream Minesweeper XP and JS Paint.

The HTTP server exposes only downloaded application files, on loopback with a
private token. A persistent origin retains autosaves/settings across restarts.
No Electron, browser profile, system Java or global file association is changed.
"""
import fcntl,http.server,json,mimetypes,os,secrets,socket,threading,urllib.parse
from pathlib import Path
import gi
gi.require_version('Gtk','3.0');gi.require_version('WebKit2','4.1')
from gi.repository import Gtk,Gdk,Gio,GLib,WebKit2

class Files(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  host='127.0.0.1:'+str(self.server.server_port)
  path=urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
  prefix='/'+self.server.token+'/'
  if self.headers.get('Host')!=host or not path.startswith(prefix):self.send_error(404);return
  rel=path[len(prefix):] or 'index.html'
  if '..' in Path(rel).parts or '\\' in rel or '\0' in rel:self.send_error(404);return
  file=(self.server.root/rel).resolve()
  if self.server.root not in file.parents or not file.is_file():self.send_error(404);return
  try:data=file.read_bytes()
  except OSError:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(file))[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
  try:self.wfile.write(data)
  except (BrokenPipeError,ConnectionResetError):pass

def run(base,data,app):
 GLib.set_prgname('mintxp-addon-'+app['id']);GLib.set_application_name(app['name'])
 lock=(data/'window.lock').open('a')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  dlg=Gtk.MessageDialog(message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.OK,text=app['name']+' is already open.');dlg.run();dlg.destroy();return
 config=data/'origin.json'
 origin=json.loads(config.read_text()) if config.exists() else {'port':0,'token':secrets.token_hex(24)}
 try:server=http.server.ThreadingHTTPServer(('127.0.0.1',origin['port']),Files)
 except OSError:
  dlg=Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR,buttons=Gtk.ButtonsType.OK,text='The saved local application port is in use. Close the other instance and retry. Saved data was preserved.');dlg.run();dlg.destroy();return
 server.daemon_threads=True;server.root=(base/'web').resolve();server.token=origin['token'];origin['port']=server.server_port
 if not config.exists():
  fd=os.open(config,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as out:json.dump(origin,out)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 url='http://127.0.0.1:'+str(origin['port'])+'/'+origin['token']+'/'
 manager=WebKit2.UserContentManager()
 profile=WebKit2.WebsiteDataManager(base_data_directory=str(data/'webkit'),base_cache_directory=str(data/'cache'))
 context=WebKit2.WebContext.new_with_website_data_manager(profile)
 view=WebKit2.WebView(user_content_manager=manager,web_context=context)
 win=Gtk.Window(title=app['name']);win.set_wmclass('mintxp-addon-'+app['id'],'MintXPAddon'+app['id'].title())
 win.set_default_size(1000,740);win.set_position(Gtk.WindowPosition.CENTER)
 win.set_icon_name('applications-graphics' if app['id']=='jspaint' else 'applications-games')
 if app['id']=='jspaint':
  icon=base/'icon.svg'
  if not icon.exists():icon=base/'web/images/icons/128x128.png'
  if icon.exists():win.set_icon_from_file(str(icon))
 if app['id']=='jspaint':
  # JS Paint's browser download fallback cannot know whether Save was cancelled.
  # Use its supported hook and acknowledge only WebKit's completed transfer.
  script="""
  (()=>{
    const pending = new Map();
    window.mintxpSaveFinished = (uri, ok) => {
      const finish = pending.get(uri);
      if (finish) { pending.delete(uri); URL.revokeObjectURL(uri); finish(ok); }
    };
    window.systemHooks = window.systemHooks || {};
    window.systemHooks.showSaveFileDialog = async (options) => {
      if (pending.size) return;
      const {save_as_prompt} = await import(new URL('src/functions.js', document.baseURI).href);
      const choice = await save_as_prompt({
        dialogTitle:options.dialogTitle, defaultFileName:options.defaultFileName,
        defaultFileFormatID:options.defaultFileFormatID, formats:options.formats
      });
      const blob = await options.getBlob(choice.newFileFormatID);
      const uri = URL.createObjectURL(blob);
      const success = await new Promise(resolve=>{
        pending.set(uri, resolve);
        const link = document.createElement('a');
        link.href=uri; link.download=choice.newFileName;
        document.body.appendChild(link); link.click(); link.remove();
      });
      if (success) options.savedCallbackUnreliable?.({
        ...choice, newFileHandle:null, newBlob:blob
      });
    };
  })();
  """
  manager.add_script(WebKit2.UserScript.new(script,WebKit2.UserContentInjectedFrames.TOP_FRAME,WebKit2.UserScriptInjectionTime.START,None,None))
 if app['id']=='minesweeper':
  win.set_decorated(False);win.set_default_size(254,380);win.set_icon_from_file(str(base/'icon.png'))
  manager.register_script_message_handler('host')
  def message(manager,result):
   try:
    m=json.loads(result.get_js_value().to_string());cmd=m.get('cmd')
    if cmd=='size':
     w=max(150,min(1800,int(m['w'])));h=max(150,min(1000,int(m['h'])));view.set_size_request(1,1)
     geometry=Gdk.Geometry();geometry.min_width=geometry.max_width=w;geometry.min_height=geometry.max_height=h
     win.set_geometry_hints(None,geometry,Gdk.WindowHints.MIN_SIZE|Gdk.WindowHints.MAX_SIZE);win.resize(w,h)
    elif cmd=='quit':view.try_close()
    elif cmd=='minimise':win.iconify()
    elif cmd=='drag':win.begin_move_drag(1,int(m['x']),int(m['y']),Gdk.CURRENT_TIME)
    elif cmd=='url' and m.get('url')=='https://git.new/Minesweeper-XP':Gio.AppInfo.launch_default_for_uri(m['url'],None)
   except (ValueError,KeyError,TypeError):pass
  manager.connect('script-message-received::host',message)
  script="""
  const send = data => window.webkit.messageHandlers.host.postMessage(JSON.stringify(data));
  window.runtime = {
    WindowSetSize:(w,h)=>send({cmd:'size',w,h}), Quit:()=>send({cmd:'quit'}),
    WindowMinimise:()=>send({cmd:'minimise'}), BrowserOpenURL:url=>send({cmd:'url',url})
  };
  document.addEventListener('mousedown', e=>{
    if(e.button===0 && e.target.closest('.title-bar') && !e.target.closest('button,img'))
      send({cmd:'drag',x:e.screenX,y:e.screenY});
  });
  """
  manager.add_script(WebKit2.UserScript.new(script,WebKit2.UserContentInjectedFrames.TOP_FRAME,WebKit2.UserScriptInjectionTime.START,None,None))
 def policy(view,decision,kind):
  if kind in (WebKit2.PolicyDecisionType.NAVIGATION_ACTION,WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION):
   action=decision.get_navigation_action();uri=action.get_request().get_uri()
   if uri.startswith('blob:http://127.0.0.1:'+str(origin['port'])+'/') or uri.startswith('data:image/'):
    decision.download();return True
   if not uri.startswith(url):
    decision.ignore()
    if action.is_user_gesture() and urllib.parse.urlsplit(uri).scheme in ('http','https'):Gio.AppInfo.launch_default_for_uri(uri,None)
    return True
  return False
 view.connect('decide-policy',policy)
 view.connect('context-menu',lambda *args:True)
 view.connect('notify::title',lambda *args:win.set_title(view.get_title() or app['name']))
 def download(context,transfer):
  acknowledged=False
  def acknowledge(ok):
   nonlocal acknowledged
   if acknowledged:return
   acknowledged=True
   if app['id']=='jspaint':
    uri=transfer.get_request().get_uri()
    view.run_javascript('window.mintxpSaveFinished?.('+json.dumps(uri)+','+json.dumps(ok)+')',None,None,None)
  transfer.connect('finished',lambda *args:acknowledge(True))
  transfer.connect('failed',lambda *args:acknowledge(False))
  def destination(transfer,suggested):
   dlg=Gtk.FileChooserDialog(title=app['name']+' — Save',transient_for=win,action=Gtk.FileChooserAction.SAVE)
   dlg.add_buttons(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_SAVE,Gtk.ResponseType.OK)
   dlg.set_do_overwrite_confirmation(True);dlg.set_current_name(Path(suggested).name or 'image.png')
   if dlg.run()==Gtk.ResponseType.OK:
    file=Path(dlg.get_filename());transfer.set_allow_overwrite(True);transfer.set_destination(file.as_uri())
   else:transfer.cancel()
   dlg.destroy();return True
  transfer.connect('decide-destination',destination)
 context.connect('download-started',download)
 win.connect('delete-event',lambda *args:(view.try_close(),True)[1]);view.connect('close',lambda *args:win.destroy())
 win.connect('destroy',Gtk.main_quit);win.add(view);win.show_all();view.load_uri(url)
 try:Gtk.main()
 finally:server.shutdown();server.server_close();lock.close()
