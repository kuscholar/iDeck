// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// CEF126's public RunAsCrashpadHandler removes its role switch before
// HandlerMain. Adapt that contract without accepting other Chromium roles
// or discarding crash database, reporting, IPC or security arguments.
#ifndef IDECK_CEF_HANDLER_ARGS_H_
#define IDECK_CEF_HANDLER_ARGS_H_
#include <string_view>

namespace ideck_cef {
inline bool RemoveHandlerRole(int* argc, char* argv[]) {
  bool role_seen = false;
  int destination = 1;
  for (int i = 1; i < *argc; ++i) {
    const std::string_view argument(argv[i]);
    if (argument.rfind("--type=", 0) == 0) {
      if (argument != "--type=crashpad-handler" || role_seen) return false;
      role_seen = true;
    } else {
      argv[destination++] = argv[i];
    }
  }
  argv[destination] = nullptr;
  *argc = destination;
  return true;
}
}  // namespace ideck_cef
#endif
