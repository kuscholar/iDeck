/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Own test only: actual glibc local versus global libX11 dependency scope.
 */
extern void *dlopen(const char *,int);
extern void *dlsym(void *,const char *);
extern int dlclose(void *);
extern int strcmp(const char *,const char *);
int main(int argc,char **argv) {
    if(argc!=2||(strcmp(argv[1],"local")&&strcmp(argv[1],"global")))return 2;
    void *plugin=dlopen("/ideck-scope-plugin.so",2|(!strcmp(argv[1],"global")?256:0));
    if(!plugin)return 3;
    int (*query)(void)=(int (*)(void))dlsym(plugin,"ideck_scope_query");
    if(!query)return 4;
    int global=!strcmp(argv[1],"global");
    if((dlsym(0,"ideck_scope_query")!=0)!=global)return 6;
    int result=query();
    if((dlsym(0,"ideck_scope_query")!=0)!=global)return 7;
    if(dlclose(plugin))return 5;return result;
}
