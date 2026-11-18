/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY real pinned kernel ordinary mapping, no Steam/OS fixtures. */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "kernel/init.h"
#include "kernel/mm.h"
#include "kernel/task.h"
#include "kernel/errno.h"
#include "fs/real.h"
static unsigned fail_calloc,fail_malloc,nc,nm,live;static int armed;
static void *owned[8192];
static void record(void *p){if(!p)return;for(unsigned i=0;i<8192;i++)if(!owned[i]){owned[i]=p;live++;return;}abort();}
void *ideck_test_calloc(size_t n,size_t s){if(armed&&++nc==fail_calloc){errno=ENOMEM;return NULL;}void *p=calloc(n,s);record(p);return p;}
void *ideck_test_malloc(size_t s){if(armed&&++nm==fail_malloc){errno=ENOMEM;return NULL;}void *p=malloc(s);record(p);return p;}
void ideck_test_free(void *p){if(p)for(unsigned i=0;i<8192;i++)if(owned[i]==p){owned[i]=NULL;live--;break;}free(p);}
extern _Atomic uint64_t ideck_map_pte_allocation_failures;
static int baseline;
int main(int argc,char **argv){
 assert(argc==5);baseline=!strcmp(argv[1],"baseline");const char *kind=argv[2];
 assert(!mount_root(&realfs,"/")&&!become_first_process());
 fail_calloc=(unsigned)atoi(argv[3]);fail_malloc=(unsigned)atoi(argv[4]);
 struct mem *mem=current->mem;page_t start=0x80001e0,old_page=start+700;
 pages_t pages=1024;unsigned mapflags=P_READ|P_WRITE;
 int overlap=!strcmp(kind,"replace");
 if(!strcmp(kind,"none"))mapflags=0;
 if(overlap){assert(!pt_map_nothing(mem,old_page,1,P_READ|P_WRITE));}
 else {old_page=0x200;assert(!pt_map_nothing(mem,old_page,1,P_READ|P_WRITE));}
 struct pt_entry *entry=mem_pt(mem,old_page);assert(entry);
 struct data *old=entry->data;unsigned old_flags=entry->flags;unsigned refs=atomic_load(&old->refcount);
 *(unsigned char *)old->data=0x5a;
 assert(!pt_map_lazy(mem,0xa000000,5,P_READ));
 long count=atomic_load(&anon_page_count);unsigned initial_live=live;int initial_used=mem->pgdir_used;unsigned long changes=mem->mmu.changes;
 armed=1;int result=pt_map_nothing(mem,start,pages,mapflags);armed=0;
 if(fail_calloc||fail_malloc){
  assert(result==_ENOMEM);assert(atomic_load(&anon_page_count)==count);
  entry=mem_pt(mem,old_page);assert(entry&&entry->data==old&&entry->flags==old_flags&&atomic_load(&old->refcount)==refs);
  assert(*(unsigned char *)old->data==0x5a);
  for(page_t p=start;p<start+pages;p++)if(p!=old_page)assert(!mem_pt(mem,p));
  assert(mem->pgdir_used==initial_used&&live==initial_live&&mem->mmu.changes==changes);
  assert(mem_find_reservation(mem,0xa000000)!=NULL);
  /* A normal retry after the one-shot HOST refusal must still work. */
  assert(!pt_map_nothing(mem,start,pages,mapflags));
  assert(!pt_unmap(mem,start,pages));
  assert(atomic_load(&anon_page_count)==count-(overlap?1:0));
 }else{
  assert(!result);entry=mem_pt(mem,start);assert(entry);
  struct data *data=entry->data;assert(atomic_load(&data->refcount)==pages);
  assert(atomic_load(&anon_page_count)==count+((mapflags&P_WRITE)?(long)pages:0)-(overlap?1:0));
  for(page_t p=start;p<start+pages;p++){entry=mem_pt(mem,p);assert(entry&&entry->data==data&&entry->offset==(p-start)*PAGE_SIZE);}
  assert(!pt_unmap(mem,start,pages));assert(atomic_load(&anon_page_count)==count-(overlap?1:0));
 }
 if(!baseline&&fail_calloc)assert(atomic_load(&ideck_map_pte_allocation_failures)==1);
 printf("real kernel ordinary map kind=%s calloc=%u malloc=%u result=%d rollback=PASS\n",kind,nc,nm,result);
 return 0;
}
