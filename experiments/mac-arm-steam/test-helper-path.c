// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#include "helper-path.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void) {
 char out[4096];assert(ideck_native_helper_path("/private/UUID/Steam-iOS.app/steam_osx",out,sizeof out));
 assert(!strcmp(out,"/private/UUID/Steam-iOS.app/Mac/Contents/Frameworks/Steam Helper.app/Contents/MacOS/Steam Helper"));
 assert(!ideck_native_helper_path("/private/UUID/Steam-iOS.app/Mac/Contents/MacOS/steam_osx",out,sizeof out));
 assert(!ideck_native_helper_path("relative.app/steam_osx",out,sizeof out));assert(!ideck_native_helper_path(NULL,out,sizeof out));assert(!ideck_native_helper_path("/a.app/steam_osx",out,3));assert(!ideck_native_helper_path("/a.app/other",out,sizeof out));
 puts("helper native path PASS: exactly one Mac root, logical-path rejection and bounded output");
}
