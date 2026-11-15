/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "BlockedWaitCallers.h"
#include "kernel/memory.h"
#include <string.h>
#include <stdbool.h>
#include <stdint.h>

static bool existing(struct mem *mem,uint64_t address,void *output,size_t bytes,bool code) {
    if(address>>48 || bytes>PAGE_SIZE || PGOFFSET(address)>PAGE_SIZE-bytes)return false;
    struct pt_entry *p=mem_pt(mem,PAGE(address));
    if(!p||!p->data||!p->data->data)return false;
    if(code){
        if((p->flags&(P_READ|P_EXEC))!=(P_READ|P_EXEC)||!p->data->fd)return false;
    }else{
        unsigned wanted=P_READ|P_WRITE|P_ANONYMOUS|P_GROWSDOWN;
        if((p->flags&wanted)!=wanted||(p->flags&P_EXEC)||p->data->fd)return false;
    }
    size_t low=PGOFFSET(address);
    if(p->offset>p->data->size||low>p->data->size-p->offset||
       bytes>p->data->size-p->offset-low)return false;
    memcpy(output,(char *)p->data->data+p->offset+low,bytes);return true;
}
void ideck_blocked_wait_callers(struct mem *mem,uint64_t fp,struct ideck_wait_callers *out){
    if(!out)return;memset(out,0,sizeof *out);
    if(!mem){out->status=2;return;}
    if(!read_wrtrylock(&mem->lock)){out->status=1;return;}
    uint64_t first=fp;
    for(unsigned i=0;i<IDECK_WAIT_CALLER_LIMIT;i++){
        if(!fp)break;
        if((fp&15)||fp>>48||fp<first||fp-first>1024*1024){out->status=4;break;}
        uint64_t abi[2];
        if(!existing(mem,fp,abi,sizeof abi,false)){out->status=2;break;}
        uint64_t lr=abi[1];struct ideck_wait_caller row={.lr=lr};
        if(lr<16||(lr&3)||lr>>48||!existing(mem,lr-16,row.code,sizeof row.code,true)){
            out->status=3;break;
        }
        uint32_t call=row.code[3];
        if((call&0xfc000000u)!=0x94000000u&&(call&0xfffffc1fu)!=0xd63f0000u){out->status=3;break;}
        out->frames[out->count++]=row;
        if(!abi[0])break;
        if(abi[0]<=fp||abi[0]-fp>1024*1024){out->status=4;break;}
        fp=abi[0];
    }
    read_wrunlock(&mem->lock);
}
const char *ideck_blocked_wait_callers_marker(void){return "IDECK_BLOCKED_WAIT_CALLERS_V1";}
