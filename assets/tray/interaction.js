// Drag the representation, never detach the native client actor. GPL-3.0-or-later.
const Clutter=imports.gi.Clutter,St=imports.gi.St,Main=imports.ui.main,Cinnamon=imports.gi.Cinnamon;
class TrayPointer {
 constructor(owner){this.owner=owner;this.pending=null;this.dragging=false;this.modal=false;this.ghost=null;this.marker=null;this.replaying=false;this.signal=global.stage.connect('captured-event',(_a,e)=>{try{return this.event(e);}catch(error){global.logError(error);this.finish();return Clutter.EVENT_STOP;}});}
 hitSource(source){
  for(let actor=source;actor;actor=actor.get_parent()){
   if(actor._mintxpItem)return {item:actor._mintxpItem,row:actor};
   const item=this.owner.items.get(actor);if(item&&!item.fold.folded)return {item,row:null};
  }return null;
 }
 replay(event){
  const p=this.pending;if(!p)return;this.replaying=true;
  try {for(let a=p.source;a;a=a.get_parent()){if(a.event(event,false))break;if(a===p.item.actor||a===p.row)break;}}
  finally{this.replaying=false;}
 }
 event(e){
  if(this.replaying||this.owner.dead||this.owner.failure)return Clutter.EVENT_PROPAGATE;
  const type=e.type();
  if(type===Clutter.EventType.BUTTON_PRESS&&e.get_button()===1&&!this.pending&&!global.settings.get_boolean('panel-edit-mode')){
   const hit=this.hitSource(e.get_source());if(!hit)return Clutter.EVENT_PROPAGATE;
   this.pending=Object.assign(hit,{source:e.get_source(),event:e.copy(),start:e.get_coords()});return Clutter.EVENT_STOP;
  }
  if(!this.pending)return Clutter.EVENT_PROPAGATE;
  if(type===Clutter.EventType.MOTION){
   const [x,y]=e.get_coords(),[sx,sy]=this.pending.start;
   if(!this.dragging&&Math.hypot(x-sx,y-sy)>=7)this.begin(x,y);
   if(this.dragging)this.motion(x,y);
   return Clutter.EVENT_STOP;
  }
  if(type===Clutter.EventType.BUTTON_RELEASE&&e.get_button()===1){
   if(this.dragging){this.restoreOpacity();const [x,y]=e.get_coords(),dest=this.owner.dropTarget(x,y,this.pending.item);if(dest&&!this.pending.item.actor.is_finalized())this.owner.place(this.pending.item.key,dest.wanted,dest.before);}
   else if(this.pending.row)this.owner.setFavorite(this.pending.item.key,!this.owner.isFavorite(this.pending.item.key));
   else {this.replay(this.pending.event);this.replay(e);}
   this.finish();return Clutter.EVENT_STOP;
  }
  if(type===Clutter.EventType.KEY_PRESS&&e.get_key_symbol()===Clutter.KEY_Escape){this.finish();return Clutter.EVENT_STOP;}
  return this.dragging?Clutter.EVENT_STOP:Clutter.EVENT_PROPAGATE;
 }
 begin(x,y){
  // Modal pointer ownership keeps the gesture alive outside the panel/window.
  this.modal=Main.pushModal(this.owner.actor);if(!this.modal){this.finish();return;}
  this.dragging=true;this.ghost=new St.BoxLayout({style_class:'xp-tray-drag',reactive:false});
  const icon=this.owner.iconFor(this.pending.item);icon.icon_size=28;this.ghost.add_child(icon);
  Main.uiGroup.add_child(this.ghost);Cinnamon.util_set_hidden_from_pick(this.ghost,true);this.ghost.opacity=235;
  this.marker=new St.Widget({style_class:'xp-tray-insert',reactive:false});Main.uiGroup.add_child(this.marker);Cinnamon.util_set_hidden_from_pick(this.marker,true);
  this.pending.opacity=this.pending.item.actor.opacity;this.pending.item.actor.opacity=160;this.motion(x,y);
 }
 motion(x,y){
  this.ghost.set_position(Math.round(x+12),Math.round(y-36));const target=this.owner.dropTarget(x,y,this.pending.item);
  if(target){this.marker.show();this.marker.set_position(target.x,target.y);this.marker.set_size(target.w,target.h);}
  else this.marker.hide();
 }
 restoreOpacity(){const p=this.pending;if(p&&p.opacity!==undefined&&!p.item.actor.is_finalized()){p.item.actor.opacity=p.opacity;delete p.opacity;}}
 finish(){
  this.restoreOpacity();
  if(this.ghost)this.ghost.destroy();if(this.marker)this.marker.destroy();this.ghost=this.marker=null;
  if(this.modal)Main.popModal(this.owner.actor);this.modal=false;this.dragging=false;this.pending=null;
  if(!this.owner.dead){this.owner.apply(false);this.owner.scheduleEditor();}
 }
 destroy(){this.finish();global.stage.disconnect(this.signal);}
}
module.exports={TrayPointer};
