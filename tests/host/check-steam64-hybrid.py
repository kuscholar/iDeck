#!/usr/bin/env python3
"""Check lossless forwarding of Windows/Chromium argument tails on the host."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
test = r'''
#include <assert.h>
#include <wchar.h>
#include "hybrid-webhelper-args.h"
int main(void) {
 assert(!wcscmp(hybrid_args_tail(NULL), L""));
 assert(!wcscmp(hybrid_args_tail(L"C:\\foo.exe"), L""));
 assert(!wcscmp(hybrid_args_tail(L"\"C:\\Program Files\\foo.exe\""), L""));
 assert(!wcscmp(hybrid_args_tail(L"\"C:\\Program Files\\foo.exe\"\t  --a=1 \"x y\""), L"--a=1 \"x y\""));
 assert(!wcscmp(hybrid_args_tail(L"foo.exe --name=中文 --path=\"a\\\\\"b\""), L"--name=中文 --path=\"a\\\\\"b\""));
 assert(!wcscmp(hybrid_args_tail(L"foo.exe\t--single-process"), L"--single-process"));
}
'''
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / 'test.c'
    src.write_text(test)
    binary = Path(td) / 'test'
    subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-I', str(root / 'tests/steam-ui'),
                    str(src), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('PASS hybrid command-line forwarding (host only)')
