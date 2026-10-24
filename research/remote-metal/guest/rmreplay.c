/* End-to-end: build a winemetal-shaped command list, pack it with the REAL
 * packer, ship it, and have the host validate and replay it onto a Metal
 * encoder -- then read the pixels back and check the geometry.
 *
 * This closes the loop. Everything upstream was proven separately: the packer
 * against 41,994 live records, the validator against 88 tests, the transport
 * and control plane against the host GPU. Nothing had yet decoded a packed
 * batch into actual draw calls.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include "../protocol.h"
#include "../wmt_pack.h"

static int g_fd; static uint32_t g_seq;
static int rd(int fd,void*p,size_t n){uint8_t*b=p;while(n){ssize_t r=read(fd,b,n);if(r<=0)return -1;b+=r;n-=(size_t)r;}return 0;}
static int wr(int fd,const void*p,size_t n){const uint8_t*b=p;while(n){ssize_t r=write(fd,b,n);if(r<=0)return -1;b+=r;n-=(size_t)r;}return 0;}
static uint32_t call(uint16_t op,const void*arg,uint32_t alen,void*out,uint32_t ocap,uint32_t*olen){
    if (out&&ocap) memset(out,0,ocap); if (olen) *olen=0;
    struct rm_hdr h={RM_MAGIC,RM_VERSION,op,++g_seq,0,alen,0};
    if(wr(g_fd,&h,sizeof h))return 0xffffffff;
    if(alen&&wr(g_fd,arg,alen))return 0xffffffff;
    struct rm_hdr r; if(rd(g_fd,&r,sizeof r))return 0xffffffff;
    if(r.magic!=RM_MAGIC||r.version!=RM_VERSION||r.opcode!=op||r.seq!=h.seq)return 0xffffffff;
    uint32_t n=r.payload_len,take=(out&&n)?(n<ocap?n:ocap):0;
    if(take&&rd(g_fd,out,take))return 0xffffffff;
    for(uint32_t l=n-take;l;){uint8_t s[4096];uint32_t c=l<sizeof s?l:(uint32_t)sizeof s;if(rd(g_fd,s,c))return 0xffffffff;l-=c;}
    if(olen)*olen=take; return r.status;
}

static uint8_t recbuf[WMTW_MAX_BATCH_BYTES], sidebuf[WMTW_MAX_SIDECAR_BYTES];

int main(int argc,char**argv){
    const char*host=argc>1?argv[1]:"10.0.1.53";
    g_fd=socket(AF_INET,SOCK_STREAM,0);
    struct sockaddr_in a={.sin_family=AF_INET,.sin_port=htons(RM_PORT)};
    inet_pton(AF_INET,host,&a.sin_addr);
    if(connect(g_fd,(struct sockaddr*)&a,sizeof a)){perror("connect");return 1;}
    int one=1; setsockopt(g_fd,IPPROTO_TCP,TCP_NODELAY,&one,sizeof one);
    setsockopt(g_fd,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof one);
    const char*tok=getenv("RMETAL_TOKEN");
    if(!tok||call(RM_OP_PING,tok,(uint32_t)strlen(tok),0,0,0)!=RM_OK){fprintf(stderr,"auth failed\n");return 1;}
    printf("[rmreplay] connected\n\n");

    struct rm_ret_handle rh; struct rm_ret_u64 ru; struct rm_ret_resource rr; uint32_t st;
    call(RM_OP_COPY_ALL_DEVICES,0,0,&rh,sizeof rh,0); uint64_t arr=rh.handle;
    struct rm_arg_handle_u64 ao={arr,0};
    call(RM_OP_ARRAY_OBJECT,&ao,sizeof ao,&rh,sizeof rh,0); uint64_t dev=rh.handle;
    struct rm_arg_handle ad={dev};
    /* v3: the queue call carries maxCommandBufferCount. */
    struct rm_arg_handle_u64 qarg = { dev, 64 };
    call(RM_OP_NEW_COMMAND_QUEUE,&qarg,sizeof qarg,&rh,sizeof rh,0); uint64_t queue=rh.handle;

    /* vertex buffer via the chunked path */
    static const float verts[6]={0.0f,0.8f,-0.8f,-0.8f,0.8f,-0.8f};
    struct rm_buffer_create bc={dev,sizeof verts,0,0};
    call(RM_OP_BUFFER_CREATE,&bc,sizeof bc,&rr,sizeof rr,0);
    uint64_t vbuf=rr.handle;
    uint8_t vm[sizeof(struct rm_buffer_range)+sizeof verts];
    struct rm_buffer_range*vr=(void*)vm; vr->handle=vbuf; vr->offset=0; vr->length=sizeof verts;
    memcpy(vm+sizeof *vr,verts,sizeof verts);
    call(RM_OP_BUFFER_WRITE,vm,(uint32_t)sizeof vm,0,0,0);

    /* render target */
    struct rm_texture_desc td; memset(&td,0,sizeof td);
    td.device=dev; td.pixel_format=80; td.width=64; td.height=64; td.depth=1;
    td.array_length=1; td.type=2; td.mipmap_level_count=1; td.sample_count=1;
    td.usage=1|4 /*shaderRead|renderTarget*/;
    call(RM_OP_NEW_TEXTURE_INFO,&td,sizeof td,&rr,sizeof rr,0);
    uint64_t tex=rr.handle;

    /* pipeline from a metallib blob */
    const char*blob=argc>2?argv[2]:"/tmp/draw.metallib";
    FILE*f=fopen(blob,"rb"); if(!f){printf("  no metallib at %s\n",blob);return 1;}
    fseek(f,0,SEEK_END); long bl=ftell(f); fseek(f,0,SEEK_SET);
    uint8_t*bb=malloc((size_t)bl);
    if (fread(bb,1,(size_t)bl,f)!=(size_t)bl) return 1; fclose(f);
    call(RM_OP_DISPATCH_DATA,bb,(uint32_t)bl,&rh,sizeof rh,0); uint64_t dd=rh.handle;
    struct rm_arg_handle_u64 al={dev,dd};
    st=call(RM_OP_NEW_LIBRARY_DATA,&al,sizeof al,&rh,sizeof rh,0);
    if(st!=RM_OK){printf("  library FAILED\n");return 1;}
    uint64_t lib=rh.handle, fn[2];
    const char*fns[2]={"vmain","fmain"};
    for(int i=0;i<2;i++){
        uint8_t fbuf[sizeof(struct rm_arg_handle)+32];
        struct rm_arg_handle*fa=(void*)fbuf; fa->handle=lib;
        size_t n=strlen(fns[i]); memcpy(fbuf+sizeof *fa,fns[i],n);
        call(RM_OP_NEW_FUNCTION,fbuf,(uint32_t)(sizeof *fa+n),&rh,sizeof rh,0);
        fn[i]=rh.handle;
    }
    struct rm_new_pipeline np={dev,fn[0],fn[1],80};
    st=call(RM_OP_NEW_RENDER_PIPELINE,&np,sizeof np,&rh,sizeof rh,0);
    if(st!=RM_OK){printf("  pipeline FAILED\n");return 1;}
    uint64_t pso=rh.handle;
    printf("  resources ready (all remote handles)\n");

    /* ---- pack a batch with the REAL packer ---- */
    struct wmtw_packer p={recbuf,sizeof recbuf,0,sidebuf,sizeof sidebuf,0,0};
    struct wmtw_viewport vp={0,0,64,64,0,1};
    struct wmtw_setviewports*sv=wmtw_rec_alloc(&p,sizeof *sv,WMTW_OP_SetViewports);
    sv->viewports_offset=wmtw_side_put(&p,&vp,sizeof vp); sv->viewports_count=1;
    struct wmtw_setpso*sp=wmtw_rec_alloc(&p,sizeof *sp,WMTW_OP_SetPSO); sp->pso=pso;
    struct wmtw_setvertexbuffer*sb=wmtw_rec_alloc(&p,sizeof *sb,WMTW_OP_SetVertexBuffer);
    sb->buffer=vbuf; sb->offset=0; sb->index=0;
    struct wmtw_draw*dr=wmtw_rec_alloc(&p,sizeof *dr,WMTW_OP_Draw);
    dr->primitive=3; dr->start=0; dr->count=3; dr->instances=1; dr->base_instance=0;

    static uint8_t msg[sizeof(struct rm_wmt_submit)+sizeof(struct wmtw_batch)
                       +WMTW_MAX_BATCH_BYTES+WMTW_MAX_SIDECAR_BYTES];
    struct rm_wmt_submit*sub=(void*)msg;
    memset(sub,0,sizeof *sub);
    sub->queue=queue; sub->color_texture=tex; sub->present_drawable=0;
    sub->clear_a=1.0;
    struct wmtw_batch*wb=(void*)(msg+sizeof *sub);
    wb->magic=WMTW_BATCH_MAGIC; wb->version=WMTW_VERSION; wb->encoder_kind=0;
    wb->record_bytes=p.rec_len; wb->record_count=p.count;
    wb->sidecar_bytes=p.side_len; wb->reserved=0;
    memcpy(msg+sizeof *sub+sizeof *wb,recbuf,p.rec_len);
    memcpy(msg+sizeof *sub+sizeof *wb+p.rec_len,sidebuf,p.side_len);
    sub->batch_bytes=(uint32_t)(sizeof *wb+p.rec_len+p.side_len);

    st=call(RM_OP_SUBMIT_WMT_BATCH,msg,(uint32_t)(sizeof *sub+sub->batch_bytes),&ru,sizeof ru,0);
    printf("  submit packed batch    -> %s, %llu records replayed\n",
           st==RM_OK?"OK":"FAIL (see host log)",(unsigned long long)ru.value);
    if(st!=RM_OK) return 1;

    /* ---- verify the pixels ---- */
    static uint8_t px[64*64*4]; uint32_t got=0;
    struct rm_arg_handle at={tex};
    call(RM_OP_TEXTURE_GETBYTES,&at,sizeof at,px,sizeof px,&got);
    uint32_t lit=0;
    for(uint32_t i=0;i+3<got;i+=4) if(px[i]||px[i+1]||px[i+2]) lit++;
    printf("  readback               -> %u bytes, %u/%u lit (%.1f%%)\n",
           got,lit,got/4,100.0*lit/(got/4.0));
    printf("  %s\n",(lit>400&&lit<2600)
        ? "REAL PACKED BATCH REPLAYED AND RASTERISED ON THE HOST GPU"
        : "*** unexpected coverage ***");
    close(g_fd); return 0;
}
