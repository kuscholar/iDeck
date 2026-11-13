/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
static long call(long n,long a,long b,long c){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x8):"memory","cc");return x0;
}
static int contains(const char *bytes,unsigned size,const char *wanted){
 for(unsigned i=0;i<size;i++){unsigned j=0;while(wanted[j]&&i+j<size&&bytes[i+j]==wanted[j])j++;if(!wanted[j])return 1;}return 0;
}
void _start(void){
 char bytes[4096];long fd=call(56,-100,(long)"/Steam/steamapps/libraryfolders.vdf",0);int result=1;
 if(fd>=0){long n=call(63,fd,(long)bytes,sizeof bytes);long close=call(57,fd,0,0);
  if(n>0&&!close&&contains(bytes,(unsigned)n,"/mnt/ideck/SteamLibrary")&&contains(bytes,(unsigned)n,"/Steam"))result=0;
 }
 call(94,result,0,0);__builtin_unreachable();
}
