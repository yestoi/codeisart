import numpy as np, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import bench_attract as B
    from flashguard import worst_area
for (w,h) in [(64,64),(128,32)]:
    rng=np.random.default_rng(0)
    for M in B.MODES:
        m=M(w,h,np.random.default_rng(1)); frames=[]
        for i in range(120):
            mo=np.zeros((h,w),bool)
            if 30<i<90: x=int((i-30)/60*w); mo[h//3:,max(0,x-3):x+3]=True
            f=np.zeros((h,w,3),np.uint8); m.step(mo,f,i/30); frames.append(f.copy())
        print(f"{w}x{h} {M.__name__:10s} flicker area {worst_area(frames[10:]):.3f}  mean APL {np.mean([(B.np.asarray(f,float)/255).mean() for f in frames]):.3f}")
