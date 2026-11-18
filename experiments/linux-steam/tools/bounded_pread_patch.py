# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Transform only a pinned private copy; preserve the ordinary pread path."""
PIN='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
HELPER=r'''
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include "NativeKernelLog.h"
extern ssize_t realfs_pread(struct fd *,void *,size_t,off_t);
/* Lab-only regular real/fakefs file reads, excluding memfd and other backends.
 * Never retry a failed allocation or backend operation. Full-count regular
 * reads use sequential explicit offsets and a bounded native scratch buffer.
 * Partial progress, EOF and errors remain visible; no bytes are synthesized.
 */
const char *ideck_bounded_pread_marker(void){return "IDECK_BOUNDED_REGULAR_PREAD_V1";}
static void ideck_pread_note(dword_t requested,dword_t done,sdword_t result,
                            unsigned calls,int allocation_failed,int copy_failed,int backend_error){
    static atomic_uint success_rows,failure_rows;
    atomic_uint *counter=(result<0||copy_failed||backend_error)?&failure_rows:&success_rows;
    if(atomic_fetch_add_explicit(counter,1,memory_order_relaxed)>=8)return;
    char line[240];snprintf(line,sizeof line,
        "IDECK_BOUNDED_REGULAR_PREAD_V1 requested=%llu scratch=65536 completed=%llu result=%lld backend_calls=%u allocation_failed=%d copy_failed=%d backend_error=%d payload_logged=0",
        (unsigned long long)requested,(unsigned long long)done,(long long)result,
        calls,allocation_failed,copy_failed,backend_error);ideck_native_log_line(line);
}
static dword_t ideck_regular_pread(struct fd *fd,addr_t address,dword_t size,off_t_ offset){
    char *scratch=malloc(65536);
    if(!scratch){ideck_pread_note(size,0,_ENOMEM,0,1,0,0);return _ENOMEM;}
    dword_t done=0;sdword_t result=0;unsigned calls=0;int copy_failed=0,backend_error=0;
    lock(&fd->lock);
    while(done<size){
        size_t part=size-done>65536?65536:(size_t)(size-done);
        ssize_t n=fd->ops->pread(fd,scratch,part,offset+(off_t_)done);calls++;
        if(n<0){backend_error=(int)n;result=done?(sdword_t)done:n;break;}
        if((size_t)n>part){result=done?(sdword_t)done:_EIO;break;}
        if(n==0){result=done;break;}
        if(user_write(address+done,scratch,(size_t)n)){
            copy_failed=1;result=done?(sdword_t)done:_EFAULT;break;
        }
        done+=(dword_t)n;result=(sdword_t)done;
        if((size_t)n<part)break;
    }
    unlock(&fd->lock);free(scratch);
    ideck_pread_note(size,done,result,calls,0,copy_failed,backend_error);return (dword_t)result;
}
'''

def patched(body):
    signature='dword_t sys_pread(fd_t f, addr_t buf_addr, dword_t size, off_t_ off) {'
    assert body.count(signature)==1 and 'ideck_regular_pread' not in body
    begin=body.index(signature);end=body.index('\ndword_t sys_pwrite(',begin)
    function=body[begin:end]
    anchor='    char *buf = malloc((size_t)size+1);'
    assert function.count(anchor)==1
    guard='''    /* Scope the experiment to bounded-size regular-file requests. Existing
     * zero/small/oversized/negative-offset/memfd/nonregular paths stay intact. */
    if(size>65536 && size<=16*1024*1024 && off>=0 &&
       (uint64_t)off<=INT64_MAX-(uint64_t)size &&
       buf_addr<=(addr_t)-1-size && !fd->memfd && fd->ops->pread==realfs_pread){
        struct statbuf st;
        if(!realfs_fstat(fd,&st) && S_ISREG(st.mode)){
            dword_t result=ideck_regular_pread(fd,buf_addr,size,off);
            fd_close(fd);return result;
        }
    }
'''
    function=function.replace(anchor,guard+anchor,1)
    return body[:begin]+HELPER+'\n'+function+body[end:]
