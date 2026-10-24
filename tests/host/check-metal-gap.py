#!/usr/bin/env python3
"""The metal-gap census line in madeira_d3d12.c; source checks, no Metal.

Red Dead Redemption 2 (build 467, log 13:09) grew Metal's currentAllocatedSize
from 2366 to 2931 MB in its last minute while the ml1057 estimate stayed at
~1.55 GB. Every 5 s, next to the ml1150 total, the runtime now says what the
total is made of: standalone textures as Metal sizes them (with the estimate
for the same textures), the runtime's texture heaps, the application's heaps
backed by Metal placement heaps, the buffers, the argument ring chunks, and
the rest. Checks:
  - a standalone texture (not in a placed heap, not in a runtime texture heap)
    is sized with MTLDevice_heapTextureSizeAndAlign and counted once; its
    release takes off the same Metal size and the same estimate, before the
    estimate itself is released;
  - ring chunks are counted when a NEW chunk is made, not when the pool hands
    one back;
  - placement heaps count while the application holds them;
  - the census line prints every part, the rest, and the frees waiting for the
    GPU, inside the 5 s clock.
"""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
src = (root / "madeira-d3d12/src/pe/madeira_d3d12.c").read_text()
ok = True


def check(what, cond):
    global ok
    print(("ok   " if cond else "FAIL ") + what)
    ok &= bool(cond)


def block(start, end="\n}\n"):
    i = src.index(start)
    return src[i:src.index(end, i) + len(end)]


res = block("struct mad_resource {", "\n};\n")
check("struct mad_resource carries metal_bytes", "UINT64 metal_bytes;" in res)

create = block("static HRESULT mad_create_resource_at(struct mad_device *d, D3D12_HEAP_TYPE heap_type,\n"
               "                                      const D3D12_RESOURCE_DESC *desc, REFIID riid, void **out,\n"
               "                                      struct mad_memheap *ph, UINT64 poff) {")
acct = create[create.index("if (!r->placed_heap) {   /* ml1057"):]
acct = acct[:acct.index("hr = res_QI(")]
check("standalone textures only: not placed in an application heap, not in a runtime texture heap",
      "if (!r->hp_used) {   /* madeira-bcd metal-gap" in acct)
check("sized as Metal sizes them and counted once",
      "MTLDevice_heapTextureSizeAndAlign(d->mtl_device, &ti, &msz, &mal);" in acct
      and "r->metal_bytes = msz;" in acct
      and "InterlockedExchangeAdd64(&g_sa_tex_bytes, (LONG64)msz);" in acct
      and "InterlockedExchangeAdd64(&g_sa_tex_logical, (LONG64)bytes);" in acct
      and acct.count("InterlockedIncrement(&g_sa_tex_n);") == 1
      and acct.index("mad_acct(r,") < acct.index("r->metal_bytes = msz;"))

rel = block("static ULONG STDMETHODCALLTYPE res_Release(ID3D12Resource *This) {")
check("release takes off the same Metal size and estimate, before the estimate is released",
      "InterlockedExchangeAdd64(&g_sa_tex_bytes, -(LONG64)r->metal_bytes);" in rel
      and "InterlockedExchangeAdd64(&g_sa_tex_logical, -(LONG64)r->acct_bytes);" in rel
      and "InterlockedDecrement(&g_sa_tex_n);" in rel
      and rel.index("if (r->metal_bytes) {") < rel.index("if (r->acct_bytes) mad_acct(r, r->acct_cat, r->acct_bytes, -1);"))
check("mad_acct does not clear acct_bytes on release (the census reads it first)",
      "if (sign > 0) { r->acct_bytes = bytes;" in block("static void mad_acct(struct mad_resource *r, unsigned cat, UINT64 bytes, int sign) {"))

ring = block("static int mad_ring_chunk_get(struct mad_device *d, struct mad_ringchunk *out) {")
check("ring chunks counted when a new one is made, after the pool and the failure check",
      ring.index("if (got) return 1;") < ring.index("InterlockedIncrement(&g_ring_chunks);")
      and ring.index("if (!out->buf || !bi.memory.ptr) return 0;") < ring.index("InterlockedIncrement(&g_ring_chunks);"))

heap = block("static HRESULT STDMETHODCALLTYPE device_CreateHeap(ID3D12Device *This, const D3D12_HEAP_DESC *desc,")
mrel = block("static ULONG STDMETHODCALLTYPE memheap_Release(ID3D12Heap *This) {")
check("placement heaps count while the application holds them",
      "if (h->mtl) { mad_resident(hd, h->mtl); InterlockedExchangeAdd64(&g_mheap_bytes, (LONG64)desc->SizeInBytes); }" in heap
      and "InterlockedExchangeAdd64(&g_mheap_bytes, -(LONG64)h->desc.SizeInBytes);" in mrel
      and mrel.index("if (h->mtl) {") < mrel.index("g_mheap_bytes"))

clock = src[src.index("/* ml1150: the memory census on a clock"):]
clock = clock[:clock.index("\n    {\n        static unsigned said;")]
check("the census line prints every part, the rest and the waiting frees, on the 5 s clock",
      "if (now - prev > 5 * qpf.QuadPart" in clock and "[madeira-d3d12] metal-gap: Metal %lld MB = standalone textures %ld" in clock
      and "(metal - sa - theaps - mheaps - bufs - rings) >> 20" in clock and "md->nmhret" in clock
      and "ml1150 Metal currentAllocatedSize %llu MB" in clock)

print("PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
