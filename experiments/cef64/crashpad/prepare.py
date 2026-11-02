#!/usr/bin/env python3
"""Prepare matched standalone Crashpad with CEF's complete public crash policy.

SPDX-License-Identifier: GPL-3.0-or-later
Madeira Converter Exception: see LICENSE-EXCEPTION.md
Upstream source retains its Apache/BSD notices. No Valve files are inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

CRASHPAD = "1174aa4fc3196f478b5b4b77fc970d1cb85cb7cf"
CEF = "a5d51ba9db7ee74a523dc247bd09ec91ba4d7446"
PATCH = "e1474ca60831144a5c096e8dcd3f8e0a36307b55ceb1ab63fe45883dcd396d85"
DEPS = {
    "third_party/mini_chromium/mini_chromium": (
        "https://chromium.googlesource.com/chromium/mini_chromium",
        "a6607b1fd76b740f31c2249fef2c0bec27ffbe52"),
    "third_party/zlib/zlib": (
        "https://chromium.googlesource.com/chromium/src/third_party/zlib",
        "fef58692c1d7bec94c4ed3d030a45a1832a9615d"),
    "third_party/googletest/googletest": (
        "https://chromium.googlesource.com/external/github.com/google/googletest",
        "af29db7ec28d6df1c7f0f745186884091e602e07"),
}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def clone(url, revision, target):
    if not target.exists():
        subprocess.run(["git", "clone", "--config", "core.autocrlf=false",
                        "--filter=blob:none", "--no-checkout", url, str(target)], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", "--detach", revision], check=True)
    if git(target, "rev-parse", "HEAD").decode().strip() != revision:
        raise ValueError("wrong source revision: " + str(target))
    if git(target, "status", "--porcelain", "--untracked-files=normal").strip():
        raise ValueError("preserve existing source changes or unrelated files: " + str(target))


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("non-unique standalone adaptation: " + old)
    return text.replace(old, new)


def adapt_entry(text):
    text = replace_once(text, '#include "handler/handler_main.h"',
                        '#include "handler/handler_main.h"\n#include "ideck/cef_handler_args.h"')
    return replace_once(text, 'int HandlerMainAdaptor(int argc, char* argv[]) {\n',
                        'int HandlerMainAdaptor(int argc, char* argv[]) {\n'
                        '  if (!ideck_cef::RemoveHandlerRole(&argc, argv)) return 2;\n')


def write_lf(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as output:
        output.write(text)


def prepare(root, cef):
    if (root / "ideck-crashpad-source.json").exists():
        raise ValueError("already prepared; use a fresh disposable checkout")
    clone("https://chromium.googlesource.com/crashpad/crashpad", CRASHPAD, root)
    for relative, (url, revision) in DEPS.items():
        clone(url, revision, root / relative)
    clone("https://github.com/chromiumembedded/cef.git", CEF, cef)
    patch = git(cef, "show", "HEAD:patch/patches/crashpad_tp_1995.patch")
    if hashlib.sha256(patch).hexdigest() != PATCH:
        raise ValueError("unrecognized complete CEF Crashpad patch")
    patch_file = root / "ideck-cef-crashpad.patch"
    patch_file.write_bytes(patch)
    # All eight files, including settings-v2, upload policy and option parsing.
    subprocess.run(["git", "apply", "-p3", "--check", str(patch_file)], cwd=root, check=True)
    subprocess.run(["git", "apply", "-p3", str(patch_file)], cwd=root, check=True)
    baseline = {p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                for p in git(root, "diff", "--name-only").decode().splitlines()}

    # Keep the complete CEF upload/backoff/key-filter implementation. Rebase
    # only its include paths and the one string helper absent in mini_chromium.
    public_files = {}
    for name in ("cef_crash_report_upload_thread.cc", "cef_crash_report_upload_thread.h",
                 "cef_crash_report_utils.cc", "cef_crash_report_utils.h"):
        relative = "libcef/common/" + name
        data = git(cef, "show", "HEAD:" + relative)
        public_files[relative] = hashlib.sha256(data).hexdigest()
        text = data.decode().replace("third_party/crashpad/crashpad/", "")
        if name == "cef_crash_report_utils.cc":
            text = replace_once(text, '#include "base/strings/string_split.h"',
                                '#include "ideck/cef_string_pairs.h"')
            text = text.replace("base::StringPairs", "ideck_cef::StringPairs")
            text = text.replace("base::SplitStringIntoKeyValuePairs", "ideck_cef::SplitStringIntoKeyValuePairs")
        target = root / "cef" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        write_lf(target, text)
    (root / "cef/LICENSE.txt").write_bytes(git(cef, "show", "HEAD:LICENSE.txt"))
    ideck = root / "ideck"
    ideck.mkdir()
    here = Path(__file__).resolve().parent
    for name in ("cef_string_pairs.h", "cef_handler_args.h", "smoke.cc"):
        shutil.copyfile(here / name, ideck / name)
    entry = root / "handler/main.cc"
    original_entry = entry.read_bytes()
    write_lf(entry, adapt_entry(original_entry.decode()))

    # This target always includes the CEF policy. Do not use Chromium's //base:
    # it would introduce a second PartitionAlloc address-space requirement.
    build = root / "handler/BUILD.gn"
    text = replace_once(build.read_text(), 'import("//cef/libcef/features/features.gni")\n', "")
    text = replace_once(text, "  if (enable_cef) {", "  if (true) {  # Standalone handler retains CEF's upload policy.")
    text = replace_once(text, '    configs += [ "//cef/libcef/features:config" ]\n', "")
    text = replace_once(text, '    "//cef/libcef/features",\n', "")
    write_lf(build, text)
    main = root / "handler/handler_main.cc"
    text = replace_once(main.read_text(), '#include "cef/libcef/features/features.h"\n', "")
    if text.count("#if BUILDFLAG(ENABLE_CEF)") != 2:
        raise ValueError("unrecognized CEF handler conditionals")
    text = text.replace("#if BUILDFLAG(ENABLE_CEF)", "#if 1  // This standalone target includes the published CEF crash policy.")
    write_lf(main, text)

    (ideck / "BUILD.gn").write_text('''# iDeck GPL-3.0-or-later with Madeira Converter Exception.
import("../build/crashpad_buildconfig.gni")
crashpad_executable("crashpad_smoke") {
  sources = [ "smoke.cc" ]
  deps = [ "../client", "../util", "../third_party/mini_chromium:base" ]
}
''', encoding="utf-8")
    # Default target deliberately excludes upstream test executables. Their
    # sources remain available; the real handler/client smoke is built below.
    root_build = root / "BUILD.gn"
    root_build.write_text('''# iDeck focused standalone build; upstream notices remain in source.
config("crashpad_config") { include_dirs = [ ".", root_gen_dir ] }
group("default") { deps = [ "handler:crashpad_handler", "ideck:crashpad_smoke" ] }
''', encoding="utf-8")
    manifest = {
        "crashpad_revision": CRASHPAD, "cef_revision": CEF,
        "cef_full_handler_patch_sha256": PATCH, "complete_patch_files": baseline,
        "dependencies": {k: {"url": u, "revision": v} for k, (u, v) in DEPS.items()},
        "cef_original_files": public_files,
        "handler_entry_original_sha256": hashlib.sha256(original_entry).hexdigest(),
        "scope": "standalone real Crashpad handler/client and complete CEF upload policy; no Valve inputs",
        "adaptations": "GN paths/feature selection, CEF include rebasing, Chromium-equivalent string-pair helper; remove only one exact CEF crashpad role switch before real HandlerMain",
        "reporting": "real IPC/registration/minidumps preserved; no fake handler or disabled checks",
    }
    (root / "ideck-crashpad-source.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--cef-checkout", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.checkout.resolve(), args.cef_checkout.resolve())
