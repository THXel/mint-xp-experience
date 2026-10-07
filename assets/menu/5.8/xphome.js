const XP = require('./xplocale');
// Mint XP Experience: local XP integration modifications, 2026-09-30 to 2026-10-04.
// Original upstream notices and licences remain applicable; see docs/SOURCES.md.
// XP-style landing page over the existing Cinnamenu application/category engine.
const St = imports.gi.St;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Gtk = imports.gi.Gtk;
const Clutter = imports.gi.Clutter;
const Cinnamon = imports.gi.Cinnamon;
const CMenu = imports.gi.CMenu;
const Util = imports.misc.util;
const Main = imports.ui.main;
const Pango = imports.gi.Pango;
const Tooltips = imports.ui.tooltips;
const {PanelLoc} = imports.ui.panel;

class XPHome {
    constructor(display) {
        this.display = display;
        this.dialogPolish=global._xpDialogPolish||(global._xpDialogPolish=new XPDialogPolish());this.dialogPolish.refs++;
        this.app = display.appThis;
        this.flyouts = new XPFlyouts(this);
        this.homeVisible = true;
        this.actor = new St.BoxLayout({style_class: 'xp-start-body'});
        this.left = new St.BoxLayout({vertical: true, style_class: 'xp-start-left', x_expand: true});
        this.right = new St.BoxLayout({vertical: true, style_class: 'xp-start-right'});
        this.appScroll = new St.ScrollView({style_class: 'xp-start-app-scroll', x_expand: true, y_expand: true});
        this.appScroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC);
        this.appBox = new St.BoxLayout({vertical: true});
        this.appScroll.add_actor(this.appBox);
        this.left.add_child(this.appScroll);
        this.programButton = this.button(XP.t('Alle Programme'), 'go-next', () => this.flyouts.programs(), null, false);
        this.programButton.add_style_class_name('xp-all-programs');
        this.left.add_child(this.programButton);
        this.actor.add_child(this.left);
        // Scroll the places column when the monitor cannot fit every entry.
        // Its minimum height must not push All Programs beneath the search box.
        this.rightScroll = new St.ScrollView({style_class:'xp-start-right-scroll'});
        this.rightScroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC);
        this.rightScroll.add_actor(this.right);
        this.actor.add_child(this.rightScroll);
        this.back = this.button(XP.t('Zurück zur Startansicht'), 'go-previous', () => this.home(), null, false);
        this.back.add_style_class_name('xp-start-back');
        this.back.hide();
        this.footer = new St.BoxLayout({style_class: 'xp-start-footer', x_expand: true});
        this.footer.add_child(new St.Widget({x_expand: true}));
        this.lock = this.button(XP.t('Sperren'), 'system-lock-screen', () => Util.spawn(['cinnamon-screensaver-command', '--lock']));
        this.logout = this.button(XP.t('Abmelden …'), 'system-log-out', () => this.app.sessionManager.LogoutRemote(0));
        this.shutdown = this.button(XP.t('Ausschalten …'), 'system-shutdown', () => this.app.sessionManager.ShutdownRemote());
        this.footer.add_child(this.lock);this.footer.add_child(this.logout);this.footer.add_child(this.shutdown);
        this.buildPlaces();
        // Newly started desktop apps also count when launched from the taskbar.
        this.display.displaySignals.connect(Cinnamon.AppSystem.get_default(), 'app-state-changed', (system, app) => {
            const info = app.get_app_info();
            if (app.get_state() === Cinnamon.AppState.RUNNING && info && info.should_show())
                this.app.recentApps.add(app.get_id());
        });
    }
    button(title, icon, action, subtitle = null, close = true, application = null, recent = false) {
        const button = new St.Button({style_class: 'xp-start-link', can_focus: true, x_expand: true, accessible_name: title});
        button.set_fill(true,false);button.set_alignment(St.Align.START,St.Align.MIDDLE);
        button.xpTitle = title;button.xpAppId=application ? (application.id||application.get_id()) : null;button.xpRecent=recent;
        this.display.displaySignals.connect(button,'key-press-event', (actor,event) => {const result=this.key(event);return result===null ? Clutter.EVENT_PROPAGATE : result;});
        if (subtitle) button.add_style_class_name('xp-start-primary');
        const row = new St.BoxLayout({style_class: 'xp-start-link-content', x_expand: true, x_align: Clutter.ActorAlign.FILL});
        row.add_child(icon instanceof St.Icon ? icon : new St.Icon({icon_name: icon || 'application-x-executable', icon_size: subtitle ? 36 : 28, icon_type: St.IconType.FULLCOLOR}));
        const words = new St.BoxLayout({vertical: true, y_align: Clutter.ActorAlign.CENTER, x_expand: true});
        const label = new St.Label({text: title, style_class: 'xp-start-title',x_expand:true});
        label.clutter_text.set_ellipsize(Pango.EllipsizeMode.END);
        words.add_child(label);button.xpLabel=label;button.xpTooltip=new Tooltips.Tooltip(button,title);
        if (subtitle) words.add_child(new St.Label({text: subtitle, style_class: 'xp-start-subtitle'}));
        row.add_child(words);button.set_child(row);
        this.display.displaySignals.connect(button, 'clicked', () => {
            if (close) {this.flyouts.close(false);this.app.menu.close();}
            try { action(); } catch (e) { Main.notifyError(XP.t('Startmenü'), e.message); }
        });
        if (application) this.display.displaySignals.connect(button, 'button-press-event', (actor, event) => {
            if (event.get_button() !== 3) return Clutter.EVENT_PROPAGATE;
            this.flyouts.programContext(button.xpAppId,button,button.xpRecent);
            return Clutter.EVENT_STOP;
        });
        return button;
    }
    separator(box) { box.add_child(new St.Widget({style_class: 'xp-start-separator'})); }
    openURI(uri) {
        const app = Gio.DesktopAppInfo.new('org.mintxp.Explorer.desktop');
        if (app) app.launch_uris([uri], global.create_app_launch_context());
        else Gio.app_info_launch_default_for_uri(uri, global.create_app_launch_context());
    }
    launchDesktop(id) {
        const app = Gio.DesktopAppInfo.new(id);
        if (!app) throw new Error(XP.t('Programm nicht gefunden: ') + id);
        app.launch([], global.create_app_launch_context());
        this.app.recentApps.add(id);
    }
    buildPlaces() {
        const add = (title, icon, action) => this.right.add_child(this.button(title, icon, action));
        const folder = (title, icon, kind) => {
            const path = GLib.get_user_special_dir(kind);
            if (path) add(title, icon, () => this.openURI(Gio.File.new_for_path(path).get_uri()));
        };
        add(XP.t('Eigene Dateien'), 'user-home', () => this.openURI(Gio.File.new_for_path(GLib.get_home_dir()).get_uri()));
        folder(XP.t('Eigene Dokumente'), 'folder-documents', GLib.UserDirectory.DIRECTORY_DOCUMENTS);
        folder(XP.t('Eigene Bilder'), 'folder-pictures', GLib.UserDirectory.DIRECTORY_PICTURES);
        folder(XP.t('Eigene Musik'), 'folder-music', GLib.UserDirectory.DIRECTORY_MUSIC);
        add(XP.t('Arbeitsplatz'), 'computer', () => this.openURI('computer:///'));
        add(XP.t('Netzwerkumgebung'), 'network-workgroup', () => this.openURI('network:///'));
        this.separator(this.right);
        add(XP.t('Systemsteuerung'), 'preferences-system', () => Util.spawn([GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'xp-control-panel'])]));
        add(XP.t('Software'), 'system-software-install', () => Util.spawn(['mintinstall']));
        this.recentButton=this.button(XP.t('Zuletzt verwendet  ▸'), 'document-open-recent', () => this.flyouts.documents(), null, false);
        this.right.add_child(this.recentButton);
        this.separator(this.right);
        this.right.add_child(this.button(XP.t('Suchen …'), 'edit-find', () => {
            this.programs();global.stage.set_key_focus(this.display.searchView.searchEntryText);
        }, null, false));
        add('Terminal', 'org.gnome.Terminal', () => this.launchDesktop('org.gnome.Terminal.desktop'));
        const mintIcon = new St.Icon({gicon: new Gio.FileIcon({file:Gio.File.new_for_path('/usr/share/icons/hicolor/scalable/apps/linuxmint-logo.svg')}),icon_size:28});
        add(XP.t('Systeminformationen'), mintIcon, () => this.launchDesktop('mintreport.desktop'));
    }
    populate() {
        // Disconnect handlers before removing old buttons, so reopening does not leak actors.
        for (const actor of this.appBox.get_children()) {
            this.display.displaySignals.disconnect('clicked', actor);
            this.display.displaySignals.disconnect('button-press-event', actor);
            this.display.displaySignals.disconnect('key-press-event', actor);
        }
        this.appBox.destroy_all_children();
        const seen = new Set();
        const browser = Gio.AppInfo.get_default_for_uri_scheme('https');
        const email = Gio.AppInfo.get_default_for_uri_scheme('mailto');
        for (const [title, app, fallback] of [[XP.t('Internet'), browser, 'web-browser'], [XP.t('E-Mail'), email, 'internet-mail']]) {
            if (!app || seen.has(app.get_id())) continue;
            seen.add(app.get_id());
            const icon = app.get_icon() ? new St.Icon({gicon: app.get_icon(), icon_size: 36, icon_type: St.IconType.FULLCOLOR}) : fallback;
            this.appBox.add_child(this.button(title, icon, () => {app.launch([], global.create_app_launch_context());this.app.recentApps.add(app.get_id());}, app.get_display_name()));
        }
        this.separator(this.appBox);
        this.appBox.add_child(new St.Label({text:XP.t('Zuletzt gestartet'),style_class:'xp-start-subtitle',style:'padding: 3px 8px 5px;'}));
        const recent = this.app.listRecent_apps(20).filter(app => !seen.has(app.id)).slice(0,6);
        for (const app of recent) {
            if (seen.has(app.id)) continue;
            seen.add(app.id);
            const icon = new St.Icon({gicon: app.get_app_info()?.get_icon() || new Gio.ThemedIcon({name:'application-x-executable'}),icon_size:32,icon_type:St.IconType.FULLCOLOR});
            this.appBox.add_child(this.button(app.name, icon, () => {
                this.app.recentApps.add(app.id);app.open_new_window(-1);
            }, null, true, app, true));
        }
        if (!recent.length) this.appBox.add_child(new St.Label({text:XP.t('Noch keine Programme gestartet'),style_class:'xp-start-subtitle',style:'padding: 8px;'}));
    }
    home() {
        if (this.app.menu.isOpen) global.stage.set_key_focus(this.display.searchView.searchEntryText);
        this.flyouts.close(false);
        this.display.searchView.searchEntry.set_text('');
        this.homeVisible = true;this.actor.show();this.display.middlePane.hide();this.back.hide();
        this.display.sidebar.sidebarOuterBox.hide();
        this.display.clearFocusedActors();
        if (this.app.menu.isOpen && Main.animations_enabled) {
            this.display.mainBox.remove_all_transitions();this.display.mainBox.opacity=180;
            this.display.mainBox.ease({opacity:255,duration:140,mode:Clutter.AnimationMode.EASE_OUT_QUAD});
        }
    }
    destroy() {this.flyouts.destroy();this.dialogPolish.release();}
    programs(category = 'all') {
        this.flyouts.close(false);
        global.stage.set_key_focus(this.display.searchView.searchEntryText);
        this.homeVisible = false;this.actor.hide();this.display.middlePane.show();this.back.show();
        this.display.sidebar.sidebarOuterBox.hide();
        this.app.setActiveCategory(category);this.display.updateMenuSize();
    }
    searchChanged(text) {
        if (text.length) this.flyouts.close(false);
        if (text.length && this.homeVisible) {this.homeVisible=false;this.actor.hide();this.display.middlePane.show();this.back.show();}
    }
    key(event) {
        if (!this.homeVisible || this.display.contextMenu.isOpen) return null;
        if (this.flyouts.panels.length && this.flyouts.layer.contains(global.stage.get_key_focus())) return this.flyouts.key(event);
        const key = event.get_key_symbol();
        const focus = global.stage.get_key_focus();
        const buttons = [...this.appBox.get_children(),this.programButton,...this.right.get_children(),this.lock,this.logout,this.shutdown].filter(a => a instanceof St.Button && a.visible);
        const index = buttons.findIndex(b => b === focus || b.contains(focus));
        if(index>=0 && buttons[index].xpAppId && (key===Clutter.KEY_Menu || (key===Clutter.KEY_F10 && (event.get_state()&Clutter.ModifierType.SHIFT_MASK)))) {
            this.flyouts.programContext(buttons[index].xpAppId,buttons[index],buttons[index].xpRecent);return Clutter.EVENT_STOP;
        }
        if(index>=0 && [Clutter.KEY_Home,Clutter.KEY_End,Clutter.KEY_Page_Up,Clutter.KEY_Page_Down].includes(key)) {
            const target=key===Clutter.KEY_Home?0:key===Clutter.KEY_End?buttons.length-1:Math.max(0,Math.min(buttons.length-1,index+(key===Clutter.KEY_Page_Up?-6:6)));
            buttons[target].grab_key_focus();return Clutter.EVENT_STOP;
        }
        if (key===Clutter.KEY_Right && (focus===this.programButton || focus===this.recentButton)) {focus.emit('clicked',1);return Clutter.EVENT_STOP;}
        if (key===Clutter.KEY_Escape && this.flyouts.panels.length) {this.flyouts.close();return Clutter.EVENT_STOP;}
        if ([Clutter.KEY_Tab,Clutter.KEY_ISO_Left_Tab,Clutter.KEY_Down,Clutter.KEY_Up,Clutter.KEY_Left,Clutter.KEY_Right].includes(key)) {
            const backwards = [Clutter.KEY_ISO_Left_Tab,Clutter.KEY_Up,Clutter.KEY_Left].includes(key) || (key===Clutter.KEY_Tab && (event.get_state() & Clutter.ModifierType.SHIFT_MASK));
            const next = index < 0 ? (backwards ? buttons.length-1 : 0) : (index+(backwards?-1:1)+buttons.length)%buttons.length;
            buttons[next].grab_key_focus();return Clutter.EVENT_STOP;
        }
        if (index>=0 && [Clutter.KEY_Return,Clutter.KEY_KP_Enter,Clutter.KEY_space].includes(key)) {buttons[index].emit('clicked',1);return Clutter.EVENT_STOP;}
        if (key===Clutter.KEY_Escape) {this.app.menu.close();return Clutter.EVENT_STOP;}
        // Typing always enters the retained search field.
        const character = event.get_key_unicode();
        if (index>=0 && character && character.codePointAt(0)>=32 && !(event.get_state() & (Clutter.ModifierType.CONTROL_MASK | Clutter.ModifierType.MOD1_MASK))) {const text=this.display.searchView.searchEntryText;global.stage.set_key_focus(text);text.set_text(character);text.set_cursor_position(-1);return Clutter.EVENT_STOP;}
        return null;
    }
}
// All actors stay inside the start menu, so its existing modal grab also covers
// the side panels. No additional desktop-wide grabs or launch commands are used.
class XPFlyouts {
    constructor(home) {
        this.home=home;this.app=home.app;this.panels=[];this.timer=0;
        this.layer=new St.Widget({width:0,height:0,layout_manager:new Clutter.FixedLayout(),reactive:false});
    }
    cancelTimer() {if(this.timer){GLib.source_remove(this.timer);this.timer=0;}}
    bounds() {
        const m=Main.layoutManager.findMonitorForActor(this.app.menu.actor);
        const b={x:m.x+4,y:m.y+4,right:m.x+m.width-4,bottom:m.y+m.height-4};
        for(const p of Main.panelManager.getPanelsInMonitor(m.index)) {
            if(!p.getIsVisible())continue;
            if(p.panelPosition===PanelLoc.top)b.y+=p.actor.height;
            if(p.panelPosition===PanelLoc.bottom)b.bottom-=p.actor.height;
            if(p.panelPosition===PanelLoc.left)b.x+=p.actor.width;
            if(p.panelPosition===PanelLoc.right)b.right-=p.actor.width;
        }
        return b;
    }
    closeFrom(level,restoreFocus=true) {
        this.cancelTimer();
        const first=this.panels[level];
        if(first && this.app.menu.isOpen) {
            const f=global.stage.get_key_focus();
            if(restoreFocus || this.panels.slice(level).some(p=>f && p.actor.contains(f)))
                global.stage.set_key_focus(restoreFocus ? first.source : this.home.display.searchView.searchEntryText);
        }
        while(this.panels.length>level) {
            const p=this.panels.pop();p.source.remove_style_class_name('xp-open');p.actor.destroy();
        }
        this.contextActive=this.panels.some(p=>p.context);
    }
    close(restoreFocus=true) {this.closeFrom(0,restoreFocus);this.kind=null;this.contextActive=false;}
    destroy() {this.close(false);if(this.propertiesDialog)this.propertiesDialog.destroy();this.layer.destroy();}
    position(panel,level,measure=true) {
        const scale=global.ui_scale,b=this.bounds();
        const rootProgram=level===0 && this.kind==='programs' && !panel.context;
        const anchor=level ? this.panels[level-1].actor : ((rootProgram||panel.context) ? panel.source : this.app.menu.actor);
        const [ax]=anchor.get_transformed_position(),[aw]=anchor.get_transformed_size();
        const [,sy]=panel.source.get_transformed_position(),[,sh]=panel.source.get_transformed_size();
        const width=Math.min(panel.width*scale,b.right-b.x);
        let maxHeight=Math.min(b.bottom-b.y,560*scale);
        if(rootProgram)maxHeight=Math.min(maxHeight,sy+sh-this.home.actor.get_transformed_position()[1]);
        const naturalHeight=measure ? Math.ceil(panel.actor.get_preferred_height(width)[1]) : panel.actor.height;
        const height=measure ? Math.min(naturalHeight,Math.max(100*scale,maxHeight)) : panel.actor.height;
        let left=level>0 && this.panels[level-1].opensLeft;
        let x=left ? ax-width+1 : ax+aw-1;
        if(x+width>b.right){left=true;x=ax-width+1;}
        else if(x<b.x){left=false;x=ax+aw-1;}
        x=Math.max(b.x,Math.min(x,b.right-width));panel.opensLeft=left;
        const y=Math.max(b.y,Math.min(rootProgram ? sy+sh-height : sy,b.bottom-height));
        const [ox,oy]=this.layer.get_transformed_position();
        if(Math.abs(panel.actor.x-(x-ox))>.5 || Math.abs(panel.actor.y-(y-oy))>.5)panel.actor.set_position(x-ox,y-oy);
        if(measure)panel.actor.set_size(width,height);
    }
    show(title,entries,source,level=0,width=320,context=false) {
        this.closeFrom(level,false);
        const actor=new St.BoxLayout({vertical:true,style_class:'xp-flyout',reactive:true});
        if(this.kind!=='programs'||context)actor.add_child(new St.Label({text:title,style_class:'xp-flyout-heading'}));
        const scroll=new St.ScrollView({x_expand:true,y_expand:true,style_class:'xp-flyout-scroll'});
        scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);
        const body=new St.BoxLayout({vertical:true,x_expand:true});scroll.add_actor(body);actor.add_child(scroll);
        const panel={actor,scroll,body,source,rows:[],width,context};this.panels.push(panel);this.layer.add_child(actor);
        const list=entries.length ? entries : [{title:XP.t('Keine Einträge vorhanden'),disabled:true,icon:'dialog-information'}];
        for(const entry of list) {
            const row=new St.Button({style_class:'xp-flyout-row',can_focus:!entry.disabled,reactive:!entry.disabled,x_expand:true,accessible_name:entry.title});
            row.set_fill(true,false);row.set_alignment(St.Align.START,St.Align.MIDDLE);
            const content=new St.BoxLayout({style_class:'xp-flyout-row-content',x_expand:true});
            const icon=entry.gicon ? new St.Icon({gicon:entry.gicon,icon_size:22}) : new St.Icon({icon_name:entry.icon||'application-x-executable',icon_size:22,icon_type:St.IconType.FULLCOLOR});
            content.add_child(icon);
            const label=new St.Label({text:entry.title,x_expand:true,y_align:Clutter.ActorAlign.CENTER});
            label.clutter_text.set_ellipsize(Pango.EllipsizeMode.END);content.add_child(label);
            if(entry.children)content.add_child(new St.Label({text:'▸',style_class:'xp-flyout-arrow',y_align:Clutter.ActorAlign.CENTER}));
            row.set_child(content);row.xpTitle=entry.title;row.xpEntry=entry;row.xpLabel=label;row.xpLevel=level;
            const activate=()=>{
                this.cancelTimer();
                if(entry.children){this.branch(row,true);return;}
                this.close(false);if(!entry.keepOpen)this.app.menu.close();
                try{entry.action();}catch(e){Main.notifyError(XP.t('Startmenü'),e.message);}
            };
            row.connect('clicked',activate);
            row.connect('key-press-event',(actor,event)=>this.key(event));
            row.connect('enter-event',(actor,event)=>this.hover(row,event));
            row.connect('motion-event',(actor,event)=>{
                const child=this.panels[level+1];
                if(!this.contextActive && (!child || child.source===row)) {
                    const [x,y]=event.get_coords();panel.intentOrigin={x,y,time:Date.now()};
                }
                return Clutter.EVENT_PROPAGATE;
            });
            row.connect('leave-event',()=>{this.cancelTimer();return Clutter.EVENT_PROPAGATE;});
            if(entry.appId)row.connect('button-press-event',(actor,event)=>{
                if(event.get_button()!==3)return Clutter.EVENT_PROPAGATE;
                this.programContext(entry.appId,row,false);return Clutter.EVENT_STOP;
            });
            row.xpTooltip=new Tooltips.Tooltip(row,entry.detail||entry.title);
            const showTip=row.xpTooltip.show.bind(row.xpTooltip);
            row.xpTooltip.show=()=>{if(entry.detail || label.clutter_text.get_layout().is_ellipsized())showTip();};
            row.xpTooltip._tooltip.clutter_text.set_line_wrap(true);
            row.xpTooltip._tooltip.clutter_text.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR);
            row.xpTooltip._tooltip.set_style('max-width: 520px;');
            if(entry.disabled)row.add_style_pseudo_class('insensitive');
            panel.rows.push(row);body.add_child(row);
        }
        actor.connect('notify::allocation',()=>{if(this.panels[level]===panel)this.position(panel,level,false);});
        source.add_style_class_name('xp-open');this.position(panel,level);
        if(Main.animations_enabled){actor.opacity=130;actor.ease({opacity:255,duration:130,mode:Clutter.AnimationMode.EASE_OUT_QUAD});}
        return panel;
    }
    branch(row,focus) {
        if(!this.app.menu.isOpen || this.contextActive)return;
        const existing=this.panels[row.xpLevel+1];
        let p=existing;
        if(!existing || existing.source!==row)p=this.show(row.xpTitle,row.xpEntry.children(),row,row.xpLevel+1,340);
        if(focus)this.focus(p.rows.find(r=>!r.xpEntry.disabled));
    }
    focus(row) {
        if(!row)return;row.grab_key_focus();
        const p=this.panels[row.xpLevel],a=p.scroll.vscroll.adjustment;
        const box=row.get_allocation_box();
        if(box.y1<a.value)a.value=box.y1;
        else if(box.y2>a.value+a.page_size)a.value=Math.max(0,box.y2-a.page_size);
    }
    key(event) {
        this.cancelTimer();
        const key=event.get_key_symbol(),f=global.stage.get_key_focus();
        const p=this.panels.find(p=>p.rows.some(r=>r===f||r.contains(f)));
        if(!p)return Clutter.EVENT_PROPAGATE;
        const rows=p.rows.filter(r=>!r.xpEntry.disabled),i=rows.findIndex(r=>r===f||r.contains(f)),row=rows[i];
        if(row.xpEntry.appId && (key===Clutter.KEY_Menu || (key===Clutter.KEY_F10 && (event.get_state()&Clutter.ModifierType.SHIFT_MASK)))) {
            this.programContext(row.xpEntry.appId,row,false);return Clutter.EVENT_STOP;
        }
        if([Clutter.KEY_Home,Clutter.KEY_End,Clutter.KEY_Page_Up,Clutter.KEY_Page_Down].includes(key)) {
            const step=Math.max(1,Math.floor(p.scroll.vscroll.adjustment.page_size/Math.max(1,row.height))-1);
            const target=key===Clutter.KEY_Home?0:key===Clutter.KEY_End?rows.length-1:Math.max(0,Math.min(rows.length-1,i+(key===Clutter.KEY_Page_Up?-step:step)));
            this.closeFrom(row.xpLevel+1,false);this.focus(rows[target]);return Clutter.EVENT_STOP;
        }
        if([Clutter.KEY_Up,Clutter.KEY_Down,Clutter.KEY_Tab,Clutter.KEY_ISO_Left_Tab].includes(key)) {
            const back=key===Clutter.KEY_Up||key===Clutter.KEY_ISO_Left_Tab||(key===Clutter.KEY_Tab&&(event.get_state()&Clutter.ModifierType.SHIFT_MASK));
            this.closeFrom(row.xpLevel+1,false);this.focus(rows[(i+(back?-1:1)+rows.length)%rows.length]);return Clutter.EVENT_STOP;
        }
        if(key===Clutter.KEY_Left||key===Clutter.KEY_Escape){this.closeFrom(row.xpLevel,true);if(!this.panels.length)this.kind=null;return Clutter.EVENT_STOP;}
        if(key===Clutter.KEY_Right){if(row.xpEntry.children)this.branch(row,true);return Clutter.EVENT_STOP;}
        if([Clutter.KEY_Return,Clutter.KEY_KP_Enter,Clutter.KEY_space].includes(key)){row.emit('clicked',1);return Clutter.EVENT_STOP;}
        const char=event.get_key_unicode();
        if(char && char.codePointAt(0)>=32 && !(event.get_state()&(Clutter.ModifierType.CONTROL_MASK|Clutter.ModifierType.MOD1_MASK))) {
            this.close(false);const text=this.home.display.searchView.searchEntryText;global.stage.set_key_focus(text);text.set_text(char);text.set_cursor_position(-1);return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }
    towardChild(row,point) {
        const panel=this.panels[row.xpLevel],child=this.panels[row.xpLevel+1],origin=panel.intentOrigin;
        if(!child || child.context || child.source===row || !origin || Date.now()-origin.time>500)return false;
        const [cx,cy]=child.actor.get_transformed_position(),[cw,ch]=child.actor.get_transformed_size();
        const edge=child.opensLeft ? cx+cw : cx;
        if(child.opensLeft ? point.x>=origin.x : point.x<=origin.x)return false;
        const t=(point.x-origin.x)/(edge-origin.x);
        if(t<0 || t>1)return false;
        const top=origin.y+t*(cy-12-origin.y),bottom=origin.y+t*(cy+ch+12-origin.y);
        return point.y>=Math.min(top,bottom) && point.y<=Math.max(top,bottom);
    }
    hover(row,event) {
        this.cancelTimer();
        if(this.contextActive) {if(this.panels[row.xpLevel]?.context)row.grab_key_focus();return Clutter.EVENT_PROPAGATE;}
        if(this.home.display.contextMenu.isOpen)return Clutter.EVENT_PROPAGATE;
        const [x,y]=event.get_coords(),protect=this.towardChild(row,{x,y});
        this.hoverDelay=protect?450:(row.xpEntry.children?180:100);
        if(!protect)row.grab_key_focus();
        this.timer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,this.hoverDelay,()=>{
            this.timer=0;
            if(!this.app.menu.isOpen || this.contextActive || !row.has_pointer)return GLib.SOURCE_REMOVE;
            row.grab_key_focus();
            if(row.xpEntry.children)this.branch(row,false);
            else this.closeFrom(row.xpLevel+1,false);
            return GLib.SOURCE_REMOVE;
        });
        return Clutter.EVENT_PROPAGATE;
    }
    panelLauncher() {
        const defs=imports.ui.appletManager.definitions.filter(d=>d.uuid==='grouped-window-list@cinnamon.org' && d.applet?.pinnedFavorites);
        return (defs.find(d=>d.applet.panel===this.app.panel)||defs[0])?.applet || null;
    }
    programContext(id,source,recent=false) {
        this.cancelTimer();
        const app=Cinnamon.AppSystem.get_default().lookup_app(id);if(!app)return;
        const level=source.xpLevel===undefined?0:source.xpLevel+1;
        if(level===0){this.close(false);this.kind='context';}
        const launcher=this.panelLauncher(),fav=this.app.appFavorites.isFavorite(id);
        const pinned=launcher?.pinnedFavorites._favorites.some(f=>f.id===id);
        const entries=[{title:XP.t('Öffnen'),icon:'media-playback-start',action:()=>{app.open_new_window(-1);this.app.recentApps.add(id);}}];
        if(launcher)entries.push({title:pinned?'Von Taskleiste lösen':'An Taskleiste anheften',icon:'list-add',action:()=>{
            const target=this.panelLauncher();if(!target)throw new Error('Taskleiste nicht verfügbar');
            const current=target.pinnedFavorites._favorites.some(f=>f.id===id);
            if(pinned && current)target.pinnedFavorites.removeFavorite(id);
            else if(!pinned && !current)target.acceptNewLauncher(id);
        }});
        entries.push({title:fav?XP.t('Aus Favoriten entfernen'):XP.t('Zu Favoriten hinzufügen'),icon:'starred',action:()=>{
            if(fav)this.app.appFavorites.removeFavorite(id);else this.app.appFavorites.addFavorite(id);
        }});
        if(recent)entries.push({title:XP.t('Aus zuletzt gestartet entfernen'),icon:'edit-clear',action:()=>{
            this.app.settings.recentApps=this.app.settings.recentApps.filter(other=>other!==id);
        }});
        entries.push({title:XP.t('Eigenschaften'),icon:'document-properties',action:()=>this.properties(app)});
        const p=this.show(app.name || app.get_name(),entries,source,level,340,true);this.contextActive=true;
        this.focus(p.rows[0]);
    }
    properties(app) {
        const info=app.get_app_info();
        const text=[info.get_description()||'', 'Programm: '+info.get_display_name(),
            'Startbefehl: '+(info.get_commandline()||'—'), 'Programmdatei: '+(info.get_filename()||'—')].filter(Boolean).join('\n\n');
        const dialog=new imports.ui.modalDialog.ModalDialog();
        const content=new imports.ui.dialog.MessageDialogContent({title:'Eigenschaften – '+(app.name || app.get_name()),description:text});
        content.set_style('max-width: 720px;');dialog.contentLayout.add_child(content);
        dialog.setButtons([{label:XP.t('Schließen'),action:()=>dialog.destroy(),key:Clutter.KEY_Escape,default:true}]);
        dialog.connect('destroy',()=>{if(this.propertiesDialog===dialog)this.propertiesDialog=null;});
        this.propertiesDialog=dialog;dialog.open();
    }
    applicationEntry(app,id=null) {
        const appId=id||app.id||app.get_id();
        return {title:app.name || app.get_name(),appId,gicon:app.get_app_info()?.get_icon(),
            action:()=>{app.open_new_window(-1);this.app.recentApps.add(appId);}};
    }
    directoryEntries(dir,ancestors=new Set()) {
        const id=dir.get_menu_id();
        if(dir.get_is_nodisplay() || ancestors.has(id) || ancestors.size>=16)return [];
        const path=new Set(ancestors);path.add(id);
        const entries=[],seen=new Set(),iter=dir.iter();let type;
        while((type=iter.next())!==CMenu.TreeItemType.INVALID) {
            if(type===CMenu.TreeItemType.DIRECTORY) {
                const child=iter.get_directory(),items=this.directoryEntries(child,path);
                if(items.length)entries.push({title:child.get_menu_id()==='wine-Programs'?'Programme':child.get_name(),
                    icon:'folder',directoryId:child.get_menu_id(),children:()=>items});
            } else if(type===CMenu.TreeItemType.ENTRY) {
                const entry=iter.get_entry(),appId=entry.get_desktop_file_id();
                if (entry.get_is_excluded() || entry.get_is_nodisplay_recurse()) continue;
                const app=Cinnamon.AppSystem.get_default().lookup_app(appId);
                if(app && !app.get_nodisplay() && !seen.has(appId)) {
                    seen.add(appId);entries.push(this.applicationEntry(app,appId));
                }
            }
        }
        // Some Cinnamon menu trees retain parent entries after a merged
        // submenu allocates the same apps. Show each app in its child group.
        const nestedIds=new Set();
        const collect=items=>{for(const item of items){if(item.appId)nestedIds.add(item.appId);if(item.children)collect(item.children());}};
        for(const entry of entries)if(entry.children)collect(entry.children());
        return entries.filter(entry=>entry.children||!nestedIds.has(entry.appId)).sort((a,b)=>Number(!!b.children)-Number(!!a.children)||a.title.localeCompare(b.title));
    }
    appEntries(category) {
        if(!['all','favorite_apps'].includes(category)) {
            const dir=this.app.apps.getDirs().find(d=>d.get_menu_id()===category);
            if(dir)return this.directoryEntries(dir);
        }
        const apps=category==='favorite_apps' ? this.app.listFavoriteApps() : this.app.apps.listApplications(category)||[];
        return apps.slice().sort((a,b)=>a.name.localeCompare(b.name)).map(app=>this.applicationEntry(app));
    }
    programs() {
        if(this.kind==='programs' && this.panels.length){this.close();return;}
        this.close(false);this.kind='programs';
        const categories=this.home.display.categoriesView.buttons.filter(b=>b.id==='all'||b.id==='favorite_apps'||(!['recents','places','favorite_files'].includes(b.id)&&!b.id.startsWith('/')&&!b.id.startsWith('emoji:')));
        const entries=categories.map(b=>({title:b.id==='all'?'Alle Programme (A–Z)':b.category_name,icon:b.id==='favorite_apps'?'starred':'folder',children:()=>this.appEntries(b.id)}));
        entries.push({title:XP.t('Kategorienübersicht …'),icon:'view-list-symbolic',keepOpen:true,action:()=>this.home.programs()});
        const p=this.show(XP.t('Alle Programme'),entries,this.home.programButton,0,270);this.focus(p.rows[0]);
    }
    documentEntries() {
        if(!this.app.recentsEnabled)return [];
        return this.app.recentManagerDefault.get_items().filter(info=>{
            if(info.get_private_hint() || info.get_mime_type()==='inode/directory')return false;
            if(/^(computer|trash|network):/.test(info.get_uri()))return false;
            const file=Gio.File.new_for_uri(info.get_uri()),path=file.get_path();
            return !path || (GLib.file_test(path,GLib.FileTest.EXISTS) && !GLib.file_test(path,GLib.FileTest.IS_DIR));
        }).sort((a,b)=>b.get_modified()-a.get_modified()).slice(0,15).map(info=>({title:info.get_display_name(),detail:info.get_display_name()+'\n'+info.get_uri_display(),gicon:info.get_gicon(),action:()=>Gio.app_info_launch_default_for_uri(info.get_uri(),global.create_app_launch_context())}));
    }
    documents() {
        if(this.kind==='documents' && this.panels.length){this.close();return;}
        this.close(false);this.kind='documents';
        const entries=this.documentEntries();
        if(!entries.length)entries.push({title:this.app.recentsEnabled?'Noch keine letzten Dokumente':XP.t('Dokumentverlauf ist ausgeschaltet'),icon:'document-open-recent',disabled:true});
        const p=this.show(XP.t('Zuletzt verwendete Dokumente'),entries,this.home.recentButton,0,390);this.focus(p.rows.find(r=>!r.xpEntry.disabled));
    }
}

// Native confirmation/inhibitor handling remains authoritative; decoration never powers off.
class XPDialogPolish {
    constructor() {
        this.refs=0;this.pending=new Map();
        this.proto=imports.ui.endSessionDialog.EndSessionDialog.prototype;
        this.hadAdd=Object.prototype.hasOwnProperty.call(this.proto,'addButton');
        this.oldAdd=this.proto.addButton;this.oldCaps=this.proto._getCapabilities;
        this.oldInhibitors=this.proto._presentInhibitorInfo;this.transition=null;this.transitionTimer=0;this.active=true;
        const self=this;
        this.add=function(info){
            const spec=self.describe(info.label);const translated=Object.assign({},info,{label:spec.label});
            const button=self.oldAdd.call(this,translated);button._xpAction=spec;
            button.accessible_name=spec.label;
            if(!self.pending.has(this)){
                const id=GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE,()=>{self.pending.delete(this);if(this.state!==3)self.styleDialog(this);return GLib.SOURCE_REMOVE;});
                self.pending.set(this,id);
                this.connect('destroy',()=>{const timer=self.pending.get(this);if(timer){GLib.source_remove(timer);self.pending.delete(this);}});
            }
            return button;
        };
        this.caps=function(result,error){
            // Wrap before Cinnamon binds these callbacks, including the countdown default.
            if(!error && this._dialogProxy && !this._dialogProxy._xpDecorated){
                const proxy=this._dialogProxy;proxy._xpDecorated=true;
                for(const [method,mode] of [['ShutdownRemote','shutdown'],['RestartRemote','reboot'],['LogoutRemote','logout']]){
                    const native=proxy[method];proxy[method]=function(...args){
                        proxy._xpMode=mode;self.startTransition(mode);
                        if(!args.length)args=[(result,error)=>{if(error)self.stopTransition();}];
                        try{return native.apply(this,args);}catch(e){self.stopTransition();throw e;}
                    };
                }
                const cancel=proxy.CancelRemote;proxy.CancelRemote=function(...args){self.stopTransition();return cancel.apply(this,args);};
                for(const method of ['SuspendRemote','HibernateRemote','SwitchUserRemote']){
                    const native=proxy[method];if(native)proxy[method]=function(...args){proxy._xpMode=null;self.stopTransition();return native.apply(this,args);};
                }
                const ignore=proxy.IgnoreInhibitorsRemote;
                proxy.IgnoreInhibitorsRemote=function(...args){if(proxy._xpMode)self.startTransition(proxy._xpMode);return ignore.apply(this,args);};
            }
            self.oldCaps.call(this,result,error);if(!error)self.styleDialog(this);
        };
        this.inhibitors=function(...args){self.stopTransition();return self.oldInhibitors.apply(this,args);};
        this.proto._presentInhibitorInfo=this.inhibitors;
        this.proto.addButton=this.add;this.proto._getCapabilities=this.caps;
    }
    stopTransition() {
        if(this.transitionTimer){GLib.source_remove(this.transitionTimer);this.transitionTimer=0;}
        if(this.transition){try{this.transition.force_exit();}catch(e){}this.transition=null;}
    }
    startTransition(mode) {
        this.stopTransition();
        if(!this.active)return;
        const path=GLib.build_filenamev([GLib.get_home_dir(),'.local','share','mint-xp-experience','assets','session','shutdown.py']);
        if(!GLib.file_test(path,GLib.FileTest.IS_REGULAR))return;
        // Give native inhibitor/authorization dialogs time to appear before decorating.
        this.transitionTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,350,()=>{
            this.transitionTimer=0;
            try{
                const child=Gio.Subprocess.new(['/usr/bin/python3','-B',path,'--mode',mode],Gio.SubprocessFlags.STDOUT_SILENCE|Gio.SubprocessFlags.STDERR_SILENCE);
                this.transition=child;child.wait_async(null,()=>{if(this.transition===child)this.transition=null;});
            }catch(e){global.logWarning('Mint XP shutdown decoration: '+e.message);}
            return GLib.SOURCE_REMOVE;
        });
    }
    describe(text) {
        const entries=[['Cancel',XP.t('Abbrechen'),null],['Suspend',XP.t('Bereitschaft'),'system-suspend'],['Hibernate',XP.t('Ruhezustand'),'system-suspend'],['Restart',XP.t('Neu starten'),'gnome-session-reboot'],['Shut Down',XP.t('Ausschalten'),'system-shutdown'],['Log Out',XP.t('Abmelden'),'system-log-out'],['Switch User',XP.t('Benutzer wechseln'),'system-users'],['Ignore and continue',XP.t('Trotzdem fortfahren'),'dialog-warning']];
        const e=entries.find(e=>text===e[0]||text===_(e[0])||text===e[1]);
        return e?{label:e[1],icon:e[2],cancel:e[0]==='Cancel'}:{label:text,icon:null,cancel:false};
    }
    styleDialog(dialog) {
        const box=dialog.buttonLayout,buttons=box.get_children();if(!buttons.length)return;
        dialog.dialogLayout._dialog.add_style_class_name('xp-session-actions');
        if(dialog._applicationsSection)dialog._applicationsSection.title=XP.t('Einige Programme sind noch beschäftigt oder enthalten ungespeicherte Änderungen.');
        const content=dialog._messageDialogContent;
        if(content){
            content.title=[XP.t('Computer neu starten'),XP.t('Computer ausschalten'),XP.t('Abmelden')][dialog._mode]||content.title;
            if(!content.description||!content.description.trim())content.description=XP.t('Bitte wähle eine Aktion.');
        }
        if(dialog._xpButtons && dialog._xpButtons.length===buttons.length && dialog._xpButtons.every(b=>buttons.includes(b)))return;
        dialog._xpButtons=buttons.slice();
        const focused=global.stage.get_key_focus();
        const restoreFocus=focused && buttons.some(b=>b===focused||b.contains(focused));
        const layout=new Clutter.GridLayout({column_spacing:14,row_spacing:18});
        for(const button of buttons)box.remove_child(button);
        box.set_layout_manager(layout);
        const priority={'system-suspend':0,'system-shutdown':1,'gnome-session-reboot':2};
        const actions=buttons.filter(b=>!b._xpAction?.cancel).sort((a,b)=>(priority[a._xpAction?.icon]??3)-(priority[b._xpAction?.icon]??3)),cancel=buttons.find(b=>b._xpAction?.cancel);
        actions.forEach((button,index)=>{
            const spec=button._xpAction||this.describe(button.label);
            if(!button._xpStyled){
                const row=new St.BoxLayout({vertical:true,style_class:'xp-session-action-content',x_align:Clutter.ActorAlign.CENTER,y_align:Clutter.ActorAlign.CENTER});
                if(spec.icon){
                    const names=spec.icon==='gnome-session-reboot'?[spec.icon,'system-reboot','view-refresh']:[spec.icon];
                    const tiles={'system-suspend':'standby','system-shutdown':'power','gnome-session-reboot':'restart'};
                    const tile=tiles[spec.icon];
                    const path=tile?GLib.build_filenamev([GLib.get_home_dir(),'.local','share','cinnamon','applets','mintxp-menu@mintxp','5.8','session-icons',tile+'.svg']):null;
                    const gicon=path&&GLib.file_test(path,GLib.FileTest.EXISTS)?new Gio.FileIcon({file:Gio.File.new_for_path(path)}):new Gio.ThemedIcon({names});
                    row.add_child(new St.Icon({gicon,icon_size:40,icon_type:St.IconType.FULLCOLOR,style_class:'xp-session-action-icon'}));
                }
                row.add_child(new St.Label({text:spec.label,x_align:Clutter.ActorAlign.CENTER}));button.set_child(row);button._xpStyled=true;
                button.add_style_class_name('xp-session-action');
            }
            button.x_expand=true;button.y_expand=true;box.add_child(button);layout.attach(button,index,0,1,1);
        });
        if(cancel){cancel.x_expand=false;cancel.set_alignment(St.Align.MIDDLE,St.Align.MIDDLE);cancel.add_style_class_name('xp-session-cancel');box.add_child(cancel);layout.attach(cancel,Math.max(0,actions.length-1),1,1,1);}
        if(restoreFocus)focused.grab_key_focus();
    }
    release() {
        if(--this.refs>0)return;
        this.active=false;this.stopTransition();
        if(this.proto._presentInhibitorInfo===this.inhibitors)this.proto._presentInhibitorInfo=this.oldInhibitors;
        for(const id of this.pending.values())GLib.source_remove(id);this.pending.clear();
        if(this.proto.addButton===this.add){if(this.hadAdd)this.proto.addButton=this.oldAdd;else delete this.proto.addButton;}
        if(this.proto._getCapabilities===this.caps)this.proto._getCapabilities=this.oldCaps;
        if(global._xpDialogPolish===this)delete global._xpDialogPolish;
    }
}

module.exports = {XPHome};
