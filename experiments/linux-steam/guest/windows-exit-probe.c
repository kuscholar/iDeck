/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Own PE fixture/future runtime smoke test. No game, Steam or authentication. */
__declspec(dllimport) void ExitProcess(unsigned);
void mainCRTStartup(void) { ExitProcess(7); }
