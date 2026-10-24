// ml2106: a game's controller output applied to the physical pad.
// GPL-3.0-or-later WITH the Madeira Converter Exception, version 1; see
// LICENSE-EXCEPTION.md. docs/CONTROLLERS.md has the user-facing picture.
//
// Two sources, both in WiniosGamepad.c, both written outside the app:
//  - the virtual DualSense's output reports (env.MADEIRA_PAD_MODE = hid /
//    dualsense), parsed by the wineserver (build/hidpad/hidpad_reports.h
//    hidpad_dualsense_output) into struct winios_hidpad_output: the rumble
//    pair, both adaptive trigger effects, lightbar colour, player LEDs, mic LED;
//  - XInputSetState's two motor speeds per XInput slot (win32u op 2,
//    NtUserGamepadOp_SetVibration, build/win32u-unix/driver_ios.c; needs the
//    paired Wine xinput change).
// The writers call winios_pad_output_set_notify's hook when something changed;
// the hook schedules one main-thread pass (never more than one in flight),
// which reads the newest state and applies what differs from what it applied
// last. No timer, no polling: nothing runs while the game sends nothing.
//
// iOS gives an app GameController's view of the pad only, so this is the
// closest mapping, not the DualSense protocol:
//  - rumble -> CoreHaptics: one continuous haptic event per handle (left =
//    the large, low-frequency motor; right = the small, high-frequency one)
//    from GCController.haptics, its intensity following the motor byte;
//  - trigger effects -> GCDualSenseAdaptiveTrigger modes
//    (Winios/WiniosPadEffects.h decides which);
//  - lightbar -> GCController.light.color; player LEDs -> playerIndex.
// Not reachable from an app: audio-based haptics, speaker, headset, mic and
// its LED, LED brightness and fades.
#import "PadOutput.h"
#import <GameController/GameController.h>
#import <CoreHaptics/CoreHaptics.h>
#import <objc/message.h>
#include <math.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include "Winios/WiniosGamepad.h"
#include "Winios/WiniosPadEffects.h"

#define PAD_SLOTS WINIOS_GAMEPAD_MAX
#define PAD_LOG_LIMIT 8
#define RUMBLE_GIVE_UP 8        // failed haptics set-ups in a row before a pad goes without rumble

/* GCDualSenseAdaptiveTriggerPositionalResistiveStrengths and
 * GCDualSenseAdaptiveTriggerPositionalAmplitudes (iOS 15.4+) are both
 * `struct { float values[10]; }`. The positional modes are sent through
 * objc_msgSend with this identical struct, behind respondsToSelector:, so
 * this file does not depend on how an SDK spells their Swift/ObjC names. */
typedef struct { float values[WINIOS_TRIGGER_ZONES]; } MadeiraTriggerPositions;

static int g_xinput, g_hid, g_active = 1;
static unsigned int g_logged_rumble, g_logged_trigger, g_logged_light, g_logged_index, g_logged_mic;
static unsigned int g_passes, g_next_tally = 100;

static void pad_output_apply(void);

static void on_main(dispatch_block_t block)
{
    if ([NSThread isMainThread]) block();
    else dispatch_async(dispatch_get_main_queue(), block);
}

// ---------------------------------------------------------------- rumble

@interface MadeiraRumble : NSObject
- (instancetype)initWithController:(GCController *)controller slot:(int)slot;
- (void)setLow:(float)low high:(float)high;
- (void)stop;
- (void)teardown;
@end

@implementation MadeiraRumble {
    __weak GCController *_controller;
    int _slot;
    int _channels;              // 0 not looked yet, 2 left+right handles, 1 one engine, -1 no haptics
    CHHapticEngine *_engine[2];
    id<CHHapticPatternPlayer> _player[2];   // plain players: push restarts them before their event ends
    CFAbsoluteTime _startedAt[2];
    BOOL _playing[2];
    float _want[2];             // per engine: 0 left/low (or the only one), 1 right/high
    float _sent[2];
    unsigned int _failures;     // failed engine/player set-ups in a row; 0 again once one works
    unsigned int _logged, _losses, _strikes;
    CFAbsoluteTime _retryAt;    // no new set-up before this (back-off after a failure)
}

- (instancetype)initWithController:(GCController *)controller slot:(int)slot
{
    if ((self = [super init])) {
        _controller = controller;
        _slot = slot;
        _sent[0] = _sent[1] = -1;
    }
    return self;
}

- (BOOL)lookUpChannels
{
    if (_channels) return _channels > 0;
    GCDeviceHaptics *haptics = _controller.haptics;
    NSSet<GCHapticsLocality> *where = haptics.supportedLocalities;
    if (!haptics) _channels = -1;
    else if ([where containsObject:GCHapticsLocalityLeftHandle] && [where containsObject:GCHapticsLocalityRightHandle])
        _channels = 2;
    else _channels = 1;
    fprintf(stderr, "[hidpad-out] ml2107 slot %d haptics: %s (localities %s)\n", _slot,
            _channels == 2 ? "left + right handle engines" :
            _channels == 1 ? "one engine (default locality)" : "none, this pad gets no rumble",
            where.count ? [where.allObjects componentsJoinedByString:@","].UTF8String : "none");
    return _channels > 0;
}

/* A failed engine or player set-up. The pad's haptics service
 * (gamecontrollerd) can refuse one attempt and take a later one, so this
 * backs off (2, 4, 8, then 15 s) instead of giving up at once. Two failures
 * in a row before either handle ever played switch the pad to one engine
 * (default locality); RUMBLE_GIVE_UP in a row leave it without rumble for
 * the session. */
- (void)fail:(const char *)what error:(NSError *)error
{
    NSError *under = error.userInfo[NSUnderlyingErrorKey];
    char detail[192] = "";
    double wait;

    _failures++;
    wait = _failures >= 4 ? 15.0 : (double)(1u << _failures);
    _retryAt = CFAbsoluteTimeGetCurrent() + wait;
    if (under)
        snprintf(detail, sizeof(detail), ", underlying %s %ld", under.domain.UTF8String, (long)under.code);
    if (_logged++ < 8)
        fprintf(stderr, "[hidpad-out] ml2107 slot %d haptics %s failed (%u in a row): %s [%s %ld%s]%s\n",
                _slot, what, _failures, error ? error.localizedDescription.UTF8String : "no detail",
                error ? error.domain.UTF8String : "-", error ? (long)error.code : 0L, detail,
                _failures < RUMBLE_GIVE_UP ? "; trying again later" : "");
    if (_channels == 2 && _failures == 2 && !_player[0] && !_player[1]) {
        _channels = 1;
        _want[0] = fmaxf(_want[0], _want[1]);
        _want[1] = 0;
        fprintf(stderr, "[hidpad-out] ml2107 slot %d haptics: the per-handle engines keep failing; "
                "one engine (default locality) from now on\n", _slot);
    }
    if (_failures == RUMBLE_GIVE_UP)
        fprintf(stderr, "[hidpad-out] ml2107 slot %d haptics: %u failures in a row, no rumble on this pad "
                "for this session\n", _slot, _failures);
}

- (void)engineLost:(int)i engine:(CHHapticEngine *)engine reason:(long)reason
{
    if (!engine || _engine[i] != engine) return;
    if (_losses++ < 4)
        fprintf(stderr, "[hidpad-out] ml2107 slot %d haptic engine %d %s (%ld); restarting on demand\n",
                _slot, i, reason < 0 ? "reset" : "stopped", reason);
    _engine[i] = nil;
    _player[i] = nil;
    _playing[i] = NO;
    _sent[i] = -1;
    /* A pad that keeps dropping its engine: leave it alone. iOS stops the engines
     * when the app goes to the background or audio is interrupted; those do not count. */
    if (reason != CHHapticEngineStoppedReasonApplicationSuspended
        && reason != CHHapticEngineStoppedReasonAudioSessionInterrupt && ++_strikes > 20)
        _failures = RUMBLE_GIVE_UP;
    if (g_active) [self push];
}

- (id<CHHapticPatternPlayer>)playerFor:(int)i
{
    if (_player[i]) return _player[i];
    if (_failures >= RUMBLE_GIVE_UP || CFAbsoluteTimeGetCurrent() < _retryAt) return nil;
    GCDeviceHaptics *haptics = _controller.haptics;
    if (!haptics) return nil;
    GCHapticsLocality where = _channels == 2 ? (i == 0 ? GCHapticsLocalityLeftHandle : GCHapticsLocalityRightHandle)
                                             : GCHapticsLocalityDefault;
    CHHapticEngine *engine = [haptics createEngineWithLocality:where];
    if (!engine) {
        [self fail:"createEngineWithLocality" error:nil];
        return nil;
    }
    engine.playsHapticsOnly = YES;
    __weak MadeiraRumble *weakSelf = self;
    __weak CHHapticEngine *weakEngine = engine;
    engine.stoppedHandler = ^(CHHapticEngineStoppedReason reason) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [weakSelf engineLost:i engine:weakEngine reason:(long)reason];
        });
    };
    engine.resetHandler = ^{
        dispatch_async(dispatch_get_main_queue(), ^{
            [weakSelf engineLost:i engine:weakEngine reason:-1];
        });
    };
    NSError *error = nil;
    if (![engine startAndReturnError:&error]) {
        [self fail:"engine start" error:error];
        return nil;
    }
    // One long continuous event at full strength; the intensity control
    // (0..1, a multiplier) follows the motor. Low sharpness for the large
    // motor, higher for the small one.
    float sharpness = _channels == 2 ? (i == 0 ? 0.2f : 0.6f) : 0.4f;
    NSArray<CHHapticEventParameter *> *parameters = @[
        [[CHHapticEventParameter alloc] initWithParameterID:CHHapticEventParameterIDHapticIntensity value:1.0f],
        [[CHHapticEventParameter alloc] initWithParameterID:CHHapticEventParameterIDHapticSharpness value:sharpness],
    ];
    CHHapticEvent *event = [[CHHapticEvent alloc] initWithEventType:CHHapticEventTypeHapticContinuous
                                                         parameters:parameters
                                                       relativeTime:0
                                                           duration:30.0];
    CHHapticPattern *pattern = [[CHHapticPattern alloc] initWithEvents:@[event] parameters:@[] error:&error];
    // A PLAIN player only, on this fresh engine. Game controllers refuse the
    // advanced one with "Couldn't communicate with a helper application"
    // (Apple developer forums thread 773615: the engine's connection to
    // com.apple.GameController.gamecontrollerd.haptics breaks, a plain
    // CHHapticPatternPlayer works). Asking for the advanced player first broke
    // the engine for the plain one too: on a DualSense in God of War the plain
    // player then failed with the same error on both handles and the pad never
    // rumbled. The plain player takes the same intensity control; push
    // restarts it before the 30 s event ends.
    id<CHHapticPatternPlayer> player = pattern ? [engine createPlayerWithPattern:pattern error:&error] : nil;
    if (!player) {
        [engine stopWithCompletionHandler:nil];
        [self fail:"pattern player" error:error];
        return nil;
    }
    if (_logged++ < 8)
        fprintf(stderr, "[hidpad-out] ml2107 slot %d haptics ready on %s%s\n", _slot, where.UTF8String,
                _failures ? " after failed attempts" : "");
    _failures = 0;
    _engine[i] = engine;
    _player[i] = player;
    _playing[i] = NO;
    _sent[i] = -1;
    return player;
}

- (void)sendLevel:(float)level to:(id<CHHapticPatternPlayer>)player
{
    CHHapticDynamicParameter *intensity =
        [[CHHapticDynamicParameter alloc] initWithParameterID:CHHapticDynamicParameterIDHapticIntensityControl
                                                        value:level
                                                 relativeTime:0];
    [player sendParameters:@[intensity] atTime:CHHapticTimeImmediate error:nil];
}

- (void)push
{
    for (int i = 0; i < 2; i++) {
        float level = g_active ? _want[i] : 0;
        if (level < 0.5f / 255.0f) {
            if (_playing[i]) [_player[i] stopAtTime:CHHapticTimeImmediate error:nil];
            _playing[i] = NO;
            _sent[i] = 0;
            continue;
        }
        id<CHHapticPatternPlayer> player = [self playerFor:i];
        if (!player) continue;
        // A plain player does not loop: start it again well before its 30 s event ends.
        if (_playing[i] && CFAbsoluteTimeGetCurrent() - _startedAt[i] > 25.0) {
            [player stopAtTime:CHHapticTimeImmediate error:nil];
            _playing[i] = NO;
        }
        if (!_playing[i]) {
            NSError *error = nil;
            [self sendLevel:level to:player];
            if (![player startAtTime:CHHapticTimeImmediate error:&error]) {
                // Drop this handle's engine: the next try (after the back-off)
                // builds a fresh one instead of starting a dead player again.
                CHHapticEngine *engine = _engine[i];
                _engine[i] = nil;   // before stopping: its stoppedHandler then finds nothing to restart
                _player[i] = nil;
                [engine stopWithCompletionHandler:nil];
                [self fail:"player start" error:error];
                continue;
            }
            _playing[i] = YES;
            _startedAt[i] = CFAbsoluteTimeGetCurrent();
            [self sendLevel:level to:player];
        } else if (level != _sent[i]) {
            [self sendLevel:level to:player];
        }
        _sent[i] = level;
    }
}

- (void)setLow:(float)low high:(float)high
{
    if (![self lookUpChannels]) return;
    if (_channels == 2) {
        _want[0] = low;
        _want[1] = high;
    } else {
        _want[0] = fmaxf(low, high);
        _want[1] = 0;
    }
    [self push];
}

- (void)stop
{
    for (int i = 0; i < 2; i++) {
        if (_playing[i]) [_player[i] stopAtTime:CHHapticTimeImmediate error:nil];
        _playing[i] = NO;
        _sent[i] = -1;
    }
}

- (void)teardown
{
    [self stop];
    for (int i = 0; i < 2; i++) {
        CHHapticEngine *engine = _engine[i];
        _engine[i] = nil;           // before stopping: its stoppedHandler then finds nothing to restart
        _player[i] = nil;
        [engine stopWithCompletionHandler:nil];
    }
}
@end

// ------------------------------------------------------------- the state

static GCController *g_slot[PAD_SLOTS];
static MadeiraRumble *g_rumble[PAD_SLOTS];
static struct winios_hidpad_output g_applied;   // the HID output last applied to slot 0
static int g_applied_valid;                     // 0: apply everything again next pass
static int g_triggers_set;                      // a trigger mode other than off is on the pad
static atomic_flag g_scheduled = ATOMIC_FLAG_INIT;

/* The writers' hook (WiniosGamepad.c): any thread, often the wineserver's. */
static void pad_output_notify(void)
{
    if (atomic_flag_test_and_set(&g_scheduled)) return;
    dispatch_async(dispatch_get_main_queue(), ^{
        atomic_flag_clear(&g_scheduled);
        pad_output_apply();
    });
}

static const char *trigger_kind_name(int kind)
{
    switch (kind) {
    case WINIOS_TRIGGER_OFF: return "off";
    case WINIOS_TRIGGER_FEEDBACK: return "feedback";
    case WINIOS_TRIGGER_WEAPON: return "weapon";
    case WINIOS_TRIGGER_VIBRATION: return "vibration";
    case WINIOS_TRIGGER_FEEDBACK_ZONES: return "feedback-zones";
    case WINIOS_TRIGGER_VIBRATION_ZONES: return "vibration-zones";
    }
    return "keep";
}

static void apply_trigger(GCDualSenseAdaptiveTrigger *trigger, const struct winios_trigger_plan *p, const char *name)
{
    MadeiraTriggerPositions zones;
    const char *how = "";

    memcpy(zones.values, p->zones, sizeof(zones.values));
    switch (p->kind) {
    case WINIOS_TRIGGER_KEEP:
        return;
    case WINIOS_TRIGGER_OFF:
        [trigger setModeOff];
        break;
    case WINIOS_TRIGGER_FEEDBACK:
        [trigger setModeFeedbackWithStartPosition:p->start resistiveStrength:p->strength];
        break;
    case WINIOS_TRIGGER_WEAPON:
        [trigger setModeWeaponWithStartPosition:p->start endPosition:p->end resistiveStrength:p->strength];
        break;
    case WINIOS_TRIGGER_VIBRATION:
        [trigger setModeVibrationWithStartPosition:p->start amplitude:p->amplitude frequency:p->frequency];
        break;
    case WINIOS_TRIGGER_FEEDBACK_ZONES: {
        SEL sel = NSSelectorFromString(@"setModeFeedbackWithResistiveStrengths:");
        if ([trigger respondsToSelector:sel]) {
            ((void (*)(id, SEL, MadeiraTriggerPositions))objc_msgSend)(trigger, sel, zones);
        } else {
            [trigger setModeFeedbackWithStartPosition:p->start resistiveStrength:p->strength];
            how = " (positional mode unavailable: single strength)";
        }
        break;
    }
    case WINIOS_TRIGGER_VIBRATION_ZONES: {
        SEL sel = NSSelectorFromString(@"setModeVibrationWithAmplitudes:frequency:");
        if ([trigger respondsToSelector:sel]) {
            ((void (*)(id, SEL, MadeiraTriggerPositions, float))objc_msgSend)(trigger, sel, zones, p->frequency);
        } else {
            [trigger setModeVibrationWithStartPosition:p->start amplitude:p->amplitude frequency:p->frequency];
            how = " (positional mode unavailable: single amplitude)";
        }
        break;
    }
    }
    g_triggers_set |= p->kind != WINIOS_TRIGGER_OFF;
    if (g_logged_trigger++ < 2 * PAD_LOG_LIMIT)
        fprintf(stderr, "[hidpad-out] ml2107 %s: sony %s (%#x) -> %s start %.2f end %.2f strength %.2f "
                "amplitude %.2f frequency %.2f%s\n", name, winios_trigger_mode_name(p->mode), p->mode,
                trigger_kind_name(p->kind), p->start, p->end, p->strength, p->amplitude, p->frequency, how);
}

static GCDualSenseGamepad *dualsense_of(GCController *controller)
{
    GCExtendedGamepad *pad = controller.extendedGamepad;
    return [pad isKindOfClass:[GCDualSenseGamepad class]] ? (GCDualSenseGamepad *)pad : nil;
}

static void triggers_off(GCController *controller)
{
    GCDualSenseGamepad *ds = dualsense_of(controller);
    if (!ds || !g_triggers_set) return;
    [ds.leftTrigger setModeOff];
    [ds.rightTrigger setModeOff];
    g_triggers_set = 0;
}

/* The virtual DualSense's lightbar, LEDs and trigger effects on player 1's pad. */
static void apply_hid(GCController *controller, const struct winios_hidpad_output *out)
{
    GCDualSenseGamepad *ds = dualsense_of(controller);
    const struct winios_hidpad_output *was = g_applied_valid ? &g_applied : NULL;
    unsigned int reduction = out->power_valid ? out->power_reduction & 7 : 0;
    unsigned int was_reduction = was && was->power_valid ? was->power_reduction & 7 : 0;
    int t;

    for (t = 0; t < 2 && ds; t++) {
        struct winios_trigger_plan plan;
        if (!out->trigger_valid[t]) continue;
        if (was && was->trigger_valid[t] && !memcmp(was->trigger[t], out->trigger[t], 11) && was_reduction == reduction)
            continue;
        winios_trigger_plan_from_effect(out->trigger[t], reduction, &plan);
        apply_trigger(t ? ds.rightTrigger : ds.leftTrigger, &plan, t ? "R2" : "L2");
    }
    if (out->lightbar_valid && controller.light &&
        (!was || !was->lightbar_valid || was->red != out->red || was->green != out->green || was->blue != out->blue)) {
        controller.light.color = [[GCColor alloc] initWithRed:out->red / 255.0f
                                                        green:out->green / 255.0f
                                                         blue:out->blue / 255.0f];
        if (g_logged_light++ < PAD_LOG_LIMIT)
            fprintf(stderr, "[hidpad-out] ml2107 lightbar %02x%02x%02x\n", out->red, out->green, out->blue);
    }
    if (out->player_leds_valid && (!was || !was->player_leds_valid || was->player_leds != out->player_leds)) {
        int index = winios_player_index_from_leds(out->player_leds);
        controller.playerIndex = index < 0 ? GCControllerPlayerIndexUnset : (GCControllerPlayerIndex)index;
        if (g_logged_index++ < PAD_LOG_LIMIT)
            fprintf(stderr, "[hidpad-out] ml2107 player LEDs %02x -> playerIndex %d\n", out->player_leds, index + 1);
    }
    if (out->mute_led_valid && (!was || !was->mute_led_valid || was->mute_led != out->mute_led) &&
        g_logged_mic++ < 2)
        fprintf(stderr, "[hidpad-out] ml2107 mic LED %u asked for: GameController has no API for it\n", out->mute_led);
    g_applied = *out;
    g_applied_valid = 1;
}

static void pad_output_apply(void)
{
    struct winios_hidpad_output out;
    unsigned int reduction;
    int i;

    if (!g_active || (!g_xinput && !g_hid)) return;
    memset(&out, 0, sizeof(out));
    if (g_hid) winios_hidpad_get_output(0, &out);
    reduction = out.power_valid ? (out.power_reduction >> 4) & 7 : 0;

    for (i = 0; i < PAD_SLOTS; i++) {
        struct winios_gamepad_vibration motors;
        float low = 0, high = 0;
        if (!g_rumble[i]) continue;
        if (g_xinput && winios_gamepad_get_vibration(i, &motors)) {
            low = winios_xinput_level(motors.left);
            high = winios_xinput_level(motors.right);
        }
        if (g_hid && i == 0 && out.rumble_valid) {
            low = fmaxf(low, winios_rumble_level(out.rumble_left, reduction));
            high = fmaxf(high, winios_rumble_level(out.rumble_right, reduction));
        }
        if ((low > 0 || high > 0) && g_logged_rumble++ < PAD_LOG_LIMIT)
            fprintf(stderr, "[hidpad-out] ml2107 slot %d rumble low %.2f high %.2f\n", i, low, high);
        [g_rumble[i] setLow:low high:high];
    }
    if (g_hid && g_slot[0]) apply_hid(g_slot[0], &out);

    if (++g_passes == g_next_tally) {
        fprintf(stderr, "[hidpad-out] ml2107 %u passes applied (rumble lines %u, trigger modes %u, lightbar %u, "
                "player LEDs %u)\n", g_passes, g_logged_rumble, g_logged_trigger, g_logged_light, g_logged_index);
        g_next_tally = g_next_tally < 100000000u ? g_next_tally * 10 : ~0u;
    }
}

// --------------------------------------------------------- entry points

void madeira_pad_output_configure(int xinput, int hid)
{
    on_main(^{
        int i;
        g_xinput = !!xinput;
        g_hid = !!hid;
        g_applied_valid = 0;
        winios_gamepad_set_rumble_caps(g_xinput);
        winios_pad_output_set_notify(g_xinput || g_hid ? pad_output_notify : NULL);
        fprintf(stderr, "[hidpad-out] ml2106 session output: xinput-rumble=%d hid=%d\n", g_xinput, g_hid);
        if (!g_xinput && !g_hid)
            for (i = 0; i < PAD_SLOTS; i++) [g_rumble[i] stop];
        pad_output_apply();
    });
}

void madeira_pad_output_set_slot(int slot, GCController *controller)
{
    on_main(^{
        if (slot < 0 || slot >= PAD_SLOTS || g_slot[slot] == controller) return;
        [g_rumble[slot] teardown];
        g_rumble[slot] = nil;
        g_slot[slot] = controller;
        if (controller) g_rumble[slot] = [[MadeiraRumble alloc] initWithController:controller slot:slot];
        if (slot == 0) {
            g_applied_valid = 0;    // a new player 1 gets the whole state
            g_triggers_set = 0;
        }
        pad_output_apply();
    });
}

void madeira_pad_output_set_active(int active)
{
    on_main(^{
        int i;
        if (g_active == !!active) return;
        g_active = !!active;
        if (g_active) {
            g_applied_valid = 0;
            pad_output_apply();
            return;
        }
        for (i = 0; i < PAD_SLOTS; i++) [g_rumble[i] stop];
        if (g_hid && g_slot[0]) triggers_off(g_slot[0]);
    });
}
