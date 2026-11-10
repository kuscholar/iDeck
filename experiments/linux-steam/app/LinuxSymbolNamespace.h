/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Force-include ONLY in LinuxRunner and its native C adapters in an isolated
 * build. Preserve the C identifier and Objective-C selectors: change just the
 * external assembler name of the task TLS, which collides with wineserver's
 * process-global current. This is not complete runtime coexistence permission.
 */
#ifndef IDECK_LINUX_SYMBOL_NAMESPACE_H
#define IDECK_LINUX_SYMBOL_NAMESPACE_H
#if defined(IDECK_LAB_LINUX_SYMBOL_NAMESPACE) && IDECK_LAB_LINUX_SYMBOL_NAMESPACE && !defined(__ASSEMBLER__)
#if !defined(__APPLE__) || !defined(__clang__)
#error Linux task symbol namespace currently qualified only for Darwin Clang C/ObjC
#endif
#ifdef __cplusplus
extern "C" {
#endif
struct task;
/* asm labels are literal Darwin object names, including the leading _. */
extern __thread struct task *current __asm__("_ideck_linux_current");
#ifdef __cplusplus
}
#endif
#endif
#endif
