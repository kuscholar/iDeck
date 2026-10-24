#!/usr/bin/env python3
"""Nothing between thread_suspend and thread_resume in the samplers may take a lock.

Build 476, RDR2 (2026-10-09 16:55:52): the guest RIP profile (ml979) suspended
every thread and called pthread_from_mach_thread_np with it still suspended.
That call takes libpthread's thread-list lock; a thread suspended while it held
the lock (starting or ending a thread) was never resumed, so the profile, the
[xp] probe, the stack dumps and every later thread start and exit blocked: the
game froze. The watchdog logged (malloc, Swift) with its thread suspended.

This check reads build/ntdll-unix/server_ios.c, finds every thread_suspend and
the standalone thread_resume that closes its window, and fails when the window
calls anything that can take a lock.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'build/ntdll-unix/server_ios.c'

FORBIDDEN = (
    'pthread_from_mach_thread_np', 'pthread_getname_np', 'pthread_kill',
    'wine_log_write', 'wine_ui_log', 'dprintf', 'fprintf', 'printf(', 'ERR(', 'WARN(', 'TRACE(',
    'malloc', 'calloc', 'realloc', 'free(', 'dladdr', 'ios_ts_sym', 'ios_ts_map_for_teb',
    'pthread_mutex_lock', 'os_unfair_lock_lock',
)
RESUME = re.compile(r'^\s*thread_resume\s*\(.*\);\s*$')
CALL = re.compile(r'\bthread_suspend\s*\(')


def windows(lines):
    """(suspend line, resume line) pairs, 1-based; resume is the first
    standalone thread_resume after the suspend (a resume inside a one-line
    failure branch does not end the window)."""
    out = []
    for i, line in enumerate(lines):
        if not CALL.search(line) or line.lstrip().startswith(('*', '/*', '//')):
            continue
        for j in range(i + 1, min(i + 200, len(lines))):
            if RESUME.match(lines[j]):
                out.append((i + 1, j + 1))
                break
        else:
            raise SystemExit(f'{SRC.name}:{i + 1}: thread_suspend without a thread_resume within 200 lines')
    return out


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def main():
    raw = SRC.read_text().splitlines()
    code = strip_comments('\n'.join(raw)).splitlines()
    found = windows(code)
    if len(found) < 6:
        raise SystemExit(f'expected at least 6 suspend windows in {SRC.name}, found {len(found)}')
    bad = []
    for s, r in found:
        skip = set()
        # `kr = thread_suspend(...); if (kr != KERN_SUCCESS) { ...; return; }`:
        # nothing is suspended inside that failure branch.
        m = re.search(r'(\w+)\s*=\s*thread_suspend\s*\(', code[s - 1])
        if m and re.match(r'\s*if\s*\(\s*%s\s*!=\s*KERN_SUCCESS\s*\)\s*\{' % m.group(1), code[s]):
            depth, n = 0, s
            while True:
                depth += code[n].count('{') - code[n].count('}')
                skip.add(n)
                n += 1
                if depth <= 0:
                    break
        for n in range(s, r - 1):          # lines after the suspend, before the resume
            if n in skip:
                continue
            text = code[n]
            if n == s - 1:                  # the suspend line itself: only what follows the call
                text = text[CALL.search(text).end():]
            for f in FORBIDDEN:
                if f in text:
                    bad.append(f'{SRC.name}:{n + 1}: {f} inside the suspend window {s}-{r}')
    if bad:
        raise SystemExit('\n'.join(bad))

    # The two windows this check was written for.
    src = SRC.read_text()
    prof = src.index('static void ios_guest_rip_profile')
    body = src[prof:src.index('\n}\n', prof)]
    lookup = body.index('pt = pthread_from_mach_thread_np( tl[k] );')
    assert lookup < body.index('if (thread_suspend( tl[k] ) != KERN_SUCCESS) continue;'), \
        'ml979: the pthread lookup must come before the suspend'
    assert 'ios_ts_teb( pt )' in body
    dog = src.index('Suspend thread for consistent state reading')
    seg = src[dog:src.index('dispatch_after(', dog)]
    assert seg.index('thread_resume(wine_mach_thread);') < seg.index('wine_log_write("[Wine WATCHDOG %ds] PC='), \
        'watchdog: resume before logging'
    assert seg.count('thread_resume(') == 1, 'watchdog: exactly one resume'
    print(f'suspend windows: {len(found)} checked, none takes a lock')


if __name__ == '__main__':
    main()
