"""Small, read-only summaries shared by media selection and confirmation."""
from pathlib import Path
from .components import ROOT

def names(w,options):
 icons=w.t('icons_imported') if options.get('icon_mode')=='imported' or ('icon_mode' not in options and options.get('icon_import')) else w.t('icons_bundled')
 source=options.get('sound_source',':keep:')
 sound=w.t('sound_keep') if source in (':keep:',':builtin:') or not options.get('sounds') else w.t('sound_mint') if source==':mint:' else options.get('sound_theme') or w.t('sound_custom')
 return icons,sound

def selection(w):
 return dict(icon_mode=w.icon_mode.get_active_id(),icon_import=w.icons.get_text(),sounds=w.sound_pack.get_active_id()!='keep',sound_source={'keep':':keep:','mint':':mint:'}.get(w.sound_pack.get_active_id(),w.sound_source.get_text()),sound_theme=w.sound.get_text())

def summary(w,icons=True,sounds=True):
 selected=selection(w);chosen=names(w,selected);current=names(w,w.engine.read_current().get('options',{}))
 rows=[]
 for i,(key,enabled) in enumerate((('icons',icons),('sounds',sounds))):
  value=chosen[i] if enabled else current[i]
  if key=='sounds' and selected['sound_source']==':keep:':value=w.t('sound_keep')
  rows.append(w.t(key)+': '+value)
 return '\n'.join(rows)+'\n\n'+w.t('media_scope')

def refresh(w,*_):
 if not hasattr(w,'media_state_labels') or getattr(w,'rebuilding',False):return
 record=w.engine.read_current();current=record.get('options',{});selected=selection(w)
 now=list(names(w,current));chosen=names(w,selected)
 try:
  live_icons=w.engine.settings.effective('org.cinnamon.desktop.interface','icon-theme')
  expected_icons='Mint-XP-Experience-Imported' if current.get('icon_mode')=='imported' else 'Mint-XP-Experience-Icons'
  if not current.get('icons') or live_icons!=expected_icons:now[0]=live_icons
  live_sounds=w.engine.settings.effective('org.cinnamon.desktop.sound','theme-name')
  expected_sounds='LinuxMint' if current.get('sound_source')==':mint:' else 'Mint-XP-Experience-Sounds'
  if not current.get('sounds') or live_sounds!=expected_sounds:now[1]=live_sounds
 except (AttributeError,RuntimeError):pass
 icon_pending=selected['icon_mode']!=current.get('icon_mode','imported' if current.get('icon_import') else 'bundled') or (selected['icon_mode']=='imported' and selected['icon_import']!=current.get('icon_import',''))
 sound_pending=selected['sounds'] and any(selected[k]!=current.get(k) for k in ('sounds','sound_source','sound_theme'))
 for i,pending in enumerate((icon_pending,sound_pending)):
  active=now[i] if record.get('installed') else w.t('state_disabled')
  w.media_state_labels[i].set_text(w.t('media_current')+': '+active+'\n'+w.t('media_selected')+': '+chosen[i]+'\n'+w.t('media_pending_short' if pending else 'media_same'))
 # Preview only validated PNGs; never load arbitrary vector documents here.
 from .gui import Gtk
 from gi.repository import GdkPixbuf
 for child in w.icon_preview.get_children():child.destroy()
 root=Path(selected['icon_import']) if selected['icon_mode']=='imported' and selected['icon_import'] else ROOT/'assets/icons'
 for name,group in (('folder','places'),('computer','devices'),('user-trash','places')):
  item=Gtk.Image();w.icon_preview.pack_start(item,False,False,0)
  for rel in ('32/'+name+'.png','32/'+group+'/'+name+'.png','48/'+name+'.png','48/'+group+'/'+name+'.png'):
   p=root/rel
   try:
    if p.is_file() and p.stat().st_size<1024*1024:
     item.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(p),32,32,True));break
   except Exception:continue
 w.icon_preview.show_all()

def backup_label(w,path):
 import datetime
 try:data=w.engine.read('snapshots/'+path.name,{})
 except (ValueError,OSError):return w.t('error')+' · '+path.stem
 try:
  when=datetime.datetime.fromisoformat(data.get('created_at','')).astimezone()
 except (ValueError,TypeError):when=datetime.datetime.fromtimestamp(path.stat().st_mtime).astimezone()
 reason={'manual':'backup','media':'media_page','sounds':'sound_options','uninstall':'uninstall'}.get(data.get('reason'),'backup')
 return when.strftime('%d.%m.%Y %H:%M:%S')+' · '+w.t(reason)
