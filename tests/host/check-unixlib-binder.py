#!/usr/bin/env python3
"""Unix-library binder by caller bitness (virtual_ios.c load_builtin_unixlib); no Wine runs.

Part A reads the by-module match chain and checks that every branch names the same 64-bit table
the upstream chain returned for it (the list below is upstream's, in order), that no branch hands
a 32-bit caller a 64-bit table, and that the mapped-file-name fallback is only asked for a 32-bit
caller.  Part B compiles the production ios_module_export_name and ios_bind_unixlib_table against
synthetic PE32 and PE32+ headers: both layouts are named from their own export directory, a
64-bit caller always gets the 64-bit table, and a 32-bit caller without a wow64 table is refused
with STATUS_NOT_SUPPORTED.
"""
from pathlib import Path
import re, subprocess, tempfile

root = Path(__file__).resolve().parents[2]
src = (root / "build/ntdll-unix/virtual_ios.c").read_text()

def function(source, start):
    a = source.index(start); b = source.index("{", a); depth = 1; c = b + 1
    while depth:
        depth += (source[c] == "{") - (source[c] == "}"); c += 1
    return source[a:c]

# ---- Part A: the match chain
chain = function(src, "static NTSTATUS load_builtin_unixlib(")
upstream = [  # (match test, 64-bit table) in upstream order
    ('strstr(match, "winemetal")', "dxmt_winemetal_unix_call_funcs"),
    ('strstr(match, "wineios.drv")', "audio_null_ios_unix_call_funcs"),
    ('strstr(match, "ws2_32")', "ws2_32_unix_call_funcs"),
    ('strstr(match, "bcrypt")', "bcrypt_unix_call_funcs"),
    ('strstr(match, "secur32")', "secur32_unix_call_funcs"),
    ('strstr(match, "crypt32")', "crypt32_unix_call_funcs"),
    ('strstr(match, "dwrite")', "dwrite_unix_call_funcs"),
    ('strstr(match, "nsi.dll")', "nsi_unix_call_funcs"),
    ('strstr(match, "win32u")', "ios_stub_unix_call_table"),
    ('strstr(match, "opengl32")', "ios_gl_stub_unix_call_table"),
]
# the 32-bit table each branch offers (upstream had none)
wow64 = {
    "dxmt_winemetal_unix_call_funcs": "dxmt_winemetal_unix_call_wow64_funcs",
    "audio_null_ios_unix_call_funcs": "audio_null_ios_unix_call_wow64_funcs",
    "ws2_32_unix_call_funcs": "ws2_32_unix_call_wow64_funcs",
    "bcrypt_unix_call_funcs": "bcrypt_unix_call_wow64_funcs",
    "secur32_unix_call_funcs": "secur32_unix_call_wow64_funcs",
    "crypt32_unix_call_funcs": "crypt32_unix_call_wow64_funcs",
    "dwrite_unix_call_funcs": "dwrite_unix_call_wow64_funcs",
    "nsi_unix_call_funcs": "nsi_unix_call_wow64_funcs",
    "ios_stub_unix_call_table": "ios_stub_unix_call_table",
    "ios_gl_stub_unix_call_table": "ios_gl_stub_unix_call_table",
}
assert "extern const void *dxmt_winemetal_unix_call_wow64_funcs[];" in src
branches = re.split(r"\n        \} else ", chain[chain.index('if (match && strstr(match, "winemetal"))'):])
# The i386 D3D9 shim's branch is not upstream's: it is entered by 32-bit callers only
# (so a 64-bit module keeps the upstream chain), offers only its wow64 table and no 64-bit one.
d3d9 = [b for b in branches if '"d3d9shim"' in b.split("{")[0]]
if d3d9:
    assert len(d3d9) == 1
    head = d3d9[0].split("{")[0]
    assert head.startswith("if (wow && ("), head
    assert "funcs_wow64 = (const void *)dxmt_d3d9_unix_call_wow64_funcs;" in d3d9[0]
    assert "funcs64" not in d3d9[0], "the d3d9shim branch must not offer a 64-bit table"
    branches.remove(d3d9[0])
# winegstreamer's branch is new (upstream has no winegstreamer unix side on iOS): it must hand
# a 32-bit caller its own wow64 table, never a 64-bit one.  It is checked here and then left
# out of the comparison with upstream's chain.
wg = [b for b in branches if 'strstr(match, "winegstreamer")' in b.split("\n")[0]]
assert len(wg) == 1, len(wg)
assert "funcs_wow64 = (const void *)winegstreamer_unix_call_wow64_funcs;" in wg[0], wg[0]
branches = [b for b in branches if b is not wg[0]]
# dnsapi's branch is new too (#70: upstream dnsapi has no unix side on iOS); same rule.
dns = [b for b in branches if 'strstr(match, "dnsapi")' in b.split("\n")[0]]
assert len(dns) == 1, len(dns)
assert "funcs64 = (const void *)dnsapi_unix_call_funcs;" in dns[0], dns[0]
assert "funcs_wow64 = (const void *)dnsapi_unix_call_wow64_funcs;" in dns[0], dns[0]
branches = [b for b in branches if b is not dns[0]]
assert len(branches) == len(upstream) + 1, len(branches)
for (test, table), body in zip(upstream, branches):
    assert test in body.split("\n")[0], (test, body.split("\n")[0])
    m = re.search(r"funcs64 = (?:funcs_wow64 = )?\(const void \*\)(\w+);", body)
    assert m and m.group(1) == table, (test, m and m.group(1))
    w = re.search(r"funcs_wow64 = ([^;]+);", body) or re.search(r"funcs64 = funcs_wow64 = \(const void \*\)(\w+);", body)
    assert w, test
    assert "_unix_call_funcs" not in w.group(1), ("64-bit table offered to a 32-bit caller", test)
    assert w.group(1).replace("(const void *)", "") == wow64[table], (test, w.group(1))
last = branches[-1]
assert "funcs64 = (const void *)ios_stub_unix_call_table;" in last and "funcs_wow64 = NULL;" in last
assert "status = ios_bind_unixlib_table( module, libname, wow, funcs64, funcs_wow64, funcs );" in chain
assert "if (!match && wow && ios_module_mapped_file_name( module, secname, sizeof(secname) ))" in chain
print("PASS: every branch keeps upstream's 64-bit table and offers its own 32-bit table (winemetal included); no 64-bit table reaches a 32-bit caller; the mapped-file fallback is 32-bit only")

# ---- Part B: behaviour of the helpers
names = function(src, "static const char *ios_module_export_name( const void *module )")
bind = function(src, "static NTSTATUS ios_bind_unixlib_table(")
harness = r"""
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
typedef uint8_t BYTE; typedef uint16_t WORD; typedef uint32_t DWORD; typedef uint64_t ULONGLONG;
typedef int BOOL; typedef int NTSTATUS;
#define STATUS_SUCCESS 0
#define STATUS_NOT_SUPPORTED ((NTSTATUS)0xc00000bb)
#define IMAGE_DOS_SIGNATURE 0x5a4d
#define IMAGE_NT_SIGNATURE 0x00004550
#define IMAGE_NT_OPTIONAL_HDR32_MAGIC 0x10b
#define IMAGE_NT_OPTIONAL_HDR64_MAGIC 0x20b
#define IMAGE_DIRECTORY_ENTRY_EXPORT 0
#define dprintf(fd, ...) fprintf( stderr, __VA_ARGS__ )
typedef struct { WORD e_magic; WORD pad[29]; int32_t e_lfanew; } IMAGE_DOS_HEADER;
typedef struct { DWORD VirtualAddress, Size; } IMAGE_DATA_DIRECTORY;
typedef struct { WORD Machine, NumberOfSections; DWORD TimeDateStamp, PointerToSymbolTable, NumberOfSymbols;
                 WORD SizeOfOptionalHeader, Characteristics; } IMAGE_FILE_HEADER;
typedef struct { WORD Magic; BYTE MajorLinkerVersion, MinorLinkerVersion;
                 DWORD SizeOfCode, SizeOfInitializedData, SizeOfUninitializedData, AddressOfEntryPoint, BaseOfCode, BaseOfData;
                 DWORD ImageBase, SectionAlignment, FileAlignment; WORD v[6]; DWORD Win32VersionValue, SizeOfImage,
                 SizeOfHeaders, CheckSum; WORD Subsystem, DllCharacteristics; DWORD s[4]; DWORD LoaderFlags,
                 NumberOfRvaAndSizes; IMAGE_DATA_DIRECTORY DataDirectory[16]; } IMAGE_OPTIONAL_HEADER32;
typedef struct { WORD Magic; BYTE MajorLinkerVersion, MinorLinkerVersion;
                 DWORD SizeOfCode, SizeOfInitializedData, SizeOfUninitializedData, AddressOfEntryPoint, BaseOfCode;
                 ULONGLONG ImageBase; DWORD SectionAlignment, FileAlignment; WORD v[6]; DWORD Win32VersionValue,
                 SizeOfImage, SizeOfHeaders, CheckSum; WORD Subsystem, DllCharacteristics; ULONGLONG s[4];
                 DWORD LoaderFlags, NumberOfRvaAndSizes; IMAGE_DATA_DIRECTORY DataDirectory[16]; } IMAGE_OPTIONAL_HEADER64;
typedef struct { DWORD Signature; IMAGE_FILE_HEADER FileHeader; IMAGE_OPTIONAL_HEADER32 OptionalHeader; } IMAGE_NT_HEADERS32;
typedef struct { DWORD Signature; IMAGE_FILE_HEADER FileHeader; IMAGE_OPTIONAL_HEADER64 OptionalHeader; } IMAGE_NT_HEADERS64;
typedef struct { DWORD Characteristics, TimeDateStamp; WORD MajorVersion, MinorVersion; DWORD Name, Base,
                 NumberOfFunctions, NumberOfNames, AddressOfFunctions, AddressOfNames, AddressOfNameOrdinals; } IMAGE_EXPORT_DIRECTORY;
_Static_assert(__builtin_offsetof(IMAGE_NT_HEADERS32, OptionalHeader.DataDirectory) == 0x78, "PE32 layout");
_Static_assert(__builtin_offsetof(IMAGE_NT_HEADERS64, OptionalHeader.DataDirectory) == 0x88, "PE32+ layout");
""" + names + "\n" + bind + r"""
static unsigned char img[2][0x2000];
static void make( unsigned char *m, int pe32plus, const char *name, DWORD resource_rva ) {
    IMAGE_DOS_HEADER *dos = (void *)m; IMAGE_EXPORT_DIRECTORY *exp = (void *)(m + 0x1000);
    dos->e_magic = IMAGE_DOS_SIGNATURE; dos->e_lfanew = 0x80;
    if (pe32plus) { IMAGE_NT_HEADERS64 *nt = (void *)(m + 0x80); nt->Signature = IMAGE_NT_SIGNATURE;
        nt->OptionalHeader.Magic = IMAGE_NT_OPTIONAL_HDR64_MAGIC; nt->OptionalHeader.SizeOfImage = 0x2000;
        nt->OptionalHeader.NumberOfRvaAndSizes = 16; nt->OptionalHeader.DataDirectory[0].VirtualAddress = 0x1000;
        nt->OptionalHeader.DataDirectory[2].VirtualAddress = resource_rva; }
    else { IMAGE_NT_HEADERS32 *nt = (void *)(m + 0x80); nt->Signature = IMAGE_NT_SIGNATURE;
        nt->OptionalHeader.Magic = IMAGE_NT_OPTIONAL_HDR32_MAGIC; nt->OptionalHeader.SizeOfImage = 0x2000;
        nt->OptionalHeader.NumberOfRvaAndSizes = 16; nt->OptionalHeader.DataDirectory[0].VirtualAddress = 0x1000;
        nt->OptionalHeader.DataDirectory[2].VirtualAddress = resource_rva; }
    exp->Name = 0x1100; strcpy( (char *)m + 0x1100, name );
}
int main( void ) {
    static const int t64[4], twow[4];
    const void *funcs = NULL;
    make( img[0], 1, "ws2_32.dll", 0 );
    make( img[1], 0, "winemetal.dll", 0 );    /* PE32 without a resource directory: the old parse read 0 */
    printf( "%s %s\n", ios_module_export_name( img[0] ), ios_module_export_name( img[1] ) );
    if (ios_bind_unixlib_table( img[0], "x", 0, t64, NULL, &funcs ) || funcs != t64) return 3;
    funcs = NULL;
    if (ios_bind_unixlib_table( img[0], "x", 1, t64, NULL, &funcs ) != STATUS_NOT_SUPPORTED || funcs) return 4;
    if (ios_bind_unixlib_table( img[0], "x", 1, t64, twow, &funcs ) || funcs != twow) return 5;
    puts( "bind ok" );
    return 0;
}
"""
with tempfile.TemporaryDirectory() as t:
    c = Path(t) / "binder.c"; c.write_text(harness)
    exe = Path(t) / "binder"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wno-unused-function", "-fsanitize=address,undefined",
                    str(c), "-o", str(exe)], check=True)
    out = subprocess.run([str(exe)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.split() == ["ws2_32.dll", "winemetal.dll", "bind", "ok"], out.stdout
print("PASS: PE32 and PE32+ images are named from their own export directory; 64-bit callers get the 64-bit table, 32-bit callers without a wow64 table are refused")
