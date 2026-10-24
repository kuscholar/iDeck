// ml2106: a game's controller output (rumble, DualSense adaptive triggers,
// lightbar, player LEDs) applied to the physical pad through GameController
// and CoreHaptics. GPL-3.0-or-later WITH the Madeira Converter Exception,
// version 1; see LICENSE-EXCEPTION.md.
//
// Plain C entry points so Swift calls them with no name translation. Each may
// be called on any thread; the work happens on the main thread.
#import <Foundation/Foundation.h>
#import <GameController/GameController.h>   // the full GCController, so Swift sees the real class

NS_ASSUME_NONNULL_BEGIN

/// Once per Wine session, before the game starts (GamepadInput.beginPadSession).
/// xinput: play XInputSetState rumble on the pad in that XInput slot.
/// hid: apply the virtual DualSense's output reports to player 1's pad.
/// 0/0 turns everything off and leaves the pads as they are.
void madeira_pad_output_configure(int xinput, int hid);

/// The physical controller in XInput slot 0-3 (slot 0 is also the HID pad's
/// player 1), or nil. GamepadInput.refreshControllers reports every change.
void madeira_pad_output_set_slot(int slot, GCController *_Nullable controller);

/// 0 when the app resigns active / goes to the background: motors stop and
/// adaptive triggers go off. 1 re-applies what the game last asked for.
void madeira_pad_output_set_active(int active);

NS_ASSUME_NONNULL_END
