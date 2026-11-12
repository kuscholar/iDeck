/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_LAB_STARTUP_MODE_H
#define IDECK_LAB_STARTUP_MODE_H
#define IDECK_LAB_COLD_SETUP "madeira-linux-lab-setup"
/* 0: existing Linux route, 1: explicit cold native route, negative: conflicting
 * experiment arguments. Selection only, never starts either engine. */
int ideck_lab_startup_mode(int argc,const char *const *argv);
#endif
