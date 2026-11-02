#!/usr/bin/env python3
"""Read-only submap descent must follow the original requested address."""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[2]
s=(root/'build/diagnostics/steam_ui_vm_probe.h').read_text()
body=s[s.index('static int madeira_steam_ui_vm_backing'):s.index('\n#endif',s.index('static int madeira_steam_ui_vm_backing'))]
code=r'''#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t vm_address_t,vm_size_t;typedef unsigned natural_t,mach_msg_type_number_t;typedef int kern_return_t;
typedef struct{unsigned is_submap,user_tag,share_mode,external_pager,object_id;uint64_t offset;int protection,max_protection;}vm_region_submap_info_data_64_t;
typedef vm_region_submap_info_data_64_t *vm_region_recurse_info_t;
#define VM_REGION_SUBMAP_INFO_COUNT_64 1
#define KERN_SUCCESS 0
#define KERN_INVALID_ARGUMENT 4
static unsigned calls;static int mode;static uint64_t target;
static int mach_task_self(void){return 7;}
static int vm_region_recurse_64(int task,vm_address_t *base,vm_size_t *size,natural_t *depth,vm_region_recurse_info_t info,mach_msg_type_number_t *count){
 assert(task==7&&*count==1);calls++;
 if(!*depth)target=*base;else assert(*base==target);
 if(mode==1)return 4;
 if(mode==2||!*depth){*base=0;*size=UINT64_C(0x8000000000);info->is_submap=1;return 0;}
 assert(*depth==1);*base=mode==3?target+0x1000:target-0x1000;*size=0x2000;
 info->is_submap=0;info->user_tag=31;return 0;
}
'''+body+r'''
int main(int argc,char **argv){assert(argc==2);mode=atoi(argv[1]);FILE *out=tmpfile();assert(out);assert(!madeira_steam_ui_vm_backing(out));rewind(out);
 char line[900];unsigned rows=0;while(fgets(line,sizeof(line),out)){rows++;assert(strstr(line,mode?"contains=0":"contains=1"));}assert(rows==8);
 assert(calls==(mode==1?8:mode==2?64:16));fclose(out);return 0;}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.c').write_text(code)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 for mode in range(4):subprocess.run([str(p/'test'),str(mode)],check=True)
print('PASS actual read-only VM backing observer: original target descent, leaf containment, errors and eight-level bound; ASan/UBSan')
