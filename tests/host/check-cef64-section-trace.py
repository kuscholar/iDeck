#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception-1
"""Failed native calls must not dereference an invalid diagnostic output pointer."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "build/ntdll-unix/sync_ios.c").read_text()
body = source[source.index("NTSTATUS WINAPI NtCreateSection("):source.index("/* Native globals")]
fixture = r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
typedef uint32_t NTSTATUS,ULONG,ACCESS_MASK;
typedef void* HANDLE;
typedef struct {int unused;} OBJECT_ATTRIBUTES,LARGE_INTEGER;
#define WINAPI
#define SEC_IMAGE 0x1000000
static int failure,logs; static void *logged;
static struct { struct {void *UniqueThread,*UniqueProcess;} ClientId; void *Peb;} teb;
#define NtCurrentTeb() (&teb)
typedef uintptr_t ULONG_PTR;
static NTSTATUS ios_original_NtCreateSection(HANDLE *out,ACCESS_MASK access,
 const OBJECT_ATTRIBUTES *attr,const LARGE_INTEGER *size,ULONG protect,ULONG flags,HANDLE file) {
 (void)access;(void)attr;(void)size;(void)protect;(void)flags;(void)file;
 if(failure)return 0xc0000005;
 *out=(void*)0x42;return 0;
}
static int capture(int fd,const char *format,...) {
 (void)fd;(void)format;va_list args;va_start(args,format);
 (void)va_arg(args,unsigned);(void)va_arg(args,unsigned);
 (void)va_arg(args,void*);(void)va_arg(args,void*);logged=va_arg(args,void*);
 va_end(args);logs++;return 0;
}
#define dprintf capture
'''
main = r'''
int main(void) {
 setenv("MADEIRA_CEF64_SECTION_TRACE","1",1);
 setenv("MADEIRA_STEAM_UI_SESSION","1",1);
 HANDLE out=0; assert(!NtCreateSection(&out,0,0,0,0,SEC_IMAGE,0));
 assert(out==(void*)0x42 && logged==(void*)0x42 && logs==1);
 failure=1;
 assert(NtCreateSection((HANDLE*)1,0,0,0,0,SEC_IMAGE,0)==0xc0000005);
 assert(logged==0 && logs==2);
 assert(NtCreateSection(NULL,0,0,0,0,SEC_IMAGE,0)==0xc0000005);
 assert(logged==0 && logs==3);
 puts("PASS production section trace: failed calls never read output handle; original statuses preserved");
}
'''
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path / "test.c").write_text(fixture + body + main)
    subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", str(path / "test.c"),
                    "-o", str(path / "test")], check=True)
    subprocess.run([str(path / "test")], check=True,
                   env={**os.environ, "UBSAN_OPTIONS": "halt_on_error=1"})
