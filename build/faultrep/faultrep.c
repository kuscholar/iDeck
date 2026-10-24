/*
 * faultrep.dll for Madeira (arm64ec).
 *
 * Windows Error Reporting's client DLL. Games import it statically to register
 * crash reporting (Ghost of Tsushima does), so its absence fails the whole
 * import table with STATUS_DLL_NOT_FOUND before the game runs a single
 * instruction. There is nothing to report to here: every entry point succeeds
 * without doing anything, which is what Wine's own faultrep does for the three
 * functions it implements. The export list is Wine's plus WerReportHang.
 *
 * Built by build/faultrep/build.sh.
 */
#include <windows.h>

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    (void)inst; (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(inst);
    return TRUE;
}

BOOL WINAPI AddERExcludedApplicationA(LPCSTR name) { (void)name; return TRUE; }
BOOL WINAPI AddERExcludedApplicationW(LPCWSTR name) { (void)name; return TRUE; }

/* EFaultRepRetVal: frrvOk = 0. */
int WINAPI ReportFault(EXCEPTION_POINTERS *ep, DWORD opt) { (void)ep; (void)opt; return 0; }

HRESULT WINAPI WerReportHang(HWND wnd, PCWSTR name) { (void)wnd; (void)name; return E_NOTIMPL; }

/* Undocumented or long obsolete; nothing calls them with anything that
 * needs an answer, so they all report failure. */
#define FAULTREP_STUB(name) BOOL WINAPI name(void) { SetLastError(ERROR_NOT_SUPPORTED); return FALSE; }
FAULTREP_STUB(CreateMinidumpA)
FAULTREP_STUB(CreateMinidumpW)
FAULTREP_STUB(ReportEREvent)
FAULTREP_STUB(ReportEREventDW)
FAULTREP_STUB(ReportFaultDWM)
FAULTREP_STUB(ReportFaultFromQueue)
FAULTREP_STUB(ReportFaultToQueue)
FAULTREP_STUB(ReportHang)
FAULTREP_STUB(ReportKernelFaultA)
FAULTREP_STUB(ReportKernelFaultDWW)
FAULTREP_STUB(ReportKernelFaultW)
