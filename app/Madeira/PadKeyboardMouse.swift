import Foundation
import UIKit

/// A physical controller as keyboard and mouse, for games without controller
/// support (or with it switched off).
///
/// Steam does this for desktop players with Steam Input; Madeira Dock runs
/// Valve's client headless, so there is no Steam Input here, and nothing else
/// translates a pad for such a game. In this mode the pad is not published to
/// XInput at all: the game sees no controller, and every pad input is turned
/// into what the touch controls already produce, through the same posting
/// paths (winios_post_key, winios_pointer, HardwareInput.postRelative).
///
/// Bindings come from three places, the most specific winning:
/// - The game's own binds table (`LibraryEntry.controllerBinds`, edited in the
///   Session menu's Controller binds page and in Game details): one action per
///   controller input, stored with the game.
/// - A touch control of the active layout can name a controller input
///   (`TouchControl.padBinding`: "A", "LB", "RT", "D↑", ...; "LS" or "RS" for a
///   stick control). That input then does what the touch control does.
/// - Inputs neither of those bind take the built-in template below: WASD on
///   the left stick, mouse on the right stick, the triggers as the mouse
///   buttons, the D-pad as the arrow keys, Start as Escape, Select as Tab.
///
/// The mode is a per-game choice (LibraryEntry.controllerMode, Game details and
/// the Session menu), off by default: a game with native controller support
/// keeps XInput, as before. MADEIRA_PAD_KBM=0 removes the choice.
struct PadBindings: Equatable {
    static let buttonNames = ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "L3", "R3",
                              "Menu", "View", "D↑", "D↓", "D←", "D→"]
    static let stickNames = ["LS", "RS"]

    /// What each digital input does; the triggers count as digital here.
    var buttons: [String: ControlAction]
    /// The key stick the left stick drives (.joystickWASD/.joystickArrows), or
    /// .none when the right stick took the keys and the left one is unused.
    var leftStick: ControlAction
    /// The right stick moves the mouse (default) or drives a key stick.
    var rightStick: ControlAction
    /// Vertical speed of the right-stick mouse relative to its horizontal speed
    /// (1 = the same). Games scale pitch and yaw differently from a mouse, and a
    /// stick cannot be compensated by hand the way a wrist does.
    var mouseVertical: Double = 1.0

    /// The built-in template: the keyboard-and-mouse layout most PC games use.
    static let template = PadBindings(
        buttons: ["A": .key(0x20),            // Space
                  "B": .key(0x11),            // Ctrl
                  "X": .key(0x45),            // E
                  "Y": .key(0x52),            // R
                  "LB": .key(0x51),           // Q
                  "RB": .key(0x46),           // F
                  "LT": .mouseRight,
                  "RT": .mouseLeft,
                  "L3": .key(0x10),           // Shift
                  "R3": .key(0x43),           // C
                  "Menu": .key(0x1B),         // Escape
                  "View": .key(0x09),         // Tab
                  "D↑": .key(0x26), "D↓": .key(0x28), "D←": .key(0x25), "D→": .key(0x27)],
        leftStick: .joystickWASD,
        rightStick: .none)                    // .none on the right stick means: the mouse

    /// The template with the layout's own bindings on top, then the game's binds
    /// table on top of that. A binding replaces the template's entry for that
    /// input; a key stick bound to RS takes the right stick away from the mouse.
    /// In the table, `.none` on a button means "does nothing", on RS "the mouse",
    /// on LS "unused".
    static func build(controls: [TouchControl], binds: [String: ControlAction]? = nil, mouseVertical: Double? = nil) -> PadBindings {
        var b = template
        if let v = mouseVertical, v.isFinite { b.mouseVertical = min(max(v, 0.25), 2.0) }
        for c in controls {
            guard let name = c.padBinding else { continue }
            if c.action.stickKeys != nil {
                if name == "LS" { b.leftStick = c.action }
                else if name == "RS" { b.rightStick = c.action }
            } else if buttonNames.contains(name), !c.action.isPad, c.action != .none {
                b.buttons[name] = c.action
            }
        }
        for (name, action) in binds ?? [:] where !action.isPad {
            if name == "LS" { b.leftStick = action.stickKeys != nil ? action : .none }
            else if name == "RS" { b.rightStick = action.stickKeys != nil ? action : .none }
            else if buttonNames.contains(name), action.stickKeys == nil { b.buttons[name] = action }
        }
        return b
    }

    /// What the template gives an input, for the binds page's "Default" rows.
    static func templateAction(_ name: String) -> ControlAction {
        switch name {
        case "LS": return template.leftStick
        case "RS": return template.rightStick
        default:   return template.buttons[name] ?? .none
        }
    }

    /// The binds page's row labels: XInput names in the table, Start/Select on screen.
    static func displayName(_ name: String) -> String {
        name == "Menu" ? "Start" : name == "View" ? "Select" : name
    }

    var usesMouseStick: Bool { rightStick.stickKeys == nil }
}

/// Turns pad samples into key and mouse events. Fed from GamepadInput's sampling
/// queue (250 Hz); every call runs on that queue, so the edge state needs no lock.
final class PadKeyboardMouse {
    static let shared = PadKeyboardMouse()

    /// XInput button masks, as GamepadInput publishes them.
    private static let masks: [(String, UInt16)] = [
        ("D↑", 0x0001), ("D↓", 0x0002), ("D←", 0x0004), ("D→", 0x0008),
        ("Menu", 0x0010), ("View", 0x0020), ("L3", 0x0040), ("R3", 0x0080),
        ("LB", 0x0100), ("RB", 0x0200), ("A", 0x1000), ("B", 0x2000), ("X", 0x4000), ("Y", 0x8000)
    ]
    private static let triggerThreshold: UInt8 = 128
    /// Stick deflection (0...1) below which no direction key is held.
    private static let stickDeadzone = 0.35

    private var held: Set<String> = []            // digital inputs currently down
    private var leftDir = -1, rightDir = -1        // 8-way sectors of the key sticks
    private var leftKeys: [Int32] = [], rightKeys: [Int32] = []
    private var lastSample: UInt64 = 0             // mach time of the previous feed
    private var carry = MotionCarry()
    private var mouseMoving = false
    private var logged = 0

    /// One pad sample while the mode is on. `dt` comes from the sample clock.
    func feed(buttons: UInt16, lt: UInt8, rt: UInt8, lx: Int16, ly: Int16, rx: Int16, ry: Int16,
              bindings: PadBindings, focused: Bool) {
        let now = mach_absolute_time()
        let dt = lastSample == 0 ? 1.0 / 250.0 : Self.seconds(now - lastSample)
        lastSample = now

        var down: Set<String> = []
        for (name, mask) in Self.masks where buttons & mask != 0 { down.insert(name) }
        if lt >= Self.triggerThreshold { down.insert("LT") }
        if rt >= Self.triggerThreshold { down.insert("RT") }
        for name in held.subtracting(down) {
            if let a = pressedWith.removeValue(forKey: name) { act(a, down: false) }
        }
        for name in down.subtracting(held) {
            if let a = bindings.buttons[name] { pressedWith[name] = a; act(a, down: true) }
        }
        held = down

        let l = Self.unit(lx, ly), r = Self.unit(rx, ry)
        if let keys = bindings.leftStick.stickKeys {
            leftDir = Self.applyStick(from: leftDir, to: Self.sector(l.x, l.y), keys: keys, heldKeys: &leftKeys)
        }
        if let keys = bindings.rightStick.stickKeys {
            rightDir = Self.applyStick(from: rightDir, to: Self.sector(r.x, r.y), keys: keys, heldKeys: &rightKeys)
        } else if focused {
            // Motion by the time since the last sample, unfloored: samples come from
            // the 4 ms timer and from every controller change, so StickVelocity.frame's
            // 1/240 s floor would make the cursor faster the more often the pad reports.
            let v = StickVelocity.deflect(r.x, r.y)
            let k = InputSettings.shared.sensRel * StickVelocity.fullRate * min(dt, 1.0 / 15.0)
            let f = (dx: v.x * k, dy: -v.y * k)
            if f.dx != 0 || f.dy != 0 {
                let d = carry.add(f.dx, f.dy * bindings.mouseVertical, gain: 1)
                if d.dx != 0 || d.dy != 0 {
                    if !mouseMoving {
                        mouseMoving = true
                        DispatchQueue.main.async { HardwareInput.shared.stickMoved() }
                    }
                    HardwareInput.shared.postRelative(d.dx, d.dy)
                }
            } else if mouseMoving {
                mouseMoving = false
                carry.reset()
            }
        }
    }

    /// Whether a key or mouse button is down, or the mouse is moving.
    var holding: Bool { !pressedWith.isEmpty || !leftKeys.isEmpty || !rightKeys.isEmpty || mouseMoving }

    /// Release everything this driver holds: the mode went off, the app
    /// resigned active, the session ended, the library took the pad, or the
    /// controller disconnected.
    func releaseAll(_ why: String) {
        for (_, a) in pressedWith { act(a, down: false) }
        pressedWith.removeAll()
        held.removeAll()
        for vk in leftKeys { winios_post_key(vk, 0) }
        for vk in rightKeys { winios_post_key(vk, 0) }
        leftKeys.removeAll(); rightKeys.removeAll()
        leftDir = -1; rightDir = -1
        lastSample = 0
        carry.reset()
        mouseMoving = false
        if logged < 32 { logged += 1; fputs("[pad-kbm] released (\(why))\n", stderr) }
    }

    /// Each input is released through the action it was pressed with, so a layout
    /// edit during a hold cannot leave a key down.
    private var pressedWith: [String: ControlAction] = [:]
    private func act(_ action: ControlAction, down: Bool) {
        switch action {
        case .key(let vk):
            winios_post_key(vk, down ? 1 : 0)
        case .mouseLeft:
            winios_pointer(0, 0, down ? 0x0002 : 0x0004, 0)   // LEFTDOWN / LEFTUP
        case .mouseRight:
            winios_pointer(0, 0, down ? 0x0008 : 0x0010, 0)   // RIGHTDOWN / RIGHTUP
        case .keyboardToggle:
            if down { DispatchQueue.main.async { MetalBackedView.toggleKeyboard() } }
        case .none, .joystickWASD, .joystickArrows, .pad:
            break                                              // sticks are handled by sector; pad actions are XInput's
        }
    }

    // ---- stick arithmetic, the same sectors as the touch key sticks ----

    private static func unit(_ x: Int16, _ y: Int16) -> (x: Double, y: Double) {
        (Double(x) / 32767.0, Double(y) / 32767.0)
    }
    /// 0 = up, clockwise in 45° steps; -1 inside the dead zone.
    static func sector(_ x: Double, _ y: Double) -> Int {
        guard (x * x + y * y).squareRoot() >= stickDeadzone else { return -1 }
        var a = atan2(x, y) * 180 / .pi            // 0° is up, 90° is right
        if a < 0 { a += 360 }
        return Int((a + 22.5) / 45.0) % 8
    }
    static func sectorKeys(_ d: Int, _ q: [Int32]) -> [Int32] {
        switch d {
        case 0: return [q[0]]
        case 1: return [q[0], q[1]]
        case 2: return [q[1]]
        case 3: return [q[2], q[1]]
        case 4: return [q[2]]
        case 5: return [q[2], q[3]]
        case 6: return [q[3]]
        case 7: return [q[0], q[3]]
        default: return []
        }
    }
    /// Release what is no longer held and press what newly is, so a held
    /// direction does not stutter while the thumb wanders inside one sector.
    private static func applyStick(from: Int, to: Int, keys q: [Int32], heldKeys: inout [Int32]) -> Int {
        guard to != from else { return from }
        let old = Set(heldKeys), new = Set(sectorKeys(to, q))
        for vk in old.subtracting(new) { winios_post_key(vk, 0) }
        for vk in new.subtracting(old) { winios_post_key(vk, 1) }
        heldKeys = Array(new)
        return to
    }

    private static let timebase: Double = {
        var info = mach_timebase_info_data_t()
        mach_timebase_info(&info)
        return Double(info.numer) / Double(info.denom) / 1e9
    }()
    private static func seconds(_ ticks: UInt64) -> Double { Double(ticks) * timebase }
}
