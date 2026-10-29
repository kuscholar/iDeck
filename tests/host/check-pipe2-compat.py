#!/usr/bin/env python3
"""Production iOS pipe compatibility implementation, real descriptor contracts."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.c').write_text(r'''
#include "pipe2_compat.h"
#include <assert.h>
#include <string.h>
int main(void) {
 int f[2]={-2,-3};
 assert(madeira_pipe2_compat(f,0x40000000)==-1 && errno==EINVAL && f[0]==-2 && f[1]==-3);
 assert(madeira_pipe2_compat(NULL,0)==-1 && errno==EFAULT);
 int modes[]={0,O_CLOEXEC,O_NONBLOCK,O_CLOEXEC|O_NONBLOCK};
 for(int n=0;n<4;n++) {
  assert(madeira_pipe2_compat(f,modes[n])==0);
  for(int i=0;i<2;i++) {
   assert(!!(fcntl(f[i],F_GETFD)&FD_CLOEXEC)==!!(modes[n]&O_CLOEXEC));
   assert(!!(fcntl(f[i],F_GETFL)&O_NONBLOCK)==!!(modes[n]&O_NONBLOCK));
  }
  if(modes[n]&O_NONBLOCK) {char c; assert(read(f[0],&c,1)==-1 && errno==EAGAIN);}
  assert(write(f[1],"ok",2)==2); char b[2];assert(read(f[0],b,2)==2 && !memcmp(b,"ok",2));
  close(f[0]);close(f[1]);
 }
}
''')
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(root/'app/Madeira'),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real pipes, read/write, CLOEXEC/NONBLOCK, invalid flags, null output (ASan/UBSan)')
