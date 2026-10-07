"""Compact, grouped pages shared by setup and settings; scrolling is a small-screen fallback."""
from pathlib import Path
from .gui import Gtk,Gio,GLib,Pango,ROOT,LANGUAGES,COMPONENTS,CATALOG,subprocess

def build(w):
 w.rebuilding=True;w.page_containers={};w.media_state_labels=[]
 old=w.get_child()
 if old:w.remove(old);old.destroy()
 def row(parent,spacing=8):
  box=Gtk.Box(spacing=spacing);parent.pack_start(box,False,False,0);return box
 def label(parent,key,cls=None):
  v=w.label(w.t(key),cls);parent.pack_start(v,False,False,0);return v
 def buttons(parent,spec):
  b=row(parent)
  for key,fn in spec:w.button(b,key,fn)
  return b
 def card(grid,title,x,y):
  frame=Gtk.Frame(label=w.t(title));grid.attach(frame,x,y,1,1)
  box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3);box.set_border_width(7);frame.add(box);return box
 def check(box,text,value):
  c=Gtk.CheckButton(label=text);c.set_active(bool(value));c.get_child().set_line_wrap(True);c.get_child().set_line_wrap_mode(Pango.WrapMode.WORD_CHAR);c.get_child().set_xalign(0);c.get_child().set_hexpand(True);c.get_child().set_max_width_chars(24);box.pack_start(c,False,False,0);return c
 def grid(parent,columns=3):
  g=Gtk.Grid(column_spacing=10,row_spacing=10,column_homogeneous=True);parent.pack_start(g,False,False,0);return g
 def entry(parent,text=''):
  e=Gtk.Entry(text=text);e.set_editable(False);parent.pack_start(e,False,False,0);return e
 def jump(key):return lambda:w.stack.set_visible_child_name(key)
 w.outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);w.add(w.outer)
 hero=Gtk.Box(spacing=12);hero.get_style_context().add_class('hero');w.outer.pack_start(hero,False,False,0)
 logo=Gtk.Image.new_from_file(str(ROOT/'assets/session/installer-logo.png'));logo.set_tooltip_text('Mint XP Experience');hero.pack_start(logo,False,False,0)
 titles=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2);hero.pack_start(titles,True,True,0)
 titles.pack_start(w.label('Mint XP Experience','heading'),False,False,0);label(titles,'setup_title' if w.mode=='setup' else 'title')
 hero.pack_end(w.label((ROOT/'VERSION').read_text().strip()),False,False,0)
 body=Gtk.Box();w.outer.pack_start(body,True,True,0)
 w.stack=Gtk.Stack();w.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT);w.stack.set_transition_duration(160)
 sidebar=Gtk.StackSidebar();sidebar.set_stack(w.stack);nav=Gtk.ScrolledWindow();nav.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);nav.set_min_content_width(148);nav.add(sidebar);body.pack_start(nav,False,False,0);body.pack_start(w.stack,True,True,0)
 welcome=w.page('welcome')
 lang=row(welcome);lang.pack_start(w.label(w.t('language')),False,False,0);w.language=Gtk.ComboBoxText();w.language.append('auto',w.t('auto'))
 for code,name in LANGUAGES.items():w.language.append(code,name)
 w.language.set_active_id(w.options['language']);w.language.connect('changed',w.change_language);lang.pack_start(w.language,True,True,0)
 setup_source=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);welcome.pack_start(setup_source,False,False,0)
 source_parent=welcome;welcome=setup_source
 # Media selection is the first decision, directly beneath the system language.
 media_intro=w.label(w.t('media_welcome_notice'));welcome.pack_start(media_intro,False,False,0)
 w.media_rights=Gtk.CheckButton(label=w.t('media_rights'));w.media_rights.get_child().set_line_wrap(True);w.media_rights.get_child().set_max_width_chars(75);w.media_rights.set_active(getattr(w,'media_acknowledged',False));welcome.pack_start(w.media_rights,False,False,0)
 r=row(welcome);w.media_file_button=w.button(r,'media_file',w.choose_media);w.media_folder_button=w.button(r,'media_folder',lambda:w.choose_media(True))
 w.media_builtin_button=w.button(r,'media_without_iso',w.use_bundled_media)
 def rights(c):
  w.media_acknowledged=c.get_active();w.media_file_button.set_sensitive(c.get_active());w.media_folder_button.set_sensitive(c.get_active())
 w.media_rights.connect('toggled',rights);rights(w.media_rights)
 r=row(welcome);w.media_summary=w.label('');r.pack_start(w.media_summary,True,True,0);w.media_continue=w.button(r,'media_continue',w.finish_media);w.media_continue.set_no_show_all(True)
 welcome=source_parent
 if w.mode=='settings':
  setup_source.set_no_show_all(True);setup_source.hide()
  label(welcome,'settings_overview','notice')
  buttons(welcome,[('open_icons',jump('media_page')),('open_sounds',jump('sound_options'))])
  buttons(welcome,[('components',jump('components')),('backups',jump('backups'))])
  buttons(welcome,[('health',jump('health')),('remove',jump('remove'))])
  welcome=w.page('components');label(welcome,'component_notice','notice')
 w.install_controls=[]
 actions=Gtk.Box(spacing=8,homogeneous=True);w.install_gate=Gtk.EventBox();w.install_gate.set_visible_window(False);w.install_gate.add(actions);welcome.pack_start(w.install_gate,False,False,0)
 w.install_gate.connect('button-press-event',lambda *_:(not w.require_media()) if not w.media_ready else False)
 w.install_all_button=w.button(actions,'install_all',w.install_all);w.install_selected_button=w.button(actions,'install_selected',w.review)
 if w.mode=='settings':
  w.install_all_button.set_no_show_all(True);w.install_all_button.hide();w.install_selected_button.set_label(w.t('apply_component_changes'))
 for b in (w.install_all_button,w.install_selected_button):b.get_style_context().add_class('install-action');actions.set_child_packing(b,True,True,0,Gtk.PackType.START)
 components=welcome;g=grid(components);w.install_controls.append(g);w.checks={};w.system_checks={};w.addon_checks={}
 for column,(title,keys) in enumerate([('group_look',('gtk','shell','cursor','icons','wallpaper','fonts','sounds')),('group_desktop',('explorer','control','menu','taskbar','tray','default_manager','welcome_screen')),('group_extras',('games',))]):
  box=card(g,title,column,0)
  for key in keys:w.checks[key]=check(box,w.t(key),w.options[key])
  if column==2:
   for key in ('boot_install','login_install'):w.system_checks[key]=check(box,w.t(key),w.options.get(key))
   for key,item in CATALOG.items():w.addon_checks[key]=check(box,item['name'],key in w.options.get('addon_selection',[]))

 # Media actions stay outside the scroll area and remain visible on small screens.
 def action(key,label_key,fn,primary=True):
  container=w.page_containers[key]
  bar=getattr(container,'action_bar',None)
  if bar is None:
   bar=Gtk.Box(spacing=8);bar.set_border_width(10);container.pack_end(bar,False,False,0);container.action_bar=bar
  button=w.button(bar,label_key,fn);bar.set_child_packing(button,True,True,0,Gtk.PackType.START)
  if primary:button.get_style_context().add_class('install-action')
  button.set_sensitive(w.engine.read_current().get('installed',False));return button
 media=w.page('media_page');label(media,'media_steps','notice')
 state=w.label('','notice');media.pack_start(state,False,False,0);w.media_state_labels.append(state)
 w.icon_preview=row(media)
 w.iso_status=w.label('');media.pack_start(w.iso_status,False,False,0)
 w.iso_rights=check(media,w.t('iso_rights'),getattr(w,'media_acknowledged',False));w.iso_rights.get_child().set_max_width_chars(75)
 source_buttons=buttons(media,[('media_file',w.choose_media),('media_folder',lambda:w.choose_media(True))])
 source_buttons.set_sensitive(w.iso_rights.get_active());w.iso_rights.connect('toggled',lambda c:source_buttons.set_sensitive(c.get_active()))
 w.iso_button=source_buttons.get_children()[0]
 label(media,'icon_selection')
 w.prefer_icons=Gtk.CheckButton();w.icon_mode=Gtk.ComboBoxText();w.icon_mode.append('bundled',w.t('icons_bundled'));w.icon_mode.append('imported',w.t('icons_imported'));w.icon_mode.set_active_id(w.options.get('icon_mode','bundled'));media.pack_start(w.icon_mode,False,False,0)
 w.icons=entry(media,w.options['icon_import']);w.icons.set_placeholder_text(w.t('no_icon_pack'));label(media,'compact_icon_note')
 buttons(media,[('sound_options',jump('sound_options'))]);label(media,'media_private')
 w.icons_apply_button=action('media_page','install_icons',lambda:w.apply_media(True))
 w.media_apply_button=action('media_page','install_media',w.apply_media)
 if w.mode=='setup':label(media,'media_setup_hint')
 # Sound selection and preview are short. Technical limits stay in an explicit details dialog.
 soundpage=w.page('sound_options');state=w.label('','notice');soundpage.pack_start(state,False,False,0);w.media_state_labels.append(state)
 w.sound_pack=Gtk.ComboBoxText();w.sound_pack.append('keep',w.t('sound_keep'));w.sound_pack.append('mint',w.t('sound_mint'));w.sound_pack.append('custom',w.t('sound_custom'));w.sound_pack.set_active_id({':keep:':'keep',':builtin:':'keep',':mint:':'mint'}.get(w.options['sound_source'],'custom'));soundpage.pack_start(w.sound_pack,False,False,0)
 w.sound_choices=dict(w.options.get('sound_choices',{}));w.sound_custom_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);soundpage.pack_start(w.sound_custom_box,False,False,0)
 w.sound=Gtk.Entry(text=w.options['sound_theme']);w.sound.set_placeholder_text(w.t('sound_theme'));w.sound_custom_box.pack_start(w.sound,False,False,0)
 w.sound_source=entry(w.sound_custom_box,'' if w.options['sound_source'] in (':keep:',':builtin:',':mint:') else w.options['sound_source'])
 buttons(w.sound_custom_box,[('sound_choose',w.choose_sounds),('sound_choose_archive',lambda:w.choose_sounds(True)),('clear',lambda:w.set_sound_source(''))])
 w.sound_pack.connect('changed',lambda combo:w.checks['sounds'].set_active(combo.get_active_id()!='keep'))
 w.sound_preserve=check(soundpage,w.t('sound_preserve'),w.options['sound_preserve']);w.sound_preserve.get_child().set_max_width_chars(70)
 preview=row(soundpage);w.sound_event=Gtk.ComboBoxText()
 for event in ('bell','dialog-error','dialog-warning','notification','window-minimized','desktop-login','desktop-logout','trash-empty'):w.sound_event.append(event,w.t('sound_event_'+event))
 w.sound_event.set_active_id('desktop-login');preview.pack_start(w.sound_event,True,True,0);audition=w.button(preview,'sound_audition',w.preview_selected_sound);audition.set_sensitive(w.sound_pack.get_active_id()!='keep');w.sound_pack.connect('changed',lambda c:audition.set_sensitive(c.get_active_id()!='keep'))
 sound_tools=buttons(soundpage,[('sound_inspect',lambda:w.sound_action('inspect')),('media_file',jump('media_page'))])
 inspect=sound_tools.get_children()[0]
 details=Gtk.Expander(label=w.t('sound_details'));soundpage.pack_start(details,False,False,0);advanced=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);details.add(advanced)
 buttons(advanced,[('sound_details',lambda:w.message(w.t('sound_details'),w.t('sound_limits'))),('sound_verify',lambda:w.sound_action('verify')),('sound_undo',lambda:w.sound_action('remove'))])
 w.sound_apply_button=action('sound_options','install_sounds',lambda:w.sound_action('apply'))
 def sound_actions(combo):
  selected=combo.get_active_id()!='keep';installed=w.engine.read_current().get('installed',False)
  w.sound_apply_button.set_sensitive(installed and selected);w.media_apply_button.set_sensitive(installed and selected);inspect.set_sensitive(selected)
  w.media_apply_button.set_tooltip_text(w.t('media_apply_notice'))
 w.sound_pack.connect('changed',sound_actions);sound_actions(w.sound_pack)
 label(soundpage,'sound_apply_hint' if w.mode=='settings' else 'media_setup_hint')
 options=w.page('options');g=grid(options,2);look=card(g,'group_look',0,0);session=card(g,'welcome_options',1,0);w.spins={}
 for key,lower,upper in [('font_size',9,18),('icon_size',20,48)]:
  r=row(look);r.pack_start(w.label(w.t(key)),True,True,0);spin=Gtk.SpinButton.new_with_range(lower,upper,1);spin.set_value(w.options[key]);w.spins[key]=spin;r.pack_end(spin,False,False,0)
 r=row(session);r.pack_start(w.label(w.t('welcome_duration')),True,True,0);spin=Gtk.SpinButton.new_with_range(.5,8,.1);spin.set_digits(1);spin.set_value(w.options['welcome_duration']);w.spins['welcome_duration']=spin;r.pack_end(spin,False,False,0)
 w.fade=check(session,w.t('welcome_fade'),w.options['welcome_fade']);w.monitors=Gtk.ComboBoxText();w.monitors.append('all',w.t('all_monitors'));w.monitors.append('primary',w.t('primary_monitor'));w.monitors.set_active_id(w.options['welcome_monitors']);session.pack_start(w.monitors,False,False,0);w.button(session,'welcome_preview',w.preview_welcome)
 buttons(options,[('welcome',jump('welcome')),('preview',w.review)])
 w.addon_page=w.page('addons');label(w.addon_page,'compact_addons','notice');w.addon_rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);w.addon_page.pack_start(w.addon_rows,False,False,0);w.button(w.addon_page,'refresh_status',w.refresh_addons);w.refresh_addons()
 w.health=w.page('health');w.health_rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);w.health.pack_start(w.health_rows,False,False,0);buttons(w.health,[('refresh_status',w.refresh_status),('diagnostic',w.export_report)]);w.refresh_status()
 backups=w.page('backups');label(backups,'baseline_notice','notice');label(backups,'restore_scope');w.backups=Gtk.ComboBoxText();backups.pack_start(w.backups,False,False,0);w.reload_backups()
 buttons(backups,[('backup',lambda:w.run_job(w.engine.backup)),('restore',w.restore)])
 buttons(backups,[('verify',lambda:w.run_job(w.verify)),('recover',lambda:w.run_job(w.engine.recover))]);buttons(backups,[('rescue_help',w.rescue_help),('open_backup',lambda:Gio.AppInfo.launch_default_for_uri(w.engine.state.as_uri(),None))])
 remove=w.page('remove');label(remove,'remove_notice','notice');label(remove,'conflict_help');w.remove_addons=check(remove,w.t('remove_owned_addons'),True);w.remove_addons.get_child().set_max_width_chars(75);w.button(remove,'uninstall',w.remove_install)
 helpbox=w.page('help');label(helpbox,'update_notice','notice');buttons(helpbox,[('help',lambda:Gio.AppInfo.launch_default_for_uri((ROOT/'docs/INSTALL.de.md').as_uri(),None)),('sound_sources',lambda:Gio.AppInfo.launch_default_for_uri((ROOT/'docs/SOUND-SOURCES.de.md').as_uri(),None))]);w.button(helpbox,'session_appearance',lambda:subprocess.Popen(['/usr/bin/python3','-B',str(ROOT/'system/control.py')]))
 w.completion_box=w.page('completion');w.completion_text=w.label(w.t('completion_empty'));w.completion_text.set_selectable(True);w.completion_box.pack_start(w.completion_text,False,False,0);buttons(w.completion_box,[('open_settings',lambda:w.switch_mode('settings')),('verify',lambda:w.run_job(w.verify))])
 w.status=w.label(w.t('ready'),'status');w.outer.pack_end(w.status,False,False,0)
 w.progress_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3);w.progress_box.set_border_width(8);w.progress_box.set_no_show_all(True);w.progress_label=w.label('');w.progress_box.pack_start(w.progress_label,False,False,0)
 w.progress_bar=Gtk.ProgressBar();w.progress_bar.set_show_text(True);w.progress_bar.set_pulse_step(.08);w.progress_box.pack_start(w.progress_bar,False,False,0);w.progress_detail=w.label('');w.progress_detail.set_line_wrap(False);w.progress_detail.set_ellipsize(Pango.EllipsizeMode.MIDDLE);w.progress_box.pack_start(w.progress_detail,False,False,0);w.outer.pack_end(w.progress_box,False,False,0)
 w.show_all()
 w.sound_custom_box.set_no_show_all(True);w.sound_preserve.set_no_show_all(True)
 def source_controls(combo):
  custom=combo.get_active_id()=='custom';w.sound_custom_box.set_visible(custom);w.sound_preserve.set_visible(custom)
 w.sound_pack.connect('changed',source_controls);source_controls(w.sound_pack)
 if w.mode=='setup':
  for key in ('backups','remove','health','addons'):w.stack.get_child_by_name(key).hide()
 w.stack.set_visible_child_name('welcome');w.rebuilding=False
 from .gui_media import update_gate
 update_gate(w)
 from .gui_status import refresh as refresh_media
 for combo in (w.icon_mode,w.sound_pack):combo.connect('changed',lambda *_:refresh_media(w))
 for field in (w.icons,w.sound,w.sound_source):field.connect('changed',lambda *_:refresh_media(w))
 refresh_media(w)
