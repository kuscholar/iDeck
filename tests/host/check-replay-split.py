#!/usr/bin/env python3
"""[perf] replay split (madeira_d3d12.c, madeira.cfg replay-split = 1); no Wine runs.

Red Dead Redemption 2 (build 460, log 2026-10-08 23:59:11) spent 31-60 ms of
a 38-72 ms open-world frame in ExecuteCommandLists with the GPU 24-34 % busy,
and the encode split explained only ~8 ms of it. The replay split times
ExecuteCommandLists by step and command kind.

Compiles mad_rs_bucket against the real command enum and checks every kind
has a bucket the line names, and textually that:
  - the switch is read with default 0 and costs nothing when off (every
    timer read in the replay is behind the flag);
  - mad_exec_list sums per list and adds to the globals once per list;
  - mad_ecl_run times the queue lock, prebuild, batch open and flush;
  - the [perf] block prints the line after the encode split.
Needs python3 and a C compiler (CC, default cc).
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root / 'madeira-d3d12/src/pe/madeira_d3d12.c').read_text()

enum = src[src.index('enum mad_ck {'):]
enum = enum[:enum.index('};') + 2]
kinds = list(dict.fromkeys(re.findall(r'\b(MC_[A-Z0-9_]+)\b', enum)))
names = src[src.index('enum { RS_LOCK,'):src.index('static volatile LONG64 g_rs_t[RS_N];')]
bucket = src[src.index('static int mad_rs_bucket(enum mad_ck k) {'):]
bucket = bucket[:bucket.index('\n}\n') + 3]

harness = '#include <stdio.h>\n' + enum + '\n' + names + bucket + r'''
int main(void)
{
''' + ''.join(f'    printf("{k} %s\\n", g_rs_names[mad_rs_bucket({k})]);\n' for k in kinds) + r'''
    return 0;
}
'''

cc = os.environ.get('CC', 'cc')
with tempfile.TemporaryDirectory(prefix='madeira-replay-split-') as directory:
    c = Path(directory) / 'r.c'
    exe = Path(directory) / 'r'
    c.write_text(harness)
    build = subprocess.run([cc, '-std=gnu11', '-Wall', '-Werror', '-Wno-unused-function', '-Wno-unused-variable',
                            '-o', str(exe), str(c)], capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr + harness
    out = subprocess.run([str(exe)], capture_output=True, text=True, check=True).stdout
got = dict(line.split(' ', 1) for line in out.splitlines())
assert set(got) == set(kinds), (set(kinds) - set(got))
expect = {
    'MC_DRAW': 'draw', 'MC_DRAW_INDEXED': 'draw', 'MC_DRAW_INDIRECT': 'indirect',
    'MC_DRAW_INDEXED_INDIRECT': 'indirect', 'MC_DISPATCH_INDIRECT': 'indirect', 'MC_DISPATCH': 'dispatch',
    'MC_COPY_BB': 'copy', 'MC_COPY_B2T': 'copy', 'MC_COPY_T2B': 'copy', 'MC_COPY_T2T': 'copy', 'MC_RESOLVE': 'copy',
    'MC_CLEAR_RT': 'clear', 'MC_CLEAR_DS': 'clear', 'MC_FILL_BB': 'clear', 'MC_FILL_TEX': 'clear',
    'MC_BARRIER': 'barrier', 'MC_RTS': 'targets', 'MC_QUERY_BEGIN': 'query', 'MC_QUERY_END': 'query',
    'MC_QUERY_RESOLVE': 'query',
}
for k, v in got.items():
    assert v == expect.get(k, 'state'), (k, v)
print(f'PASS: all {len(kinds)} command kinds map to a named bucket (draws, copies, clears, barriers, ... the rest is state)')

assert 'g_replay_split = mad_cfg_int_pe("replay-split", 0) ? 1 : 0;' in src
el = src[src.index('static void mad_exec_list(struct mad_queue *q, struct mad_list *l, obj_handle_t cb) {'):]
el = el[:el.index('\n}\n')]
assert 'const int rs = mad_rs_on();' in el and 'UINT64 rs_t = rs ? mad_tick() : 0;' in el
assert el.count('mad_tick()') == 3, 'three timer reads in the replay, all behind rs'
for m in re.finditer(r'mad_tick\(\)', el):
    line = el[el.rfind('\n', 0, m.start()) + 1:el.find('\n', m.start())]
    ctx = el[max(0, m.start() - 200):m.start()]
    assert 'rs ?' in line or 'if (rs)' in ctx, line
assert el.count('InterlockedExchangeAdd64(&g_rs_t[b], rs_sum[b])') == 1, 'globals once per list'
print('PASS: mad_exec_list reads the timer only when replay-split is on and adds to the globals once per list')

er = src[src.index('static void mad_ecl_run(ID3D12CommandQueue *This, UINT count, ID3D12CommandList *const *lists) {'):]
er = er[:er.index('\n}\n')]
for step in ('RS_LOCK', 'RS_PREBUILD', 'RS_BATCH', 'RS_FLUSH'):
    assert f'if (rs) mad_rs_step({step}, &rs_t);' in er, step
assert er.index('EnterCriticalSection(&ml1021_q->submit_lock)') < er.index('mad_rs_step(RS_LOCK')
assert er.index('mad_prebuild_lists(count, lists);') < er.index('mad_rs_step(RS_PREBUILD')
print('PASS: mad_ecl_run times the queue lock, prebuild, batch open and flush')

pp = src[src.index('static void mad_perf_present(void) {'):]
pp = pp[:pp.index('\n}\n')]
assert pp.index('[perf] encode split per frame') < pp.index('mad_rs_report((double)g_perf_presents);')
print('PASS: the [perf] block prints the replay split after the encode split')

wrap = src[src.index('static int mad_air_build_tables_ex(struct mad_exec *e,'):]
wrap = wrap[:wrap.index('\n}\n')]
assert 'UINT64 t0 = g_replay_split > 0 ? mad_tick() : 0;' in wrap and 'if (t0) mad_rs_step(RS_TABLES, &t0);' in wrap
assert 'mad_air_build_tables_ex_body(e, rs, root, consts, pso, cb_bind, arg_bind, arg_qwords, nair, airv, vis_mask,' in wrap
assert src.index('static int mad_air_build_tables_ex_body(') < src.index('static int mad_air_build_tables_ex(struct mad_exec *e,')
print('PASS: argument-table building is timed as its own bucket, only with replay-split on')
