"""Rough per-frame cost of candidate attract modes in numpy (update+draw into uint8 frame)."""
import time, numpy as np

def pal(stops, n=256):
    xs=np.linspace(0,1,len(stops)); t=np.linspace(0,1,n)
    return np.stack([np.interp(t,xs,[s[i] for s in stops]) for i in range(3)],1).astype(np.uint8)
FIRE=pal([(0,0,0),(90,0,0),(220,60,0),(255,170,20),(255,240,160)])
COOL=pal([(0,0,0),(0,40,60),(0,160,120),(180,255,200)])

class Ghost:
    def __init__(s,w,h,rng): s.acc=np.zeros((h,w),np.float32)
    def step(s,motion,frame,t):
        s.acc*=0.94; np.maximum(s.acc,motion*1.0,out=s.acc)
        frame[:]=COOL[(s.acc*255).astype(np.uint8)]

class Fire:
    def __init__(s,w,h,rng): s.f=np.zeros((h+1,w),np.float32); s.rng=rng; s.noise=np.zeros(w,np.float32)
    def step(s,motion,frame,t):
        s.noise=0.8*s.noise+0.2*s.rng.random(s.f.shape[1],dtype=np.float32)
        s.f[-1]=0.55+0.45*s.noise
        s.f[:-1][motion]=np.maximum(s.f[:-1][motion],0.9)
        below=s.f[1:]
        avg=(below+np.roll(below,1,1)+np.roll(below,-1,1)+s.f[:-1])*0.25
        s.f[:-1]=np.clip(avg-0.018,0,1)
        frame[:]=FIRE[(s.f[:-1]*255).astype(np.uint8)]

class Rain:
    def __init__(s,w,h,rng,n=None):
        s.w,s.h=w,h; n=n or w; s.x=rng.integers(0,w,n); s.y=rng.random(n,dtype=np.float32)*h; s.v=rng.uniform(15,35,n).astype(np.float32); s.rng=rng
        s.buf=np.zeros((h,w),np.float32)
    def step(s,motion,frame,t):
        s.y+=s.v/30
        yi=s.y.astype(int)
        hit=(yi>=0)&(yi<s.h); blocked=np.zeros_like(hit); blocked[hit]=motion[yi[hit],s.x[hit]]
        s.x[blocked]=np.clip(s.x[blocked]+np.where(s.rng.random(blocked.sum())<.5,-2,2),0,s.w-1)
        dead=s.y>=s.h; s.y[dead]=0; s.x[dead]=s.rng.integers(0,s.w,dead.sum())
        s.buf*=0.7; ok=(yi>=0)&(yi<s.h); s.buf[yi[ok],s.x[ok]]=1.0
        frame[:]=COOL[(s.buf*255).astype(np.uint8)]

class Boids:
    def __init__(s,w,h,rng,n=60):
        s.w,s.h=w,h; s.p=rng.random((n,2))*[w,h]; s.v=rng.normal(0,1,(n,2)); s.trail=np.zeros((h,w),np.float32)
    def step(s,motion,frame,t):
        d=s.p[:,None,:]-s.p[None,:,:]; d2=(d**2).sum(-1)+1e-6
        near=d2<64; sep=d2<9
        cnt=near.sum(1,keepdims=True)
        coh=(near[:,:,None]*s.p[None]).sum(1)/cnt - s.p
        ali=(near[:,:,None]*s.v[None]).sum(1)/cnt - s.v
        rep=(sep[:,:,None]*d/d2[:,:,None]).sum(1)
        s.v+=0.01*coh+0.05*ali+0.5*rep
        sp=np.linalg.norm(s.v,axis=1,keepdims=True)+1e-6; s.v=s.v/sp*np.clip(sp,0.5,1.5)
        s.p=(s.p+s.v)%[s.w,s.h]
        s.trail*=0.8; xi=s.p[:,0].astype(int); yi=s.p[:,1].astype(int)
        s.trail[yi,xi]=1; s.trail[yi,(xi+1)%s.w]=1; s.trail[(yi+1)%s.h,xi]=1; s.trail[(yi+1)%s.h,(xi+1)%s.w]=1
        frame[:]=FIRE[(s.trail*255).astype(np.uint8)]

class Fireflies(Boids):
    def __init__(s,w,h,rng,n=48):
        super().__init__(w,h,rng,n); s.ph=rng.random(n)*2*np.pi; s.om=2*np.pi*0.5
    def step(s,motion,frame,t):
        z=np.exp(1j*s.ph).mean(); s.ph+=s.om/30+0.3/30*np.abs(z)*np.sin(np.angle(z)-s.ph)
        s.p=(s.p+s.v*0.3)%[s.w,s.h]
        glow=np.clip(np.cos(s.ph),0,1)**4
        s.trail[:]=0; xi=s.p[:,0].astype(int); yi=s.p[:,1].astype(int)
        np.maximum.at(s.trail,(yi,xi),glow); np.maximum.at(s.trail,(yi,(xi+1)%s.w),glow)
        frame[:]=FIRE[(s.trail*255).astype(np.uint8)]

class Contours:
    def __init__(s,w,h,rng):
        yy,xx=np.mgrid[0:h,0:w].astype(np.float32); s.x=xx/16; s.y=yy/16
    def step(s,motion,frame,t):
        v=np.sin(s.x*1.3+t*0.3)+np.sin(s.y*1.7-t*0.23)+np.sin((s.x+s.y)*0.9+t*0.17)+np.sin(np.hypot(s.x-2,s.y-2)*2-t*0.5)
        band=np.abs(((v*2.5)%1.0)-0.5)<0.09
        frame[:]=0; frame[band]=(40,180,255)

class Stars:
    def __init__(s,w,h,rng,n=150):
        s.w,s.h=w,h; s.rng=rng; s.p=rng.uniform(-1,1,(n,2)).astype(np.float32); s.z=rng.uniform(0.1,1,n).astype(np.float32)
    def step(s,motion,frame,t):
        s.z-=0.01; dead=s.z<0.05; s.z[dead]=1; s.p[dead]=s.rng.uniform(-1,1,(dead.sum(),2))
        sx=(s.p[:,0]/s.z*s.w/4+s.w/2).astype(int); sy=(s.p[:,1]/s.z*s.h/4+s.h/2).astype(int)
        ok=(sx>=0)&(sx<s.w)&(sy>=0)&(sy<s.h); frame[:]=0
        b=np.clip((1-s.z[ok])*255,40,255).astype(np.uint8); frame[sy[ok],sx[ok]]=b[:,None]

class Ripple:
    def __init__(s,w,h,rng): s.a=np.zeros((h,w),np.float32); s.b=np.zeros_like(s.a); s.rng=rng; s.w,s.h=w,h
    def step(s,motion,frame,t):
        if s.rng.random()<0.05: s.a[s.rng.integers(2,s.h-2),s.rng.integers(2,s.w-2)]+=8
        s.a[motion]+=0.3
        for _ in range(2):
            n=np.zeros_like(s.a)
            n[1:-1,1:-1]=(s.a[:-2,1:-1]+s.a[2:,1:-1]+s.a[1:-1,:-2]+s.a[1:-1,2:])*0.5-s.b[1:-1,1:-1]
            n*=0.985; s.b,s.a=s.a,n
        frame[:]=COOL[np.clip(np.abs(s.a)*120,0,255).astype(np.uint8)]

class Life:
    def __init__(s,w,h,rng): s.c=rng.random((h,w))<0.3; s.age=np.zeros((h,w),np.float32); s.k=0
    def step(s,motion,frame,t):
        s.c|=motion; s.k+=1
        if s.k%4==0:
            c=s.c.astype(np.uint8); n=sum(np.roll(np.roll(c,dy,0),dx,1) for dy in(-1,0,1) for dx in(-1,0,1) if dy or dx)
            s.c=(n==3)|(s.c&(n==2))
        s.age=np.where(s.c,np.minimum(s.age+0.1,1),s.age*0.8)
        frame[:]=FIRE[(s.age*255).astype(np.uint8)]

class Eye:
    def __init__(s,w,h,rng):
        s.w,s.h=w,h; yy,xx=np.mgrid[0:h,0:w]; s.xx,s.yy=xx,yy; s.r=min(h,w//2)//2-1
        s.cx=[w//4,3*w//4] if w>h else [w//2]; s.cy=h//2
    def step(s,motion,frame,t):
        m=motion.nonzero(); tx=(m[1].mean()/s.w-.5) if len(m[1]) else np.sin(t*.3)*.4
        frame[:]=0; lid=1.0 if (t%5)>0.2 else 0.3
        for cx in s.cx:
            d=((s.xx-cx)/s.r)**2+((s.yy-s.cy)/(s.r*lid))**2
            frame[d<=1]=(200,200,190)
            px=cx+tx*s.r*0.8; dp=(s.xx-px)**2+(s.yy-s.cy)**2
            frame[(dp<=(s.r*0.45)**2)&(d<=1)]=(0,120,200); frame[(dp<=(s.r*0.2)**2)&(d<=1)]=0

class Aurora:
    def __init__(s,w,h,rng):
        s.w,s.h=w,h; s.x=np.arange(w,dtype=np.float32); s.yy=np.arange(h,dtype=np.float32)[:,None]/h
    def step(s,motion,frame,t):
        top=0.25+0.15*np.sin(s.x*0.11+t*0.4)+0.1*np.sin(s.x*0.037-t*0.23)
        inten=0.5+0.5*np.sin(s.x*0.07+t*0.6)*np.sin(s.x*0.019-t*0.15)
        v=np.clip(1-(s.yy-top)/0.35,0,1)*(s.yy>top)*inten
        frame[:]=COOL[(v*200).astype(np.uint8)]

class Heartline:
    def __init__(s,w,h,rng): s.w,s.h=w,h; s.hist=np.zeros(w,np.float32); s.rng=rng; s.cols=np.arange(w)
    def step(s,motion,frame,t):
        s.hist=np.roll(s.hist,-1); s.hist[-1]=s.rng.random()**3
        amp=(s.hist*(s.h/2-2)).astype(int); frame[:]=0; mid=s.h//2
        yy=np.arange(s.h)[:,None]; m=np.abs(yy-mid)<=amp[None,:]+1
        frame[m]=(255,60,120)

MODES=[Ghost,Fire,Rain,Boids,Fireflies,Contours,Stars,Ripple,Life,Eye,Aurora,Heartline]
for (w,h) in [(64,64),(128,32)]:
    print(f"--- {w}x{h}")
    rng=np.random.default_rng(0)
    motions=[rng.random((h,w))<0.05 for _ in range(30)]
    for M in MODES:
        m=M(w,h,np.random.default_rng(1)); frame=np.zeros((h,w,3),np.uint8)
        for i in range(30): m.step(motions[i%30],frame,i/30)
        t0=time.perf_counter(); N=600
        for i in range(N): m.step(motions[i%30],frame,i/30)
        ms=(time.perf_counter()-t0)/N*1000
        print(f"{M.__name__:10s} {ms:6.3f} ms/frame on M1  (~{ms*8:5.1f} ms Pi4 at 8x)")
# overhead benchmarks
a=np.zeros((64,64),np.float32)
t0=time.perf_counter()
for i in range(100000): a*=0.9
print("tiny ufunc on 64x64 float32: %.2f us"%((time.perf_counter()-t0)/100000*1e6))
