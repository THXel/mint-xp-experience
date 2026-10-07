import math,sys,tempfile,unittest
from pathlib import Path
from mintxp.components import ROOT
from mintxp.engine import Engine
from test_engine import FakeSettings
sys.path.insert(0,str(ROOT/'assets/xp-explorer'))
from transfer_scene import endpoints,paper_at
class Progress(unittest.TestCase):
 def test_counts_describe_real_completed_writes_and_observer_is_optional(self):
  with tempfile.TemporaryDirectory() as td:
   home=Path(td)/'home';home.mkdir();e=Engine(home,Path(td)/'state',FakeSettings());events=[];observed=[]
   desired={'files':{'.config/theme':e.descriptor(b'new')},'settings':{'test/theme':"'XP'"}}
   def observe(phase,done,total,detail):
    if phase=='files' and done==1:observed.append((home/'.config/theme').read_bytes())
    events.append((phase,done,total))
   e.progress=observe;e.apply(desired,False)
   self.assertEqual(observed,[b'new']);self.assertIn(('files',0,1),events);self.assertIn(('files',1,1),events)
   self.assertIn(('check',1,1),events);self.assertEqual(events[-1][0],'commit')
   def broken(*args):raise RuntimeError('closed UI')
   e.progress=broken;e.uninstall();self.assertFalse((home/'.config/theme').exists())
 def test_failed_write_reports_no_success_and_rolls_back(self):
  with tempfile.TemporaryDirectory() as td:
   home=Path(td)/'home';home.mkdir();settings=FakeSettings();e=Engine(home,Path(td)/'state',settings);events=[]
   e.progress=lambda *event:events.append(event)
   desired={'files':{'.config/theme':e.descriptor(b'new')},'settings':{'test/theme':"'XP'"}};settings.fail=True
   with self.assertRaises(OSError):e.apply(desired,False)
   self.assertNotIn('commit',[row[0] for row in events]);self.assertFalse((home/'.config/theme').exists())
class Artwork(unittest.TestCase):
 def test_every_icon_decodes_at_small_and_large_sizes(self):
  import gi
  gi.require_version('GdkPixbuf','2.0');from gi.repository import GdkPixbuf
  files=list((ROOT/'assets/icons/scalable').rglob('*.svg'));self.assertGreaterEqual(len(files),100)
  for p in files:
   for size in (16,48):
    pix=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(p),size,size,True)
    self.assertEqual((pix.get_width(),pix.get_height()),(size,size),str(p))
 def test_animation_destinations_and_motion_are_action_specific(self):
  self.assertEqual(endpoints('trash')[1],'user-trash');self.assertEqual(endpoints('restore')[0],'user-trash-full')
  for kind in ('delete','empty-trash'):self.assertIsNone(endpoints(kind)[1])
  for kind in ('copy','move','trash','delete','empty-trash','restore','undo','rename'):
   for width in (300,430,800):
    for phase in (0,.2,.5,.8,.99):
     values=paper_at(kind,phase,0,width);x,y,angle,alpha,t=values
     self.assertTrue(all(math.isfinite(v) for v in values));self.assertTrue(0<=alpha<=1);self.assertTrue(0<=x<=width)
  self.assertNotEqual(paper_at('copy',.5,0,430),paper_at('copy',.8,0,430))
