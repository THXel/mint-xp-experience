// Mint XP Experience — collapsible notification area. GPL-3.0-or-later.
const Applet=imports.ui.applet,St=imports.gi.St,Clutter=imports.gi.Clutter;
const Gio=imports.gi.Gio,GLib=imports.gi.GLib,ByteArray=imports.byteArray,Pango=imports.gi.Pango;
const Main=imports.ui.main,Manager=imports.ui.appletManager,Popup=imports.ui.popupMenu;
const Settings=imports.ui.settings,DND=imports.ui.dnd,Tooltips=imports.ui.tooltips;
const Policy=require('./logic'),{t}=require('./strings');
const {TrayPointer}=require('./interaction');
const {IdleCollapse}=require('./idle');
const Meta=imports.gi.Meta;
const UUID='mintxp-tray@mintxp';

// Collapse geometry, not the source actor's visible property. Client visibility
// changes keep working (e.g. printers, inactive reports, notification indicators).
class FoldedActor {
 constructor(actor){
  this.actor=actor;this.folded=false;this.saved=null;this.generation=0;
 }
 remember(){const a=this.actor;return {min:a.min_width,minSet:a.min_width_set,natural:a.natural_width,naturalSet:a.natural_width_set,opacity:a.opacity,expand:a.x_expand,clip:a.clip_to_allocation,focus:a.can_focus};}
 restoreProperties(){
  const a=this.actor,s=this.saved;if(!s)return;
  a.min_width=s.min;a.natural_width=s.natural;a.min_width_set=s.minSet;a.natural_width_set=s.naturalSet;
  a.opacity=s.opacity;a.x_expand=s.expand;a.clip_to_allocation=s.clip;a.can_focus=s.focus;
 }
 set(fold,animate=true){
  if(fold===this.folded)return;const a=this.actor;const generation=++this.generation;
  a.remove_transition('width');a.remove_transition('opacity');
  if(fold){
   if(!this.saved)this.saved=this.remember();this.folded=true;
   a.clip_to_allocation=true;a.x_expand=false;a.can_focus=false;
   if(animate&&a.visible)a.ease({width:0,opacity:0,duration:150,mode:Clutter.AnimationMode.EASE_OUT_QUAD});
   else {a.width=0;a.opacity=0;}
  }else{
   this.folded=false;this.restoreProperties();const target=a.get_preferred_width(-1)[1],opacity=this.saved?this.saved.opacity:255;
   if(animate&&a.visible){a.width=0;a.opacity=0;a.clip_to_allocation=true;a.ease({width:target,opacity,duration:170,mode:Clutter.AnimationMode.EASE_OUT_QUAD,onComplete:()=>{if(this.generation===generation){this.restoreProperties();this.saved=null;}}});}
   else {this.restoreProperties();this.saved=null;}
  }
 }
 restore(){this.generation++;const a=this.actor;a.remove_transition('width');a.remove_transition('opacity');this.restoreProperties();this.saved=null;this.folded=false;}
}

class XPTray extends Applet.Applet {
 constructor(metadata,orientation,panelHeight,instanceId){
  super(orientation,panelHeight,instanceId);this.setAllowedLayout(Applet.AllowedLayout.HORIZONTAL);
  this.actor.remove_style_class_name('applet-box');this.actor.add_style_class_name('xp-tray-toggle');this.actor.can_focus=true;
  this.chevron=new St.Icon({icon_size:20,icon_type:St.IconType.FULLCOLOR,style_class:'xp-tray-chevron',y_align:Clutter.ActorAlign.CENTER});this.chevronPath=metadata.path;this.chevronState='';this.actor.connect('notify::hover',()=>this.updateChevron());this.actor.connect('key-focus-in',()=>this.updateChevron());this.actor.connect('key-focus-out',()=>this.updateChevron());this.actor.add_child(this.chevron);this.gap=new St.Widget({width:8});this.actor.add_child(this.gap);this.gap.hide();
  this.divider=new St.Widget({style_class:'xp-tray-divider',reactive:false});Main.uiGroup.add_child(this.divider);imports.gi.Cinnamon.util_set_hidden_from_pick(this.divider,true);this.divider.hide();this.layoutId=0;this.zones=[];
  this.items=new Map();this.ready=false;this.dead=false;this.rebuildId=0;this.timer=0;this.failure=false;
  this.idleClock=new IdleCollapse(GLib.get_monotonic_time()/1000);this.idleTimer=0;
  this.activitySignal=global.stage.connect('captured-event',(_actor,event)=>{this.trayActivity(event);return Clutter.EVENT_PROPAGATE;});
  this.settings=new Settings.AppletSettings(this,UUID,instanceId);
  for(const [key,property] of [['always-open','alwaysOpen'],['auto-collapse','autoCollapse'],['expanded','expanded'],['favorites','favorites'],['order','iconOrder']])this.settings.bind(key,property,()=>this.changed());
  this.menu=new Applet.AppletPopupMenu(this,orientation);this.menu.box.set_style('background-color: #ece9d8; border: 1px solid #7093c7;');this.menuManager=new Popup.PopupMenuManager(this);this.menuManager.addMenu(this.menu);
  this.menu.connect('open-state-changed',(_menu,open)=>{if(open)this.buildEditor();else if(this.pointer&&this.pointer.pending&&this.pointer.pending.row)this.pointer.finish();});
  this.autoSwitch=new Popup.PopupSwitchMenuItem(t(12),!!this.autoCollapse);this.autoSwitch.connect('toggled',(_item,state)=>this.writeSetting('auto-collapse',state));this._applet_context_menu.addMenuItem(this.autoSwitch);
  this.modeSwitch=new Popup.PopupSwitchMenuItem(t(3),!!this.alwaysOpen);this.modeSwitch.connect('toggled',(_item,state)=>this.writeSetting('always-open',state));this._applet_context_menu.addMenuItem(this.modeSwitch);
  const customize=new Popup.PopupMenuItem(t(4));customize.connect('activate',()=>GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE,()=>{if(!this.dead)this.menu.open();return GLib.SOURCE_REMOVE;}));this._applet_context_menu.addMenuItem(customize);
  this.editSignal=global.settings.connect('changed::panel-edit-mode',()=>this.apply(false));
  this.pointer=new TrayPointer(this);this.ready=true;this.timer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,1200,()=>{this.scan();return this.dead||this.failure?GLib.SOURCE_REMOVE:GLib.SOURCE_CONTINUE;});
 }
 updateChevron(){
  const state=(this.alwaysOpen||this.expanded?'right':'left')+((this.actor.hover||global.stage.key_focus===this.actor)?'-hover':'');
  if(state===this.chevronState)return;this.chevronState=state;
  this.chevron.gicon=Gio.FileIcon.new(Gio.File.new_for_path(this.chevronPath+'/chevron-'+state+'.svg'));
  this.actor.accessible_name=this.alwaysOpen?t(4):this.expanded?t(2):t(1);
 }
 on_applet_added_to_panel(){this.scan();this.resetIdle();}
 on_applet_clicked(){if(this.alwaysOpen)this.menu.toggle();else this.writeSetting('expanded',!this.expanded);}
 on_panel_height_changed(){if(this.ready){this.restoreAll();this.scan();}}
 on_orientation_changed(){if(this.ready){this.restoreAll();this.scan();}}
 writeSetting(key,value){this.settings.setValue(key,value);this.changed();}
 changed(){if(!this.ready||this.dead)return;this.apply();this.resetIdle();if(this.menu.isOpen)this.scheduleEditor();}
 resetIdle(){
  this.idleClock.touch(GLib.get_monotonic_time()/1000);
  if(this.idleTimer){GLib.source_remove(this.idleTimer);this.idleTimer=0;}
  if(this.dead||!this.ready||!this.expanded||this.alwaysOpen||!this.autoCollapse||this.failure)return;
  this.idleTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,250,()=>{
   if(this.dead){this.idleTimer=0;return GLib.SOURCE_REMOVE;}
   const eligible=this.autoCollapse&&this.expanded&&!this.alwaysOpen&&!this.failure;
   if(!eligible){this.idleTimer=0;return GLib.SOURCE_REMOVE;}
   if(this.idleClock.due(GLib.get_monotonic_time()/1000,eligible,this.idleBlocked())){
    this.idleTimer=0;this.writeSetting('expanded',false);return GLib.SOURCE_REMOVE;
   }
   return GLib.SOURCE_CONTINUE;
  });
 }
 trayActivity(event){
  if(this.dead||!this.expanded||this.alwaysOpen||!this.autoCollapse)return;
  const type=event.type();
  if(![Clutter.EventType.MOTION,Clutter.EventType.BUTTON_PRESS,Clutter.EventType.BUTTON_RELEASE,Clutter.EventType.SCROLL,Clutter.EventType.KEY_PRESS,Clutter.EventType.KEY_RELEASE,Clutter.EventType.TOUCH_BEGIN,Clutter.EventType.TOUCH_UPDATE,Clutter.EventType.TOUCH_END].includes(type))return;
  let source=event.get_source(),inside=false;
  for(let a=source;a;a=a.get_parent()){
   if(a===this.actor||a===this.menu.actor||a===this.panel._rightBox||this.items.has(a)){inside=true;break;}
  }
  if(inside||(this.pointer&&this.pointer.pending))this.idleClock.touch(GLib.get_monotonic_time()/1000);
 }
 idleBlocked(){
  if(this.menu.isOpen||this._applet_context_menu.isOpen||Main.modalCount>0||DND.isDragging()||this.pointer.pending||global.settings.get_boolean('panel-edit-mode'))return true;
  for(const d of Manager.definitions){
   const app=d.applet;if(!app||d.panelId!==this.panel.panelId||d.location_label!=='right')continue;
   if((app.menu&&app.menu.isOpen)||(app._applet_context_menu&&app._applet_context_menu.isOpen))return true;
   if(d.uuid==='xapp-status@cinnamon.org')for(const icon of Object.values(app.statusIcons||{})){
    if(icon.proxy&&(icon.proxy.primary_menu_is_open||icon.proxy.secondary_menu_is_open))return true;
   }
  }
  // Legacy GTK tray menus can have their own X11 grab outside Cinnamon's stage.
  return global.get_window_actors().some(a=>a.visible&&a.meta_window&&[Meta.WindowType.POPUP_MENU,Meta.WindowType.DROPDOWN_MENU,Meta.WindowType.COMBO].includes(a.meta_window.get_window_type()));
 }
 comm(name){
  const match=String(name||'').match(/^org\.freedesktop\.statusnotifieritem-(\d+)-\d+$/i);if(!match)return '';
  try {const [ok,b]=Gio.File.new_for_path('/proc/'+match[1]+'/comm').load_contents(null);if(ok)return ByteArray.toString(b).trim().toLowerCase();}catch(e){}return '';
 }
 collect(){
  const result=[],id=this.panel.panelId;
  for(const d of Manager.definitions){
   if(d.panelId!==id||d.location_label!=='right'||Policy.protectedApplet(d.uuid))continue;
   const app=d.applet;if(!app)continue;
   if(d.uuid==='xapp-status@cinnamon.org'){
    for(const icon of Object.values(app.statusIcons||{})){
     const name=icon.proxy.name||'Application',comm=this.comm(name);
     result.push({key:'xapp:'+Policy.stableName(name,comm),label:comm||name,actor:icon.actor,icon:icon.iconName||'application-x-executable'});
    }
    // The recorder indicator is intentionally untouched.
   }else if(d.uuid==='systray@cinnamon.org'){
    for(const button of app.button_box.get_children()){
     const icon=button.child,name=icon.wm_class||icon.title||'Legacy application';
     result.push({key:'legacy:'+Policy.stableName(name,''),label:name,actor:button,icon:'application-x-executable'});
    }
   }else result.push({key:'applet:'+d.uuid,label:app._meta.name||d.uuid,actor:app.actor,icon:app._meta.icon||'preferences-system'});
  }
  return result;
 }
 scan(){
  if(!this.ready||this.dead||!this.panel||this.pointer.dragging)return;
  try{
   const entries=this.collect(),seen=new Set(entries.map(e=>e.actor));let changed=false;
   for(const [actor,item] of this.items){if(!seen.has(actor)){try{this.releaseItem(item);actor.disconnect(item.destroyId);}catch(e){}this.items.delete(actor);changed=true;}}
   for(const e of entries){
    const old=this.items.get(e.actor);
    if(old){old.label=e.label;old.icon=e.icon;old.key=e.key;}
    else {const item=Object.assign({},e,{fold:new FoldedActor(e.actor),translation:e.actor.translation_x});item.destroyId=e.actor.connect('destroy',()=>{this.items.delete(e.actor);this.scheduleEditor();});item.layoutSignal=e.actor.connect('allocation-changed',()=>this.queueLayout());this.items.set(e.actor,item);changed=true;}
   }
   this.apply(false);if(changed&&this.menu.isOpen)this.scheduleEditor();
  }catch(e){this.restoreAll();this.failure=true;global.logError(e);Main.notifyError(t(0),'The notification area was left expanded. Reload the applet to retry.');}
 }
 apply(animate=true){
  if(!this.ready||this.dead)return;
  const edit=global.settings.get_boolean('panel-edit-mode');
  for(const item of this.items.values())item.fold.set(Policy.shouldCollapse(item.key,this.favorites,this.alwaysOpen||this.failure,this.expanded,edit),animate);
  const visible=[...this.items.values()].filter(i=>i.actor.visible);this.gap.visible=!edit&&(this.alwaysOpen||this.expanded)&&visible.some(i=>this.isFavorite(i.key))&&visible.some(i=>!this.isFavorite(i.key));this.queueLayout();
  this.updateChevron();this.set_applet_tooltip(this.alwaysOpen?t(3)+' — '+t(4):this.expanded?t(2):t(1));
  if(this.modeSwitch)this.modeSwitch.setToggleState(!!this.alwaysOpen);
  if(this.autoSwitch)this.autoSwitch.setToggleState(!!this.autoCollapse);
 }
 releaseItem(item){item.fold.restore();item.actor.translation_x=item.translation;if(item.layoutSignal){item.actor.disconnect(item.layoutSignal);item.layoutSignal=0;}}
 restoreAll(){for(const item of this.items.values()){try{item.fold.restore();item.actor.translation_x=item.translation;}catch(e){}}if(this.divider)this.divider.hide();}
 scheduleEditor(){
  if(this.rebuildId||this.dead)return;
  this.rebuildId=GLib.timeout_add(GLib.PRIORITY_DEFAULT,100,()=>{if(DND.isDragging()||this.pointer.dragging)return GLib.SOURCE_CONTINUE;this.rebuildId=0;if(!this.dead&&this.menu.isOpen)this.buildEditor();return GLib.SOURCE_REMOVE;});
 }
 isFavorite(key){return Policy.pinned(key,this.favorites);}
 orderedItems(){return Policy.ordered([...this.items.values()],this.iconOrder);}
 place(key,wanted,before){
  this.settings.setValue('favorites',Policy.changedFavorites(this.favorites,key,wanted));
  this.settings.setValue('order',Policy.movedOrder(this.iconOrder,[...this.items.values()].map(i=>i.key),key,before));this.changed();
 }
 queueLayout(){if(this.layoutId||this.dead)return;this.layoutId=GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE,()=>{this.layoutId=0;if(!this.dead)this.layout();return GLib.SOURCE_REMOVE;});}
 layout(){
  if(!this.panel||this.dead)return;
  const all=[...this.items.values()];for(const i of all)i.actor.translation_x=i.translation;
  if(global.settings.get_boolean('panel-edit-mode')||this.failure){this.divider.hide();return;}
  const visible=this.orderedItems().filter(i=>i.actor.visible&&i.actor.width>0.1),hidden=visible.filter(i=>!this.isFavorite(i.key)),pinned=visible.filter(i=>this.isFavorite(i.key));
  const [ax,ay]=this.actor.get_transformed_position(),[,ah]=this.actor.get_transformed_size();
  let x=ax+this.actor.width-(this.gap.visible?8:0);this.panelBounds={start:x,y:ay,height:ah};
  for(const i of hidden){const current=i.actor.get_transformed_position()[0];i.actor.translation_x+=x-current;x+=i.actor.width;}
  this.boundary=x+(this.gap.visible?4:0);
  if(this.gap.visible){this.divider.show();this.divider.set_position(Math.round(x+3),Math.round(ay+ah*.22));this.divider.set_size(2,Math.round(ah*.56));x+=8;}else this.divider.hide();
  for(const i of pinned){const current=i.actor.get_transformed_position()[0];i.actor.translation_x+=x-current;x+=i.actor.width;}
  this.panelBounds.end=x;for(const i of all)if(i.actor.sync_hover)i.actor.sync_hover();
 }
 dropTarget(x,y,item){
  if(this.menu.isOpen){
   for(const {wanted,zone,scroll} of this.zones){
    const [sx,sy]=scroll.get_transformed_position(),[sw,sh]=scroll.get_transformed_size();if(x<sx||x>sx+sw||y<sy||y>sy+sh)continue;
    const rows=zone.get_children().filter(r=>r._mintxpItem&&r._mintxpItem.key!==item.key);
    const row=rows.find(r=>y<r.get_transformed_position()[1]+r.height/2),last=rows[rows.length-1];
    const line=row?row.get_transformed_position()[1]:last?last.get_transformed_position()[1]+last.height:sy+5;
    return {wanted,before:row?row._mintxpItem.key:null,x:sx+4,y:Math.max(sy,Math.min(sy+sh-2,line)),w:sw-8,h:2};
   }return null;
  }
  const b=this.panelBounds;if(!b||y<b.y-8||y>b.y+b.height+8||x<b.start-10||x>b.end+12)return null;
  const wanted=x>=this.boundary;const entries=this.orderedItems().filter(i=>i.actor.visible&&!i.fold.folded&&i.key!==item.key&&this.isFavorite(i.key)===wanted);
  const next=entries.find(i=>x<i.actor.get_transformed_position()[0]+i.actor.width/2),last=entries[entries.length-1];
  const line=next?next.actor.get_transformed_position()[0]:last?last.actor.get_transformed_position()[0]+last.actor.width:wanted?this.boundary+4:b.start;
  return {wanted,before:next?next.key:null,x:Math.round(line),y:Math.round(b.y+5),w:2,h:Math.round(b.height-10)};
 }
 setFavorite(key,wanted){this.writeSetting('favorites',Policy.changedFavorites(this.favorites,key,wanted));}
 iconFor(item){
  try{return new St.Icon({gicon:Gio.icon_new_for_string((item.icon||'').trim()||'application-x-executable'),icon_size:22,icon_type:St.IconType.FULLCOLOR});}
  catch(e){return new St.Icon({icon_name:'application-x-executable',icon_size:22});}
 }
 row(item){
  const row=new St.Button({style_class:'xp-tray-row',can_focus:true,x_expand:true,accessible_name:item.label});row.set_fill(true,false);row.set_alignment(St.Align.START,St.Align.MIDDLE);const content=new St.BoxLayout({style_class:'xp-tray-row-content',x_expand:true});const icon=this.iconFor(item);content.add_child(icon);
  const label=new St.Label({text:item.label,x_expand:true,y_align:Clutter.ActorAlign.CENTER});label.clutter_text.set_ellipsize(Pango.EllipsizeMode.END);content.add_child(label);row.set_child(content);
  row._mintxpItem=item;row.connect('clicked',()=>this.setFavorite(item.key,!this.isFavorite(item.key)));
  const tooltip=new Tooltips.Tooltip(row,item.label+(item.actor.visible?'':' — '+t(10)));row.connect('destroy',()=>tooltip.destroy());
  return row;
 }
 column(wanted){
  const column=new St.BoxLayout({vertical:true,style_class:'xp-tray-column'});column.add_child(new St.Label({text:t(wanted?5:6),style_class:'xp-tray-heading'}));
  const scroll=new St.ScrollView({style:'max-height: 420px;',x_expand:true});scroll.set_policy(imports.gi.Gtk.PolicyType.NEVER,imports.gi.Gtk.PolicyType.AUTOMATIC);
  const zone=new St.BoxLayout({vertical:true,style_class:'xp-tray-drop',reactive:true,x_expand:true});
  zone._delegate={handleDragOver:(source)=>{if(source.owner!==this)return DND.DragMotionResult.NO_DROP;zone.add_style_pseudo_class('drop');return DND.DragMotionResult.MOVE_DROP;},handleDragOut:()=>zone.remove_style_pseudo_class('drop'),acceptDrop:(source)=>{zone.remove_style_pseudo_class('drop');if(source.owner!==this||typeof source.key!=='string')return false;this.setFavorite(source.key,wanted);return true;}};
  const items=[...this.items.values()].filter(i=>Policy.pinned(i.key,this.favorites)===wanted);
  for(const item of Policy.ordered(items,this.iconOrder))zone.add_child(this.row(item));if(!items.length)zone.add_child(new St.Label({text:t(8),style_class:'xp-tray-empty'}));
  this.zones.push({wanted,zone,scroll});scroll.add_actor(zone);column.add_child(scroll);return column;
 }
 buildEditor(){
  if(this.dead||DND.isDragging()||this.pointer.dragging)return;this.zones=[];this.menu.removeAll();
  const auto=new Popup.PopupSwitchMenuItem(t(12),!!this.autoCollapse);auto.connect('toggled',(_item,state)=>this.writeSetting('auto-collapse',state));this.menu.addMenuItem(auto);
  const mode=new Popup.PopupSwitchMenuItem(t(3),!!this.alwaysOpen);mode.connect('toggled',(_item,state)=>this.writeSetting('always-open',state));this.menu.addMenuItem(mode);
  const help=new Popup.PopupMenuItem(t(7),{reactive:false});help.actor.add_style_class_name('xp-tray-help');help.label.clutter_text.set_line_wrap(true);help.label.clutter_text.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR);help.label.set_style('max-width: 520px; color: #24476c; text-shadow: none;');this.menu.addMenuItem(help);
  const section=new Popup.PopupBaseMenuItem({reactive:false});const columns=new St.BoxLayout({style_class:'xp-tray-editor'});columns.add_child(this.column(true));columns.add_child(this.column(false));section.addActor(columns);this.menu.addMenuItem(section);
  const foot=new Popup.PopupMenuItem(t(9),{reactive:false});foot.actor.add_style_class_name('xp-tray-help');foot.label.clutter_text.set_line_wrap(true);foot.label.set_style('max-width: 520px; color: #24476c; text-shadow: none;');this.menu.addMenuItem(foot);
  const close=new Popup.PopupMenuItem(t(11));close.connect('activate',()=>this.menu.close());this.menu.addMenuItem(close);
 }
 on_applet_removed_from_panel(){
  this.dead=true;if(this.idleTimer)GLib.source_remove(this.idleTimer);this.idleTimer=0;global.stage.disconnect(this.activitySignal);this.pointer.destroy();if(this.layoutId)GLib.source_remove(this.layoutId);if(this.timer)GLib.source_remove(this.timer);if(this.rebuildId)GLib.source_remove(this.rebuildId);global.settings.disconnect(this.editSignal);
  this.restoreAll();for(const [actor,item] of this.items){try{this.releaseItem(item);actor.disconnect(item.destroyId);}catch(e){}}this.items.clear();this.divider.destroy();this.menu.destroy();this.settings.finalize();
 }
}
function main(metadata,orientation,panelHeight,instanceId){return new XPTray(metadata,orientation,panelHeight,instanceId);}
