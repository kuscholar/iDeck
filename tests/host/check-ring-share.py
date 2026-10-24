#!/usr/bin/env python3
"""ring-share (madeira.cfg ring-share = 1) and the ExecuteIndirect fast-path tallies; no Wine runs.

Red Dead Redemption 2 on build 470 (2026-10-09 14:48): the argument-ring chunks
of madeira-d3d12 grew from 32 MB to 1575 MB within two minutes of play, because
every command list kept the chunks of its last replay until it was reset, and
a list executed again without a reset took new ones. Compiles the production
ring functions of madeira-d3d12/src/pe/madeira_d3d12.c (chunk get, retire,
pool put, list rewind, ring take) with stubs and checks, in a model of many
lists replayed over frames with the GPU some batches behind:
  - without ring-share the behaviour is the old one (chunks pile up per list);
  - with ring-share (a replay's chunks go to the queue's open batch and
    retire with its serial at the commit) the chunks stay near what the GPU
    has in flight and do not grow with time;
  - in both, no chunk is handed out to another replay while a batch the GPU
    has not finished still reads it;
and textually: the replay end parks only with the switch and a GPU timeline,
the commit retires the parked chunks with the batch's serial, the census
counts live chunks, and every ExecuteIndirect replay with indirect-fast is
tallied by why it took or skipped the fast path.
Needs python3 and a C compiler.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root / 'madeira-d3d12/src/pe/madeira_d3d12.c').read_text()


def function(signature):
    start = src.index(signature)
    return src[start:src.index('\n}\n', start) + 3]


replay = function('static void mad_exec_list(struct mad_queue *q, struct mad_list *l, obj_handle_t cb) {')
park_site = 'if (l->nrings && q->device->gpu_event && mad_ring_share_on()) mad_ring_park(q, l);'
assert replay.rstrip().endswith(park_site + '\n}'), 'the last thing a replay does'
flush = function('static void mad_queue_flush(struct mad_queue *q) {')
unpark_site = 'if (q->nring_parked) mad_ring_unpark(q, serial);'
assert flush.index('q->batch_serial[(q->batches + 1) & 63] = serial;') < flush.index(unpark_site) < \
    flush.index('__atomic_store_n(&q->batches, q->batches + 1, __ATOMIC_RELEASE);')
share = function('static int mad_ring_share_on(void) {')
assert 'mad_cfg_int_pe("ring-share", 0)' in share, 'off by default'
release = function('static ULONG STDMETHODCALLTYPE list_Release(ID3D12GraphicsCommandList *This) {')
assert 'InterlockedExchangeAdd(&g_ring_chunks, -(LONG)l->nrings);' in release, 'the census counts live chunks'
site = src[src.index('/* madeira-bcd: indirect-fast -- record 0 was encoded, the rest share its state */'):][:800]
assert 'if (!k && mad_indirect_fast_on()) {' in site and 'mad_ifr_note(why, c->u.ind.count);' in site
assert 'if (why == IFR_USED) { exec_indirect_rest(&e, c); break; }' in site
why = function('static int exec_indirect_fast_why(struct mad_exec *e, const struct mad_cmd *c) {')
for reason in ('IFR_ONE_RECORD', 'IFR_DIAG', 'IFR_CAPTURE', 'IFR_DUMP', 'IFR_COMPUTE', 'IFR_NO_ENCODER',
               'IFR_GS_EMU', 'IFR_DXBC_TESS', 'IFR_BACKEND', 'IFR_NO_IB'):
    assert reason in why, reason
print('PASS: a replay parks its chunks with ring-share, the commit retires them with its serial; live-chunk census; '
      'ExecuteIndirect fast-path tallies')

pieces = ''.join(function(sig) for sig in (
    'static UINT64 mad_gpu_completed(struct mad_device *d) {',
    'static int mad_ring_chunk_get(struct mad_device *d, struct mad_ringchunk *out) {',
    'static void mad_ring_retire(struct mad_device *d, struct mad_list *l, UINT64 serial) {',
))
pieces += src[src.index('static int g_ring_share = -1;'):src.index('/* At the end of a replay: the list')]
pieces += function('static void mad_ring_park(struct mad_queue *q, struct mad_list *l) {')
pieces += function('static void mad_ring_unpark(struct mad_queue *q, UINT64 serial) {')
pieces += function('static void mad_ring_pool_put(struct mad_device *d, struct mad_list *l) {')
pieces += function('static int mad_list_ring_grow(struct mad_exec *e) {')
pieces += function('static int exec_ring_take_z(struct mad_exec *e, unsigned n, size_t zero_bytes, obj_handle_t *buf, UINT64 *off, void **cpu, UINT64 *gpu) {')
pieces += function('static void mad_list_rings_rewind(struct mad_list *l) {')
slot_bytes = next(line for line in src.split('\n') if line.startswith('#define MAD_ARG_SLOT_BYTES'))

harness = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t UINT64; typedef int64_t LONG64; typedef int32_t LONG; typedef uint64_t obj_handle_t;
typedef struct { int unused; } CRITICAL_SECTION;
#define FAIL(...) do { fprintf(stderr, __VA_ARGS__); exit(1); } while (0)
static void EnterCriticalSection(CRITICAL_SECTION *c) { (void)c; }
static void LeaveCriticalSection(CRITICAL_SECTION *c) { (void)c; }
static LONG InterlockedIncrement(volatile LONG *p) { return ++*p; }
static LONG InterlockedDecrement(volatile LONG *p) { return --*p; }
#define MAD_ARG_RING_BYTES (64u * 1024u)
''' + slot_bytes + r'''
enum { WMTResourceStorageModeShared = 0 };
struct WMTBufferInfo { UINT64 length; unsigned options; struct { void *ptr; } memory; UINT64 gpu_address; };
static volatile LONG g_ring_chunks;
static long g_cfg_ring_share;
static long mad_cfg_int_pe(const char *key, long dflt) { return strcmp(key, "ring-share") ? dflt : g_cfg_ring_share; }
static void d3d12_log(const char *fmt, ...) { (void)fmt; }
struct mad_ringchunk { obj_handle_t buf; void *cpu; UINT64 gpu; UINT64 serial; };
struct mad_device {
    CRITICAL_SECTION ring_lock; obj_handle_t mtl_device, gpu_event;
    struct mad_ringchunk *ring_pool, *ring_retired;
    unsigned nring_pool, ring_pool_cap, nring_retired, ring_retired_cap;
};
struct mad_queue { struct mad_device *device; UINT64 batches, batch_serial[64], last_serial;
                   struct mad_ringchunk *ring_parked; unsigned nring_parked, ring_parked_cap; };
struct mad_list {
    obj_handle_t *rings; void **ring_cpu; UINT64 *ring_gpu; unsigned nrings; unsigned ring_used;
    struct mad_queue *ring_q; UINT64 ring_batch;
};
struct mad_exec { struct mad_queue *q; struct mad_list *l; };

/* the GPU timeline and the chunk owners */
static UINT64 gpu_done;
#define MAXB 20000
#define PER (MAD_ARG_RING_BYTES / MAD_ARG_SLOT_BYTES)
static UINT64 slot_busy_until[MAXB * PER];   /* serial of the last batch that read slot (buf - 1, n) */
static unsigned slot_owner[MAXB * PER], replay_id;   /* the replay that last wrote it */
static unsigned chunks_made;
static UINT64 MTLSharedEvent_signaledValue(obj_handle_t e) { (void)e; return gpu_done; }
static obj_handle_t MTLDevice_newBuffer(obj_handle_t dev, struct WMTBufferInfo *bi) {
    static char mem[1];
    (void)dev;
    if (chunks_made >= MAXB) return 0;
    bi->memory.ptr = mem; bi->gpu_address = 0x1000000ull * (chunks_made + 1);
    return ++chunks_made;
}
static void NSObject_release(obj_handle_t o) { (void)o; }
static int mad_grow(void **p, unsigned *cap, unsigned need, size_t sz) {
    if (need > *cap) { unsigned n = *cap ? *cap * 2 : 16; while (n < need) n *= 2; *p = realloc(*p, (size_t)n * sz); *cap = n; }
    return *p != NULL;
}
static int flushes;
static void mad_queue_flush(struct mad_queue *q) { flushes++; q->batches++; q->batch_serial[q->batches & 63] = q->batches; q->last_serial = q->batches; }
static void *memset_cpu(void *p, int c, size_t n) { (void)p; (void)c; (void)n; return p; }
#define memset(p, c, n) ((p) == (void *)0 ? (p) : memset_cpu((p), (c), (n)))
static void mad_list_rings_rewind(struct mad_list *l);
''' + pieces + r'''
#undef memset

/* One replay of list l into the queue's open batch: n argument slots. */
static void replay(struct mad_queue *q, struct mad_list *l, unsigned n)
{
    struct mad_exec e = { q, l };
    unsigned i;
    replay_id++;
    l->ring_q = q; l->ring_batch = q->batches + 1;
    for (i = 0; i < n; i++) {
        obj_handle_t b; UINT64 off, gpu; void *cpu;
        if (!exec_ring_take_z(&e, 1, 0, &b, &off, &cpu, &gpu)) FAIL("ring take failed\n");
        {
            size_t at = (size_t)(b - 1) * PER + (size_t)(off / MAD_ARG_SLOT_BYTES);
            if (slot_busy_until[at] > gpu_done && slot_owner[at] != replay_id)
                FAIL("slot %u of chunk %llu handed out while batch %llu still reads it (GPU at %llu)\n",
                     (unsigned)(off / MAD_ARG_SLOT_BYTES), (unsigned long long)b,
                     (unsigned long long)slot_busy_until[at], (unsigned long long)gpu_done);
            slot_busy_until[at] = q->batches + 1; slot_owner[at] = replay_id;
        }
    }
    if (l->nrings && q->device->gpu_event && mad_ring_share_on()) mad_ring_park(q, l);   /* as mad_exec_list ends */
}

/* as mad_queue_flush: the serial, then the parked chunks, then the count */
static void commit(struct mad_queue *q)
{
    UINT64 serial = q->batches + 1;
    q->last_serial = serial;
    q->batch_serial[(q->batches + 1) & 63] = serial;
    if (q->nring_parked) mad_ring_unpark(q, serial);
    q->batches++;
}

/* Frames: 400 lists alive (Red Dead Redemption 2 keeps hundreds), 16 of them recorded and
 * replayed a frame (one executed twice without a reset), the GPU three batches behind.
 * Returns the chunks created. */
static unsigned model(long share, unsigned frames)
{
    static struct mad_list lists[400];
    struct mad_device d; struct mad_queue q;
    unsigned f, i;
    memset(&d, 0, sizeof d); memset(&q, 0, sizeof q); memset(lists, 0, sizeof lists); memset(slot_busy_until, 0, sizeof slot_busy_until);
    chunks_made = 0; gpu_done = 0; g_ring_share = -1; g_cfg_ring_share = share; g_ring_chunks = 0;
    memset(slot_owner, 0, sizeof slot_owner); replay_id = 0;
    d.gpu_event = 1; q.device = &d;
    srand(7);
    for (f = 0; f < frames; f++) {
        for (i = 0; i < 16; i++) {
            struct mad_list *l = &lists[(f * 16 + i) % 400];
            mad_list_rings_rewind(l);                      /* Reset */
            replay(&q, l, 20 + rand() % 400);              /* ExecuteCommandLists */
            if (i == 3) replay(&q, l, 50);                 /* executed again without a reset */
        }
        commit(&q);
        gpu_done = q.batches > 3 ? q.batches - 3 : 0;
    }
    return chunks_made;
}

int main(void)
{
    unsigned old_way = model(0, 600), shared = model(1, 600);
    if (shared * 5 > old_way) FAIL("ring-share should keep far fewer chunks: %u against %u\n", shared, old_way);
    printf("PASS: 600 frames, 400 lists: %u chunks the old way, %u with ring-share; no chunk reused while the GPU reads it\n",
           old_way, shared);
    if (model(1, 2000) > shared + shared / 4) FAIL("ring-share should not grow with time\n");
    printf("PASS: with ring-share the chunks do not grow with time (2000 frames)\n");
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-ring-') as directory:
    temporary = Path(directory)
    cc = os.environ.get('CC', 'cc')
    if not shutil.which(cc):
        raise SystemExit('SKIP: no C compiler')
    (temporary / 'ring.c').write_text(harness)
    subprocess.run([cc, '-std=gnu11', '-Wall', '-Wno-unused-function', '-Wno-unused-variable',
                    str(temporary / 'ring.c'), '-o', str(temporary / 'ring')], check=True)
    subprocess.run([str(temporary / 'ring')], check=True)
