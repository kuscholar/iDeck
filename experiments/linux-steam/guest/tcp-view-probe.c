/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Freestanding actual ARM64 Linux syscall control; no host/socket mocks.
 */
static long call(long n,long a,long b,long c,long d,long e,long f) {
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8) : "memory","cc");
    return x0;
}
static long c3(long n,long a,long b,long c) { return call(n,a,b,c,0,0,0); }
static unsigned len(const char *s) { unsigned n=0;while(s[n])n++;return n; }
static long report_fd=-1;
static void out(const char *s) { c3(64,1,(long)s,len(s));if(report_fd>=0)c3(64,report_fd,(long)s,len(s)); }
static int failures;
static void check(const char *s,int ok) {out(s);out(ok?"=PASS\n":"=FAIL\n");if(!ok)failures++;}
static void closefd(long fd) {if(fd>=0)c3(57,fd,0,0);}
static unsigned decimal(char *b,unsigned long n) {char t[24];unsigned c=0;do{t[c++]=(char)('0'+n%10);n/=10;}while(n);for(unsigned i=0;i<c;i++)b[i]=t[c-i-1];b[c]=0;return c;}
static int starts(const char *s,const char *prefix) {while(*prefix)if(*s++!=*prefix++)return 0;return 1;}
static int has_inode(const char *table,unsigned long inode,int state) {
    const char *s=table;
    while(*s){const char *field[10]={0};unsigned count=0;
        while(*s&&*s!='\n'){while(*s==' '||*s=='\t')s++;if(!*s||*s=='\n')break;if(count<10)field[count]=s;count++;while(*s&&*s!=' '&&*s!='\t'&&*s!='\n')s++;}
        if(count>=10){unsigned long n=0;const char *p=field[9];while(*p>='0'&&*p<='9')n=n*10+(*p++-'0');
            int a=field[3][0],b=field[3][1];a=a<='9'?a-'0':a-'A'+10;b=b<='9'?b-'0':b-'A'+10;
            if(n==inode&&(state<0||a*16+b==state))return 1;}
        if(*s=='\n')s++;
    }return 0;
}
static char table[32768];
static int load(const char *path) {
    long fd=call(56,-100,(long)path,0,0,0,0);if(fd<0)return 0;
    long n=c3(63,fd,(long)table,sizeof table-1);closefd(fd);if(n<0)return 0;table[n]=0;return 1;
}
struct stat {unsigned long dev,ino;unsigned mode,nlink,uid,gid;unsigned long rest[12];};
static unsigned long inode(long fd) {struct stat st={0};return c3(80,fd,(long)&st,0)==0?st.ino:0;}
#if IDECK_TCP_LSOF
static int contains(const char *s,const char *needle) {for(;*s;s++)if(starts(s,needle))return 1;return 0;}
static int lsof_owner(int family,unsigned short network_port) {
    char endpoint[64]={0},expected[32]="p";
    const char *prefix=family==2?"TCP@127.0.0.1:":"TCP@[::1]:";
    unsigned end=0;while(prefix[end]){endpoint[end]=prefix[end];end++;}
    unsigned port=((unsigned)network_port>>8)|((unsigned)network_port<<8&0xffff);
    decimal(endpoint+end,port);decimal(expected+1,(unsigned long)c3(172,0,0,0));
    unsigned n=len(expected);expected[n]='\n';expected[n+1]=0;
    int pipe[2];if(c3(59,(long)pipe,0x80000,0))return 0;
    long pid=call(220,17,0,0,0,0,0);
    if(pid==0){closefd(pipe[0]);c3(24,pipe[1],1,0);closefd(pipe[1]);
        const char *argv[]={"/usr/bin/lsof","-P","-F","upnR","-i",endpoint,0};const char *env[]={"HOME=/root","PATH=/usr/bin:/bin",0};
        c3(221,(long)argv[0],(long)argv,(long)env);c3(94,127,0,0);__builtin_unreachable();}
    closefd(pipe[1]);char response[4096];unsigned used=0;long got;
    while(used<sizeof response-1&&(got=c3(63,pipe[0],(long)(response+used),sizeof response-1-used))>0)used+=(unsigned)got;
    response[used]=0;closefd(pipe[0]);int status=-1;
    int ok=pid>0&&call(260,pid,(long)&status,0,0,0,0)==pid&&status==0&&contains(response,expected);
    out("official-lsof-expected-owner-record=");out(response);return ok;
}
#endif
static void family_test(int family) {
    struct {unsigned short family,port;unsigned address;unsigned char extra[20];} addr={0};
    addr.family=(unsigned short)family;unsigned size=family==2?16:28;
    if(family==2)addr.address=0x0100007f;else addr.extra[15]=1;
    long listener=c3(198,family,1|0x80000,0),client=-1,accepted=-1,copy=-1;
    int ok=listener>=0&&c3(200,listener,(long)&addr,size)==0&&c3(201,listener,2,0)==0;
    unsigned got=size;ok=ok&&c3(204,listener,(long)&addr,(long)&got)==0&&got==size;
    client=c3(198,family,1|0x80000,0);ok=ok&&client>=0&&c3(203,client,(long)&addr,size)==0;
    if(ok)accepted=c3(202,listener,0,0);
    ok=ok&&accepted>=0;
    check(family==2?"tcp4-real-loopback-connect":"tcp6-real-loopback-connect",ok);
    if(!ok)goto cleanup;
    unsigned long li=inode(listener),ci=inode(client),ai=inode(accepted);
    check("tcp-distinct-open-description-inodes",li&&ci&&ai&&li!=ci&&li!=ai&&ci!=ai);
    copy=c3(23,listener,0,0);check("tcp-dup-same-inode",copy>=0&&inode(copy)==li);
    const char *path=family==2?"/proc/net/tcp":"/proc/net/tcp6";
    check("tcp-live-listen-established-rows",load(path)&&has_inode(table,li,10)&&has_inode(table,ci,1)&&has_inode(table,ai,1));
    char link[80]="/proc/self/fd/",value[80]={0},expected[80]="socket:[";
    decimal(link+14,(unsigned long)listener);unsigned at=8+decimal(expected+8,li);expected[at++]=']';expected[at]=0;
    long n=call(78,-100,(long)link,(long)value,sizeof value-1,0,0);if(n>=0)value[n]=0;
    check("tcp-proc-fd-matches-table-inode",n==(long)at&&starts(value,expected));
    check("tcp-self-net-alias",load(family==2?"/proc/self/net/tcp":"/proc/self/net/tcp6")&&has_inode(table,li,10));
#if IDECK_TCP_LSOF
    c3(25,accepted,2,1);check("tcp-official-lsof-resolves-actual-guest-pid",lsof_owner(family,addr.port));
#endif
    closefd(listener);listener=-1;
    check("tcp-dup-retains-row",load(path)&&has_inode(table,li,10));
    closefd(copy);copy=-1;
    check("tcp-last-close-removes-row",load(path)&&!has_inode(table,li,-1));
cleanup:closefd(copy);closefd(accepted);closefd(client);closefd(listener);
}
void _start(void) {
    report_fd=call(56,-100,(long)"/tcp-probe-results.txt",0x241,0600,0,0);
    family_test(2);family_test(10);
    check("tcp-snapshot-complete",failures==0);
    closefd(report_fd);
    c3(94,failures?1:0,0,0);__builtin_unreachable();
}
