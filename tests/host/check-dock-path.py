#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 125hz
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Madeira Dock's transfer path through Wine's own resolver, without running Wine.

Extract the real Wine prefix resolver. Mock only its downstream directory
lookup with a case-exact filesystem lookup; this tests drive independence,
not guest API execution or Steam authentication. The Wine source is the wine
submodule (or WINE_FILE_C=<path to dlls/ntdll/unix/file.c>).
"""
from pathlib import Path
import os, shutil, subprocess, tempfile
root = Path(__file__).resolve().parents[2]
SWIFTC = os.environ.get('SWIFTC') or shutil.which('swiftc') or str(Path.home() / '.local/share/swiftly/bin/swiftc')
swift = (root/'app/Madeira/MadeiraDock.swift').read_text()
wine = Path(os.environ.get('WINE_FILE_C') or root/'wine/dlls/ntdll/unix/file.c').read_text()
def function(text, signature, end='\n}'):
    start=text.index(signature); return text[start:text.index(end,start)+len(end)]
path_function=function(swift,'    static func handoffGuestPath(', '\n    }')
prefix = function(wine,'static inline int get_dos_prefix_len(')
resolver = function(wine,'static NTSTATUS nt_to_unix_file_name_no_root(')
code=r'''
#include <assert.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
typedef uint16_t WCHAR;
typedef struct { unsigned short Length; WCHAR *Buffer; } UNICODE_STRING;
typedef struct { UNICODE_STRING *ObjectName; } OBJECT_ATTRIBUTES;
typedef int NTSTATUS;
typedef int BOOL;
typedef int BOOLEAN;
typedef unsigned int UINT;
#define TRUE 1
#define FALSE 0
#define MAX_DIR_ENTRY_LEN 255
#define INVALID_NT_CHARS '*','?','<','>','|','"'
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
enum {STATUS_SUCCESS,STATUS_OBJECT_PATH_SYNTAX_BAD,STATUS_BAD_DEVICE_TYPE,
      STATUS_OBJECT_NAME_INVALID,STATUS_NO_MEMORY,STATUS_OBJECT_PATH_NOT_FOUND,STATUS_NO_SUCH_FILE};
static const WCHAR nt_prefixW[]={'\\','?','?','\\'};
static const char *config_dir;
static WCHAR *u16chr(const WCHAR *s,WCHAR c) { while(*s) { if(*s==c)return (WCHAR *)s; s++; } return NULL; }
#define wcschr u16chr
static int wcsnicmp(const WCHAR *a,const WCHAR *b,size_t n) { return memcmp(a,b,n*2); }
static int ntdll_wcstoumbs(const WCHAR *in,int n,char *out,int cap,BOOL flag) {
    (void)flag; if(n>=cap)return -1;
    for(int i=0;i<n;i++) { if(in[i]>127)return -1; out[i]=(char)in[i]; }return n;
}
static NTSTATUS get_dos_device(char **name,int pos) { (void)name;(void)pos;return STATUS_BAD_DEVICE_TYPE; }
static NTSTATUS lookup_unix_name(int fd,OBJECT_ATTRIBUTES *attr,UNICODE_STRING *nt_name,unsigned off,
    char **name,int cap,int pos,UINT disp,BOOL reparse,BOOLEAN is_unix,unsigned count) {
    (void)fd;(void)nt_name;(void)disp;(void)reparse;(void)is_unix;(void)count;
    (*name)[pos++]='/';
    for(unsigned i=off;i<attr->ObjectName->Length/2;i++) {
        assert(pos<cap-1); WCHAR c=attr->ObjectName->Buffer[i];
        (*name)[pos++]=c=='\\'?'/':(char)c;
    }
    (*name)[pos]=0; struct stat st;
    return stat(*name,&st)==0?STATUS_SUCCESS:STATUS_NO_SUCH_FILE;
}
'''+prefix+'\n'+resolver+r'''
int main(int argc,char **argv) {
    assert(argc==5); config_dir=argv[1];
    for(int i=2;i<4;i++) {
        const char *dos=argv[i]; assert(!strncmp(dos,i==2?"\\\\?\\":"Z:",i==2?4:2));
        char native[4096]; snprintf(native,sizeof(native),"\\??\\%s",i==2?dos+4:dos);
        WCHAR buffer[4096]; size_t n=strlen(native);
        for(size_t j=0;j<n;j++)buffer[j]=(unsigned char)native[j];
        UNICODE_STRING name={n*2,buffer}; OBJECT_ATTRIBUTES attr={&name}; char *result=NULL;
        int status=nt_to_unix_file_name_no_root(&attr,&name,&result,1,TRUE,0);
        if(i==2) { assert(status==STATUS_SUCCESS); assert(!strcmp(result,argv[4])); }
        else assert(status==STATUS_NO_SUCH_FILE);
        free(result);
    }
    puts("PASS: actual Wine Unix-prefix resolver reaches protected file without Z:; legacy drive path fails");
}
'''
with tempfile.TemporaryDirectory(prefix='madeira-dock-path-') as directory:
    folder=Path(directory); protected=folder/'Application Support/MadeiraDock/launch.auth'
    protected.parent.mkdir(parents=True); protected.write_text('synthetic transport fixture')
    prefix_dir=folder/'wine'; (prefix_dir/'dosdevices').mkdir(parents=True)
    (prefix_dir/'drive_c').mkdir(); (prefix_dir/'dosdevices/c:').symlink_to('../drive_c')
    main=folder/'main.swift'; binary=folder/'swift-path'
    main.write_text('import Foundation\nenum MadeiraDock {\n'+path_function+'\n}\n'+
        'let u = URL(fileURLWithPath: CommandLine.arguments[1])\n'+
        'print(MadeiraDock.handoffGuestPath(u))\n'+
        'print(MadeiraDock.handoffGuestPath(u, unixNamespace: false))\n')
    subprocess.run([SWIFTC,str(main),'-o',str(binary)],check=True)
    paths=subprocess.check_output([str(binary),str(protected)],text=True).splitlines()
    source=folder/'check.c'; source.write_text(code); binary=folder/'check'
    subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(source),'-o',str(binary)],check=True)
    subprocess.run([str(binary),str(prefix_dir),*paths,str(protected)],check=True)
