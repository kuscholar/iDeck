// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv){
 if(argc!=3)return 2;
 void *original=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
 printf("synthetic host original-executable-loaded=%d\n",original!=NULL);
 void *bundle=dlopen(argv[2],RTLD_NOW|RTLD_LOCAL);
 if(!bundle){fprintf(stderr,"synthetic bundle load failed: %s\n",dlerror());return 4;}
 int(*readfn)(void)=dlsym(bundle,"IDeckFixtureRead");const char *(*marker)(void)=dlsym(bundle,"IDeckFixtureMarker");
 if(!readfn||!marker||strcmp(marker(),"IDeckSyntheticHelperFixture-v1")||readfn()!=100)return 5;
 puts("synthetic host discriminator PASS: metadata-only signed bundle loads; constructor1/main0; original result separately reported; no Steam/CEF claims");return 0;
}
