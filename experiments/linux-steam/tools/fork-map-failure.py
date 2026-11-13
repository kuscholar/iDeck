#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Opt-in fork table-copy allocation checks in private pinned source copies.

Does not change the ordinary mapping allocator, memory limits, FEX or Valve.
Partial child state stays owned by the child and mm_copy destroys it on error.
"""
PIN = 'd1419782da2e299fe22f1ddb85c70ae3d1e276b1'

def function(body, signature):
    start = body.index(signature)
    end = body.index('{', start) + 1
    depth = 1
    while depth:
        depth += (body[end] == '{') - (body[end] == '}')
        end += 1
    return body[start:end]

def memory(body):
    original = function(body, 'static struct pt_entry *mem_pt_new(')
    helper = original.replace('mem_pt_new(', 'ideck_fork_pt_new(')
    helper = helper.replace('    int i0 =', '    if (l0 == NULL) return NULL;\n    int i0 =', 1)
    helper = helper.replace('        mem->pgdir_used++;', '        if (l1 == NULL) return NULL;\n        mem->pgdir_used++;')
    helper = helper.replace('    int i2 =', '    if (l2 == NULL) return NULL;\n    int i2 =', 1)
    helper = helper.replace('    int i3 =', '    if (l3 == NULL) return NULL;\n    int i3 =', 1)
    original_copy = function(body, 'int pt_copy_on_write(')
    copy = original_copy.replace('    for (page_t page =', '    int error = 0;\n    for (page_t page =', 1)
    copy = copy.replace('        if (pt_unmap_always(dst, page, 1) < 0)\n            return -1;', '''        error = pt_unmap_always(dst, page, 1);
        if (error < 0) goto finish;
        /* Allocate before changing the source flags or backing refcount. */
        struct pt_entry *dst_entry = ideck_fork_pt_new(dst, page);
        if (dst_entry == NULL) { error = _ENOMEM; goto finish; }''')
    copy = copy.replace('        struct pt_entry *dst_entry = mem_pt_new(dst, page);\n', '')
    account_start = copy.index('#if ANON_MMAP_LIMIT_PAGES > 0\n    // The child')
    account_end = copy.index('    for (struct mem_reservation', account_start)
    accounting = copy[account_start:account_end]
    copy = copy[:account_start] + copy[account_end:]
    copy = copy.replace('        if (copy) {', '        if (copy == NULL) { error = _ENOMEM; goto finish; }\n        {')
    copy = copy.replace('    mem_changed(src);', '''finish:
    /* Charge even a partial child before its caller destroys it. */
''' + accounting + '    mem_changed(src);')
    copy = copy.replace('    return 0;\n}', '    return error;\n}')
    assert 'mem_pt_new(dst' not in copy and copy.count('finish:') == 1
    return body.replace(original_copy, helper + '\n\n' + copy) + '\nconst char *ideck_fork_map_failure_marker(void){return "IDECK_FORK_MAP_ENOMEM_V1";}\n'

def mmap(body):
    old = '    if (ipc_shm_mm_copy(mm, new_mm) < 0) {'
    assert body.count(old) == 1
    body = body.replace(old, '''    if (new_mm->mem.pgdir == NULL || ipc_shm_mm_copy(mm, new_mm) < 0 ||
            pt_copy_on_write(&mm->mem, &new_mm->mem, 0, MEM_PAGES) < 0) {''')
    old = '    pt_copy_on_write(&mm->mem, &new_mm->mem, 0, MEM_PAGES);\n'
    assert body.count(old) == 1
    return body.replace(old, '')

def fork(body):
    old = '        task_set_mm(task, mm_copy(mm));'
    assert body.count(old) == 1
    return body.replace(old, '''        struct mm *child_mm = mm_copy(mm);
        if (child_mm == NULL) return _ENOMEM;
        task_set_mm(task, child_mm);''')
