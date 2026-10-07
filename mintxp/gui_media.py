"""Welcome-page media decision; settings and installer share one selection."""
from .gui import Gtk, GLib


def update_gate(w):
    ready = w.mode != 'setup' or w.media_ready
    for child in w.install_controls:
        child.set_sensitive(ready)
    for button in (w.install_all_button,w.install_selected_button):button.set_sensitive(ready)
    w.install_gate.set_above_child(not ready)
    # Other configuration pages must not bypass the required welcome decision.
    for key in ('options','sound_options','media_page','addons'):
        child = w.stack.get_child_by_name(key)
        if child:child.set_sensitive(ready)
    if not w.media_ready:
        text = w.t('media_pending' if w.media_counts else 'media_required')
    elif not w.media_counts:
        text = w.t('media_current_ready' if w.mode=='settings' else 'media_builtin_ready')
    else:
        text = w.t('media_ready_summary').format(icons=w.media_counts.get('icons',0),sounds=w.media_counts.get('sounds',0))
    w.media_summary.set_text(text)
    w.media_continue.set_visible(bool(w.media_counts) and not w.media_ready)


def bundled(w):
    if w.busy:return
    w.icon_mode.set_active_id('bundled')
    w.sound_pack.set_active_id('keep')
    w.checks['icons'].set_active(True);w.checks['sounds'].set_active(False)
    w.media_counts={};w.media_ready=True
    update_gate(w)


def finish(w):
    if w.busy:return
    w.media_ready=True
    update_gate(w)


def choose(w, folder=False):
    if w.busy:return
    # A short licence notice is always visible on Welcome; this is an acknowledgement,
    # not a claim that the importer grants additional rights.
    if not (w.media_rights.get_active() or w.iso_rights.get_active()):return
    dlg=Gtk.FileChooserDialog(title=w.t('media_choose'),transient_for=w,
                             action=Gtk.FileChooserAction.SELECT_FOLDER if folder else Gtk.FileChooserAction.OPEN)
    dlg.add_buttons(w.t('cancel'),Gtk.ResponseType.CANCEL,w.t('choose'),Gtk.ResponseType.OK)
    if not folder:
        dlg.add_button(w.t('media_folder'),Gtk.ResponseType.APPLY)
        from .sound_sources import ARCHIVES
        filt=Gtk.FileFilter();filt.set_name('ISO / ZIP / RAR / 7z / TAR')
        for suffix in ('.iso',*ARCHIVES):filt.add_pattern('*'+suffix);filt.add_pattern('*'+suffix.upper())
        dlg.add_filter(filt)
    response=dlg.run();path=dlg.get_filename() if response==Gtk.ResponseType.OK else None;dlg.destroy()
    if response==Gtk.ResponseType.APPLY:choose(w,True);return
    if path:
        from .media_import import import_media
        w.run_job(lambda:import_media(w.engine,path),complete=w.media_imported)


def imported(w, result):
    # Successful import only: do not alter selection on cancellation or decode error.
    sound_choices={}
    prepared=result.get('sound_plan')
    if prepared and prepared['report'].get('ambiguous'):
        sound_choices=w.resolve_sounds(prepared['report']['ambiguous'],prepared)
        if sound_choices is None:return
    if w.icons.get_text():w.media_counts.setdefault('icons',1)
    if w.sound_source.get_text() and w.sound_pack.get_active_id()=='custom':w.media_counts.setdefault('sounds',1)
    if result.get('icon_path'):
        w.icons.set_text(result['icon_path']);w.icon_mode.set_active_id('imported');w.checks['icons'].set_active(True)
        w.media_counts['icons']=result['icons']
    if result.get('sound_path'):
        w.set_sound_source(result['sound_path']);w.sound_choices=sound_choices;w.sound_pack.set_active_id('custom');w.checks['sounds'].set_active(True)
        w.media_counts['sounds']=result['sounds']
    if w.engine.read_current().get('installed'):
        w.media_ready=True;update_gate(w)
        w.iso_status.set_text(w.t('media_selection_only')+'\n'+w.t('media_ready_summary').format(icons=w.media_counts.get('icons',0),sounds=w.media_counts.get('sounds',0)))
        w.status.set_text(w.t('media_selection_only'));return
    if all(w.media_counts.get(k) for k in ('icons','sounds')):
        w.media_ready=True;update_gate(w);return
    w.media_ready=False;update_gate(w)
    missing='sounds' if not w.media_counts.get('sounds') else 'icons'
    dlg=Gtk.MessageDialog(transient_for=w,modal=True,message_type=Gtk.MessageType.QUESTION,
                         buttons=Gtk.ButtonsType.NONE,text=w.t('media_detected'))
    dlg.format_secondary_text(w.t('media_ask_'+missing))
    dlg.add_button(w.t('media_no'),Gtk.ResponseType.NO)
    dlg.add_button(w.t('media_yes'),Gtk.ResponseType.YES)
    dlg.show_all();response=dlg.run();dlg.destroy()
    if response==Gtk.ResponseType.YES:
        # Leave the lower controls locked until the second choice succeeds or
        # the user explicitly continues with the included missing component.
        GLib.idle_add(lambda:(choose(w),False)[1])
    elif response==Gtk.ResponseType.NO:finish(w)
