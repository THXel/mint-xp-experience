// Monotonic inactivity policy; shell integration lives in applet.js.
class IdleCollapse {
 constructor(now,delay=10000){this.last=now;this.delay=delay;}
 touch(now){this.last=now;}
 due(now,eligible,blocked){
  if(!eligible||blocked){this.touch(now);return false;}
  return now-this.last>=this.delay;
 }
}
module.exports={IdleCollapse};
