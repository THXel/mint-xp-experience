"""GTK3 first-run assistant and installed theme manager."""
import json, subprocess, threading, datetime
from pathlib import Path
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk,Gio,GLib,Pango
from .engine import Engine,Conflict
from .components import COMPONENTS,DEFAULTS,ROOT,plan,preflight,refresh
from .i18n import LANGUAGES,Translator
from .addons import Addons,CATALOG
from .lifecycle import status,uninstall_all,export_diagnostic,prepare_rescue

class Window(Gtk.ApplicationWindow):
    def __init__(self,app,engine=None,mode=None):
        super().__init__(application=app,title='Mint XP Experience')
        self.set_wmclass('mint-xp-experience','MintXPExperience');self.set_icon_name('preferences-desktop-theme')
        self.engine=engine or Engine();self.options=dict(DEFAULTS,**self.engine.read_current().get('options',{}))
        if self.options.get('sound_source')==':builtin:':self.options.update(sounds=False,sound_source=':keep:')
        self.options.setdefault('icon_mode','imported' if self.options.get('icon_import') else 'bundled')
        langfile=self.engine.read('preferences.json',{})
        self.options['language']=langfile.get('language',self.options['language']);self.t=Translator(self.options['language'])
        self.mode='settings' if self.engine.read_current().get('installed') else 'setup'
        self.rebuilding=False;self.language_pending=False
        self.media_ready=self.mode!='setup';self.media_counts={}
        self.busy=False;self.connect('delete-event',lambda *_:self.busy)
        display=Gdk.Display.get_default();area=(display.get_primary_monitor() or display.get_monitor(0)).get_workarea()
        self.set_default_size(min(1080,area.width-30),min(720,area.height-40));self.set_position(Gtk.WindowPosition.CENTER)
        css=Gtk.CssProvider();css.load_from_path(str(Path(__file__).with_name('installer.css')))
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.get_style_context().add_class('mintxp');self.build()
    def label(self,text,cls=None):
        w=Gtk.Label(label=text,xalign=0);w.set_line_wrap(True);w.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        w.set_max_width_chars(65)
        if cls:w.get_style_context().add_class(cls)
        return w
    def button(self,box,key,fn):
        b=Gtk.Button(label=self.t(key));b.get_child().set_line_wrap(True);b.get_child().set_max_width_chars(30);b.connect('clicked',lambda *_:fn());box.pack_start(b,False,False,0);return b
    def page(self,key):
        scroll=Gtk.ScrolledWindow();scroll.set_overlay_scrolling(False);scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);box.get_style_context().add_class('page');scroll.add(box)
        container=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);container.pack_start(scroll,True,True,0)
        self.page_containers[key]=container
        title=self.t('overview') if key=='welcome' and self.mode=='settings' else self.t(key)
        self.stack.add_titled(container,key,title);return box
    def build(self):
        from .gui_layout import build
        build(self)
    def choose_media(self,folder=False):
        from .gui_media import choose
        choose(self,folder)
    def media_imported(self,result):
        from .gui_media import imported
        imported(self,result)
    def use_bundled_media(self):
        from .gui_media import bundled
        bundled(self)
    def finish_media(self):
        from .gui_media import finish
        finish(self)
    def choose_iso(self):
        if self.busy or not self.iso_rights.get_active():return
        dlg=Gtk.FileChooserDialog(title=self.t('iso_choose'),transient_for=self,action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons(self.t('cancel'),Gtk.ResponseType.CANCEL,self.t('choose'),Gtk.ResponseType.OK)
        filt=Gtk.FileFilter();filt.set_name('Windows XP ISO');filt.add_pattern('*.iso');filt.add_pattern('*.ISO');dlg.add_filter(filt)
        selected=dlg.get_filename() if dlg.run()==Gtk.ResponseType.OK else None;dlg.destroy()
        if selected:
            from .iso_import import import_iso
            self.run_job(lambda:import_iso(self.engine,selected),complete=self.iso_imported)
    def iso_imported(self,result):
        self.media_imported(result)
        self.icons.set_text(result['icon_path']);self.set_sound_source(result['sound_path']);self.sound_pack.set_active_id('custom')
        self.checks['icons'].set_active(True);self.checks['sounds'].set_active(True)
        self.iso_status.set_text(self.t('iso_ready').format(sounds=result['sounds'],icons=result['icons']))
        self.status.set_text(self.t('iso_selected'))
    def preview_selected_sound(self):
        from . import sounds
        options=self.gather();event=self.sound_event.get_active_id()
        def audition():
            result=sounds.imported_plan(self.engine,options,reimport=True);report=result['report'];rel=report['aliases'].get(event)
            if not rel:raise ValueError(self.t('sound_missing'))
            import tempfile
            with tempfile.TemporaryDirectory(prefix='mintxp-preview-') as td:
                p=Path(rel) if report.get('pack')=='mint' else Path(td)/'preview.wav'
                if report.get('pack')!='mint':p.write_bytes(self.engine.data(result['files'][sounds.PREFIX+'originals/'+rel]))
                player=subprocess.run(['canberra-gtk-play','--file',str(p),'--property=canberra.enable=1'],capture_output=True,text=True)
                if player.returncode:raise ValueError(player.stderr.strip() or 'Sound playback failed')
            return self.t('done')
        self.run_job(audition,quiet=True)
    def switch_mode(self,mode):
        if self.busy:return
        if mode=='settings' and not self.engine.read_current().get('installed'):return
        self.gather();self.mode=mode;self.build()
    def require_media(self):
        if self.busy:return False
        if self.mode=='setup' and not self.media_ready:
            self.stack.set_visible_child_name('welcome')
            self.media_builtin_button.grab_focus()
            self.message(self.t('media_choose'),self.t('media_required'))
            return False
        return True
    def apply_media(self,icons_only=False):
        if not self.require_media():return
        from .media_settings import apply
        options=self.gather()
        if icons_only:options.update(sounds=False,sound_source=':keep:')
        from .gui_status import summary
        description=summary(self,True,not icons_only)+'\n\n'+self.t('icons_apply_notice' if icons_only else 'media_apply_notice')
        if not self.message(self.t('confirm'),description,True):return
        self.run_job(lambda:apply(self.engine,options),refresh_after=True,complete=lambda r:(self.status.set_text(self.t('done')),self.iso_status.set_text(self.t('done'))))
    def install_all(self):
        if not self.require_media():return
        for check in (*self.checks.values(),*self.addon_checks.values(),*self.system_checks.values()):check.set_active(True)
        self.checks['sounds'].set_active(self.sound_pack.get_active_id()!='keep')
        self.review()
    def refresh_addons(self):
        for child in self.addon_rows.get_children():child.destroy()
        self.addon_buttons={}
        try:
            entries=Addons(self.engine).status()
            grid=Gtk.Grid(column_spacing=10,row_spacing=10,column_homogeneous=True);self.addon_rows.pack_start(grid,False,False,0)
            for position,(key,entry) in enumerate(entries.items()):
                frame=Gtk.Frame();box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=7);box.set_border_width(12);frame.add(box)
                box.pack_start(self.label(entry['name']+' — '+self.t('addon_'+entry['state'])),False,False,0)
                box.pack_start(self.label(entry['license']),False,False,0)
                link=Gtk.LinkButton.new_with_label(entry['url'],self.t('addon_source'));box.pack_start(link,False,False,0)
                if entry.get('detail'):box.pack_start(self.label(entry['detail']),False,False,0)
                row=Gtk.Box(spacing=8);box.pack_start(row,False,False,0)
                state=entry['state']
                if state=='absent':
                    self.addon_buttons[(key,'install')]=self.button(row,'addon_install',lambda key=key:self.addon_action(key,'install'))
                if state in ('managed','external'):
                    self.addon_buttons[(key,'launch')]=self.button(row,'addon_open',lambda key=key:self.addon_action(key,'launch'))
                if state=='managed':
                    self.addon_buttons[(key,'remove')]=self.button(row,'addon_remove',lambda key=key:self.addon_action(key,'remove'))
                    self.button(row,'verify',lambda key=key:self.addon_action(key,'verify'))
                if state=='interrupted':self.button(row,'recover',lambda key=key:self.addon_action(key,'recover'))
                grid.attach(frame,position%2,position//2,1,1)
        except Exception as error:self.addon_rows.pack_start(self.label(self.t('error')+': '+str(error)),False,False,0)
        self.addon_rows.show_all()
    def addon_action(self,key,action):
        addons=Addons(self.engine)
        try:
            if action=='launch':addons.launch(key);return
            if action in ('install','remove','recover'):
                notice=self.t('addon_remove_notice') if action=='remove' else self.t('addon_license_notice') if action=='install' else self.t('addon_recover_notice')
                if action=='install' and key=='space-cadet':notice+='\n\n'+self.t('addon_pinball_notice')
                if not self.message(self.t('confirm'),CATALOG[key]['name']+'\n\n'+notice+'\n\n'+CATALOG[key]['license']+'\n'+CATALOG[key]['url'],True):return
            self.run_job(lambda:getattr(addons,action)(key))
        except Exception as error:self.message(self.t('error'),str(error))
    def apply_options(self,options):
        from .install_flow import install
        return install(self.engine,options)
    def show_completion(self,result):
        if self.engine.read_current().get('installed') and self.mode!='settings':
            self.mode='settings';self.media_ready=True;self.build()
        names=lambda keys:', '.join(self.t(k) for k in keys) or '—'
        text=self.t('completion_enabled')+':\n'+names(result['enabled'])+'\n\n'+self.t('completion_disabled')+':\n'+names(result['disabled'])
        text+='\n\n'+self.t('completion_backup')+':\n'+result['backup_path']+'\n\n'+self.t('completion_transaction')+': '+result['transaction']
        text+='\n\n'+self.t('completion_relogin' if result['relogin_recommended'] else 'completion_no_relogin')+'\n\n'+self.t('completion_optional')
        if result.get('steps'):
            text+='\n\n'+self.t('install_extras')+':\n'+'\n'.join(('✓ ' if step['ok'] else '⚠ ')+step['name']+': '+step['detail'] for step in result['steps'])
        if result.get('partial'):
            text+='\n\n'+self.t('install_partial');self.status.set_text(self.t('install_partial'))
        self.completion_text.set_text(text);self.stack.set_visible_child_name('completion')

    def preview_welcome(self):
        o=self.gather();cmd=['/usr/bin/python3','-B',str(ROOT/'assets/session/welcome.py'),'--preview','--duration',str(o['welcome_duration']),'--language',self.t.language,'--monitors',o['welcome_monitors']]
        if not o['welcome_fade']:cmd.append('--no-fade')
        subprocess.Popen(cmd)
    def refresh_status(self):
        for child in self.health_rows.get_children():child.destroy()
        try:
            report=status(self.engine)
            if (self.engine.home/'.local/share/xp-explorer').exists() and not self.options.get('explorer'):
                self.health_rows.pack_start(self.label(self.t('legacy_notice'),'notice'),False,False,0)
            grid=Gtk.Grid(column_spacing=20,row_spacing=8,column_homogeneous=True);self.health_rows.pack_start(grid,False,False,0)
            for i,entry in enumerate(report['components']):
                grid.attach(self.label(self.t(entry['component'])+' — '+self.t('state_'+entry['status'])),i%2,i//2,1,1)
            def date(value):
                return datetime.datetime.fromisoformat(value).astimezone().strftime('%Y-%m-%d %H:%M %Z') if value else self.t('unknown')
            summary=self.t('last_backup')+': '+date(report['last_backup_at'])+'\n'+self.t('original_backup')+': '+date(report['baseline_at'])
            if report['pending']:summary+='\n'+self.t('pending_notice')
            if report['changed_file_count'] or report['changed_setting_count']:summary+='\n'+self.t('conflict_notice')
            self.health_rows.pack_start(self.label(summary,'notice'),False,False,0)
        except Exception as error:self.health_rows.pack_start(self.label(self.t('error')+': '+str(error)),False,False,0)
        self.health_rows.show_all()
    def export_report(self):
        dlg=Gtk.FileChooserDialog(title=self.t('diagnostic'),transient_for=self,action=Gtk.FileChooserAction.SAVE);dlg.add_buttons(self.t('cancel'),Gtk.ResponseType.CANCEL,self.t('diagnostic'),Gtk.ResponseType.OK);dlg.set_current_name('mint-xp-diagnostic.json')
        if dlg.run()==Gtk.ResponseType.OK:
            target=dlg.get_filename();dlg.destroy()
            try:
                export_diagnostic(self.engine,target,(ROOT/'VERSION').read_text().strip());self.message(self.t('done'),self.t('diagnostic_notice')+'\n'+target)
            except Exception as error:self.message(self.t('error'),str(error))
        else:dlg.destroy()
    def rescue_help(self):
        path=prepare_rescue(self.engine,ROOT)
        self.message(self.t('rescue_help'),self.t('rescue_notice')+'\n\nmint-xp-rescue check\nmint-xp-rescue recover --yes\nmint-xp-rescue uninstall --yes\n\n'+str(path))
    def gather(self):
        self.options.update({k:b.get_active() for k,b in self.checks.items()})
        self.options.update({k:b.get_active() for k,b in self.system_checks.items()})
        self.options['addon_selection']=[k for k,b in self.addon_checks.items() if b.get_active()]
        self.options['prefer_local_icons']=False;self.options['icon_mode']=self.icon_mode.get_active_id()
        self.options.update({k:(s.get_value() if k=='welcome_duration' else s.get_value_as_int()) for k,s in self.spins.items()});self.options['sound_theme']=self.sound.get_text();self.options['sound_source']={'keep':':keep:','mint':':mint:'}.get(self.sound_pack.get_active_id(),self.sound_source.get_text());self.options['sound_choices']=dict(self.sound_choices);self.options['sound_preserve']=self.sound_preserve.get_active();self.options['icon_import']=self.icons.get_text()
        self.options.update(welcome_fade=self.fade.get_active(),welcome_monitors=self.monitors.get_active_id())
        if self.options['sound_source']==':keep:':self.options['sounds']=False
        return dict(self.options)
    def change_language(self,combo):
        if self.rebuilding or self.language_pending or self.busy:return
        lang=combo.get_active_id()
        if not lang or lang==self.options['language']:return
        self.gather();page=self.stack.get_visible_child_name();self.options['language']=lang
        preferences=self.engine.read('preferences.json',{});preferences['language']=lang
        self.engine.save('preferences.json',preferences)
        self.language_pending=True
        # Destroying the emitting combo synchronously inside ::changed can crash GTK.
        # Rebuild only after GTK finishes dispatching its selection event.
        def rebuild():
            try:
                self.t=Translator(lang);self.build()
                child=self.stack.get_child_by_name(page)
                if child and child.get_visible():self.stack.set_visible_child_name(page)
            finally:self.language_pending=False
            return False
        GLib.idle_add(rebuild)
    def sound_result(self,report):
        return self.t('sound_summary').format(files=report['unique_files'],aliases=len(report['aliases']),events=sum(e['mapped'] for e in report['cinnamon'].values()))
    def set_sound_source(self,path):
        self.sound_choices={};self.sound_source.set_text(path)
    def choose_sounds(self,archive=False):
        key='sound_choose_archive' if archive else 'sound_choose'
        dlg=Gtk.FileChooserDialog(title=self.t(key),transient_for=self,action=Gtk.FileChooserAction.OPEN if archive else Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_buttons(self.t('cancel'),Gtk.ResponseType.CANCEL,self.t('choose'),Gtk.ResponseType.OK)
        if archive:
            from .sound_sources import ARCHIVES
            filt=Gtk.FileFilter();filt.set_name('ZIP, RAR, 7z, TAR')
            for suffix in ARCHIVES:filt.add_pattern('*'+suffix);filt.add_pattern('*'+suffix.upper())
            dlg.add_filter(filt)
        if dlg.run()==Gtk.ResponseType.OK:self.set_sound_source(dlg.get_filename());self.sound_pack.set_active_id('custom')
        dlg.destroy()
    def resolve_sounds(self,ambiguous,prepared=None):
        dlg=Gtk.Dialog(title=self.t('sound_ambiguous'),transient_for=self,modal=True);dlg.set_default_size(720,420)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);box.set_border_width(14)
        box.pack_start(self.label(self.t('sound_ambiguous_notice')),False,False,0)
        from .audition import Audition
        audition=Audition();timers=[];preview_buttons=[]
        preview_status=self.label('')
        def play_candidate(combo):
            from .sounds import PREFIX
            try:
                name=combo.get_active_id();descriptor=prepared['files'][PREFIX+'originals/'+name]
                audition.play(self.engine.data(descriptor));preview_status.set_text(self.t('sound_listening'))
            except Exception as error:preview_status.set_text(self.t('error')+': '+str(error));return
            def poll():
                result=audition.poll()
                if result is None:return True
                preview_status.set_text(self.t('ready') if result==0 else self.t('sound_preview_failed'));return False
            for timer in timers:
                if GLib.MainContext.default().find_source_by_id(timer):GLib.source_remove(timer)
            timers[:]=[GLib.timeout_add(100,poll)]
        combos={}
        for key,candidates in sorted(ambiguous.items()):
            box.pack_start(self.label(key.split(':',1)[1]),False,False,0);combo=Gtk.ComboBoxText();combo.append('',self.t('sound_select_file'))
            for name in candidates:combo.append(name,name)
            combo.set_active_id('')
            for cell in combo.get_cells():cell.set_property('ellipsize',Pango.EllipsizeMode.MIDDLE);cell.set_property('width-chars',50)
            combos[key]=combo;box.pack_start(combo,False,False,0)
            if prepared is not None:
                button=Gtk.Button(label=self.t('sound_listen'));button.set_sensitive(False);button.connect('clicked',lambda _button,c=combo:play_candidate(c));combo.connect('changed',lambda c,b=button:b.set_sensitive(bool(c.get_active_id())));box.pack_start(button,False,False,0);preview_buttons.append(button)
        box.pack_start(preview_status,False,False,0)
        scroll=Gtk.ScrolledWindow();scroll.set_overlay_scrolling(False);scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);scroll.add(box);dlg.get_content_area().pack_start(scroll,True,True,0)
        dlg.add_button(self.t('cancel'),Gtk.ResponseType.CANCEL);ok=dlg.add_button(self.t('sound_use_choices'),Gtk.ResponseType.OK);ok.set_sensitive(False)
        for combo in combos.values():combo.connect('changed',lambda *_:ok.set_sensitive(all(c.get_active_id() for c in combos.values())))
        dlg.show_all();response=dlg.run();selected={k:c.get_active_id() for k,c in combos.items()} if response==Gtk.ResponseType.OK else None;audition.stop()
        for timer in timers:
            if GLib.MainContext.default().find_source_by_id(timer):GLib.source_remove(timer)
        dlg.destroy();return selected
    def sound_description(self,report):
        text=self.sound_result(report)
        for name,event in report['cinnamon'].items():
            text+='\n'+name+': '+(event['file']+(' ['+self.t('sound_off')+']' if event['enabled'] is False else '') if event['mapped'] else self.t('sound_missing'))
        if report['missing_aliases']:text+='\n\n'+self.t('sound_missing')+': '+', '.join(report['missing_aliases'])
        if report.get('unassigned_files'):text+='\n\n'+self.t('sound_unused')+':\n'+'\n'.join(report['unassigned_files'])
        return text
    def sound_preview(self,result,options,activate=False):
        from . import sounds
        report=result['report']
        if report.get('ambiguous'):
            selected=self.resolve_sounds(report['ambiguous'],result)
            if selected is None:self.status.set_text(self.t('ready'));return
            self.sound_choices.update(selected);options['sound_choices']=dict(self.sound_choices)
            self.run_job(lambda:sounds.imported_plan(self.engine,options,reimport=True),complete=lambda result:self.sound_preview(result,options,activate));return
        if not activate:self.message(self.t('sound_options'),self.sound_description(report));return
        try:sounds.ensure_ready(report)
        except Exception as error:self.message(self.t('error'),str(error));return
        if not self.message(self.t('confirm'),self.sound_description(report)+'\n\n'+self.t('sound_backup_notice'),True):return
        self.checks['sounds'].set_active(True)
        if not self.engine.read_current().get('installed'):self.review();return
        self.run_job(lambda:self.sound_result(sounds.apply_import(self.engine,options,prepared=result)),complete=lambda text:self.status.set_text(self.t('done')+' · '+text))
    def sound_action(self,action):
        from . import sounds
        try:
            o=self.gather()
            if action in ('verify','test','remove'):
                current=self.engine.read_current()
                if not current.get('options',{}).get('sounds') or not current.get('files',{}).get(sounds.PREFIX+'mapping.json'):
                    self.message(self.t('sound_options'),self.t('sound_import_required'));return
            if action in ('inspect','apply'):
                self.run_job(lambda:sounds.imported_plan(self.engine,o,reimport=True),complete=lambda result:self.sound_preview(result,o,action=='apply'))
            elif action=='verify':self.run_job(lambda:sounds.verify(self.engine),complete=lambda report:self.message(self.t('sound_options'),self.sound_description(report)))
            elif action=='test':self.run_job(lambda:sounds.play_test(self.engine,self.sound_event.get_active_id()),quiet=True)
            elif self.message(self.t('confirm'),self.t('sound_undo_notice'),True):
                self.checks['sounds'].set_active(False);self.run_job(lambda:sounds.remove_import(self.engine))
        except Exception as error:self.message(self.t('error'),str(error))
    def choose_icons(self):
        dlg=Gtk.FileChooserDialog(title=self.t('choose'),transient_for=self,action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_buttons(self.t('cancel'),Gtk.ResponseType.CANCEL,self.t('choose'),Gtk.ResponseType.OK)
        if dlg.run()==Gtk.ResponseType.OK:self.icons.set_text(dlg.get_filename());self.icon_mode.set_active_id('imported')
        dlg.destroy()
    def message(self,title,text,confirm=False):
        dlg=Gtk.Dialog(title=title,transient_for=self,modal=True);dlg.set_default_size(650,360)
        scroll=Gtk.ScrolledWindow();scroll.set_overlay_scrolling(False);scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);scroll.set_min_content_height(260)
        box=self.label(text);box.set_selectable(True);box.set_margin_start(18);box.set_margin_end(18);scroll.add(box)
        dlg.get_content_area().pack_start(scroll,True,True,0)
        dlg.add_button(self.t('cancel'),Gtk.ResponseType.CANCEL)
        if confirm:dlg.add_button(self.t('apply'),Gtk.ResponseType.OK)
        dlg.show_all();answer=dlg.run();dlg.destroy();return answer==Gtk.ResponseType.OK
    def review(self):
        if not self.require_media():return
        try:
            options=self.gather();preflight(options)
            from .gui_applets import review as review_applets
            if not review_applets(self,options):return
            selected=[self.t(k) for k in COMPONENTS if options[k]]
            for key in options.get('addon_selection',[]):
                selected.append(CATALOG[key]['name']+' — '+CATALOG[key]['license']+'\n'+CATALOG[key]['url'])
            for key in ('boot_install','login_install'):
                if options.get(key):selected.append(self.t(key))
            if options.get('addon_selection'):selected.append(self.t('addon_license_notice'))
            if 'space-cadet' in options.get('addon_selection',[]):selected.append(self.t('addon_pinball_notice'))
            if options.get('boot_install') or options.get('login_install'):selected.append(self.t('system_install_notice'))
            description=self.t('preview_notice')+'\n\n'+'\n'.join('• '+s for s in selected)+'\n\n'+self.t('baseline_notice')+'\n'+str(self.engine.state)
            if self.message(self.t('confirm'),description,True):self.run_job(lambda:self.apply_options(options),refresh_after=True,complete=self.show_completion)
        except Exception as error:self.message(self.t('error'),str(error))
    def verify(self):
        if self.engine.read('pending.json'):raise Conflict('An interrupted operation needs recovery.')
        base=self.engine.read('baseline.json')
        if base:self.engine.verify_objects(base)
        errors=self.engine.check(self.engine.read_current(),allow_preferences=True)
        if errors:raise Conflict('\n'.join(errors))
        return self.t('done')
    def restore(self):
        name=self.backups.get_active_id()
        if not name:return
        try:data=self.engine.read('snapshots/'+name+'.json',{})
        except (ValueError,OSError) as error:self.message(self.t('error'),str(error));return
        components=', '.join(self.t(k) for k in COMPONENTS if data.get('options',{}).get(k)) or '—'
        text=self.backups.get_active_text()+'\n\n'+self.t('components')+': '+components+'\n\n'+self.t('restore_scope')
        if self.message(self.t('confirm'),text,True):self.run_job(lambda:self.engine.restore(name),True,complete=lambda _:self.reload_settings())
    def remove_install(self):
        from .removal import complete
        accessories=self.remove_addons.get_active()
        text=self.t('remove_notice')+'\n\n'+self.t('conflict_notice')
        if accessories:text+='\n\n'+self.t('remove_owned_addons')
        if self.message(self.t('confirm'),text,True):self.run_job(lambda:complete(self.engine,accessories),True)
    def reload_backups(self):
        self.backups.remove_all()
        from .gui_status import backup_label
        for p in sorted((self.engine.state/'snapshots').glob('*.json'),reverse=True):self.backups.append(p.stem,backup_label(self,p))
        self.backups.set_active(0)
    def reload_settings(self):
        self.options=dict(DEFAULTS,**self.engine.read_current().get('options',{}));self.options.setdefault('icon_mode','imported' if self.options.get('icon_import') else 'bundled')
        self.options['language']=self.t.language;self.build()
    def run_job(self,fn,refresh_after=False,complete=None,quiet=False):
        if self.busy:return
        self.busy=True;self.stack.set_sensitive(False);self.status.set_text(self.t('busy'))
        self.progress_box.set_no_show_all(False);self.progress_box.show_all();self.progress_bar.set_fraction(0)
        # One mailbox avoids thousands of queued GTK callbacks during large installs.
        self.job_progress=('prepare',0,None,'');previous_observer=self.engine.progress
        self.engine.progress=lambda phase,done,total,detail:setattr(self,'job_progress',(phase,done,total,detail))
        def paint_progress():
            phase,done,total,detail=self.job_progress
            if phase=='overall':
                self.progress_label.set_text(self.t('progress_overall'))
                part=detail;sub=self.t('progress_'+part['phase'])
                if part.get('total') and part['phase']=='download':sub+=': '+GLib.format_size(part['done'])+' / '+GLib.format_size(part['total'])
                self.progress_detail.set_text(sub+(' — '+part['detail'] if part['detail'] else ''))
                self.progress_bar.set_fraction(max(0,min(1,done/total)))
                self.progress_bar.set_text(str(round(100*done/total))+'% · '+str(done)+' / '+str(total)+' '+self.t('progress_steps'))
                return self.busy
            self.progress_label.set_text(self.t('progress_'+phase));self.progress_detail.set_text(str(detail))
            if total:
                self.progress_bar.set_fraction(max(0,min(1,done/total)))
                self.progress_bar.set_text((GLib.format_size(done)+' / '+GLib.format_size(total)) if phase=='download' else str(done)+' / '+str(total))
            else:
                self.progress_bar.pulse();self.progress_bar.set_text(self.t('busy'))
            return self.busy
        paint_progress();progress_timer=GLib.timeout_add(120,paint_progress)
        def worker():
            try:
                result=fn()
                if refresh_after:refresh()
                GLib.idle_add(finish,None,result)
            except Exception as error:GLib.idle_add(finish,str(error),None)
        def finish(error,result):
            GLib.source_remove(progress_timer);self.engine.progress=previous_observer
            self.busy=False;self.stack.set_sensitive(True);self.reload_backups();self.refresh_status();self.refresh_addons()
            from .gui_media import update_gate
            update_gate(self)
            # Keep one final 100% only for a completely successful installation.
            if not error and isinstance(result,dict) and result.get('progress') and not result.get('partial'):
                paint_progress();self.progress_detail.set_text(self.t('done'))
            else:
                self.progress_box.hide();self.progress_box.set_no_show_all(True)
                self.progress_bar.set_fraction(0);self.progress_bar.set_text('')
                self.progress_label.set_text('');self.progress_detail.set_text('')
            self.status.set_text(self.t('error') if error else self.t('done'))
            if error:
                explanation=self.t('conflict_help')+'\n\n' if 'protected' in error.lower() or 'conflict' in error.lower() else ''
                self.message(self.t('error'),explanation+error)
            elif complete:
                try:complete(result)
                except Exception as failure:self.message(self.t('error'),str(failure))
            elif not quiet:self.message(self.t('done'),self.t('restart_notice') if refresh_after else str(result))
            if not error:
                from .gui_status import refresh as refresh_media
                refresh_media(self)
            if not error and refresh_after and not self.engine.read_current().get('installed'):self.get_application().quit()
            return False
        threading.Thread(target=worker,daemon=False).start()

class Application(Gtk.Application):
    def __init__(self,mode=None):
        super().__init__(application_id='org.mintxp.Experience');self.mode=mode
    def do_activate(self):
        win=self.get_active_window()
        if win:win.present()
        else:Window(self,mode=self.mode).present()
def run(mode=None):return Application(mode).run([])
