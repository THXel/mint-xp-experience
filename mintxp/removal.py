"""Complete removal: preflight owned accessories, retain independent applications/data."""
from .engine import Conflict
from .lifecycle import uninstall_all
from .addons import Addons

def complete(engine,remove_addons=True,addons=None,bridge=None):
 addons=addons or Addons(engine)
 owned=[]
 if remove_addons:
  for key,item in addons.status().items():
   if item['state']=='interrupted':raise Conflict('Recover the interrupted accessory before uninstalling: '+item['name'])
   if item['state']=='managed':addons.verify(key);owned.append(key)
 # All known conflicts are checked before system restoration/authentication.
 current=engine.read_current()
 errors=engine.check(current,allow_preferences=True) if current.get('installed') else []
 if errors:raise Conflict('Changes protected:\n'+'\n'.join(errors))
 backup=engine.backup(reason='uninstall') if engine.read_current().get('installed') else None
 transaction=uninstall_all(engine,bridge)
 removed=[]
 for key in owned:
  try:addons.remove(key);removed.append(key)
  except Exception as error:
   engine.save('accessory-removal.json',{'complete':False,'removed':removed,'remaining':owned[len(removed):]})
   raise Conflict('Desktop restored. Accessory removal can be retried: '+str(error)) from error
 engine.save('accessory-removal.json',{'complete':True,'removed':removed,'remaining':[]})
 return {'transaction':transaction,'backup':backup,'accessories_removed':removed}
