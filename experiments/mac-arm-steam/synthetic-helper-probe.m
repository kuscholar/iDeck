// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Own signed fixture only. No Steam entry, CEF, PID spoofing or child processes.
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <limits.h>
#import <stdio.h>
#import <stdlib.h>
#import <string.h>
#import <unistd.h>
__attribute__((constructor)) static void SyntheticHelperProbe(void){
 const char *setting=getenv("IDeckSyntheticHelperProbe");if(!setting || strcmp(setting,"1"))return;
 @autoreleasepool{
  void *lib=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY);int(*nativepath)(char *,uint32_t *)=lib?dlsym(lib,"_NSGetExecutablePath"):NULL;
  char raw[PATH_MAX];uint32_t n=sizeof raw;
  if(!nativepath || nativepath(raw,&n)){fputs("[ideck-synthetic-helper] setup=failed\n",stderr);_exit(2);}
  NSString *root=[@(raw) stringByDeletingLastPathComponent];
  const char *names[]={"IDeckSyntheticExecutable","IDeckSyntheticBundle"};int okay=1;
  for(unsigned i=0;i<2;++i){
   NSString *path=[root stringByAppendingPathComponent:[@"Mac/Contents/MacOS/" stringByAppendingString:@(names[i])]];
   dlerror();void *h=dlopen(path.fileSystemRepresentation,RTLD_NOW|RTLD_LOCAL);int valid=0;
   if(h){int(*readfn)(void)=dlsym(h,"IDeckFixtureRead");const char *(*marker)(void)=dlsym(h,"IDeckFixtureMarker");valid=readfn&&marker&&!strcmp(marker(),"IDeckSyntheticHelperFixture-v1")&&readfn()==100;}
   fprintf(stderr,"[ideck-synthetic-helper] kind=%s loaded=%d fixture-verified=%d main-called=0\n",i?"bundle":"executable",h!=NULL,valid);
   if(i && !valid)okay=0;
  }
  fprintf(stderr,"[ideck-synthetic-helper] diagnostic-result=%d steam-entry=0 cef=0 process-emulation=0\n",okay?0:3);_exit(okay?0:3);
 }
}
