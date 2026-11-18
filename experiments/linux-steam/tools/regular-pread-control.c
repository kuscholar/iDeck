/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY exact sys_pread + real pinned fd/PTE operations. */
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "kernel/errno.h"
#include "kernel/mm.h"
#include "fs/real.h"
#include "fs/fd.h"
extern ssize_t realfs_pread(struct fd *,void *,size_t,off_t);
static int armed,fail_large,fail_all,backend_fail,short_read;
static unsigned allocations,backend_calls,frees;
static size_t peak;
static void *owned;
void *ideck_test_pread_malloc(size_t n){
 if(armed){allocations++;if(n>peak)peak=n;if(fail_all||(fail_large&&n>1024*1024)){errno=ENOMEM;return NULL;}}
 void *p=malloc(n);if(armed){assert(!owned);owned=p;}return p;
}
void ideck_test_pread_free(void *p){if(p&&p==owned){frees++;owned=NULL;}free(p);}
ssize_t ideck_test_pread_backend(struct fd *fd,void *p,size_t size,off_t off){
 backend_calls++;if(backend_fail&&(int)backend_calls==backend_fail)return _ENOMEM;
 if(short_read&&size>100)size=100;return realfs_pread(fd,p,size,off);
}
static void bytes(addr_t address,size_t count,off_t_ off){
 unsigned char block[4096];size_t done=0;
 while(done<count){size_t n=count-done<sizeof block?count-done:sizeof block;
  assert(!user_read(address+done,block,n));
  for(size_t i=0;i<n;i++)assert(block[i]==(unsigned char)(((uint64_t)off+done+i)*17+3));done+=n;
 }
}
int main(int argc,char **argv){
 assert(argc==4);int enabled=atoi(argv[1]);const char *mode=argv[2];const size_t total=0x4ee50f;
 assert(!mount_root(&realfs,"/")&&!become_first_process());
 struct fd *file=generic_open(argv[3],O_RDONLY_,0);assert(!IS_ERR(file));
 struct fd_ops memops={0};struct fd_ops ops=*file->ops;ops.pread=ideck_test_pread_backend;file->ops=&ops;
 fd_t number=f_install(file,0);assert(number>=0);fd_t fixture_number=number;
 addr_t address=0x6000000;pages_t pages=(total+8191)/4096;assert(!pt_map_nothing(current->mem,PAGE(address),pages,P_READ|P_WRITE));
 assert((sdword_t)sys_lseek64(number,17,LSEEK_SET)==17);
 dword_t size=total;off_t_ offset=0;sdword_t expected=total;int nonregular=0;
 if(!strcmp(mode,"large-refusal")){fail_large=1;if(!enabled)expected=_ENOMEM;}
 else if(!strcmp(mode,"scratch-refusal")){fail_all=1;expected=_ENOMEM;}
 else if(!strcmp(mode,"backend-refusal")){backend_fail=1;expected=_ENOMEM;}
 else if(!strcmp(mode,"partial-backend-refusal")){backend_fail=2;if(enabled)expected=65536;}
 else if(!strcmp(mode,"short")){short_read=1;expected=100;}
 else if(!strcmp(mode,"eof")){offset=total-100;size=total+123;expected=100;}
 else if(!strcmp(mode,"zero")){size=0;expected=0;}
 else if(!strcmp(mode,"small")){size=4096;expected=4096;}
 else if(!strcmp(mode,"boundary")){size=65536;expected=65536;}
 else if(!strcmp(mode,"above-boundary")){size=65537;expected=65537;}
 else if(!strcmp(mode,"oversize")){size=16*1024*1024+1;expected=total;}
 else if(!strcmp(mode,"negative-offset")){offset=-1;expected=_EINVAL;}
 else if(!strcmp(mode,"bad-buffer")){address=0x7000000;expected=_EFAULT;}
 else if(!strcmp(mode,"bad-fd")){number=-1;expected=_EBADF;}
 else if(!strcmp(mode,"memfd-excluded")){
  addr_t name=0x6000000+total+128;const char label[]="pread-control";assert(!user_write(name,label,sizeof label));
  number=sys_memfd_create(name,0);assert(number>=0);struct fd *mem=f_get(number);assert(mem&&mem->memfd);
  memops=*mem->ops;memops.pread=ideck_test_pread_backend;mem->ops=&memops;
  assert((sdword_t)sys_lseek64(number,17,LSEEK_SET)==17);fail_large=1;expected=_ENOMEM;nonregular=1;
 }
 else if(!strcmp(mode,"pipe")){
  addr_t pipes=0x6000000+total+128;assert(!sys_pipe2(pipes,0));int pair[2];assert(!user_read(pipes,pair,sizeof pair));
  number=pair[0];expected=_ESPIPE;nonregular=1;assert(!sys_close(pair[1]));
 }else assert(!strcmp(mode,"normal"));
 unsigned refs=atomic_load(&file->refcount);struct fd *read_file=number>=0?f_get(number):NULL;unsigned read_refs=read_file?atomic_load(&read_file->refcount):0;armed=1;sdword_t result=(sdword_t)sys_pread(number,address,size,offset);armed=0;
 assert(result==expected);assert(!owned);assert(atomic_load(&file->refcount)==refs);if(read_file)assert(atomic_load(&read_file->refcount)==read_refs);
 if(result>0)bytes(address,(size_t)result,offset);
 if(!nonregular&&number>=0)assert((sdword_t)sys_lseek64(number,0,LSEEK_CUR)==17);
 if(!strcmp(mode,"memfd-excluded"))assert(peak==total+1&&backend_calls==0);
 if(!strcmp(mode,"large-refusal"))assert(enabled?(peak==65536&&allocations==1&&frees==1&&backend_calls>1):(backend_calls==0&&allocations==1&&frees==0));
 if(!strcmp(mode,"backend-refusal"))assert(backend_calls==1&&allocations==1&&frees==1);
 if(!strcmp(mode,"scratch-refusal"))assert(backend_calls==0&&allocations==1&&frees==0);
 if(!strcmp(mode,"small")||!strcmp(mode,"boundary")||!strcmp(mode,"zero")||!strcmp(mode,"oversize")||!strcmp(mode,"negative-offset"))assert(peak==(size_t)size+1);
 if(!strcmp(mode,"normal")&&enabled)assert(peak==65536&&allocations==1&&frees==1);
 if(nonregular)assert(!sys_close(number));
 assert(!sys_close(fixture_number));
 printf("mode=%s enabled=%d result=%d scratch_peak=%zu backend_calls=%u allocations=%u frees=%u complete=PASS\n",mode,enabled,result,peak,backend_calls,allocations,frees);
 return 0;
}
