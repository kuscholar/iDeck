#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Insert an explicit Lab diagnostic into a copied realfs source, never vendor.

The original native/Linux mapping result remains unchanged. The helper issues
four differently scoped native control mappings, immediately unmaps them and
never installs their addresses in the guest. This is not a fallback/retry fix.
"""
ANCHOR = 'int realfs_getpath(struct fd *fd, char *buf);'
FAILURE = '        if (runtime_memory_failure) runtime_memory_failure("mmap file", 0, map_size, mmap_prot, mmap_flags, native_error);'
CALL = '''        ideck_file_mmap_failure_probe(current->pid, current->tgid,
                fd->real_fd, map_size, real_offset, mmap_prot, mmap_flags,
                native_error, real_page_size);
'''


def patched(body):
    assert body.count(ANCHOR) == 1, 'Pinned realfs declaration changed'
    assert body.count(FAILURE) == 1, 'Pinned original file-mmap failure changed'
    assert 'FileMmapProbe.inc' not in body, 'Probe already applied'
    body = body.replace(ANCHOR, '#define IDECK_LAB_FILE_MMAP_PROBE 1\n#include "FileMmapProbe.inc"\n\n' + ANCHOR)
    return body.replace(FAILURE, CALL + FAILURE)
