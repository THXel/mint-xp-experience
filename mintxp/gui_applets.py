"""Explicit choice: keep all applets or disable the checked instances."""
from .gui import Gtk
from .applet_review import inventory

def review(window,options):
 rows=inventory(window.engine,options)
 if rows:
  dlg=Gtk.Dialog(title=window.t('applet_title'),transient_for=window,modal=True)
  dlg.set_default_size(700,460);box=dlg.get_content_area();box.set_spacing(10);box.set_border_width(14)
  box.pack_start(window.label(window.t('applet_notice')),False,False,0)
  scroll=Gtk.ScrolledWindow();scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);scroll.set_min_content_height(240);box.pack_start(scroll,True,True,0)
  choices=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);scroll.add(choices);checks=[]
  for item in rows:
   check=Gtk.CheckButton(label=item['name']+' · '+item['panel']+' · '+item['uuid']+'\n'+window.t(item['reason']));check.set_active(True);check.get_child().set_line_wrap(True);check.get_child().set_max_width_chars(75);choices.pack_start(check,False,False,0);checks.append((item['id'],check))
  dlg.add_button(window.t('cancel'),Gtk.ResponseType.CANCEL)
  dlg.add_button(window.t('applet_keep'),Gtk.ResponseType.NO)
  dlg.add_button(window.t('applet_disable'),Gtk.ResponseType.YES)
  dlg.set_default_response(Gtk.ResponseType.NO);dlg.show_all();answer=dlg.run()
  selected=[key for key,check in checks if check.get_active()];dlg.destroy()
  if answer not in (Gtk.ResponseType.YES,Gtk.ResponseType.NO):return False
  options['disabled_applets']=selected if answer==Gtk.ResponseType.YES else []
 else:options['disabled_applets']=[]
 options['reviewed_applets']=list(window.engine.settings.effective('org.cinnamon','enabled-applets'))
 return True
