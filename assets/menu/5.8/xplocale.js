// Read once per applet load; restart the applet after changing the shared language.
const Gio=imports.gi.Gio, GLib=imports.gi.GLib, ByteArray=imports.byteArray;
const LANGS=['de','en','fr','es','it','pt','nl','pl','tr','ru','uk','zh','ja','ko'];
function read(path){try{const [ok,data]=Gio.File.new_for_path(path).load_contents(null);if(ok){const result=JSON.parse(ByteArray.toString(data));if(result&&typeof result==='object'&&!Array.isArray(result))return result;}}catch(e){}return {};}
function language(){
 const pref=read(GLib.build_filenamev([GLib.getenv('XDG_STATE_HOME')||GLib.build_filenamev([GLib.get_home_dir(),'.local','state']),'mint-xp-experience','preferences.json']));
 if(LANGS.includes(pref.language))return pref.language;
 const loc=GLib.getenv('LC_ALL')||GLib.getenv('LC_MESSAGES')||GLib.getenv('LANG')||'en';
 if(loc==='C'||loc==='POSIX'||loc.startsWith('C.'))return 'en';
 const candidates=GLib.getenv('LC_ALL')?[loc]:(GLib.getenv('LANGUAGE')||'').split(':').concat([loc]);
 for(const item of candidates){const code=item.split(/[_.-]/)[0].toLowerCase();if(LANGS.includes(code))return code;}return 'en';
}
const LANGUAGE=language();
const dir=GLib.build_filenamev([GLib.get_home_dir(),'.local','share','cinnamon','applets','mintxp-menu@mintxp','5.8','locales']);
const BASE=read(GLib.build_filenamev([dir,'en.json']));
const MESSAGES=read(GLib.build_filenamev([dir,LANGUAGE+'.json']));
function t(source){return LANGUAGE==='de'?source:(MESSAGES[source]||BASE[source]||source);}
module.exports={t,language,LANGUAGE};
