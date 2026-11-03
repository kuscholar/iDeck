#!/usr/bin/env python3
"""Compile actual experimental image selector; legacy gates stay authoritative."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
text = (root / 'build/ntdll-unix/virtual_ios.c').read_text()
start = text.index('static int ios_cef64_data_basename(')
end = text.index('\n}', text.index('static int ios_cef64_image_data_accepts(', start)) + 2
code = text[start:end]
site=text[text.index('if (ios_x64_image_nocopy_enabled() && !ios_map_resource_view'):]
site=site[:site.index('view->protect |= VPROT_X64DATA;')]
for gate in ['!ios_wow_base()', 'nt->FileHeader.Machine == IMAGE_FILE_MACHINE_AMD64',
             'nt->OptionalHeader.Magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC',
             '!(view->protect & VPROT_ARM64EC)', '!image_info->is_hybrid', '!image_info->wine_builtin']:
    assert gate in site
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    (tmp / 'test.c').write_text(r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#include <unistd.h>
typedef uint16_t WCHAR;
typedef struct { unsigned short Length, MaximumLength; WCHAR *Buffer; } UNICODE_STRING;
static int held;
static const char *option, *session, *unity, *probe;
static const char *mock_getenv(const char *key) {
 if (!strcmp(key,"MADEIRA_CEF64_LIBCEF_DATA_ONLY")) return option;
 if (!strcmp(key,"MADEIRA_STEAM_UI_SESSION")) return session;
 if (!strcmp(key,"MADEIRA_CEF64_UNITY_DATA_ONLY")) return unity;
 if (!strcmp(key,"MADEIRA_CEF64_IMAGE_DATA_PROBE")) return probe;
 assert(0); return NULL;
}
#define getenv mock_getenv
static int ios_cef64_owned_layout(void) { return held; }
''' + code + r'''
static int accept(const char *path) {
 WCHAR buf[200]; size_t n=strlen(path); assert(n<200);
 for(size_t i=0;i<n;i++)buf[i]=(unsigned char)path[i];
 UNICODE_STRING name={n*2,n*2,buf}; return ios_cef64_image_data_accepts(&name);
}
int main(void) {
 option="1";session="1";held=1;
 assert(accept("libcef.dll"));assert(accept("C:\\Steam\\bin\\CEF.WIN64\\LIBCEF.DLL"));
 assert(accept("/bin/cef/libcef.dll"));
 const char *bad[]={"","steam.exe","steamclient64.dll","chrome_elf.dll","crashpad_handler.exe",
 "libGLESv2.dll","libcef.dll.bak","notlibcef.dll","libcef.dll/"};
 for(size_t i=0;i<sizeof(bad)/sizeof(bad[0]);i++)assert(!accept(bad[i]));
 assert(!accept("UnityPlayer.dll"));assert(!accept("ideck-x64-image.dll"));
 unity="1";assert(accept("C:\\games\\UNITYPLAYER.DLL"));
 assert(!accept("UnityPlayer.dll.bak"));assert(!accept("steam.exe"));
 assert(!accept("steamclient64.dll"));assert(!accept("chrome_elf.dll"));
 unity="10";assert(!accept("UnityPlayer.dll"));unity=NULL;
 probe="1";assert(accept("ideck-x64-image.dll"));assert(!accept("UnityPlayer.dll"));
 assert(!accept("ideck-x64-image.dll.bak"));probe=NULL;
 assert(!ios_cef64_image_data_accepts(NULL));
 WCHAR embedded[]={'l','i','b',0,'e','f','.','d','l','l'};
 UNICODE_STRING n={20,20,embedded};assert(!ios_cef64_image_data_accepts(&n));
 n.Length=19;assert(!ios_cef64_image_data_accepts(&n));
 n.Length=20;n.Buffer=NULL;assert(!ios_cef64_image_data_accepts(&n));
 held=0;assert(accept("steam.exe"));held=1;
 session=NULL;assert(accept("steam.exe"));session="0";assert(accept("steam.exe"));
 session="1 ";assert(accept("steam.exe"));session="1";
 const char *options[]={NULL,"0","true","11","1 "};
 for(size_t i=0;i<sizeof(options)/sizeof(options[0]);i++){option=options[i];assert(accept("steam.exe"));}
 return 0;
}
''')
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    str(tmp / 'test.c'), '-o', str(tmp / 'test')], check=True)
    subprocess.run([str(tmp / 'test')], check=True)
print('PASS actual libcef basename, isolated explicit gates, ordinary fallback, malformed names (ASan/UBSan)')
