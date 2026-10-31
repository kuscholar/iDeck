# Matching Steam CEF source request — draft, not sent

Proposed destination: [ValveSoftware/steam-for-linux issue 12226](https://github.com/ValveSoftware/steam-for-linux/issues/12226).
User explicitly authorized this exact technical request on 2026-10-31. The
comment has not yet been sent at this checkpoint; record its final URL below
after posting. No unrelated upstream issue/PR/message is authorized.

---

Following this request, is there a public source/patch/header distribution for
the customized CEF used by the Apple Silicon Steam client?

I am researching native ARM64 macOS Steam compatibility in
[iDeck's isolated experiment](https://github.com/kuscholar/iDeck/tree/experiment/mac-arm-steam-ios).
The official macOS client packages from manifest `1792618285` contain CEF
`126.0.0`, commit number `3171`, Chromium `126.0.6478.183`. Its public metadata
declares commit `bbb75964a9f4095daf2926163a63cbf11af56565`, platform API hash
`3bf3a90aebd22f3098ae1f2040d618be71553754`, and universal hash
`908f7378d71977393cee4bc349055b7365c3673c`.

The checked public CEF `6478` source has different fingerprints and lacks these
declarations required by the observed Steam Helper loader:

- `cef_generate_gpu_report`
- `cef_is_gpu_compositing_disabled`
- `cef_is_hardware_acceleration_enabled`
- `cef_set_force_device_scale_factor`
- `cef_set_minimum_font_size`
- `cef_set_preferred_contrast`
- `cef_set_reduced_motion_enabled`

On our standard development-signed iPad Air, the genuine framework fails a
16 GiB reservation during its constructors. An independently rebuilt macOS
ARM64 Chromium allocator component with source-wide compact pools, including
glued pools and enabled checks, now passes our on-device allocation tests.
This is an allocator component result; native Steam's browser/UI is not working.

Matching generated C API headers, the corresponding CEF/Chromium patch set and
relevant GN configuration would let us investigate a compatible source build
while preserving the actual API checks and behavior. A public location for
those materials, or a pointer to an appropriate current source distribution,
would be very helpful. Thanks.
