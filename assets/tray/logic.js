// Pure policy: stable identities, favorites and protected panel items.
function stableName(name, comm) {
    const value=String(name||'unknown').trim().toLowerCase();
    if (/^org\.freedesktop\.statusnotifieritem-\d+-\d+$/.test(value))
        return 'sni:'+(comm||value.replace(/-\d+-\d+$/,''));
    return value;
}
function favoriteKeys(value) { return Array.isArray(value) ? [...new Set(value.filter(x=>typeof x==='string'&&x.length<=200))] : []; }
function pinned(key, values) { return favoriteKeys(values).includes(key); }
function changedFavorites(values,key,wanted) { const list=favoriteKeys(values).filter(x=>x!==key);if(wanted)list.push(key);return list; }
function shouldCollapse(key, values, alwaysOpen, expanded, editMode) { return !alwaysOpen&&!expanded&&!editMode&&!pinned(key,values); }
function protectedApplet(uuid) { return ['calendar@cinnamon.org','cornerbar@cinnamon.org','show-desktop@cinnamon.org','mintxp-tray@mintxp'].includes(uuid); }
module.exports={stableName,favoriteKeys,pinned,changedFavorites,shouldCollapse,protectedApplet};
function ordered(items,order){const keys=favoriteKeys(order);return items.slice().sort((a,b)=>{const x=keys.indexOf(a.key),y=keys.indexOf(b.key);return (x<0?keys.length:x)-(y<0?keys.length:y);});}
function movedOrder(order,known,key,before){const keys=favoriteKeys([...favoriteKeys(order),...known]).filter(k=>k!==key);const at=before?keys.indexOf(before):-1;keys.splice(at<0?keys.length:at,0,key);return keys;}
module.exports.ordered=ordered;module.exports.movedOrder=movedOrder;
