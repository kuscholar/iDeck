// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#include "power-registration.c"
#include <assert.h>
static int Calls;
static void callback(void *r,mach_port_t p,uint32_t t,void *v){(void)r;(void)p;(void)t;(void)v;++Calls;}
int main(void) {
    for(int i=0;i<4;++i){IONotificationPortRef port=(void *)1;mach_port_t notifier=17;
        mach_port_t session=IORegisterForSystemPower((void *)1,i&1?NULL:&port,callback,i&2?NULL:&notifier);
        assert(session==MACH_PORT_NULL);if(!(i&1))assert(!port);if(!(i&2))assert(!notifier);
    }
    assert(!Calls);puts("power registration PASS: documented failure sentinel, cleared outputs, null outputs safe, no callback/fake port");
}
