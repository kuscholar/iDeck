#!/usr/bin/env python3
"""Compile the production read-only image patch tracer and owner selector.

Exercise mismatched PE/pool bytes, child/parent routing, unreadable and partial
reads, failed/rounded/foreign requests, overflow, the 64-line concurrent limit,
unchanged image bytes and errno. Mach reads are bounded by a fixture backend;
real iOS Mach reads and guest execution still require the native CI/device run.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "build/ntdll-unix/virtual_ios.c").read_text()


def function(signature):
    start = source.index(signature)
    return source[start:source.index("\n}", start) + 2] + "\n"


start = source.index("#define IOS_JIT_MAX_MAPPINGS")
mapping = source[start:source.index("\n};", start) + 3]
trace = source.split("/* image-patch-test:begin", 1)[1].split("/* image-patch-test:end */", 1)[0]
trace = trace[trace.index("static void ios_trace_image_patch"):]
protect = function("NTSTATUS WINAPI NtProtectVirtualMemory(")
assert protect.index("LPVOID ios_patch_requested = addr;") < protect.index("ROUND_SIZE(")
assert protect.index("ios_trace_image_patch( ios_patch_requested") > protect.rindex("[iat-sync]")
assert protect.count("ios_trace_image_patch(") == 1

harness = r'''
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef uintptr_t ULONG_PTR;
typedef uint64_t mach_vm_address_t;
typedef uint64_t mach_vm_size_t;
#define KERN_SUCCESS 0
#define PAGE_NOACCESS 1
#define PAGE_READONLY 2
#define PAGE_READWRITE 4
#define PAGE_WRITECOPY 8
#define PAGE_EXECUTE 16
#define PAGE_EXECUTE_READ 32
#define PAGE_EXECUTE_READWRITE 64
#define PAGE_EXECUTE_WRITECOPY 128
#define PAGE_GUARD 256
static unsigned char pe[96], parent[96], child[96];
static unsigned int reads;
static int read_failure, partial, missing_teb;
static void *caller;
struct test_teb { struct { uintptr_t UniqueThread; } ClientId; };
static struct test_teb teb = {{0x2c}};
static struct test_teb *NtCurrentTeb(void) { return missing_teb ? NULL : &teb; }
static void *ios_jit_current_peb(void) { return caller; }
static int mach_task_self(void) { return 1; }
static int mach_vm_read_overwrite(int task, mach_vm_address_t address, mach_vm_size_t size,
                                  mach_vm_address_t dest, mach_vm_size_t *actual)
{
    uintptr_t bases[] = {(uintptr_t)pe, (uintptr_t)parent, (uintptr_t)child};
    size_t i;
    assert(task == 1 && size && size <= 16);
    __atomic_fetch_add(&reads, 1, __ATOMIC_RELAXED);
    errno = 9876;
    if (read_failure) return 1;
    for (i = 0; i < 3; i++)
    {
        if (address >= bases[i] && address - bases[i] <= sizeof(pe) - size)
        {
            *actual = partial ? size - 1 : size;
            memcpy((void *)(uintptr_t)dest, (void *)(uintptr_t)address, *actual);
            return 0;
        }
    }
    return 1;
}
''' + mapping + r'''
static struct ios_jit_mapping ios_jit_mappings[IOS_JIT_MAX_MAPPINGS];
static int ios_jit_mapping_count;
''' + function("static int ios_iat_sync_pick_mapping(") + trace + r'''
static void record(void *addr, size_t len, unsigned int prot, unsigned int status)
{
    errno = 1234;
    ios_trace_image_patch(addr, len, prot, status);
    assert(errno == 1234);
}
static void *thread_run(void *unused)
{
    unsigned int i;
    (void)unused;
    for (i = 0; i < 100; i++) record(pe + 7, 5, PAGE_EXECUTE_READ, 0);
    return NULL;
}
int main(int argc, char **argv)
{
    unsigned int i, before;
    unsigned char pe_before[96], parent_before[96], child_before[96];
    pthread_t threads[16];
    assert(argc == 2);
    for (i = 0; i < sizeof(pe); i++) pe[i] = child[i] = 0xe9;
    memset(parent, 0xcc, sizeof(parent));
    memcpy(pe_before, pe, sizeof(pe));
    memcpy(parent_before, parent, sizeof(parent));
    memcpy(child_before, child, sizeof(child));
    caller = (void *)1;
    ios_jit_mapping_count = 2;
    /* The first containing copy belongs to the parent; the child must win. */
    ios_jit_mappings[0].pe_base = pe; ios_jit_mappings[0].jit_base = parent;
    ios_jit_mappings[0].size = sizeof(pe);
    ios_jit_mappings[1].pe_base = pe; ios_jit_mappings[1].jit_base = child;
    ios_jit_mappings[1].size = sizeof(pe); ios_jit_mappings[1].owner_peb = caller;
    if (!strcmp(argv[1], "threads"))
    {
        for (i = 0; i < 16; i++) assert(!pthread_create(&threads[i], NULL, thread_run, NULL));
        for (i = 0; i < 16; i++) assert(!pthread_join(threads[i], NULL));
        assert(reads == 128);
    }
    else if (!strcmp(argv[1], "off"))
    {
        record(pe + 7, 5, PAGE_EXECUTE_READ, 0);
        assert(!reads);
    }
    else
    {
        record(pe + 7, 5, PAGE_EXECUTE_READWRITE, 0); /* child MATCH */
        caller = (void *)2;
        record(pe + 7, 5, PAGE_EXECUTE_READ, 0);      /* fallback DIFFERENT */
        caller = (void *)1;
        before = reads;
        record(pe + 7, 17, PAGE_EXECUTE_READWRITE, 0);
        record(pe, 0, PAGE_EXECUTE_READWRITE, 0);
        record(pe, 5, PAGE_EXECUTE_READ, 0xc0000022);
        record(pe, 5, PAGE_READONLY, 0);
        record(pe, 5, PAGE_EXECUTE, 0);
        record(pe, 5, PAGE_EXECUTE_READ | PAGE_GUARD, 0);
        record(pe + 94, 5, PAGE_EXECUTE_READ, 0);     /* beyond image */
        record((void *)(UINTPTR_MAX - 2), 5, PAGE_EXECUTE_READ, 0);
        record((void *)1, 5, PAGE_EXECUTE_READ, 0);   /* no image */
        missing_teb = 1; record(pe, 5, PAGE_EXECUTE_READ, 0); missing_teb = 0;
        ios_jit_mappings[1].jit_base = (void *)(UINTPTR_MAX - 2);
        record(pe + 7, 5, PAGE_EXECUTE_READ, 0);
        ios_jit_mappings[1].jit_base = child;
        assert(reads == before);
        read_failure = 1; record(pe + 7, 5, PAGE_EXECUTE_READ, 0); read_failure = 0;
        partial = 1; record(pe + 7, 5, PAGE_EXECUTE_READ, 0); partial = 0;
        record(pe + 94, 2, PAGE_EXECUTE_READ, 0);    /* exactly to image end */
        for (i = 0; i < 100; i++) record(pe + 7, 5, PAGE_EXECUTE_READ, 0);
        assert(reads == 128);
    }
    assert(!memcmp(pe_before, pe, sizeof(pe)));
    assert(!memcmp(parent_before, parent, sizeof(parent)));
    assert(!memcmp(child_before, child, sizeof(child)));
    return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    c, exe = directory / "trace.c", directory / "trace"
    c.write_text(harness)
    command = ["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined", "-pthread"]
    if sys.platform.startswith("linux"):
        command += ["-fno-pie", "-no-pie"]
    subprocess.run(command + [str(c), "-o", str(exe)], check=True)
    env = dict(os.environ)
    env.pop("MADEIRA_IAT_SYNC_OWNER", None)
    env.pop("MADEIRA_IMAGE_PATCH_TRACE", None)
    for mode in (None, "0", "anything"):
        off = dict(env)
        if mode is not None:
            off["MADEIRA_IMAGE_PATCH_TRACE"] = mode
        result = subprocess.run([str(exe), "off"], capture_output=True, text=True, env=off)
        assert result.returncode == 0 and not result.stderr, result.stderr
    env["MADEIRA_IMAGE_PATCH_TRACE"] = "1"
    for scenario in ("normal", "threads"):
        result = subprocess.run([str(exe), scenario], capture_output=True, text=True, env=env)
        assert result.returncode == 0, result.stderr
        lines = result.stderr.splitlines()
        assert len(lines) == 64 and all(l.startswith("[image-patch]") for l in lines), lines
        assert sorted(int(re.search(r"#(\d+)", l)[1]) for l in lines) == list(range(1, 65))
        if scenario == "normal":
            assert "rva=0x7 len=5 prot=0x40" in lines[0] and lines[0].endswith("MATCH"), lines[:2]
            assert "pe=e9e9e9e9e9 pool=cccccccccc DIFFERENT" in lines[1], lines[1]
            assert lines[2].endswith("pe=unreadable pool=unreadable UNREADABLE"), lines[2]
            assert lines[3].endswith("UNREADABLE"), lines[3]
            assert "rva=0x5e len=2" in lines[4], lines[4]
        else:
            assert all(l.endswith("MATCH") for l in lines), lines

print("PASS: production tracer is read-only, optional, bounded and owner-aware; safe failed/partial reads, "
      "short requests, overflow, concurrent 64-line cap, image bytes and errno preserved")
