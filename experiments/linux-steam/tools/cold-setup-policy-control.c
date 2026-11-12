/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "LabStartupMode.h"
#include <assert.h>
#include <stdio.h>
static int mode(int n,const char *const *a){return ideck_lab_startup_mode(n,a);}
int main(void){
 const char *normal[]={"Madeira","linux-steam-retained-frontend"};assert(mode(2,normal)==0);
 const char *cold[]={"Madeira",IDECK_LAB_COLD_SETUP};assert(mode(2,cold)==1);
 const char *mixed[]={"Madeira",IDECK_LAB_COLD_SETUP,"linux-steam-retained-frontend"};assert(mode(3,mixed)<0);
 const char *native[]={"Madeira",IDECK_LAB_COLD_SETUP,"madeira-keyed-event-diagnostics"};assert(mode(3,native)<0);
 const char *twice[]={"Madeira",IDECK_LAB_COLD_SETUP,IDECK_LAB_COLD_SETUP};assert(mode(3,twice)<0);
 const char *system[]={"Madeira",IDECK_LAB_COLD_SETUP,"-ApplePersistenceIgnoreState","YES"};assert(mode(4,system)==1);
 puts("PASS explicit cold selection, existing Linux selection, experiment exclusivity and system args");return 0;
}
