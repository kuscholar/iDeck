/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "LabStartupMode.h"
#include <string.h>
#include <errno.h>
int ideck_lab_startup_mode(int argc,const char *const *argv) {
    if(argc<1||!argv)return -EINVAL;
    unsigned selected=0,other=0;
    for(int i=1;i<argc;i++) {
        if(!argv[i])return -EINVAL;
        if(!strcmp(argv[i],IDECK_LAB_COLD_SETUP))selected++;
        else if(!strncmp(argv[i],"linux-",6)||!strncmp(argv[i],"madeira-",8))other++;
    }
    if(!selected)return 0;
    return selected==1&&!other?1:-EINVAL;
}
