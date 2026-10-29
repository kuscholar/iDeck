#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Synthetic Valve key-value manifest parsing and rejection checks."""
from pathlib import Path
import importlib.util,json
root=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('fetch',root/'tools/fetch-steam-ui-client.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
archive='"file" "file.zip.1234" "size" "100" "sha2" "'+'a'*64+'"'
text='"win32" { "version" "1769731672" "bins_win32" { '+archive+' } "bins_cef_win32" { '+archive+' } "bins_webhelpers_win32" { '+archive+' } "steam_win32" { "steamrow" { '+archive+' } } }'
v,p=m.parse_manifest(text,'win32');assert v=='1769731672' and set(p)=={'bins_win32','bins_cef_win32','bins_webhelpers_win32','steam_win32'}
for bad in [text + "garbage", text[:-1],text+'}',text.replace('"100"','"-1"'),text.replace('file.zip.1234','../escape'),text.replace('a'*64,'bad'),text.replace('"version" "1769731672"','"version" "1769731672" "version" "mixed"'),text.replace('"bins_cef_win32"','"missing"')]:
 try:m.parse_manifest(bad,'win32')
 except (ValueError,KeyError):pass
 else:raise AssertionError('malformed manifest accepted')
c=json.loads((root/'app/Madeira/SteamClientPackages.json').read_text());assert len(c['packages'])==19 and len(c['files'])==6233
assert len({x['name'] for x in c['packages']})==19 and sum(x['bytes'] for x in c['packages'])==334243667
assert sum(x['bytes'] for x in c['files'].values())==729535453
print('PASS manifest nesting, architecture/package choice, duplicates, truncation, unsafe path, invalid hashes/length, complete 19-package/6233-file catalog')
