#!/usr/bin/env python3
"""Check the reporting-preserving standalone experiment, not Steam success."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "experiments/cef64/crashpad"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def check_config():
    m = module("crash_config", SOURCE / "configure.py")
    line = "ExternalHandler=" + m.HANDLER
    original = b"# keep\r\n[Config]\r\nServerURL=https://example.invalid/dumps\r\nRateLimitEnabled=true\r\n[CrashKeys]\r\nexample=small\r\n"
    changed = m.configure(original)
    assert changed == original.replace(b"[Config]\r\n", ("[Config]\r\n" + line + "\r\n").encode())
    assert m.configure(changed) == changed
    assert m.configure(b"") == ("[Config]\n" + line + "\n").encode()
    assert m.configure(b"[Config]") == ("[Config]\n" + line + "\n").encode()
    assert m.configure(b"\xef\xbb\xbf[Config]\n").startswith(b"\xef\xbb\xbf[Config]\n")
    for bad in (b"[Config]\nExternalHandler=other.exe\n", b"[Config]\n[Config]\n",
                b"[Config]\n ExternalHandler = other.exe\n",
                b"[config]\n", b"[Config]\nExternalHandler=a\nexternalhandler=b\n",
                b"[Config]\0", b"X" * 65537, b"\xff"):
        try:
            m.configure(bad)
        except (ValueError, UnicodeError):
            pass
        else:
            raise AssertionError("ambiguous config accepted")


def check_source(root):
    j = json.loads((root / "ideck-crashpad-source.json").read_text())
    p = module("standalone_prepare", SOURCE / "prepare.py")
    assert j["crashpad_revision"] == p.CRASHPAD and j["cef_revision"] == p.CEF
    patch = (root / "ideck-cef-crashpad.patch").read_bytes()
    assert hashlib.sha256(patch).hexdigest() == p.PATCH
    assert len(j["complete_patch_files"]) == 8
    for name, sha in j["complete_patch_files"].items():
        if name not in ("handler/BUILD.gn", "handler/handler_main.cc"):
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, name
    # Handler implementation differs from the full upstream patch only in
    # its compile-time CEF feature selection. No error/assertion path changes.
    current = (root / "handler/handler_main.cc").read_text()
    restored = current.replace("#if 1  // This standalone target includes the published CEF crash policy.",
                               "#if BUILDFLAG(ENABLE_CEF)")
    restored = restored.replace('#include "build/chromeos_buildflags.h"\n',
                                 '#include "build/chromeos_buildflags.h"\n#include "cef/libcef/features/features.h"\n')
    assert hashlib.sha256(restored.encode()).hexdigest() == j["complete_patch_files"]["handler/handler_main.cc"]
    for name, sha in j["cef_original_files"].items():
        data = (root / "cef" / name).read_text()
        if name.endswith("cef_crash_report_utils.cc"):
            data = data.replace('#include "ideck/cef_string_pairs.h"', '#include "base/strings/string_split.h"')
            data = data.replace("ideck_cef::", "base::")
        # Only includes lost their Chromium-root prefix.
        data = data.replace('#include "client/settings.h"', '#include "third_party/crashpad/crashpad/client/settings.h"')
        data = data.replace('#include "handler/crash_report_upload_thread.h"',
                            '#include "third_party/crashpad/crashpad/handler/crash_report_upload_thread.h"')
        assert hashlib.sha256(data.encode()).hexdigest() == sha, name
    assert (root / "ideck/cef_string_pairs.h").read_bytes() == (SOURCE / "cef_string_pairs.h").read_bytes()
    assert (root / "ideck/cef_handler_args.h").read_bytes() == (SOURCE / "cef_handler_args.h").read_bytes()
    entry = (root / "handler/main.cc").read_text()
    entry = entry.replace('#include "ideck/cef_handler_args.h"\n', '')
    entry = entry.replace('  if (!ideck_cef::RemoveHandlerRole(&argc, argv)) return 2;\n', '')
    assert hashlib.sha256(entry.encode()).hexdigest() == j["handler_entry_original_sha256"]
    assert 'public_deps = [ "mini_chromium/base" ]' in (root / "third_party/mini_chromium/BUILD.gn").read_text()
    assert 'crashpad_dependencies = "standalone"' in (root / "build/crashpad_buildconfig.gni").read_text()


def compile_parser(root):
    with tempfile.TemporaryDirectory(prefix="ideck-crashpad-host-") as temporary:
        temporary = Path(temporary)
        test = temporary / "test.cc"
        extra = '#include "cef/libcef/common/cef_crash_report_utils.h"\n' if root else ""
        test.write_text('''#include <cassert>
#include "cef_string_pairs.h"
#include "cef_handler_args.h"
''' + extra + '''
int main() {
  char executable[]="handler.exe", role[]="--type=crashpad-handler", wrong[]="--type=renderer";
  char ipc[]="--initial-client-data=opaque", report[]="--url=https://example.invalid/dumps";
  char database[]="--database=private", monitor[]="--monitor-self-argument=--type=crashpad-handler";
  char* arguments[] = {executable,role,ipc,report,database,monitor,nullptr};
  int argc=6;
  assert(ideck_cef::RemoveHandlerRole(&argc,arguments) && argc==5 && arguments[5]==nullptr);
  assert(arguments[1]==ipc && arguments[2]==report && arguments[3]==database && arguments[4]==monitor);
  char* duplicate[]={executable,role,role,nullptr}; argc=3;
  assert(!ideck_cef::RemoveHandlerRole(&argc,duplicate));
  char* invalid[]={executable,wrong,nullptr}; argc=2;
  assert(!ideck_cef::RemoveHandlerRole(&argc,invalid));
  char* standalone[]={executable,database,nullptr}; argc=2;
  assert(ideck_cef::RemoveHandlerRole(&argc,standalone) && argc==2);
  ideck_cef::StringPairs result;
  assert(ideck_cef::SplitStringIntoKeyValuePairs(" a=b, c==d, ,=e ", '=', ',', &result));
  assert((result == ideck_cef::StringPairs{{"a","b"},{"c","d"},{"","e"}}));
  assert(!ideck_cef::SplitStringIntoKeyValuePairs("missing,k=,okay=v", '=', ',', &result));
  assert((result == ideck_cef::StringPairs{{"",""},{"k",""},{"okay","v"}}));
  assert(ideck_cef::SplitStringIntoKeyValuePairs(" , ", '=', ',', &result) && result.empty());
  assert(ideck_cef::SplitStringIntoKeyValuePairs("a = b", '=', ',', &result));
  assert((result == ideck_cef::StringPairs{{"a "," b"}}));
''' + ('''
  using crash_report_utils::ParameterMap;
  const ParameterMap keys{{"K-A","one=renamed,"},{"K-B","two=second"},{"one","x"},{"two","y"},{"keep","z"}};
  assert((crash_report_utils::FilterParameters(keys) == ParameterMap{{"renamed","x"},{"second","y"},{"keep","z"}}));
  const ParameterMap malformed{{"K-A","missing"},{"keep","z"}};
  assert(crash_report_utils::FilterParameters(malformed) == malformed);
  const ParameterMap no_keys{{"keep","z"}};
  assert(crash_report_utils::FilterParameters(no_keys) == no_keys);
''' if root else "") + "}\n")
        command = ["clang++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined",
                   "-I", str(SOURCE), str(test), "-o", str(temporary / "test")]
        if root:
            command += ["-I", str(root), str(root / "cef/libcef/common/cef_crash_report_utils.cc")]
        subprocess.run(command, check=True)
        subprocess.run([str(temporary / "test")], check=True)


def check_runtime(build, tools):
    sys.path.insert(0, str(SOURCE))
    m = module("standalone_mingw_build", SOURCE / "mingw_build.py")
    for name in ("crashpad_handler.exe", "crashpad_smoke.exe"):
        original = (build / name).read_bytes()
        runtime = build / "runtime" / name
        before, identity, size = m.runtime_sections(original)
        after, new_identity, new_size = m.runtime_sections(runtime.read_bytes())
        assert before == after and identity == new_identity and new_size < size
        m.verify_image(runtime, tools)
        # Discriminate accidental code removal from removal of debug data.
        damaged = bytearray(original)
        pe = int.from_bytes(original[60:64], "little")
        section = pe + 24 + int.from_bytes(original[pe + 20:pe + 22], "little")
        raw = int.from_bytes(original[section + 20:section + 24], "little")
        damaged[raw] ^= 1
        assert m.runtime_sections(damaged)[0] != before
    print("PASS actual compact PEs: runtime bytes/RVAs/headers unchanged, TLS/unwind/imports intact; code corruption detected; not runtime execution")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--mingw-build", type=Path, help="also verify original and runtime/ actual cross-built PEs")
    parser.add_argument("--mingw-tools", type=Path)
    args = parser.parse_args()
    check_config()
    if args.source:
        check_source(args.source.resolve())
    if not args.source_only:
        compile_parser(args.source.resolve() if args.source else None)
    if bool(args.mingw_build) != bool(args.mingw_tools):
        parser.error("--mingw-build and --mingw-tools must be supplied together")
    if args.mingw_build:
        check_runtime(args.mingw_build.resolve(), args.mingw_tools.resolve())
    print("PASS standalone crash policy integrity/config preservation" +
          ("; parser and actual CEF filter ASan/UBSan" if args.source and not args.source_only else ""))
