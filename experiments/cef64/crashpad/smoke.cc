// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Own process only, empty upload URL, fresh local database. No Steam inputs.
#include <cstdio>
#include <fstream>
#include <map>
#include <string>
#include <vector>

#include "base/files/file_path.h"
#include "build/build_config.h"
#include "client/crash_report_database.h"
#include "client/crashpad_client.h"
#include "client/settings.h"
#include "util/misc/capture_context.h"
#include "base/threading/thread_local_storage.h"

#if BUILDFLAG(IS_WIN)
#include <windows.h>

namespace {
volatile LONG destructor_count = 0;
void OnTLSExit(void*) { InterlockedIncrement(&destructor_count); }
DWORD WINAPI TestTLS(void* opaque) {
  static_cast<base::ThreadLocalStorage::Slot*>(opaque)->Set(opaque);
  return 0;
}
DWORD WINAPI Deadline(void*) {
  Sleep(60000);
  std::puts("own_probe_timeout=FAIL");
  std::fflush(stdout);
  TerminateProcess(GetCurrentProcess(), 124);
  return 124;
}
}  // namespace

int wmain(int argc, wchar_t* argv[]) {
  setvbuf(stdout, nullptr, _IONBF, 0);
  if (argc != 3) return 2;
  HANDLE deadline = CreateThread(nullptr, 0, Deadline, nullptr, 0, nullptr);
  if (!deadline) return 7;
  CloseHandle(deadline);
  base::ThreadLocalStorage::Slot slot(OnTLSExit);
  HANDLE thread = CreateThread(nullptr, 0, TestTLS, &slot, 0, nullptr);
  if (!thread || WaitForSingleObject(thread, 5000) != WAIT_OBJECT_0) return 8;
  CloseHandle(thread);
  if (InterlockedCompareExchange(&destructor_count, 0, 0) != 1) return 9;
  std::puts("tls_thread_exit=PASS");
  auto database = crashpad::CrashReportDatabase::Initialize(base::FilePath(argv[2]));
  if (!database || !database->GetSettings()->SetUploadsEnabled(false)) return 3;
  crashpad::CrashpadClient client;
  const std::vector<std::string> arguments = {
      "--type=crashpad-handler", "--max-uploads=5", "--max-db-size=20", "--max-db-age=5"};
  if (!client.StartHandler(base::FilePath(argv[1]), base::FilePath(argv[2]),
                           base::FilePath(), "", std::map<std::string, std::string>(),
                           arguments, false, true) ||
      !client.WaitForHandlerStart(15000)) return 4;
  std::puts("handler_registration=PASS");
  std::fflush(stdout);
  CONTEXT context = {};
  crashpad::CaptureContext(&context);
  // Real API/IPC/dump, never a canned success. Outer harness bounds this call.
  crashpad::CrashpadClient::DumpWithoutCrash(context);
  for (unsigned attempt = 0; attempt < 100; ++attempt) {
    std::vector<crashpad::CrashReportDatabase::Report> pending, completed;
    if (database->GetPendingReports(&pending) != crashpad::CrashReportDatabase::kNoError ||
        database->GetCompletedReports(&completed) != crashpad::CrashReportDatabase::kNoError) return 5;
    pending.insert(pending.end(), completed.begin(), completed.end());
    for (const auto& report : pending) {
      std::ifstream input(report.file_path.value().c_str(), std::ios::binary);
      char signature[4] = {};
      input.read(signature, 4);
      if (input.gcount() == 4 && std::string(signature, 4) == "MDMP" && !report.uploaded) {
        std::puts("real_local_minidump=PASS\nnetwork_upload=DISABLED_FOR_OWN_TEST_ONLY");
        return 0;
      }
    }
    Sleep(100);
  }
  return 6;
}
#else
int main() {
  std::puts("Windows handler IPC test requires a Windows worker; not executed");
  return 77;
}
#endif
