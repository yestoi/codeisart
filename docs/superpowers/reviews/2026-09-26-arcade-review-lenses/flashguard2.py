import numpy as np, time
from flashguard import lum, worst_area, strobe, glitch, glitch_static, ball, h, w

class FlashLimiter:
    """Strict: a pixel may begin at most `budget` opposing transitions (>= thr linear) per second.
    An over-budget reversal is held at the previous output. Guarantees <= budget/2 flashes/s per pixel."""
    def __init__(s,h,w,fps=30,thr=0.1,budget=6):
        s.prev=None; s.ext=None; s.dir=np.zeros((h,w),np.int8)
        s.ring=np.zeros((fps,h,w),bool); s.i=0; s.thr=thr; s.budget=budget; s.held_ticks=0
    def apply(s,frame):
        if s.prev is None:
            s.prev=frame.copy(); s.ext=lum(frame); return frame
        y=lum(frame); d=y-s.ext
        up=d>=s.thr; dn=d<=-s.thr
        flip=(up&(s.dir<=0))|(dn&(s.dir>=0))
        count=s.ring.sum(0)
        hold=flip&(count>=s.budget)
        out=np.where(hold[...,None],s.prev,frame)
        flip&=~hold; up&=~hold; dn&=~hold
        yo=np.where(hold,lum(s.prev),y)
        s.dir[up]=1; s.dir[dn]=-1
        s.ext=np.where(flip,yo,np.where(s.dir>0,np.maximum(s.ext,yo),np.minimum(s.ext,yo)))
        s.ring[s.i]=flip; s.i=(s.i+1)%len(s.ring)
        s.held_ticks+=bool(hold.any()); s.prev=out
        return out

def run(name,frames):
    g=FlashLimiter(h,w); outs=[g.apply(f) for f in frames]
    same=all((a==b).all() for a,b in zip(frames,outs))
    print(f"{name:28s} raw worst {worst_area(frames):4.2f}  limited {worst_area(outs):4.2f}  held ticks {g.held_ticks:3d}/{len(frames)} identity={same}")
for hz in (2,3,4,5,10,15): run(f"full-wall strobe {hz} Hz",strobe(hz))
run("glitch frame as planned",glitch()); run("glitch static fade",glitch_static()); run("moving 4x4 ball",ball())
g=FlashLimiter(h,w); fr=strobe(10); t0=time.perf_counter()
for i in range(300): g.apply(fr[i%90])
print("limiter cost M1 %.3f ms/frame 64x64"%((time.perf_counter()-t0)/300*1000))
