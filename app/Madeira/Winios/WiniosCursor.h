/* Copyright 2026 125hz
 *
 * The program's cursor in direct mode (no virtual desktop), shared between
 * win32u and the app. GPL-3.0-or-later WITH the Madeira Converter Exception,
 * version 1; see LICENSE-EXCEPTION.md.
 *
 * In the desktop session the compositor draws the Windows cursor
 * (winios_cursor_set/show/move in Winios.m). A program running directly on the
 * game view had no cursor at all: the finger is its pointer. A hardware mouse
 * needs one, so build/win32u-unix/driver_ios.c reports the cursor image, whether
 * the program hides it and where Wine's cursor is, and HardwareInput.swift draws
 * it over the game view while the mouse is in use. The driver only reports;
 * nothing the program sees changes. Until the app calls
 * winios_direct_cursor_enable the driver does no extra work at all. */
#ifndef WINIOS_CURSOR_H
#define WINIOS_CURSOR_H

#include <stddef.h>

/* The driver never sends a larger image (driver_ios.c winios_drv_set_cursor). */
#define WINIOS_CURSOR_MAX 256

/* ---- win32u side: wine threads ---- */

/* Nonzero once the app has enabled the direct-mode cursor. */
int winios_direct_cursor_wanted(void);
/* A new cursor image: straight-alpha BGRA, w*h*4 bytes, copied before return. */
void winios_direct_cursor_set(unsigned int id, int w, int h, int hot_x, int hot_y, const void *bgra);
/* 0: the program hides its cursor (ShowCursor/SetCursor(NULL)); 1: shows it. */
void winios_direct_cursor_show(int show);
/* Wine's cursor position in screen pixels, after clipping. */
void winios_direct_cursor_pos(int x, int y);

/* ---- app side ---- */

/* Called on the reporting thread, outside the lock, at most once until the
 * next winios_direct_cursor_get: the app hops to its main thread from here. */
typedef void (*winios_direct_cursor_notify_t)(void);

/* Turn the reports on (the driver stays inert until this is called). */
void winios_direct_cursor_enable(winios_direct_cursor_notify_t notify);
/* Whether position reports notify (the app follows Wine's cursor). Image and
 * visibility changes, and the very first report, always notify. */
void winios_direct_cursor_track(int on);

struct winios_direct_cursor_state {
    int x, y;                  /* Wine's cursor position, screen pixels */
    int shown;                 /* the program shows a cursor (0 until it says so) */
    int w, h, hot_x, hot_y;    /* current image; w == 0: none yet */
    unsigned int image_serial; /* bumps on every new image */
    unsigned int reports;      /* counts notifying reports: a program is live */
};

/* Snapshot the state and re-arm the notification. */
void winios_direct_cursor_get(struct winios_direct_cursor_state *out);
/* Copy the current image (w*h*4 bytes) into dst when it fits in cap, and its
 * size, hotspot and serial into *image (the other fields are left alone).
 * Returns its serial, or 0 when there is no image or it does not fit. */
unsigned int winios_direct_cursor_copy_image(void *dst, size_t cap, struct winios_direct_cursor_state *image);

#endif
