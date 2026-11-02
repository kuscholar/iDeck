#!/usr/bin/env python3
"""Exercise the actual fixed-path C guard's failure/rollback branches on host.

Mocked Win32 filesystem calls; not a Windows or iPhone runtime claim.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix="ideck-config-guard-") as temporary:
    temporary = Path(temporary)
    (temporary / "windows.h").write_text(r'''
#include <stdint.h>
#include <wchar.h>
typedef uint32_t DWORD;
typedef int BOOL;
typedef void* HANDLE;
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define INVALID_FILE_ATTRIBUTES ((DWORD)-1)
#define FILE_ATTRIBUTE_DIRECTORY 0x10
#define FILE_ATTRIBUTE_READONLY 1
#define GENERIC_READ 1
#define GENERIC_WRITE 2
#define FILE_SHARE_READ 1
#define FILE_SHARE_WRITE 2
#define FILE_SHARE_DELETE 4
#define OPEN_EXISTING 1
#define CREATE_NEW 2
#define ERROR_FILE_NOT_FOUND 2
#define ERROR_ACCESS_DENIED 5
HANDLE CreateFileW(const wchar_t*, DWORD, DWORD, void*, DWORD, DWORD, HANDLE);
BOOL ReadFile(HANDLE, void*, DWORD, DWORD*, void*);
BOOL WriteFile(HANDLE, const void*, DWORD, DWORD*, void*);
BOOL CloseHandle(HANDLE);
DWORD GetLastError(void);
DWORD GetFileSize(HANDLE, DWORD*);
DWORD GetFileAttributesW(const wchar_t*);
BOOL SetFileAttributesW(const wchar_t*, DWORD);
BOOL DeleteFileW(const wchar_t*);
''')
    (temporary / "test.c").write_text(r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#define wmain actual_guard_main
#include "config_guard.c"
#undef wmain

static DWORD attributes, saved, error, marker_size;
static int marker_exists, allow_write, wrong_error, short_save, fail_set;
static const char *contents;
static const char valid[]="[Config]\r\nExternalHandler=C:\\iDeckCEF64Crashpad\\crashpad_handler.exe\r\nServerURL=preserve\r\n";
static HANDLE cfg_handle=(HANDLE)(uintptr_t)1, marker_handle=(HANDLE)(uintptr_t)2;
static void reset(DWORD value) {
 attributes=value; saved=0; error=0; marker_size=4; marker_exists=0;
 allow_write=wrong_error=short_save=fail_set=0; contents=valid;
}
HANDLE CreateFileW(const wchar_t *path,DWORD access,DWORD share,void *security,DWORD creation,DWORD flags,HANDLE template) {
 (void)share;(void)security;(void)flags;(void)template;
 if (!wcscmp(path,config)) {
  if (access==GENERIC_WRITE && (attributes&FILE_ATTRIBUTE_READONLY) && !allow_write) { error=wrong_error?32:5; return INVALID_HANDLE_VALUE; }
  return cfg_handle;
 }
 assert(!wcscmp(path,marker));
 if (creation==CREATE_NEW) { if(marker_exists)return INVALID_HANDLE_VALUE; marker_exists=1;return marker_handle; }
 if (!marker_exists) {error=2;return INVALID_HANDLE_VALUE;}
 return marker_handle;
}
BOOL ReadFile(HANDLE file,void *data,DWORD length,DWORD *read,void *overlap) {
 (void)overlap;
 if(file==cfg_handle) {assert(length==strlen(contents));memcpy(data,contents,length);*read=length;}
 else {assert(file==marker_handle && length==4);memcpy(data,&saved,4);*read=4;}
 return 1;
}
BOOL WriteFile(HANDLE file,const void *data,DWORD length,DWORD *written,void *overlap) {
 (void)overlap;assert(file==marker_handle && length==4);memcpy(&saved,data,4);*written=short_save?2:4;return 1;
}
BOOL CloseHandle(HANDLE file) {(void)file;return 1;}
DWORD GetLastError(void) {return error;}
DWORD GetFileSize(HANDLE file,DWORD *high) {(void)high;return file==cfg_handle?(DWORD)strlen(contents):marker_size;}
DWORD GetFileAttributesW(const wchar_t *path) {return !wcscmp(path,config)?attributes:(marker_exists?0x20:INVALID_FILE_ATTRIBUTES);}
BOOL SetFileAttributesW(const wchar_t *path,DWORD value) {assert(!wcscmp(path,config));if(fail_set){--fail_set;return 0;}attributes=value;return 1;}
BOOL DeleteFileW(const wchar_t *path) {assert(!wcscmp(path,marker));marker_exists=0;return 1;}

int main(void) {
 reset(0x20);assert(protect()==0 && attributes==0x21 && marker_exists && saved==0x20);
 assert(restore()==0 && attributes==0x20 && !marker_exists && contents==valid);
 reset(0x21);assert(protect()==0);assert(restore()==0 && attributes==0x21);
 reset(0x20);allow_write=1;assert(protect()==9 && attributes==0x20 && !marker_exists);
 reset(0x20);wrong_error=1;assert(protect()==15 && attributes==0x20 && !marker_exists);
 reset(0x20);short_save=1;assert(protect()==7 && attributes==0x20 && !marker_exists);
 reset(0x20);fail_set=1;assert(protect()==8 && attributes==0x20 && !marker_exists);
 reset(0x20);contents="[Config]\nServerURL=preserve\n";assert(protect()==4 && attributes==0x20 && !marker_exists);
 reset(0x20);marker_exists=1;saved=123;assert(protect()==4 && saved==123 && attributes==0x20);
 reset(0x21);marker_exists=1;saved=0x20;marker_size=3;assert(restore()==11 && attributes==0x21 && marker_exists);
 reset(0x21);marker_exists=1;saved=0x20;fail_set=1;assert(restore()==12 && marker_exists);
 assert(restore()==0 && attributes==0x20 && !marker_exists);
 reset(0x20);assert(restore()==0 && attributes==0x20);
 puts("PASS actual guard source: exact config gating, non-truncating write check, original attributes and all injected rollback failures (host mocks/ASan/UBSan)");
}
''')
    subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined",
                    "-I", str(temporary), "-I", str(root / "experiments/cef64/crashpad"),
                    str(temporary / "test.c"), "-o", str(temporary / "test")], check=True)
    subprocess.run([str(temporary / "test")], check=True)
