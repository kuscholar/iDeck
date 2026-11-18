/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Owned Linux AArch64/glibc diagnostic; opaque ABI sizes checked against
 * glibc-2.41 sysdeps/aarch64/nptl/bits/pthreadtypes-arch.h (LP64 only).
 * No Steam, borrowed account state, environment secrets or guest kernel edit. */
typedef unsigned long size_t;
typedef unsigned long pthread_t;
typedef union {char opaque[64];unsigned long align;} own_attr;
typedef union {char opaque[32];unsigned long align;} own_barrier;
_Static_assert(sizeof(void*)==8&&sizeof(own_attr)==64&&sizeof(own_barrier)==32,"AArch64 LP64 ABI");
extern int pthread_create(pthread_t*,const void*,void*(*)(void*),void*);
extern int pthread_join(pthread_t,void**);
extern pthread_t pthread_self(void);
extern int pthread_getattr_np(pthread_t,void*);
extern int pthread_attr_getstack(const void*,void**,size_t*);
extern int pthread_attr_destroy(void*);
extern int pthread_barrier_init(void*,const void*,unsigned);
extern int pthread_barrier_wait(void*);
extern int pthread_barrier_destroy(void*);
extern int open(const char*,int,...),close(int),printf(const char*,...);
extern long read(int,void*,size_t);
extern const char *gnu_get_libc_version(void);
extern char *getenv(const char*);
static own_barrier barrier,finish;
struct own_limit{unsigned long cur,max;};
extern int getrlimit(int,struct own_limit*);
static unsigned failures;
struct worker {unsigned id;size_t stack_bytes;unsigned checksum;int error;};
static void *worker(void *pointer){
 struct worker *w=pointer;own_attr attr;void *base=0;size_t bytes=0;
 w->error=pthread_getattr_np(pthread_self(),&attr);
 if(!w->error)w->error=pthread_attr_getstack(&attr,&base,&bytes);
 if(!w->error)w->error=pthread_attr_destroy(&attr);
 w->stack_bytes=bytes;if(!base||bytes<65536)w->error=1;
 int result=pthread_barrier_wait(&barrier);if(result!=0&&result!=-1)w->error=2;
 volatile unsigned char local[65536];unsigned total=0;
 for(unsigned i=0;i<65536;i+=4096){local[i]=(unsigned char)(w->id+i/4096);total+=local[i];}
 w->checksum=total;result=pthread_barrier_wait(&finish);if(result!=0&&result!=-1)w->error=3;return pointer;
}
static unsigned hex(char c){return c>='0'&&c<='9'?(unsigned)(c-'0'):c>='a'&&c<='f'?(unsigned)(c-'a'+10):99;}
static unsigned long long vm_bytes(void){
 static char buffer[65536];int fd=open("/proc/self/maps",0);if(fd<0){failures++;return 0;}
 long size=0;
 while(size<65535){long n=read(fd,buffer+size,65535-(size_t)size);if(n<0){failures++;break;}if(!n)break;size+=n;}
 close(fd);if(size==65535){failures++;return 0;}buffer[size]=0;
 unsigned long long total=0;
 for(long at=0;at<size;){unsigned long long first=0,last=0;
  while(at<size&&hex(buffer[at])<16)first=first*16+hex(buffer[at++]);
  if(buffer[at++]!='-'){failures++;return 0;}
  while(at<size&&hex(buffer[at])<16)last=last*16+hex(buffer[at++]);
  if(last<first){failures++;return 0;}total+=last-first;
  while(at<size&&buffer[at]!='\n')at++;if(at<size)at++;
 }
 return total;
}
int main(void){
 printf("glibc=%s\n",gnu_get_libc_version());const char *env=getenv("GLIBC_TUNABLES");
 printf("cache_setting=%s\n",env?env:"default");
 struct own_limit limit;if(getrlimit(3,&limit))return 10;printf("stack_soft_bytes=%lu\nstack_hard_bytes=%lu\n",limit.cur,limit.max);
 printf("baseline_vm_bytes=%llu\n",vm_bytes());
 for(unsigned wave=0;wave<4;wave++){
  pthread_t threads[8];struct worker workers[8];
  if(pthread_barrier_init(&barrier,0,9)||pthread_barrier_init(&finish,0,9))return 2;
  for(unsigned i=0;i<8;i++){workers[i]=(struct worker){.id=wave*8+i};if(pthread_create(&threads[i],0,worker,&workers[i]))return 3;}
  int r=pthread_barrier_wait(&barrier);if(r!=0&&r!=-1)return 4;
  printf("wave%u_active_vm_bytes=%llu\n",wave,vm_bytes());
  r=pthread_barrier_wait(&finish);if(r!=0&&r!=-1)return 11;
  for(unsigned i=0;i<8;i++){void *ret=0;if(pthread_join(threads[i],&ret)||ret!=&workers[i]||workers[i].error)return 5;
   unsigned expected=16*workers[i].id+120;if(workers[i].checksum!=expected||workers[i].stack_bytes!=workers[0].stack_bytes)return 6;
  }
  if(pthread_barrier_destroy(&barrier)||pthread_barrier_destroy(&finish))return 7;
  printf("wave%u_vm_bytes=%llu\n",wave,vm_bytes());
  printf("wave%u_thread_stack_bytes=%lu\n",wave,workers[0].stack_bytes);
 }
 printf("complete=%s\n",failures?"FAIL":"PASS");return failures?1:0;
}
