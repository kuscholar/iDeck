// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#include "helper-path.h"
#include <string.h>
int ideck_native_helper_path(const char *native,char *out,size_t capacity) {
    static const char suffix[]="/steam_osx";
    static const char helper[]="/Mac/Contents/Frameworks/Steam Helper.app/Contents/MacOS/Steam Helper";
    if(!native || !out || native[0]!='/')return 0;
    size_t n=strnlen(native,4096),s=sizeof suffix-1;
    if(n==4096 || n<=s || memcmp(native+n-s,suffix,s))return 0;
    size_t root=n-s;
    // Refuse the intentionally redirected Mac logical executable path.
    if(root<4 || memcmp(native+root-4,".app",4) || root>capacity || sizeof helper>capacity-root)return 0;
    memcpy(out,native,root);memcpy(out+root,helper,sizeof helper);return 1;
}
