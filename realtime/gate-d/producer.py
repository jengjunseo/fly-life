"""Persistent, fixed-ID PCG64 child streams, worker-major contiguous output."""
import ctypes,threading,time
import numpy as np
N=165122;STEPS=50
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetCurrentThread.restype=ctypes.c_void_p
kernel.SetThreadAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];kernel.SetThreadAffinityMask.restype=ctypes.c_size_t
class GroupAffinity(ctypes.Structure):
    _fields_=[('mask',ctypes.c_size_t),('group',ctypes.c_ushort),('reserved',ctypes.c_ushort*3)]
kernel.GetThreadGroupAffinity.argtypes=[ctypes.c_void_p,ctypes.POINTER(GroupAffinity)]
def pin_thread(cpus):
    h=kernel.GetCurrentThread();mask=sum(1<<c for c in cpus)
    if not kernel.SetThreadAffinityMask(h,mask):raise ctypes.WinError(ctypes.get_last_error())
    actual=GroupAffinity()
    if not kernel.GetThreadGroupAffinity(h,ctypes.byref(actual)):raise ctypes.WinError(ctypes.get_last_error())
    assert actual.mask==mask
    return dict(thread_id=threading.get_native_id(),logical_cpus=cpus,affinity_mask=int(actual.mask),processor_group=int(actual.group),explicitly_pinned=True)
class Producer:
    def __init__(self,seed,workers,cpus=None,packed=False):
        self.seed=seed;self.workers=workers;self.ranges=[(i*N//workers,(i+1)*N//workers) for i in range(workers)]
        self.children=np.random.SeedSequence(seed).spawn(workers);self.rng=[np.random.Generator(np.random.PCG64(s)) for s in self.children]
        self.offsets=[50*a for a,b in self.ranges];self.buffer=np.empty(50*N,dtype=np.float32)
        self.views=[self.buffer[50*a:50*b].reshape(50,b-a) for a,b in self.ranges]
        self.packed_output=np.empty((50,N),np.float32) if packed else None
        self.go=[threading.Event() for _ in range(workers)];self.done=[threading.Event() for _ in range(workers)];self.ready=[threading.Event() for _ in range(workers)]
        self.quit=False;self.errors=[];self.affinity=[None]*workers
        def worker(i):
            try:
                self.affinity[i]=pin_thread([cpus[i]]) if cpus else dict(thread_id=threading.get_native_id(),explicitly_pinned=False)
                self.ready[i].set()
                while True:
                    self.go[i].wait();self.go[i].clear()
                    if self.quit:break
                    self.rng[i].standard_normal(self.views[i].shape,dtype=np.float32,out=self.views[i]);self.done[i].set()
            except BaseException as e:self.errors.append(repr(e));self.ready[i].set();self.done[i].set()
        self.threads=[threading.Thread(target=worker,args=(i,),name=f'pcg64-{i}',daemon=True) for i in range(workers)]
        for t in self.threads:t.start()
        for e in self.ready:e.wait()
        if self.errors:raise RuntimeError(self.errors)
    def fill(self):
        started=time.perf_counter()
        for e in self.done:e.clear()
        for e in self.go:e.set()
        for e in self.done:
            if not e.wait(30):raise TimeoutError('PCG worker stalled')
        if self.errors:raise RuntimeError(self.errors)
        if self.packed_output is not None:
            for i,(a,b) in enumerate(self.ranges):np.copyto(self.packed_output[:,a:b],self.views[i])
        return (time.perf_counter()-started)*1000
    def close(self):
        self.quit=True
        for e in self.go:e.set()
        for t in self.threads:t.join(5)
    def metadata(self):
        return dict(root_seed=self.seed,worker_count=self.workers,dtype='float32',shape=[50,N],layout='worker-major: contiguous [50,width] per fixed runtime-index slice; no per-block allocation/cast',
            workers=[dict(worker_id=i,spawn_key=list(self.children[i].spawn_key),entropy=self.children[i].entropy,runtime_start=a,runtime_end=b,element_offset=50*a,local_shape=[50,b-a],contiguous=bool(self.views[i].flags.c_contiguous),affinity=self.affinity[i]) for i,(a,b) in enumerate(self.ranges)],
            packed_c_order_output=self.packed_output is not None,packing='Preallocated C-order [50,N], same fixed slices copied after fill, packing included in generation timing' if self.packed_output is not None else None,
            stream_identity='Independent deterministic PCG64 child streams implementing Gaussian current noise; NOT the single reference PCG64 sequence. Stable mapping for a fixed worker count.')
def statistics(times):
    a=np.asarray(times);return dict(blocks=len(a),mean_ms=float(a.mean()),p50_ms=float(np.median(a)),p95_ms=float(np.percentile(a,95)),p99_ms=float(np.percentile(a,99)),max_ms=float(a.max()),blocks_per_second=1000/float(a.mean()),neural_wall_ratio=50/float(a.mean()),class_name='HEADROOM PASS' if np.percentile(a,99)<=35 else 'MARGINAL REALTIME' if np.percentile(a,99)<=50 else 'FAIL')
