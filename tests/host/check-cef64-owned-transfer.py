#!/usr/bin/env python3
"""Compile the production Wine adoption function with ownership/view fixtures."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text()
adopt = 'static int ios_cef64_adopt_view' + source.split('static int ios_cef64_adopt_view', 1)[1].split('static NTSTATUS allocate_virtual_memory', 1)[0]
code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "cef64_owned_slots.h"
#define ios_cef64_record_lease(...) ((void)0) /* Separate writer test; no host VM changes. */
typedef uint32_t ULONG, NTSTATUS;
typedef uint64_t SIZE_T, ULONG_PTR;
typedef uint16_t WCHAR;
typedef struct { struct { WCHAR *Buffer; uint16_t Length; } ImagePathName, CommandLine; } RTL_USER_PROCESS_PARAMETERS;
typedef struct { RTL_USER_PROCESS_PARAMETERS *ProcessParameters; } PEB;
struct file_view { void *base; };
#define STATUS_NO_MEMORY UINT32_C(0xc0000017)
static int active=1, standalone, extras, existing, claimed, create_fails, get_calls, claims, releases;
static unsigned bank_mask, bank_views;
static uint64_t held=UINT64_C(0x7100000000), held_size=UINT64_C(0x40000000);
static RTL_USER_PROCESS_PARAMETERS params;
static PEB peb={&params}, *owner=&peb;
static int ios_cef64_owned_layout(void){return active;}
static int madeira_cef64_standalone_layout(void){return standalone;}
static PEB *ios_jit_current_peb(void){return owner;}
static int madeira_cef64_hold_get(unsigned s,uint64_t *b,uint64_t *z){assert(s<20);get_calls++;if(s>=17)return 0;if(standalone&&s>=11){if(extras>=11&&s==16){*b=UINT64_C(0x71a0000000);*z=UINT64_C(0x20000000);return 1;}if(extras>=10&&s==15){*b=UINT64_C(0x7740000000);*z=UINT64_C(0x20000000);return 1;}if(extras>=9&&s==14){*b=UINT64_C(0x7760000000);*z=UINT64_C(0x20000000);return 1;}if(extras>=8&&(s==12||s==13)){*b=s==12?UINT64_C(0x7060000000):UINT64_C(0x7080000000);*z=UINT64_C(0x20000000);return 1;}if(extras>=7&&s==11){*b=UINT64_C(0x77c0000000);*z=UINT64_C(0x20000000);return 1;}return 0;}if(standalone&&(s==9||s==10)){*b=s==9?UINT64_C(0x71c0000000):UINT64_C(0x71e0000000);*z=UINT64_C(0x20000000);return 1;}if(s==12){if(extras!=5)return 0;*b=UINT64_C(0x71e0000000);*z=UINT64_C(0x20000000);return 1;}if(s==11){if(extras<4)return 0;*b=UINT64_C(0x71c0000000);*z=UINT64_C(0x20000000);return 1;}if((s>=6&&!extras)||(s==8&&extras<2)||(s>=9&&extras<3))return 0;*b=held;*z=held_size;return 1;}
static int madeira_cef64_hold_claim(unsigned s){assert(s<17);claims++;if(extras>=4){assert(s==8||(standalone?(s>=9&&s<=16):(s==11||s==12)));unsigned bit=1u<<s;if(bank_mask&bit)return 0;bank_mask|=bit;return 1;}if(claimed)return 0;claimed=1;return 1;}
static void madeira_cef64_hold_unclaim(unsigned s){assert(s<17);releases++;if(extras>=4){assert(bank_mask&(1u<<s));bank_mask&=~(1u<<s);}else{assert(claimed);claimed=0;}}
static int find_view_range(void *base,SIZE_T size){assert(size==held_size);if(extras>=4){assert((extras>=11&&(uintptr_t)base==UINT64_C(0x71a0000000))||(uintptr_t)base==held||(uintptr_t)base==UINT64_C(0x71c0000000)||(uintptr_t)base==UINT64_C(0x71e0000000)||(extras>=7&&(uintptr_t)base==UINT64_C(0x77c0000000))||(extras>=10&&(uintptr_t)base==UINT64_C(0x7740000000))||(extras>=9&&(uintptr_t)base==UINT64_C(0x7760000000))||(extras>=8&&((uintptr_t)base==UINT64_C(0x7060000000)||(uintptr_t)base==UINT64_C(0x7080000000))));return bank_views&(1u<<((uintptr_t)base==UINT64_C(0x71a0000000)?8:(uintptr_t)base==UINT64_C(0x7740000000)?7:(uintptr_t)base==UINT64_C(0x7760000000)?6:(uintptr_t)base==UINT64_C(0x7060000000)?4:(uintptr_t)base==UINT64_C(0x7080000000)?5:(uintptr_t)base==UINT64_C(0x77c0000000)?3:(uintptr_t)base==held?0:(uintptr_t)base==UINT64_C(0x71c0000000)?1:2));}assert((uintptr_t)base==held);return existing;}
static NTSTATUS create_view(struct file_view **out,void *base,SIZE_T size,unsigned vprot){
 static struct file_view v;
 if(extras>=4){static struct file_view bank[9];unsigned index=(uintptr_t)base==UINT64_C(0x71a0000000)?8:(uintptr_t)base==UINT64_C(0x7740000000)?7:(uintptr_t)base==UINT64_C(0x7760000000)?6:(uintptr_t)base==UINT64_C(0x7060000000)?4:(uintptr_t)base==UINT64_C(0x7080000000)?5:(uintptr_t)base==UINT64_C(0x77c0000000)?3:(uintptr_t)base==held?0:(uintptr_t)base==UINT64_C(0x71c0000000)?1:2;assert(size==held_size&&vprot==5&&(bank_mask&(1u<<(index?(standalone?8+index:10+index):8))));if(create_fails)return STATUS_NO_MEMORY;bank_views|=1u<<index;bank[index].base=base;*out=&bank[index];return 0;}
 assert(claimed&&(uintptr_t)base==held&&size==held_size&&vprot==5);
 if(create_fails)return STATUS_NO_MEMORY;
 v.base=base;*out=&v;return 0;
}
''' + adopt + r'''
static void name(const char *s){static WCHAR n[128];size_t i;for(i=0;s[i];i++)n[i]=(unsigned char)s[i];params.ImagePathName.Buffer=n;params.ImagePathName.Length=(uint16_t)(2*i);}
static NTSTATUS invoke(ULONG_PTR low,ULONG_PTR high,ULONG_PTR align,int expect_handled){
 struct file_view *v=0;void *base=0;NTSTATUS status=0x1234;
 int handled=ios_cef64_adopt_view(&v,&base,held_size,0x2000,1,5,low,high,align,0,&status);
 assert(handled==expect_handled);
 if(handled&&!status)assert((uintptr_t)base==held&&v&&v->base==base);
 else assert(!base&&!v);
 return status;
}
int main(void){
 name("C:\\steam64-cef-load-probe.exe");
 active=0;assert(invoke(0,0,0,0)==0x1234&&!get_calls);active=1;
 owner=0;assert(invoke(0,0,0,0)==0x1234&&!get_calls);owner=&peb;
 name("C:\\steam.exe");assert(invoke(0,0,0,0)==0x1234&&!get_calls);
 name("C:\\steamwebhelper.exe");
 assert(invoke(held+1,0,0,1)==STATUS_NO_MEMORY&&!claims);
 assert(invoke(0,held-1,0,1)==STATUS_NO_MEMORY&&!claims);
 assert(invoke(0,held+held_size-2,0,1)==STATUS_NO_MEMORY&&!claims);
 existing=1;assert(invoke(0,0,0,1)==STATUS_NO_MEMORY&&!claims);existing=0;
 create_fails=1;assert(invoke(0,0,0,1)==STATUS_NO_MEMORY&&!claimed&&releases==1);create_fails=0;
 assert(invoke(held,held+held_size-1,0x10000,1)==0&&claimed);
 assert(invoke(0,0,0,1)==STATUS_NO_MEMORY&&claimed);
 {struct file_view *v=0;void *fixed=(void *)UINT64_C(0x7780000000);NTSTATUS st=0x1234;
  assert(!ios_cef64_adopt_view(&v,&fixed,UINT64_C(0x40000000),0x2000,1,5,0,0,0,0,&st));
  assert((uintptr_t)fixed==UINT64_C(0x7780000000)&&st==0x1234&&!v);}

 claimed=0;held=UINT64_C(0x717fff0000);held_size=UINT64_C(0x40010000);
 int previous_claims=claims;
 assert(invoke(0,0,UINT64_C(0x40000000),1)==STATUS_NO_MEMORY&&claims==previous_claims);
 assert(invoke(held,held+held_size-1,0x10000,1)==0&&claimed);
 claimed=0;held=UINT64_C(0x7600000000);held_size=UINT64_C(0x100000000);
 assert(invoke(0,0,0,0)==0x1234);
 extras=1;assert(invoke(held,held+held_size-1,0x10000,1)==0&&claimed);
 assert(invoke(0,0,0,1)==STATUS_NO_MEMORY);
 claimed=0;held=UINT64_C(0x7700000000);held_size=UINT64_C(0x20000000);
 assert(invoke(0,held-1,0,1)==STATUS_NO_MEMORY&&!claimed);
 assert(invoke(0,0,0,1)==0&&claimed);
 extras=2;claimed=0;held=UINT64_C(0x70a0000000);held_size=UINT64_C(0x20000000);
 assert(invoke(0,0,0,1)==0&&claimed);
 claimed=0;held=UINT64_C(0x7700000000);
 {struct file_view *v=0;void *base=0;NTSTATUS st=0x1234;
  assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
  assert(!st&&(uintptr_t)base==held&&claimed&&v);}
 extras=3;claimed=0;held=UINT64_C(0x7780000000);held_size=UINT64_C(0x40000000);
 {static WCHAR cmd[]={ '-', '-', 't','y','p','e','=','c','r','a','s','h','p','a','d','-','h','a','n','d','l','e','r' };
  params.CommandLine.Buffer=cmd;params.CommandLine.Length=sizeof(cmd);}
 assert(invoke(0,0,0,1)==0&&claimed);
 claimed=0;held=UINT64_C(0x773fff0000);held_size=UINT64_C(0x40010000);
 assert(invoke(0,0,0,1)==0&&claimed);
 extras=4;held=UINT64_C(0x7700000000);held_size=UINT64_C(0x20000000);
 {struct file_view *v=0;void *base=0;NTSTATUS st=0x1234;
  create_fails=1;assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
  assert(st==STATUS_NO_MEMORY&&!bank_mask&&!bank_views);create_fails=0;
  for(unsigned n=0;n<2;n++){base=0;v=0;st=0x1234;assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));assert(!st&&v&&(uintptr_t)base==(n?UINT64_C(0x71c0000000):held));}
  base=0;v=0;st=0x1234;assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));assert(st==STATUS_NO_MEMORY&&!base&&!v);
  bank_mask=bank_views=0;base=0;v=0;st=0x1234;assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,UINT64_C(0x71c0000000)+held_size-1,0,0,&st));assert(!st&&(uintptr_t)base==UINT64_C(0x71c0000000)&&bank_mask==(1u<<11));
  bank_mask=1u<<8;bank_views=1;base=(void *)(uintptr_t)held;v=0;st=0x1234;assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));assert(st==STATUS_NO_MEMORY&&(uintptr_t)base==held&&!v&&bank_mask==(1u<<8));
 }

 extras=5;bank_mask=bank_views=0;
 {const uint64_t expected[]={UINT64_C(0x7700000000),UINT64_C(0x71c0000000),UINT64_C(0x71e0000000)};
  for(unsigned n=0;n<4;n++){struct file_view *v=0;void *base=0;NTSTATUS st=0x1234;
   assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
   if(n<3)assert(!st&&v&&(uintptr_t)base==expected[n]);else assert(st==STATUS_NO_MEMORY&&!base&&!v);
  }
 }
 standalone=1;extras=6;held=UINT64_C(0x7140000000);bank_mask=bank_views=0;
 {struct file_view *v=0;void *base=(void *)UINT64_C(0x71c0000000);NTSTATUS st=0x1234;
  assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
  assert(!st&&v&&(uintptr_t)base==UINT64_C(0x71c0000000)&&bank_mask==(1u<<9));
  bank_mask=bank_views=0;
 }
 {const uint64_t expected[]={UINT64_C(0x7140000000),UINT64_C(0x71c0000000),UINT64_C(0x71e0000000)};
  for(unsigned n=0;n<4;n++){struct file_view *v=0;void *base=0;NTSTATUS st=0x1234;
   assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
   if(n<3)assert(!st&&v&&(uintptr_t)base==expected[n]);else assert(st==STATUS_NO_MEMORY&&!base&&!v);
  }
 }
 extras=7;bank_mask=bank_views=0;
 {const uint64_t expected[]={UINT64_C(0x7140000000),UINT64_C(0x71c0000000),UINT64_C(0x71e0000000),UINT64_C(0x77c0000000)};
  for(unsigned n=0;n<5;n++){struct file_view *v=0;void *base=0;NTSTATUS st=0x1234;
   assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
   if(n<4)assert(!st&&v&&(uintptr_t)base==expected[n]);else assert(st==STATUS_NO_MEMORY&&!base&&!v);
  }
  bank_mask=bank_views=0;struct file_view *v=0;void *base=(void*)UINT64_C(0x77c0000000);NTSTATUS st=0x1234;
  assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));assert(!st&&v&&(uintptr_t)base==UINT64_C(0x77c0000000));
 }
 extras=8;bank_mask=bank_views=0;
 {const uint64_t expected[]={UINT64_C(0x7140000000),UINT64_C(0x71c0000000),UINT64_C(0x71e0000000),UINT64_C(0x77c0000000),UINT64_C(0x7060000000),UINT64_C(0x7080000000)};
  for(unsigned n=0;n<7;n++){struct file_view *v=0;void *base=0;NTSTATUS st=0x1234;
   assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
   if(n<6)assert(!st&&v&&(uintptr_t)base==expected[n]);else assert(st==STATUS_NO_MEMORY&&!base&&!v);
  }
 }
 return 0;
}
'''
for tail in (False,True):
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        fixture=code.replace('0x7060000000','0x7780000000').replace('0x7080000000','0x77a0000000') if tail else code
        if tail:
            fixture=fixture.replace(' return 0;\n}\n',r'''
 extras=9;bank_mask=bank_views=0;
 {const uint64_t expected[]={UINT64_C(0x7140000000),UINT64_C(0x71c0000000),UINT64_C(0x71e0000000),UINT64_C(0x77c0000000),UINT64_C(0x7780000000),UINT64_C(0x77a0000000),UINT64_C(0x7760000000)};
  for(unsigned n=0;n<8;n++){struct file_view *v=0;void *base=0;NTSTATUS st=0x1234;
   assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
   if(n<7)assert(!st&&v&&(uintptr_t)base==expected[n]);else assert(st==STATUS_NO_MEMORY&&!base&&!v);
  }
 }
 extras=10;bank_mask=bank_views=0;
 {const uint64_t expected[]={UINT64_C(0x7140000000),UINT64_C(0x71c0000000),UINT64_C(0x71e0000000),UINT64_C(0x77c0000000),UINT64_C(0x7780000000),UINT64_C(0x77a0000000),UINT64_C(0x7760000000),UINT64_C(0x7740000000)};
  for(unsigned n=0;n<9;n++){struct file_view *v=0;void *base=0;NTSTATUS st=0x1234;
   assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
   if(n<8)assert(!st&&v&&(uintptr_t)base==expected[n]);else assert(st==STATUS_NO_MEMORY&&!base&&!v);
  }
 }
 return 0;
}
''')
        if tail:
            fixture=fixture.replace(' return 0;\n}\n',r"""
 extras=11;held=UINT64_C(0x7180000000);bank_mask=bank_views=0;
 {const uint64_t expected[]={UINT64_C(0x7180000000),UINT64_C(0x71c0000000),UINT64_C(0x71e0000000),UINT64_C(0x77c0000000),UINT64_C(0x7780000000),UINT64_C(0x77a0000000),UINT64_C(0x7760000000),UINT64_C(0x7740000000),UINT64_C(0x71a0000000)};
  for(unsigned n=0;n<10;n++){struct file_view *v=0;void *base=0;NTSTATUS st=0x1234;
   assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));
   if(n<9)assert(!st&&v&&(uintptr_t)base==expected[n]);else assert(st==STATUS_NO_MEMORY&&!base&&!v);
  }
  for(unsigned n=0;n<9;n++){bank_mask=bank_views=0;struct file_view *v=0;void *base=(void*)expected[n];NTSTATUS st=0x1234;
   assert(ios_cef64_adopt_view(&v,&base,held_size,0x42000,1,5,0,0,0,0,&st));assert(!st&&v&&(uintptr_t)base==expected[n]);
  }
 }
 return 0;
}
""")
        (temp / 'transfer.c').write_text(fixture)
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                        '-I' + str(root / 'build/ntdll-unix'), str(temp / 'transfer.c'), '-o', str(temp / 'transfer')], check=True)
        subprocess.run([str(temp / 'transfer')], check=True)
print('PASS: actual Wine adoption for original and arena-tail tables: owner/bounds/alignment/live views/duplicate/create rollback; ASan/UBSan, not device test')
