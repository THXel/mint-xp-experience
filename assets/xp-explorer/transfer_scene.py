"""Operation-specific animation geometry, independent from transfer progress."""
import math
KINDS={'copy':('folder','folder-open'),'move':('folder','folder-open'),'trash':('folder','user-trash'),'delete':('text-x-generic',None),'empty-trash':('user-trash-full',None),'restore':('user-trash-full','folder-open'),'undo':('folder-open','folder'),'rename':('text-x-generic','text-x-generic')}
def endpoints(kind):return KINDS.get(kind,KINDS['copy'])
def paper_at(kind,phase,index,width):
    t=(phase+index/3)%1
    # A short pause at each end gives the sheets a distinct, classic frame cadence.
    travel=max(0,min(1,(t-.10)/.78));eased=travel*travel*(3-2*travel)
    x=60+eased*max(1,width-130);y=43-29*math.sin(travel*math.pi)
    angle=.22*math.sin(travel*math.pi*2);alpha=min(1,t/.08,max(0,(1-t)/.12))
    if kind in ('delete','empty-trash'):
        y+=max(0,(travel-.68)/.32)*19
        alpha*=max(0,min(1,(.97-travel)/.25))
    if kind=='trash':y+=max(0,(travel-.85)/.15)*12
    return x,y,angle,alpha,travel
