#!/usr/bin/env python3
"""Exercise the real overlap lookup and gated grant block, with a mock view tree."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'build/ntdll-unix/virtual_ios.c').read_text()
def block(start):
    a=s.index(start);b=s.index('{',a);depth=1;i=b+1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}');i+=1
    return s[a:i]
lookup=block('static struct file_view *find_view_range(')
start=s.index('/* Isolated Steam UI experiment:')
a=s.index('{',start);depth=1;i=a+1
while depth:
    depth+=(s[i]=='{')-(s[i]=='}');i+=1
guard=s[a:i]
preamble=r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
typedef size_t SIZE_T;
struct wine_rb_entry {struct wine_rb_entry *left,*right;};
struct file_view {struct wine_rb_entry entry;void *base;size_t size;};
#define WINE_RB_ENTRY_VALUE(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
static struct {struct wine_rb_entry *root;} views_tree;
static int virtual_mutex,locked,enters,leaves;
static void server_enter_uninterrupted_section(int *m,sigset_t *s){assert(!locked);locked=1;enters++;}
static void server_leave_uninterrupted_section(int *m,sigset_t *s){assert(locked);locked=0;leaves++;}
'''
main=r'''
static int try_grant(uintptr_t slot,SIZE_T size){
    SIZE_T *size_ptr=&size;uintptr_t off=0,align_unit=0;int accepted=0;
    for(int iteration=0;iteration<1;iteration++){
        GUARD
        accepted=1;
    }
    assert(!locked && enters==leaves);return accepted;
}
int main(void){
    struct file_view center={.base=(void*)0x7800200000,.size=0x200000};
    struct file_view low={.base=(void*)0x7400000000,.size=0x10000};
    struct file_view high={.base=(void*)0x7c00000000,.size=0x10000};
    center.entry.left=&low.entry;center.entry.right=&high.entry;views_tree.root=&center.entry;
    unsetenv("MADEIRA_STEAM_UI_SESSION");unsetenv("MADEIRA_STEAM_UI_STRICT_RESERVATIONS");
    assert(try_grant(0x77ffff0000,0x400010000));assert(!enters);
    setenv("MADEIRA_STEAM_UI_SESSION","1",1);
    assert(try_grant(0x77ffff0000,0x400010000));assert(!enters);
    setenv("MADEIRA_STEAM_UI_STRICT_RESERVATIONS","1",1);
    assert(!try_grant(0x77ffff0000,0x400010000)); /* Guard-prefixed full pool intersects a small interior view. */
    assert(!try_grant(0x78001ffff0,0x20)); /* Partial overlap. */
    assert(!try_grant(0x7400000000,0x10000)); /* Other tree branch. */
    assert(try_grant(0x78001ffff0,0x10)); /* Boundary touch is not overlap. */
    assert(try_grant(0x7800400000,0x10000)); /* Free range. */
    setenv("MADEIRA_STEAM_UI_SESSION","10",1);
    assert(try_grant(0x77ffff0000,0x400010000)); /* Exact feature flag only. */
    puts("PASS: actual view lookup and grant guard reject partial/interior/guard-prefix overlap; preserve disjoint/boundary/default paths; locks balanced");
}
'''.replace('GUARD',guard)
with tempfile.TemporaryDirectory() as td:
    td=Path(td);(td/'test.c').write_text(preamble+lookup+main)
    subprocess.run(['cc','-fsanitize=address,undefined',str(td/'test.c'),'-o',str(td/'test')],check=True)
    subprocess.run([str(td/'test')],check=True)
