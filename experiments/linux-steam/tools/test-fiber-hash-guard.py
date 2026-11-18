#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Fault inject the ACTUAL extracted pinned resize/insert bodies on HOST.

Uses real upstream structs/list implementation. Unrelated code-page hooks and
clock/cap observers are neutral in this focused harness, not runtime stubs.
Negative child runs original unchecked code; no allocator injection in iOS.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from fiber_hash_patch import patched_engine
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];src=repo/'vendor/LinuxRunner';out=a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()==pin
original=subprocess.check_output(['git','-C',src,'show',pin+':asbestos/asbestos.c']).decode();assert original==(src/'asbestos/asbestos.c').read_text()
def function(s,name):
    start=s.index('static void '+name+'(',s.index('static struct fiber_block *fiber_lookup(struct asbestos *asbestos, addr_t addr);'))
    at=s.index('{',start);depth=1;end=at+1
    while depth:
        depth+=(s[end]=='{')-(s[end]=='}');end+=1
    return s[start:end]
preamble=r'''
#include <assert.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdatomic.h>
#include "asbestos/asbestos.h"
static _Atomic uint64_t ideck_fiber_hash_growth_failures;
static _Atomic uint64_t asbestos_stat_blocks,asbestos_stat_code_words;
static unsigned allocations;static int deny;
static void *test_calloc(size_t n,size_t size){allocations++;return deny?NULL:calloc(n,size);}
#define calloc test_calloc
#undef TRACE_
#define TRACE_(...)
static void code_seen_note(struct asbestos *a,page_t p){(void)a;(void)p;}
static void absent_exact_forget(struct asbestos *a,page_t p){(void)a;(void)p;}
static uint64_t asbestos_now_ms(void){return 17;}
static uint64_t code_cap_bytes(void){return 0;}
static size_t asbestos_code_bytes(struct asbestos *a){(void)a;return 0;}
static struct list *blocks_list(struct asbestos *a,page_t p,int side){return &a->page_hash[p%FIBER_PAGE_HASH_SIZE].blocks[side];}
static int arm64_eager_prechain_enabled;
static void fiber_prechain_same_page(struct asbestos *a,struct fiber_block *b){(void)a;(void)b;}
'''
tail=r'''
static void init(struct asbestos *a){memset(a,0,sizeof(*a));a->hash=calloc(4,sizeof(*a->hash));assert(a->hash);a->hash_size=4;a->page_hash=calloc(FIBER_PAGE_HASH_SIZE,sizeof(*a->page_hash));assert(a->page_hash);}
static int contains(struct asbestos *a,struct fiber_block *expected){
 struct list *head=&a->hash[expected->addr%a->hash_size];if(list_null(head))return 0;
 struct fiber_block *b;list_for_each_entry(head,b,chain){if(b==expected)return 1;}return 0;
}
int main(int argc,char **argv){
 assert(argc==2);struct asbestos a;init(&a);struct fiber_block blocks[64];memset(blocks,0,sizeof blocks);
 for(unsigned i=0;i<64;i++){blocks[i].addr=0x1000+i*4;blocks[i].end_addr=blocks[i].addr+4;blocks[i].used=i+1;}
 for(unsigned i=0;i<7;i++)fiber_insert(&a,&blocks[i]);assert(a.hash_size==4&&a.num_blocks==7);
 struct list *old=a.hash;struct list heads[4];memcpy(heads,old,sizeof heads);
 if(!strcmp(argv[1],"negative")){deny=1;fiber_insert(&a,&blocks[7]);return 99;}
 deny=1;unsigned before=allocations;
 fiber_resize_hash(&a,8);
 assert(a.hash==old&&a.hash_size==4&&a.flush_requested&&atomic_load(&ideck_fiber_hash_growth_failures)==1);
 assert(!memcmp(heads,a.hash,sizeof heads));for(unsigned i=0;i<7;i++)assert(contains(&a,&blocks[i]));
 // Existing table remains usable and growth is NOT retried for each insertion
 // while ordinary next-slice cache flush is requested.
 fiber_insert(&a,&blocks[7]);for(unsigned i=8;i<32;i++)fiber_insert(&a,&blocks[i]);
 assert(allocations==before+1&&a.hash_size==4&&a.num_blocks==32);
 for(unsigned i=0;i<32;i++)assert(contains(&a,&blocks[i]));
 // Model only clearing the pending policy request; actual flush lifetime is a
 // separate integration gate. Successful growth must rehash every old node.
 deny=0;a.flush_requested=false;fiber_resize_hash(&a,64);assert(a.hash!=old&&a.hash_size==64);
 for(unsigned i=0;i<32;i++)assert(contains(&a,&blocks[i]));
 fiber_insert(&a,&blocks[32]);assert(contains(&a,&blocks[32]));
 assert(a.num_blocks==33&&atomic_load(&asbestos_stat_blocks)==33);
 free(a.hash);free(a.page_hash);
 puts("ACTUAL extracted resize+insert allocationNULL rollback/old chains/retry bound/success rehash PASS; NOT full interpreter or device proof");return 0;
}
'''
rows=[]
for name,body in [('original',original),('guard',patched_engine(original))]:
    c=out/(name+'.c');c.write_text(preamble+'\n'+function(body,'fiber_resize_hash')+'\n'+function(body,'fiber_insert')+'\n'+tail)
    binary=out/name;cmd=['xcrun','clang','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(repo/'../.madeira-install/linux-steam-ipad/host'),'-Wall','-Wextra','-Werror','-Wno-unused-variable','-fsanitize=address,undefined','-fno-sanitize-recover=all',c,'-o',binary]
    with (out/(name+'-build.log')).open('x') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/(name+'.log')).open('x') as f:r=subprocess.run([binary,'negative' if name=='original' else 'guard'],stdout=f,stderr=subprocess.STDOUT,timeout=20,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
    log=(out/(name+'.log')).read_text();assert (r.returncode!=0 and ('AddressSanitizer' in log or 'runtime error' in log)) if name=='original' else r.returncode==0
    rows.append({'mode':name,'exit':r.returncode,'log_sha256':hashlib.sha256(log.encode()).hexdigest(),'actual_function_source_sha256':hashlib.sha256(c.read_bytes()).hexdigest()})
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual extracted pinned resize/insert plus real structs/list; unrelated page hooks neutralized. Original failure MUST reproduce, guarded rollback/bounded no retry/success rehash. NOT full engine/cache flush/device/CEF proof','tests':rows,'linuxrunner':pin,'transform_sha256':hashlib.sha256(Path(__file__).with_name('fiber_hash_patch.py').read_bytes()).hexdigest()},indent=2)+'\n')
print('HOST original unchecked failure reproduced; actual guarded resize/insert ownership controls PASS')
