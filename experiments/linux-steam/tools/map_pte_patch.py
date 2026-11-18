# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Own ordinary-map allocation preflight; pinned vendor source stays unchanged."""
from pathlib import Path
import importlib.util
_s=importlib.util.spec_from_file_location('fork_transform',Path(__file__).with_name('fork-map-failure.py'))
_m=importlib.util.module_from_spec(_s);_s.loader.exec_module(_m)
function=_m.function
PIN=_m.PIN

def patched_memory(body):
    original=function(body,'static struct pt_entry *mem_pt_new(')
    checked=original.replace('mem_pt_new(', 'ideck_map_pt_new(')
    checked=checked.replace('    int i0 =','    if (!l0) return NULL;\n    int i0 =',1)
    checked=checked.replace('        mem->pgdir_used++;','        if (!l1) return NULL;\n        mem->pgdir_used++;',1)
    checked=checked.replace('    int i2 =','    if (!l2) return NULL;\n    int i2 =',1)
    checked=checked.replace('    int i3 =','    if (!l3) return NULL;\n    int i3 =',1)
    helper=r'''
/* No backing/reference/accounting mutation occurs until ALL target leaves
 * exist. On failure prune empty metadata in this range; populated mappings,
 * their ownership and the caller's input backing stay untouched. Caller holds
 * the existing address-space write lock. No allocator retry or cap increase. */
_Atomic uint64_t ideck_map_pte_allocation_failures;
static bool ideck_map_node_empty(struct pt_node *node) {
    for (unsigned i=0;i<PT_ENTRIES;i++) if (node->children[i]) return false;
    return true;
}
static void ideck_map_prune_empty_leaf(struct mem *mem,page_t page) {
    if (!mem->pgdir) return;
    unsigned i0=PT_INDEX(page,0),i1=PT_INDEX(page,1),i2=PT_INDEX(page,2);
    struct pt_node *l1=mem->pgdir->children[i0];if (!l1) return;
    struct pt_node *l2=l1->children[i1];
    if (l2) {
        struct pt_entry *l3=l2->children[i2];
        if (l3) {
            for (unsigned i=0;i<PT_ENTRIES;i++) if (l3[i].data) return;
            free(l3);l2->children[i2]=NULL;
        }
        if (!ideck_map_node_empty(l2)) return;
        free(l2);l1->children[i1]=NULL;
    }
    if (!ideck_map_node_empty(l1)) return;
    free(l1);mem->pgdir->children[i0]=NULL;mem->pgdir_used--;
}
static int ideck_map_preflight(struct mem *mem,page_t start,pages_t pages) {
    if (!pages) return 0;
    if (start>=MEM_PAGES || pages>MEM_PAGES-start) return _EINVAL;
    page_t end=start+pages,failed=0;
    for (page_t page=start;page<end;) {
        if (!ideck_map_pt_new(mem,page)) { failed=page;goto rollback; }
        page_t next=(page|(PT_ENTRIES-1))+1;
        page=next<end?next:end;
    }
    return 0;
rollback:
    atomic_fetch_add_explicit(&ideck_map_pte_allocation_failures,1,memory_order_relaxed);
    for (page_t page=start;;) {
        ideck_map_prune_empty_leaf(mem,page);
        if (page==failed) break;
        page_t next=(page|(PT_ENTRIES-1))+1;
        page=next<failed?next:failed;
    }
    return _ENOMEM;
}
const char *ideck_map_pte_guard_marker(void){return "IDECK_MAP_PTE_PREFLIGHT_V1";}
'''
    anchor='static int pt_map_accounted('
    assert body.count(anchor)==1
    body=body.replace(anchor,checked+'\n'+helper+'\n'+anchor,1)
    original_map=function(body,anchor)
    allocation='''    if (data == NULL)
        return _ENOMEM;
'''
    assert original_map.count(allocation)==1
    new_map=original_map.replace(allocation,allocation+'''    int preflight=ideck_map_preflight(mem,start,pages);
    if (preflight<0) { free(data);return preflight; }
''',1)
    return body.replace(original_map,new_map,1)
