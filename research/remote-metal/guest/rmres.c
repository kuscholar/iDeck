/* Resource control-plane test: walks the dependency chain the API census
 * observed a real workload using, in that order.
 *
 *   DispatchData blob -> newLibrary -> newFunction -> computePipelineState
 *
 * Uses a precompiled metallib blob rather than shader source, because that is
 * what DXMT actually does -- newLibraryWithSource is what a hand-written test
 * reaches for and is not the path in the census.
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

static int g_fd; static uint32_t g_seq;
static int rd(int fd, void *p, size_t n){uint8_t*b=p;while(n){ssize_t r=read(fd,b,n);if(r<=0)return -1;b+=r;n-=(size_t)r;}return 0;}
static int wr(int fd, const void *p, size_t n){const uint8_t*b=p;while(n){ssize_t r=write(fd,b,n);if(r<=0)return -1;b+=r;n-=(size_t)r;}return 0;}

static uint32_t call(uint16_t op, const void *arg, uint32_t alen, void *out, uint32_t ocap, uint32_t *olen) {
    /* Clear the output FIRST. Without this a failed call that returns no
     * payload leaves the caller's buffer holding the PREVIOUS call's handle,
     * and the caller then reports success on a stale value -- which is exactly
     * how newCommandQueue could print OK while having failed. */
    if (out && ocap) memset(out, 0, ocap);
    if (olen) *olen = 0;
    struct rm_hdr h = { RM_MAGIC, RM_VERSION, op, ++g_seq, 0, alen, 0 };
    if (wr(g_fd,&h,sizeof h)) return 0xffffffff;
    if (alen && wr(g_fd,arg,alen)) return 0xffffffff;
    struct rm_hdr r; if (rd(g_fd,&r,sizeof r)) return 0xffffffff;
    /* Validate the whole reply header, not just magic. A desynchronised stream
     * otherwise attributes one call's answer to another. */
    if (r.magic != RM_MAGIC || r.version != RM_VERSION ||
        r.opcode != op || r.seq != h.seq) {
        fprintf(stderr, "  REPLY MISMATCH op=%u/%u seq=%u/%u magic=%08x ver=%u\n",
                r.opcode, op, r.seq, h.seq, r.magic, r.version);
        return 0xffffffff;
    }
    uint32_t n=r.payload_len, take=(out&&n)?(n<ocap?n:ocap):0;
    if (take && rd(g_fd,out,take)) return 0xffffffff;
    for (uint32_t left=n-take; left;) { uint8_t s[4096];
        uint32_t c=left<sizeof s?left:(uint32_t)sizeof s; if (rd(g_fd,s,c)) return 0xffffffff; left-=c; }
    if (olen) *olen = take;
    return r.status;
}

int main(int argc, char **argv) {
    const char *host = argc>1?argv[1]:"10.0.1.53";
    const char *blobpath = argc>2?argv[2]:"/tmp/test.metallib";
    g_fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = { .sin_family=AF_INET, .sin_port=htons(RM_PORT) };
    inet_pton(AF_INET, host, &a.sin_addr);
    if (connect(g_fd,(struct sockaddr*)&a,sizeof a)) { perror("connect"); return 1; }
    int one=1; setsockopt(g_fd,IPPROTO_TCP,TCP_NODELAY,&one,sizeof one);
    setsockopt(g_fd,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof one);
    const char *tok = getenv("RMETAL_TOKEN");
    if (!tok || call(RM_OP_PING, tok, (uint32_t)strlen(tok), 0,0,0) != RM_OK) {
        fprintf(stderr,"auth failed\n"); return 1; }
    printf("[rmres] connected\n\n  [control plane, census order]\n");

    struct rm_ret_handle rh; struct rm_ret_u64 ru; uint32_t st;
    call(RM_OP_COPY_ALL_DEVICES, 0,0, &rh,sizeof rh,0);
    uint64_t arr = rh.handle;
    struct rm_arg_handle_u64 ao = { arr, 0 };
    call(RM_OP_ARRAY_OBJECT, &ao,sizeof ao, &rh,sizeof rh,0);
    uint64_t dev = rh.handle;
    printf("    device                -> handle=%#llx remote=%d\n",
           (unsigned long long)dev, (int)((dev >> 63) & 1));

    struct rm_arg_handle ad = { dev };
    st = call(RM_OP_NEW_COMMAND_QUEUE, &ad,sizeof ad, &rh,sizeof rh,0);
    printf("    newCommandQueue       -> %s handle=%#llx\n",
           (st==RM_OK && rh.handle) ? "OK" : "FAIL", (unsigned long long)rh.handle);

    /* --- DispatchData blob --- */
    FILE *f = fopen(blobpath, "rb");
    if (!f) { printf("    (no metallib at %s -- skipping library chain)\n", blobpath);
              close(g_fd); return 0; }
    fseek(f,0,SEEK_END); long blen = ftell(f); fseek(f,0,SEEK_SET);
    uint8_t *blob = malloc((size_t)blen);
    if (fread(blob,1,(size_t)blen,f) != (size_t)blen) { printf("    blob read failed\n"); return 1; }
    fclose(f);
    st = call(RM_OP_DISPATCH_DATA, blob, (uint32_t)blen, &rh,sizeof rh,0);
    uint64_t dd = rh.handle;
    printf("    DispatchData (%ld b)   -> %s handle=%#llx\n", blen,
           st==RM_OK?"OK":"FAIL", (unsigned long long)dd);

    struct rm_arg_handle_u64 al = { dev, dd };
    st = call(RM_OP_NEW_LIBRARY_DATA, &al,sizeof al, &rh,sizeof rh,0);
    uint64_t lib = rh.handle;
    printf("    newLibrary(from data) -> %s\n", st==RM_OK?"OK":"FAIL (see host log)");
    if (st != RM_OK) { close(g_fd); return 1; }

    uint8_t fb[sizeof(struct rm_arg_handle)+32];
    struct rm_arg_handle *fa = (void*)fb; fa->handle = lib;
    const char *fname = argc>3?argv[3]:"cs_main";
    size_t fl = strlen(fname); memcpy(fb+sizeof *fa, fname, fl);
    st = call(RM_OP_NEW_FUNCTION, fb, (uint32_t)(sizeof *fa+fl), &rh,sizeof rh,0);
    uint64_t fn = rh.handle;
    printf("    newFunction(\"%s\")  -> %s\n", fname, (st==RM_OK && fn)?"OK":"FAIL");

    if (fn) {
        /* The real descriptor, with immutable-buffer flags set, to prove the
         * fields cross rather than just the two handles. */
        struct rm_compute_pso pso;
        memset(&pso, 0, sizeof pso);
        pso.device = dev; pso.function = fn;
        pso.immutable_buffers = 0x5;      /* buffers 0 and 2 immutable */
        pso.tgsize_multiple_of_sgwidth = 1;
        pso.num_archives = 0;
        st = call(RM_OP_NEW_COMPUTE_PSO, &pso,sizeof pso, &rh,sizeof rh,0);
        printf("    newComputePSO(desc)   -> %s handle=%#llx\n",
               (st==RM_OK && rh.handle)?"OK":"FAIL (see host log)",
               (unsigned long long)rh.handle);
    }

    /* --- in/out descriptors: the reply must carry the OUT fields back --- */
    printf("\n  [in/out descriptors]\n");
    struct rm_ret_resource rr;
    {
        struct rm_dss_desc d; memset(&d, 0, sizeof d);
        d.device = dev; d.depth_compare_function = 1 /*less*/; d.depth_write_enabled = 1;
        d.front.enabled = 1; d.front.compare_function = 7 /*always*/; d.front.write_mask = 0xff;
        st = call(RM_OP_NEW_DEPTH_STENCIL, &d,sizeof d, &rr,sizeof rr,0);
        printf("    newDepthStencilState  -> %s handle=%#llx\n",
               (st==RM_OK && rr.handle)?"OK":"FAIL", (unsigned long long)rr.handle);
    }
    {
        struct rm_sampler_desc d; memset(&d, 0, sizeof d);
        d.device = dev; d.min_filter = 1; d.mag_filter = 1; d.mip_filter = 2;
        d.r_address = d.s_address = d.t_address = 0 /*clampToEdge*/;
        d.max_anisotropy = 4; d.lod_max_clamp = 1000.0f; d.normalized_coords = 1;
        d.support_argument_buffers = 1;
        st = call(RM_OP_NEW_SAMPLER, &d,sizeof d, &rr,sizeof rr,0);
        printf("    newSamplerState       -> %s handle=%#llx gpu_resource_id=%#llx\n",
               (st==RM_OK && rr.handle)?"OK":"FAIL", (unsigned long long)rr.handle,
               (unsigned long long)rr.gpu_resource_id);
    }
    {
        struct rm_texture_desc d; memset(&d, 0, sizeof d);
        d.device = dev; d.pixel_format = 80 /*BGRA8Unorm*/;
        d.width = 256; d.height = 256; d.depth = 1; d.array_length = 1;
        d.type = 2 /*type2D*/; d.mipmap_level_count = 1; d.sample_count = 1;
        d.usage = 1 /*shaderRead*/;
        st = call(RM_OP_NEW_TEXTURE_INFO, &d,sizeof d, &rr,sizeof rr,0);
        printf("    newTexture(desc)      -> %s handle=%#llx gpu_resource_id=%#llx mach_port=%u\n",
               (st==RM_OK && rr.handle)?"OK":"FAIL", (unsigned long long)rr.handle,
               (unsigned long long)rr.gpu_resource_id, rr.mach_port);
        if (st==RM_OK && rr.mach_port != 0)
            printf("    *** mach_port must be 0: a port name cannot cross machines ***\n");
    }

    /* --- chunked buffer transfer + round-trip integrity --- */
    printf("\n  [chunked buffer transfer]\n");
    {
        const uint64_t BIG = 40ull << 20;      /* 40MB: several chunks */
        struct rm_buffer_create bc = { dev, BIG, 0, 0 };
        st = call(RM_OP_BUFFER_CREATE, &bc,sizeof bc, &rr,sizeof rr,0);
        uint64_t buf = rr.handle;
        printf("    create %lluMB          -> %s gpuAddress=%#llx\n",
               (unsigned long long)(BIG>>20), (st==RM_OK&&buf)?"OK":"FAIL",
               (unsigned long long)rr.gpu_resource_id);
        if (st != RM_OK) { close(g_fd); return 1; }

        /* deterministic pattern so a wrong offset shows up as a mismatch */
        uint8_t *src = malloc(RM_CHUNK_BYTES);
        uint8_t *msg = malloc(sizeof(struct rm_buffer_range) + RM_CHUNK_BYTES);
        double t0 = 0; uint64_t sent = 0; unsigned chunks = 0;
        for (uint64_t off = 0; off < BIG; ) {
            uint64_t n = BIG - off; if (n > RM_CHUNK_BYTES) n = RM_CHUNK_BYTES;
            for (uint64_t i = 0; i < n; i++) src[i] = (uint8_t)((off + i) * 31u);
            struct rm_buffer_range *br = (void *)msg;
            br->handle = buf; br->offset = off; br->length = n;
            memcpy(msg + sizeof *br, src, (size_t)n);
            st = call(RM_OP_BUFFER_WRITE, msg, (uint32_t)(sizeof *br + n), 0,0,0);
            if (st != RM_OK) { printf("    write @%llu FAILED\n", (unsigned long long)off); break; }
            off += n; sent += n; chunks++;
        }
        printf("    upload                -> %s %u chunks, %lluMB\n",
               st==RM_OK?"OK":"FAIL", chunks, (unsigned long long)(sent>>20));

        /* read three ranges back and verify the pattern, including a
         * deliberately unaligned one that must land at the right offset */
        uint8_t *back = malloc(RM_CHUNK_BYTES);
        uint64_t probes[3] = { 0, 12345, BIG - 4096 };
        int mismatch = 0;
        for (int k = 0; k < 3; k++) {
            uint64_t off = probes[k], n = 4096; uint32_t got = 0;
            struct rm_buffer_range br = { buf, off, n };
            st = call(RM_OP_BUFFER_READ, &br,sizeof br, back, (uint32_t)n, &got);
            if (st != RM_OK || got != n) { mismatch++; continue; }
            for (uint64_t i = 0; i < n; i++)
                if (back[i] != (uint8_t)((off + i) * 31u)) { mismatch++; break; }
        }
        printf("    readback @0/12345/end -> %s\n", mismatch ? "*** MISMATCH ***" : "all 3 ranges verified");

        /* out-of-range write must be REJECTED, not silently clamped */
        struct rm_buffer_range bad = { buf, BIG - 16, 4096 };
        uint8_t badmsg[sizeof bad + 4096];
        memcpy(badmsg, &bad, sizeof bad);
        st = call(RM_OP_BUFFER_WRITE, badmsg, (uint32_t)(sizeof bad + 4096), 0,0,0);
        printf("    write past end        -> %s\n",
               st != RM_OK ? "rejected" : "*** ACCEPTED, would corrupt host memory ***");
        free(src); free(msg); free(back);
    }

    call(RM_OP_STATS, 0,0, &ru,sizeof ru,0);
    printf("\n  live handles on host: %llu\n", (unsigned long long)ru.value);
    close(g_fd); return 0;
}
