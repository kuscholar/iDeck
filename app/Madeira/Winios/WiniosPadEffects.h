/* ml2106: what a game's DualSense effects mean on iOS. GPL-3.0-or-later WITH
 * the Madeira Converter Exception, version 1; see LICENSE-EXCEPTION.md.
 *
 * Pure C, header only, no Apple or Wine headers: the app (PadOutput.m) turns
 * the wineserver's parsed output report (struct winios_hidpad_output) into
 * GameController calls with these functions, the wineserver's log names the
 * trigger modes with them, and tests/host/check-pad-output.py runs them on the
 * host.
 *
 * TRIGGER EFFECTS. A DualSense trigger effect is 11 bytes: a mode byte and 10
 * parameters. The modes and their encodings are the ones libScePad's
 * scePadSetTriggerEffect produces, as documented by Nielk1's
 * TriggerEffectGenerator (gist 6d54cc2c00d2201ccb8c2720ad7538db, the reference
 * DSX and DS4Windows follow):
 *
 *   0x05 off (0x00, an all-zero block, is off too)
 *   0x21 feedback   [1..2] 10-bit zone mask, [3..6] 3 bits per zone: strength-1
 *   0x25 weapon     [1..2] mask with the start and end zone bits, [3] strength-1
 *   0x26 vibration  [1..2] zone mask, [3..6] 3 bits per zone: amplitude-1, [9] Hz
 *   0x22 bow        [1..2] start/end mask, [3] strength-1 | (snap force-1) << 3
 *   0x23 galloping  [1..2] start/end mask, [3] feet timing, [4] Hz
 *   0x27 machine    [1..2] start/end mask, [3] amplitude A | B << 3 (0-7), [4] Hz, [5] period
 *   0x01 simple feedback   [1] position 0-255, [2] strength 0-255
 *   0x02 simple weapon     [1] start, [2] end, [3] strength (0-255 each)
 *   0x06 simple vibration  [1] Hz, [2] amplitude 0-255, [3] position 0-255
 *   0x11 limited feedback  [1] position 0-255, [2] strength 0-10
 *   0x12 limited weapon    [1] start, [2] end (0-255), [3] strength 0-10
 *   0xfc-0xfe debug/calibration: left as they are
 *
 * Zones are the trigger's 10 positions, 0 (rest) to 9 (fully pulled).
 *
 * GameController offers (GCDualSenseAdaptiveTrigger): off; feedback from a
 * start position with one strength; weapon between a start and an end
 * position; vibration from a start position with one amplitude and frequency;
 * and since iOS 15.4 feedback and vibration with a strength/amplitude for each
 * of the same 10 positions. All values are 0..1. So feedback, weapon and
 * vibration map one to one (zones i -> i / 9, strengths 1-8 -> n / 8, Hz ->
 * Hz / 255); a zone pattern that is not "one value from a start onward" uses
 * the positional variant; bow becomes weapon (no snap-back force on iOS),
 * galloping and machine become vibration (no rhythm on iOS).
 */
#ifndef WINIOS_PAD_EFFECTS_H
#define WINIOS_PAD_EFFECTS_H
#include <stdint.h>

#define WINIOS_TRIGGER_ZONES 10

enum winios_trigger_kind {
    WINIOS_TRIGGER_KEEP,             /* debug/calibration block: change nothing */
    WINIOS_TRIGGER_OFF,
    WINIOS_TRIGGER_FEEDBACK,         /* start, strength */
    WINIOS_TRIGGER_WEAPON,           /* start, end, strength */
    WINIOS_TRIGGER_VIBRATION,        /* start, amplitude, frequency */
    WINIOS_TRIGGER_FEEDBACK_ZONES,   /* zones[] (strengths); start/strength: the closest single setting */
    WINIOS_TRIGGER_VIBRATION_ZONES,  /* zones[] (amplitudes), frequency; start/amplitude likewise */
};

struct winios_trigger_plan {
    int kind;
    uint8_t mode;                    /* the Sony mode byte it came from */
    float start, end;                /* 0..1 of the trigger's travel */
    float strength, amplitude, frequency;
    float zones[WINIOS_TRIGGER_ZONES];
};

static inline const char *winios_trigger_mode_name(uint8_t mode)
{
    switch (mode) {
    case 0x00: return "none";
    case 0x05: return "off";
    case 0x21: return "feedback";
    case 0x25: return "weapon";
    case 0x26: return "vibration";
    case 0x22: return "bow";
    case 0x23: return "galloping";
    case 0x27: return "machine";
    case 0x01: return "simple-feedback";
    case 0x02: return "simple-weapon";
    case 0x06: return "simple-vibration";
    case 0x11: return "limited-feedback";
    case 0x12: return "limited-weapon";
    case 0xfc: case 0xfd: case 0xfe: return "debug";
    }
    return "unknown";
}

static inline float winios_unit(float v)
{
    return v < 0 ? 0 : v > 1 ? 1 : v;
}

/* Lowest and highest set bit of a 10-zone mask; 0 when the mask is empty. */
static inline int winios_zone_range(unsigned int mask, int *lo, int *hi)
{
    int i;
    *lo = *hi = -1;
    for (i = 0; i < WINIOS_TRIGGER_ZONES; i++)
        if (mask & (1u << i)) {
            if (*lo < 0) *lo = i;
            *hi = i;
        }
    return *lo >= 0;
}

/* Zone masks and 3-bit values (feedback 0x21, vibration 0x26): per-zone
 * levels 0..1 (value + 1) / 8, 0 where the zone bit is clear. Then the
 * closest single setting: the first active zone and the strongest level, and
 * whether one setting says it all (every zone from the first on, one level). */
static inline int winios_trigger_zones(const uint8_t *e, struct winios_trigger_plan *p)
{
    unsigned int mask = (e[1] | e[2] << 8) & 0x3ff;
    uint32_t values = e[3] | e[4] << 8 | e[5] << 16 | (uint32_t)e[6] << 24;
    int i, first = -1, uniform = 1;
    float top = 0;

    for (i = 0; i < WINIOS_TRIGGER_ZONES; i++) {
        float v = (mask & (1u << i)) ? (float)(((values >> (3 * i)) & 7) + 1) / 8.0f : 0.0f;
        p->zones[i] = v;
        if (v > 0 && first < 0) first = i;
        if (v > top) top = v;
    }
    if (first < 0) return 0;
    for (i = first; i < WINIOS_TRIGGER_ZONES; i++)
        if (p->zones[i] != p->zones[first]) uniform = 0;
    p->start = (float)first / 9.0f;
    p->strength = p->amplitude = top;
    return uniform ? 1 : 2;
}

/* What GameController can do with effect block `e` (11 bytes). `reduction`
 * is the game's trigger power reduction, 0-7 (12.5 % steps), 0 when unset. */
static inline void winios_trigger_plan_from_effect(const uint8_t *e, unsigned int reduction,
                                                   struct winios_trigger_plan *p)
{
    float scale = 1.0f - (float)(reduction & 7) / 8.0f;
    int lo, hi, i, zones;

    *p = (struct winios_trigger_plan){0};
    p->mode = e[0];
    p->kind = WINIOS_TRIGGER_OFF;
    switch (e[0]) {
    case 0x21:
        zones = winios_trigger_zones(e, p);
        if (zones) p->kind = zones == 1 ? WINIOS_TRIGGER_FEEDBACK : WINIOS_TRIGGER_FEEDBACK_ZONES;
        break;
    case 0x26:
        if (!e[9]) break;                       /* 0 Hz: the generator writes off */
        zones = winios_trigger_zones(e, p);
        p->frequency = (float)e[9] / 255.0f;
        if (zones) p->kind = zones == 1 ? WINIOS_TRIGGER_VIBRATION : WINIOS_TRIGGER_VIBRATION_ZONES;
        break;
    case 0x25:
    case 0x22:
        if (!winios_zone_range((e[1] | e[2] << 8) & 0x3ff, &lo, &hi) || hi <= lo) break;
        p->kind = WINIOS_TRIGGER_WEAPON;
        p->start = (float)lo / 9.0f;
        p->end = (float)hi / 9.0f;
        p->strength = (float)((e[3] & 7) + 1) / 8.0f;
        break;
    case 0x23:
    case 0x27:
        if (!e[4] || !winios_zone_range((e[1] | e[2] << 8) & 0x3ff, &lo, &hi)) break;
        p->kind = WINIOS_TRIGGER_VIBRATION;
        p->start = (float)lo / 9.0f;
        p->frequency = (float)e[4] / 255.0f;
        if (e[0] == 0x27) {
            unsigned int a = e[3] & 7, b = (e[3] >> 3) & 7;
            p->amplitude = (float)(a > b ? a : b) / 7.0f;
            if (!a && !b) p->kind = WINIOS_TRIGGER_OFF;
        } else {
            p->amplitude = 0.5f;                /* a gallop is a light knock */
        }
        break;
    case 0x01:
        if (!e[2]) break;
        p->kind = WINIOS_TRIGGER_FEEDBACK;
        p->start = (float)e[1] / 255.0f;
        p->strength = (float)e[2] / 255.0f;
        break;
    case 0x11:
        if (!e[2]) break;
        p->kind = WINIOS_TRIGGER_FEEDBACK;
        p->start = (float)e[1] / 255.0f;
        p->strength = winios_unit((float)e[2] / 10.0f);
        break;
    case 0x02:
    case 0x12:
        if (!e[3] || e[2] <= e[1]) break;
        p->kind = WINIOS_TRIGGER_WEAPON;
        p->start = (float)e[1] / 255.0f;
        p->end = (float)e[2] / 255.0f;
        p->strength = e[0] == 0x02 ? (float)e[3] / 255.0f : winios_unit((float)e[3] / 10.0f);
        break;
    case 0x06:
        if (!e[1] || !e[2]) break;
        p->kind = WINIOS_TRIGGER_VIBRATION;
        p->frequency = (float)e[1] / 255.0f;
        p->amplitude = (float)e[2] / 255.0f;
        p->start = (float)e[3] / 255.0f;
        break;
    case 0xfc: case 0xfd: case 0xfe:
        p->kind = WINIOS_TRIGGER_KEEP;
        break;
    }
    if (p->kind == WINIOS_TRIGGER_OFF) return;
    p->strength *= scale;
    p->amplitude *= scale;
    for (i = 0; i < WINIOS_TRIGGER_ZONES; i++) p->zones[i] *= scale;
}

/* A rumble motor byte (0-255) as a CoreHaptics intensity 0..1, after the
 * game's rumble power reduction (0-7, 12.5 % steps). */
static inline float winios_rumble_level(uint8_t motor, unsigned int reduction)
{
    return (float)motor / 255.0f * (1.0f - (float)(reduction & 7) / 8.0f);
}

/* An XInput motor speed (0-65535) as an intensity 0..1. */
static inline float winios_xinput_level(uint16_t speed)
{
    return (float)speed / 65535.0f;
}

/* The DualSense player LEDs (bits 0-4, left to right) as GameController's
 * player index: 0-3 (GCControllerPlayerIndex1-4), -1 for all dark. Sony's
 * patterns (Linux hid-playstation.c player_ids) map exactly: 0x04 one, 0x0a
 * two, 0x15 three, 0x1b four; five lit (0x1f, "player 5") and any other
 * pattern go by the number of lit LEDs, capped at four -- iOS has four. */
static inline int winios_player_index_from_leds(uint8_t leds)
{
    unsigned int i, lit = 0;
    switch (leds & 0x1f) {
    case 0x00: return -1;
    case 0x04: return 0;
    case 0x0a: return 1;
    case 0x15: return 2;
    case 0x1b: return 3;
    }
    for (i = 0; i < 5; i++) lit += (leds >> i) & 1;
    return lit > 4 ? 3 : (int)lit - 1;
}

#endif
