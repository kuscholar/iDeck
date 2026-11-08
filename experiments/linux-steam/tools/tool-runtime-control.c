/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Native host exercise of installed diagnostic wrapper; never credential entry. */
#include "LinuxLabRuntime.h"
#include "ToolInstall.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static void *read_asset(const char *base,const char *name,size_t *size){char path[4096];int n=snprintf(path,sizeof path,"%s/%s",base,name);if(n<0||n>=(int)sizeof path)return NULL;FILE *f=fopen(path,"rb");if(!f)return NULL;if(fseek(f,0,SEEK_END)){fclose(f);return NULL;}long count=ftell(f);if(count<1||count>262144||fseek(f,0,SEEK_SET)){fclose(f);return NULL;}void *p=malloc((size_t)count);if(!p){fclose(f);return NULL;}size_t got=fread(p,1,(size_t)count,f);fclose(f);if(got!=(size_t)count){free(p);return NULL;}*size=got;return p;}
extern const char *sock_tmp_prefix;
extern unsigned ideck_lab_bridge_requests(void);
int main(int argc,char **argv){
 if(argc!=5||(strcmp(argv[4],"diagnostic")&&strcmp(argv[4],"frontend")))return 2;
 struct ideck_tool_payload p={0};p.executable=read_asset(argv[2],"ideck-madeira",&p.executable_size);p.compatibility=read_asset(argv[2],"compatibilitytool.vdf",&p.compatibility_size);p.manifest=read_asset(argv[2],"toolmanifest.vdf",&p.manifest_size);if(!p.executable||!p.compatibility||!p.manifest)return 3;
 dup2(2,666);sock_tmp_prefix=argv[3];int diagnostic=!strcmp(argv[4],"diagnostic");
 int status=diagnostic?ideck_linux_lab_compatibility_tool_probe(argv[1],&p):ideck_linux_lab_steam_frontend_with_tool(argv[1],&p);
 unsigned requests=ideck_lab_bridge_requests();printf("outer_status=%d native_bridge_requests=%u\n",status,requests);if(diagnostic)printf("scope=synthetic AppID diagnostic125; no Steam-discovered Play/ownership/game claim\n");
 free((void *)p.executable);free((void *)p.compatibility);free((void *)p.manifest);
 return status!=0||(diagnostic&&requests!=1);
}
