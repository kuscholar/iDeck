#!/usr/bin/env python3
"""Exercise production 12-byte WoW -> 16-byte native affinity conversion."""
from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).resolve().parents[2]/'build/ntdll-unix/thread_ios.c').read_text()
a=s.index('static int ios_steam_ui_affinity32(');b=s.index('static NTSTATUS update_attr_list',a)
code=r'''
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef uintptr_t ULONG_PTR;
typedef struct { uintptr_t Mask; unsigned short Group,Reserved[3]; } GROUP_AFFINITY;
typedef struct { uintptr_t Attribute,Size; void *ValuePtr; void *ReturnLength; } PS_ATTRIBUTE;
'''+s[a:b]+r'''
int main(void) {
    unsigned char *p=malloc(13);unsigned char *wire=p+1;
    unsigned mask=0x80000001U;unsigned short tail[4]={2,3,4,5};
    GROUP_AFFINITY result;PS_ATTRIBUTE attr={0,12,wire,NULL};
    assert(sizeof(GROUP_AFFINITY)==16);
    memcpy(wire,&mask,4);memcpy(wire+4,tail,8);
    unsetenv("MADEIRA_STEAM_UI_SESSION");
    assert(!ios_steam_ui_affinity32(&attr,&result));
    setenv("MADEIRA_STEAM_UI_SESSION","1",1);
    assert(ios_steam_ui_affinity32(&attr,&result));
    assert(result.Mask==0x80000001ULL && result.Group==2);
    assert(result.Reserved[0]==3 && result.Reserved[1]==4 && result.Reserved[2]==5);
    assert(!memcmp(wire,&mask,4)&&!memcmp(wire+4,tail,8));
    /* Invalid group/reserved fields must be preserved, never silently cleared. */
    mask=1;memset(tail,0,sizeof(tail));memcpy(wire,&mask,4);memcpy(wire+4,tail,8);
    assert(ios_steam_ui_affinity32(&attr,&result)&&result.Mask==1&&!result.Group);
    attr.Size=8;assert(!ios_steam_ui_affinity32(&attr,&result));
    attr.Size=16;assert(!ios_steam_ui_affinity32(&attr,&result));
    attr.Size=12;attr.ValuePtr=NULL;assert(!ios_steam_ui_affinity32(&attr,&result));
    free(p);
    puts("PASS: production affinity32 ABI, exact unaligned 12-byte read, zero extension, group/reserved preservation and ordinary/native/malformed gates (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['clang','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
