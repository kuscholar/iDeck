import UIKit

/// Helper to enable JIT via StikDebug/StikJIT URL scheme.
/// Opens StikDebug with Madeira's bundled script, polls for CS_DEBUGGED,
/// then allocates JIT memory and detaches the debugger.
enum StikJITHelper {

    // madeira-jit.js in Copy Bundle Resources is the only script source.

    enum RequestError: LocalizedError {
        case scriptMissing
        case invalidRequest
        case unavailable
        case timedOut

        var errorDescription: String? {
            switch self {
            case .scriptMissing:
                return "Madeira's JIT script is missing from this installation. Reinstall Madeira."
            case .invalidRequest:
                return "Madeira could not create the StikDebug request."
            case .unavailable:
                return "StikDebug is not installed. Install it, or configure Built-in StikJIT."
            case .timedOut:
                return "StikDebug did not attach to Madeira within 90 seconds. Check its pairing file and LocalDevVPN, then try again."
            }
        }
    }

    /// The script in Copy Bundle Resources is the single source used by both
    /// StikDebug and Built-in StikJIT.
    static var scriptData: Data? {
        guard let url = Bundle.main.url(forResource: "madeira-jit", withExtension: "js") else { return nil }
        return try? Data(contentsOf: url)
    }

    /// Check whether StikDebug is installed. `stikdebug` is its canonical scheme;
    /// the older `stikjit` alias remains declared for compatibility.
    static var isAvailable: Bool {
        guard let url = URL(string: "stikdebug://enable-jit") else { return false }
        return UIApplication.shared.canOpenURL(url)
    }

    /// Open StikDebug with our JIT script embedded in the URL.
    /// PID targets this running process rather than asking StikDebug to launch a
    /// replacement instance by bundle ID.
    static func enableJIT(completion: @escaping (Result<Void, Error>) -> Void) {
        guard let bundleID = Bundle.main.bundleIdentifier,
              let scriptData else {
            completion(.failure(RequestError.scriptMissing))
            return
        }
        var components = URLComponents()
        components.scheme = "stikdebug"
        components.host = "enable-jit"
        components.queryItems = [
            URLQueryItem(name: "bundle-id", value: bundleID),
            URLQueryItem(name: "pid", value: String(getpid())),
            URLQueryItem(name: "script-data", value: scriptData.base64EncodedString()),
        ]
        guard let url = components.url else {
            LogStore.shared.log("Failed to build StikJIT URL", level: .error)
            completion(.failure(RequestError.invalidRequest))
            return
        }

        LogStore.shared.log("Opening StikDebug to enable JIT...")

        UIApplication.shared.open(url, options: [:]) { success in
            if !success {
                LogStore.shared.log("Failed to open StikDebug. Is it installed?", level: .error)
                completion(.failure(RequestError.unavailable))
                return
            }
            waitForDebugger(completion: completion)
        }
    }

    /// ml1235 (local, 2026-10-02) is folded in here: upstream's waitForDebugger
    /// waits for `ready` (CS_DEBUGGED and a live debugger), which is what ml1235's
    /// pollForJIT did; the flag-only poll reported success at once in the
    /// flagged-without-debugger state. `ready` reads the flag silently (below).
    /// Opening a URL only proves iOS accepted it. Readiness requires both the
    /// sticky CS_DEBUGGED flag and a live debugger that can answer Madeira's BRK.
    @discardableResult
    static func waitForDebugger(timeout: TimeInterval = 90,
                                completion: @escaping (Result<Void, Error>) -> Void) -> Timer {
        let deadline = Date().addingTimeInterval(timeout)
        let timer = Timer(timeInterval: 0.5, repeats: true) { timer in
            if ready {
                timer.invalidate()
                LogStore.shared.log("JIT enabled and debugger attached.", level: .success)
                completion(.success(()))
            } else if Date() >= deadline {
                timer.invalidate()
                LogStore.shared.log(RequestError.timedOut.localizedDescription, level: .error)
                completion(.failure(RequestError.timedOut))
            }
        }
        RunLoop.main.add(timer, forMode: .common)
        return timer
    }

    /// Allocate a JIT memory pool via BRK #0xf00d, then detach the debugger.
    /// Call this after CS_DEBUGGED is confirmed.
    /// Returns the allocated RX base address and RW mapping, or nil on failure.
    static func allocateAndDetach(poolSize: Int = 128 * 1024 * 1024) -> (rx: UnsafeMutableRawPointer, rw: UnsafeMutableRawPointer, size: Int)? {
        guard let result = allocatePool(poolSize: poolSize) else { return nil }
        // Don't detach yet — Wine needs the debugger to prepare PE DLL code pages.
        // Detach will happen later via detachDebugger().
        return result
    }

    /// Why the last allocatePool() returned nil, in words for the person playing
    /// (the library shows it); nil after a success.
    private(set) static var poolFailure: String?
    static let noDebuggerMessage = "JIT is switched on, but StikDebug is not attached to Madeira, so the JIT memory cannot "
        + "be set up. This happens when JIT is enabled from StikDebug's own app list. Tap Enable JIT: StikDebug then "
        + "reopens Madeira with Madeira's script, ready to play."

    /// This app run's pool exists. The debugger detaches right after the pool is
    /// made, by design, so from then on "no debugger attached" is the normal state.
    private(set) static var poolTaken = false

    /// madeira-bcd split pool (`pool-split = 1`): the pool offsets [off, end) that
    /// lie between its two debugger regions (the main thread's stack and our
    /// PROT_NONE placeholders). ContentView exports it as WINE_IOS_JIT_HOLE; ntdll
    /// never hands it out. nil for a pool of one region.
    private(set) static var poolHole: (off: Int, end: Int)?

    /// madeira-bcd pool-mid (`pool-mid = 1` with pool-split; off by default, so GTA's
    /// pool is untouched): a free run of 64MB or more between the split pool's two regions, taken
    /// as a third debugger region M in the same span. RDR2 on build 470: a 71MB
    /// mapping sat in the band at image load, the pool came out as 285 + 319MB around
    /// a 291MB hole holding 213MB of free space, and the image copies ran it dry
    /// (d3dcompiler_47.dll, ERR_GFX_INIT). With M, poolHole is the part below M and
    /// poolHole2 the part above it (the stack); ContentView exports it as
    /// WINE_IOS_JIT_HOLE2. nil without M.
    private(set) static var poolHole2: (off: Int, end: Int)?
    private static var poolMid: (base: vm_address_t, size: vm_address_t)?

    /// madeira-bcd pool-low (`pool-low = 1`): region C, a third debugger region below
    /// the executable window whose RW alias sits at the pool's RX->RW distance. It is
    /// not part of the pool span; ntdll carves FEX's code buffers from it first.
    /// ContentView exports it as WINE_IOS_JIT_TAIL_REGION. nil without it.
    private(set) static var poolLow: (rx: Int, size: Int)?

    /// madeira-bcd Social Club layout 2 (`env.MADEIRA_SC_PA_POOLS = 2` in the game's
    /// file or madeira.cfg; virtual_ios.c, ios_sc2_boot_holds): the RW alias goes to
    /// 0x7900000000 and [0x7000000000, +4 GB) is held PROT_NONE before anything can
    /// land there, for libcef.dll's PartitionAlloc pools; ntdll takes the hold over.
    /// The alias holds no guest pointers, so its address is free (ml1037).
    static let scLayout2Alias: vm_address_t = 0x7900000000
    private static let scLayout2Hold: vm_address_t = 0x7000000000
    private static let scLayout2HoldSize: vm_size_t = 0x100000000
    private static var scHoldTaken = false

    /// The RW alias hint: 0x7900000000 with the hold taken for layout 2, else the
    /// usual 0x7000000000.
    private static func rwAliasHint() -> vm_address_t {
        if scHoldTaken { return scLayout2Alias }
        let v = (MadeiraConfig.gameValue("env.MADEIRA_SC_PA_POOLS") ?? MadeiraConfig.get("env.MADEIRA_SC_PA_POOLS") ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard v.hasPrefix("2") else { return 0x7000000000 }
        var a = scLayout2Hold
        let kr = vm_allocate(mach_task_self_, &a, scLayout2HoldSize, 0 /* VM_FLAGS_FIXED */)
        guard kr == KERN_SUCCESS, a == scLayout2Hold else {
            if kr == KERN_SUCCESS { vm_deallocate(mach_task_self_, a, scLayout2HoldSize) }
            // Name the occupant: the first region at or above the hold.
            var ra = scLayout2Hold
            var rs: vm_size_t = 0
            var info = vm_region_basic_info_data_64_t()
            var cnt = mach_msg_type_number_t(MemoryLayout<vm_region_basic_info_data_64_t>.size / MemoryLayout<Int32>.size)
            var obj: mach_port_t = 0
            let rkr = withUnsafeMutablePointer(to: &info) {
                $0.withMemoryRebound(to: Int32.self, capacity: Int(cnt)) {
                    vm_region_64(mach_task_self_, &ra, &rs, VM_REGION_BASIC_INFO_64, $0, &cnt, &obj)
                }
            }
            LogStore.shared.log(String(format: "[sc-cef] layout 2: [0x%lx,+4GB) is not free (kr=%d; first region 0x%lx+0x%lx prot=%d/%d, region kr=%d) -- usual RW alias placement",
                                       Int(scLayout2Hold), kr, Int(ra), Int(rs), Int(info.protection), Int(info.max_protection), rkr),
                                level: .error)
            return 0x7000000000
        }
        _ = vm_protect(mach_task_self_, a, scLayout2HoldSize, 0, VM_PROT_NONE)
        scHoldTaken = true
        LogStore.shared.log(String(format: "[sc-cef] layout 2: [0x%lx,+4GB) held for libcef.dll's pools; RW alias hint 0x%lx",
                                   Int(scLayout2Hold), Int(scLayout2Alias)))
        return scLayout2Alias
    }

    /// Layout 2 only if the alias landed exactly at 0x7900000000; otherwise the hold
    /// goes back and the caller maps the alias the usual way (ntdll then uses layout 1).
    private static func rwAliasKeep(_ rw: vm_address_t) -> Bool {
        guard scHoldTaken, rw != scLayout2Alias else { return true }
        vm_deallocate(mach_task_self_, scLayout2Hold, scLayout2HoldSize)
        scHoldTaken = false
        LogStore.shared.log(String(format: "[sc-cef] layout 2: the RW alias landed at 0x%lx, not 0x%lx -- hold released, usual placement",
                                   Int(rw), Int(scLayout2Alias)), level: .error)
        return false
    }

    /// Layout 2's FIXED alias mapping failed: give the hold back (ntdll then uses layout 1).
    private static func rwAliasDrop(_ kr: kern_return_t) {
        guard scHoldTaken else { return }
        vm_deallocate(mach_task_self_, scLayout2Hold, scLayout2HoldSize)
        scHoldTaken = false
        LogStore.shared.log(String(format: "[sc-cef] layout 2: the RW alias could not be mapped at 0x%lx (kr=%d) -- hold released, usual placement",
                                   Int(scLayout2Alias), kr), level: .error)
    }

    // 0 treats JIT as ready whenever CS_DEBUGGED is set, as before, without asking whether a debugger is attached.
    private static let attachCheck = MadeiraConfig.flag("MADEIRA_JIT_ATTACH_CHECK")

    /// JIT can serve a launch: CS_DEBUGGED is set, and either a debugger is
    /// attached to answer the pool request or this run's pool exists already.
    /// CS_DEBUGGED alone is not enough: it stays set after a debugger leaves, which
    /// is the state StikDebug's own app list (attach, then detach) leaves behind.
    /// ml1235: the flag is read without jit_check_debugged's log line; the library
    /// polls this every 2 s for the whole app run (and waitForDebugger every 0.5 s).
    static var ready: Bool {
        guard SigningStatus.current.debugged else { return false }
        return !attachCheck || poolTaken || isDebuggerAttached()
    }

    /// CS_DEBUGGED is set but nothing can answer a pool request: JIT has to be
    /// enabled again, through Madeira, before a game can start.
    static var flaggedWithoutDebugger: Bool { SigningStatus.current.debugged && !ready }

    /// ml1234: the early pool placeholder is unmapped once per app run. A launch that
    /// fails without a debugger now leaves the app up, and a second pool request
    /// unmapped the placeholder's range again, under whatever had been mapped there
    /// since (malloc, Metal, IOSurface).
    private static var earlyPoolReleased = false

    /// Allocate a JIT memory pool via BRK #0xf00d WITHOUT detaching the debugger.
    /// The debugger stays attached so Wine can use BRK to prepare PE code pages.
    static func allocatePool(poolSize requestedPoolSize: Int = 128 * 1024 * 1024) -> (rx: UnsafeMutableRawPointer, rw: UnsafeMutableRawPointer, size: Int)? {
        var poolSize = requestedPoolSize      // ml1036: may shrink to fit, see the hole census below
        poolFailure = nil
        LogStore.shared.log("Allocating \(poolSize / 1024 / 1024)MB JIT pool via debugger...")
        // madeira-bcd Social Club layout 2: take the [0x7000000000, +4 GB) hold
        // FIRST. Taken at alias time it lost the race on build 348 (GTA log
        // 2026-10-03 08:00: "is not free (kr=3)", the RW alias then landed at
        // 0x7014f68000 and libcef.dll's 32 GB pools had no slot -> int3): the
        // kernel hands out 0x7000000000 to the first large ANYWHERE request
        // (the debugger's pool regions, ml78/ml596). rwAliasHint() is
        // idempotent once the hold is taken; a no-op without layout 2.
        _ = rwAliasHint()

        let debuggerAttached = isDebuggerAttached()
        LogStore.shared.log("[jit-debugger] attached=\(debuggerAttached ? 1 : 0) at the pool request")
        // With no debugger attached, a JIT request fails the launch with a message; 0 lets it crash the app as before.
        // CS_DEBUGGED stays set after a debugger detaches (JIT enabled by a tool
        // that attaches and leaves, or without Madeira's script), and the pool
        // request below is a BRK only a debugger can answer: with nobody attached
        // it killed the app (EXC_BREAKPOINT in jit26_prepare_region). P_TRACED says
        // whether a debugger is attached now. The handler cannot take a BRK away
        // from an attached debugger, which sees the exception first, so a wrong
        // reading costs nothing.
        if !debuggerAttached && MadeiraConfig.flag("MADEIRA_JIT_TRAP_FALLBACK") {
            jit_arm_trap_fallback()
            LogStore.shared.log("[jit-debugger] no debugger is attached although CS_DEBUGGED is set: "
                + "an unanswered pool request now fails the launch instead of crashing the app", level: .error)
        }

        // iOS-Madeira: FEX's dispatcher emit has a position-dependent encoding
        // bug — only works when the JIT pool lands at a high enough address
        // (empirically ≥ 0x119000000, so dispatcher at +0x7ffc130 has top byte
        // 0x12). When iOS allocates 0x114-0x117xxx the dispatcher's literal-
        // pool fixups silently break and execution branches to zero memory
        // before the first compiled block runs. Pre-claim ~96MB of low address
        // space to push the next ANYWHERE allocation up.
        //
        // We keep these allocations alive for the lifetime of the process —
        // freeing them could let iOS reuse them and cause aliasing issues.
        var pinChunks: [vm_address_t] = []
        let chunkSize = 16 * 1024 * 1024  // 16 MB per chunk
        // Pin until the allocation frontier crosses the mode-A threshold
        // (0x119000000) instead of a fixed 96MB. A fixed count loses the
        // ASLR lottery whenever the base slide is low (observed 2026-07-03:
        // 6 chunks ended at 0x118790000, pool landed 8.4MB short of the
        // threshold and the run fast-failed). vm_allocate is zero-fill
        // reserve-only, so extra chunks don't add resident footprint.
        // The BAD POOL check below stays as the safety net for non-
        // sequential placements.
        let pinTarget: vm_address_t = 0x119000000
        let maxChunks = 32                 // safety cap (512 MB of reservation)
        for i in 0..<maxChunks {
            var addr: vm_address_t = 0
            let kr = vm_allocate(mach_task_self_, &addr, vm_size_t(chunkSize), VM_FLAGS_ANYWHERE)
            if kr == KERN_SUCCESS {
                // ml1036: if the frontier is ALREADY past the threshold this chunk
                // pins nothing useful and costs 16MB of the scarcest VA we have
                // (the low gap must hold the pool AND the 0x140000000 window).
                if addr >= pinTarget {
                    vm_deallocate(mach_task_self_, addr, vm_size_t(chunkSize))
                    LogStore.shared.log(String(format: "JIT-pool frontier already at 0x%lx — no pin needed", Int(addr)))
                    break
                }
                pinChunks.append(addr)
                LogStore.shared.log(String(format: "JIT-pool pin chunk %d at 0x%lx (16MB)", i, Int(addr)))
                if addr + vm_address_t(chunkSize) >= pinTarget { break }
            } else {
                LogStore.shared.log("JIT-pool pin chunk \(i) FAILED kr=\(kr)", level: .error)
                break
            }
        }

        // Ask debugger to allocate RX pages (x0=0 triggers _M allocation).
        // With pin chunks claimed, this should land at a higher address.
        //
        // Two placement constraints (violating either bricks the session):
        // - LOW BOUND: FEX has a position-dependent emit bug below
        //   0x119000000 (mode A: dispatcher branches to zero memory before
        //   block 0 runs; higher-address mode B is runtime-patched in
        //   signal_arm64_ios.c init_syscall_frame).
        // - GUEST WINDOW (ml78, 2026-07-13): with the 896MB pool the kernel
        //   often places the region at 0x7000000000 — inside the guest
        //   x86-64 64GB window [0x70,0x80)G where Wine packs PE images and
        //   the fault handlers classify PCs as guest addresses. Executing
        //   pool code there hangs the first pool call silently (black
        //   screen / wallpaper-only desktop).
        // Reject bad placements and re-roll: a bad region is freed when the
        // kernel allows, otherwise kept alive as a pin.
        // ⚠️ ml596: the old claim that the next pick "must land elsewhere" is FALSE.
        // ml595 freed and re-requested three times and the kernel handed back the
        // SAME 0x7000000000 hole each time, so the retry loop is not a strategy —
        // it is three identical attempts. Failure is therefore deterministic within
        // a launch and the caller must abort rather than run without a pool. A real
        // fix needs explicit placement (hinted allocation / reserve-and-carve),
        // not a re-roll; simply pinning the bad region to force a different address
        // costs another 896MB against the 4096MB jetsam ceiling.
        // ml1034: HOLD THE EXECUTABLE WINDOW BEFORE ALLOCATING RX.
        //
        // ml977 reserved [0x140000000,0x150000000) only AFTER the RX pool was
        // allocated, so on the iPhone 18 Pro the pool got there first and the
        // reservation could only report the loss:
        //
        //   ml977: could NOT reserve the executable window (kr=3)
        //   ml977: RX pool overlaps the executable window -- RX placement, not RW,
        //          would need changing
        //   ml977: RX=[0x122000000,0x142000000)          <- contains 0x140000000
        //   ml985: preferred base 0x140000000+0x70000 REFUSED status=0xc0000018
        //
        // RDR2.exe has BASERELOC rva=0 size=0, so it CANNOT be relocated: moved
        // to 0x146a90000, every absolute pointer in it stayed behind. Its TLS
        // AddressOfCallBacks still read 0x1432ba978 (relocated it would be
        // 0x14954a978), call_tls_callbacks walked that stale array and called
        // garbage:
        //
        //   CompileBlock: REFUSING low/invalid RIP=0x170
        //   [redeliv] 2000 identical redeliveries pc=0x0 -- unrecoverable host
        //             fault misdelivered to guest -> terminating
        //
        // The diagnosis was already in our own log; only the ORDER was wrong. So
        // reserve first: the debugger's allocator cannot hand back a range that
        // is already mapped, which removes the collision without naming an RX
        // address ourselves. Failure is still never fatal -- we log and continue
        // exactly as before, and MADEIRA_NO_EXE_WINDOW=1 skips it.
        let exeWinBase: vm_address_t = 0x140000000
        // ml1037: 128MB, not 256MB. The census on the iPhone 18 Pro read
        //   0x12067c000+505MB | [window 256MB] | 0x150000000+500MB | 0x16fa24000+261MB
        // i.e. the window itself was what split the low gap into pieces too small
        // for the pool, and the 496MB pool that did fit ran out mid-load
        // ("EXEC ALLOC FAILED ... JIT pool exhausted", exit 0xc000012d: 406MB of
        // image copies + 64MB of live code buffers). Halving the window gives the
        // hole above it ~628MB contiguous. The largest fixed-base image we ship
        // against ends at +117MB; ntdll hands the window to the first fixed map
        // of >=64MB that fits, and reads the size from WINE_IOS_EXE_WINDOW.
        let exeWinSize: vm_address_t = 0x8000000           // 128MB
        func overlapsExeWindow(_ base: vm_address_t, _ len: vm_address_t) -> Bool {
            return base < exeWinBase + exeWinSize && base + len > exeWinBase
        }
        let skipWindow = (ProcessInfo.processInfo.environment["MADEIRA_NO_EXE_WINDOW"].map { $0 != "0" } ?? false)
        var windowHeld = false
        if !skipWindow && madeira_early_window_base == UInt(exeWinBase) && madeira_early_window_size == UInt(exeWinSize) {
            // ml1040: already held since image load (JITAllocator.c constructor).
            windowHeld = true
            setenv("WINE_IOS_EXE_WINDOW", String(format: "%lx:%lx", Int(exeWinBase), Int(exeWinSize)), 1)
            LogStore.shared.log("ml1040: executable window [0x140000000,+128MB) held since image load", level: .success)
        } else if !skipWindow {
            var winAddr: vm_address_t = exeWinBase
            let krWin = vm_allocate(mach_task_self_, &winAddr, vm_size_t(exeWinSize), 0 /* VM_FLAGS_FIXED */)
            if krWin == KERN_SUCCESS && winAddr == exeWinBase {
                windowHeld = true
                setenv("WINE_IOS_EXE_WINDOW", String(format: "%lx:%lx", Int(exeWinBase), Int(exeWinSize)), 1)
                LogStore.shared.log("ml1034: reserved executable window [0x140000000,0x150000000) BEFORE "
                    + "RX allocation - a fixed-base main image can now load where it must; "
                    + "ntdll releases it on demand", level: .success)
            } else {
                if krWin == KERN_SUCCESS { vm_deallocate(mach_task_self_, winAddr, vm_size_t(exeWinSize)) }
                LogStore.shared.log("ml1034: could NOT reserve the executable window (kr=\(krWin)) BEFORE "
                    + "RX - something else already holds 0x140000000; a non-relocatable image will be "
                    + "displaced and its absolute pointers will be stale", level: .error)
                // ml1097: NAME the occupant. The ml1095 build hit this on every launch
                // (0x140000000+88MB taken before the image-load constructor ran)
                // and nothing said what it was.
                var pa = vm_address_t(exeWinBase)
                var ps: vm_size_t = 0
                var pinfo = vm_region_basic_info_data_64_t()
                var pcnt = mach_msg_type_number_t(MemoryLayout<vm_region_basic_info_data_64_t>.size / MemoryLayout<Int32>.size)
                var pobj: mach_port_t = 0
                let pkr = withUnsafeMutablePointer(to: &pinfo) {
                    $0.withMemoryRebound(to: Int32.self, capacity: Int(pcnt)) {
                        vm_region_64(mach_task_self_, &pa, &ps, VM_REGION_BASIC_INFO_64, $0, &pcnt, &pobj)
                    }
                }
                var depth: natural_t = 0
                var sinfo = vm_region_submap_info_data_64_t()
                var scnt = mach_msg_type_number_t(MemoryLayout<vm_region_submap_info_data_64_t>.size / MemoryLayout<Int32>.size)
                var sa = vm_address_t(exeWinBase)
                var ss: vm_size_t = 0
                _ = withUnsafeMutablePointer(to: &sinfo) {
                    $0.withMemoryRebound(to: Int32.self, capacity: Int(scnt)) {
                        vm_region_recurse_64(mach_task_self_, &sa, &ss, &depth, $0, &scnt)
                    }
                }
                var dl = Dl_info()
                let named = dladdr(UnsafeRawPointer(bitPattern: UInt(exeWinBase)), &dl) != 0
                let image = named && dl.dli_fname != nil ? String(cString: dl.dli_fname) : "(no dyld image)"
                LogStore.shared.log(String(format: "ml1097: occupant of 0x140000000: region 0x%lx+%luMB prot=%d/%d (kr=%d) user_tag=%u share=%d resident=%u pages; %@",
                                           Int(pa), Int(ps >> 20), pinfo.protection, pinfo.max_protection, pkr,
                                           sinfo.user_tag, Int(sinfo.share_mode), sinfo.pages_resident, image), level: .error)
            }
        }

        let goodLow = 0x119000000
        let guestLo = 0x7000000000
        let guestHi = 0x8000000000

        // ml1036: HOLE CENSUS, then size the pool to what can actually be placed.
        //
        // ml1034 held the window first, and the very next launch could not place
        // the pool at all: three identical "BAD POOL placement 0x7000000000"
        // and an abort. The debugger's allocator is first-fit with no address
        // hint, and on this phone the usable low gap is small -- from the slide-
        // dependent frontier (0x11ed.. to 0x1258.. observed) up to the window.
        // With the frontier at 0x1223d0000 that is 460MB: a 512MB pool does not
        // fit, so the kernel falls through to the guest window, which we refuse.
        // Before ml1034 the same launch would have "worked" by swallowing
        // 0x140000000 and then killing any fixed-base game -- so the choice is
        // between a smaller pool and a run that cannot survive. Measure the
        // holes, log them, and take the largest pool that fits.
        // ml1040: the run directly above the window has been held since image load
        // so that nothing of ours could land in it. Release it now -- the very
        // next allocation of this size is the debugger's.
        var plugs: [(vm_address_t, vm_size_t)] = []
        // madeira-bcd split pool switch (see SPLIT POOL below); the census reads it too.
        let splitValue = (MadeiraConfig.gameValue("pool-split") ?? MadeiraConfig.get("pool-split") ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        // Opt-in: keep page-sized remainders in A/B instead of discarding up to
        // 16MB from each free run. The requested A+B budget and region C stay unchanged.
        let pageFit = ["1", "on", "true", "yes"].contains(splitValue)
            && ["1", "on", "true", "yes"].contains((MadeiraConfig.gameValue("pool-page-fit")
                ?? MadeiraConfig.get("pool-page-fit") ?? "")
                .trimmingCharacters(in: .whitespacesAndNewlines).lowercased())
        if pageFit {
            LogStore.shared.log("[pool-split] page-fit=1: A/B requests fit 16KB pages within the requested \(requestedPoolSize >> 20)MB budget; C retains pool-low-margin")
        }
        // madeira-bcd pool-pair (below): region A's run and the size the single-region
        // pool would have had, for the check after the request.
        var pairA: (base: vm_address_t, size: vm_address_t)? = nil
        var pairSingle = 0
        let earlyPoolBase = vm_address_t(madeira_early_pool_base)
        let earlyPoolSize = vm_address_t(madeira_early_pool_size)
        if earlyPoolBase != 0 && earlyPoolReleased {
            LogStore.shared.log(String(format: "ml1234: the early pool placeholder 0x%lx+%luMB was released by an earlier pool request in this run; not unmapped again",
                                       Int(earlyPoolBase), Int(earlyPoolSize >> 20)))
        } else if earlyPoolBase != 0 {
            vm_deallocate(mach_task_self_, earlyPoolBase, vm_size_t(earlyPoolSize))
            earlyPoolReleased = true
            LogStore.shared.log(String(format: "ml1040: released the early pool placeholder 0x%lx+%luMB for the debugger",
                                       Int(earlyPoolBase), Int(earlyPoolSize >> 20)))
            // madeira-bcd: what the placeholder ran into at image load. Normally the
            // main thread's stack (VM tag 30); anything else that low splits the pool.
            if madeira_early_intruder_base != 0 {
                LogStore.shared.log(String(format: "ml1135: the placeholder ended at the mapping 0x%lx+%luMB (VM tag %u, prot %u), already there at image load",
                                           Int(madeira_early_intruder_base), Int(madeira_early_intruder_size >> 20),
                                           madeira_early_intruder_tag, madeira_early_intruder_prot))
            }
        } else {
            LogStore.shared.log("ml1040: no early pool placeholder was obtained — placement is left to chance", level: .error)
            // ml1135: what was already mapped above the window at image load (user_tag
            // is the VM_MEMORY_* allocation tag; 0 = untagged anonymous memory).
            if madeira_early_intruder_base != 0 {
                LogStore.shared.log(String(format: "ml1135: the placeholder was blocked at image load by a mapping at 0x%lx+%luMB (VM tag %u, prot %u) -- this is what shrinks the JIT pool",
                                           Int(madeira_early_intruder_base), Int(madeira_early_intruder_size >> 20),
                                           madeira_early_intruder_tag, madeira_early_intruder_prot), level: .error)
            }
        }
        do {
            var holes: [(base: vm_address_t, size: vm_address_t)] = []
            var addr = vm_address_t(goodLow)
            var prevEnd = vm_address_t(goodLow)
            while addr < vm_address_t(guestLo) {
                var rsize: vm_size_t = 0
                var info = vm_region_basic_info_data_64_t()
                var cnt = mach_msg_type_number_t(MemoryLayout<vm_region_basic_info_data_64_t>.size / MemoryLayout<Int32>.size)
                var obj: mach_port_t = 0
                let kr = withUnsafeMutablePointer(to: &info) {
                    $0.withMemoryRebound(to: Int32.self, capacity: Int(cnt)) {
                        vm_region_64(mach_task_self_, &addr, &rsize, VM_REGION_BASIC_INFO_64, $0, &cnt, &obj)
                    }
                }
                if kr != KERN_SUCCESS { break }
                let start = min(addr, vm_address_t(guestLo))
                if start > prevEnd && start - prevEnd >= 64 << 20 { holes.append((prevEnd, start - prevEnd)) }
                prevEnd = max(prevEnd, addr + vm_address_t(rsize))
                addr = prevEnd
            }
            let desc = holes.map { String(format: "0x%lx+%luMB", Int($0.base), Int($0.size >> 20)) }.joined(separator: " ")
            LogStore.shared.log("ml1036: free holes >=64MB in [0x119000000,0x7000000000) with the window held: "
                + (desc.isEmpty ? "NONE" : desc))
            let largest = holes.map { $0.size }.max() ?? 0
            // madeira-bcd pool-pair (pool-split only): two runs ABOVE the window, split
            // only by the main thread's stack, can beat the largest single run when that
            // one lies BELOW the window, where the pool cannot split ("the gap would
            // hold the executable window"). GTA V build 364, 21:00 and 23:47: 470MB below
            // vs 369+331MB / 436+327MB above -> a 464MB pool and "[jit-pool] EXHAUSTED";
            // the pair gives 688 / 752MB. Region A takes the run above the window (every
            // lower run that could hold it is plugged, so first-fit lands there) and
            // takeSecondRegion then takes B exactly as for any split pool. Used only when
            // the single-region pool would land below the window and the pair is larger;
            // `pool-pair = 0` in the game's file or madeira.cfg turns it off.
            let pairOff = ["0", "off", "false", "no"].contains((MadeiraConfig.gameValue("pool-pair")
                ?? MadeiraConfig.get("pool-pair") ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased())
            let ceiling: vm_address_t = 0x180000000           // SHARED_REGION_BASE_ARM64, as takeSecondRegion
            let singleFit = largest < vm_address_t(poolSize)
                ? poolRunSize(available: largest, wanted: vm_address_t(poolSize), pageFit: pageFit)
                : vm_address_t(poolSize)
            if ["1", "on", "true", "yes"].contains(splitValue) && windowHeld && !pairOff && singleFit < vm_address_t(poolSize) {
                // Where the single-region request lands: first-fit, past ml1040's plugs
                // (holes below the placeholder, only when a hole above it fits).
                let steered = earlyPoolBase != 0 && holes.contains { $0.base + $0.size > earlyPoolBase && $0.size >= singleFit }
                let singleAt = holes.first(where: { $0.size >= singleFit && !(steered && $0.base + $0.size <= earlyPoolBase) })
                if let s = singleAt, s.base + s.size <= exeWinBase {
                    var best = singleFit
                    var bestB: (base: vm_address_t, size: vm_address_t) = (base: 0, size: 0)
                    for run in holes where run.base >= exeWinBase + exeWinSize && run.base < ceiling {
                        let aFit = min(poolRunSize(available: min(run.size, ceiling - run.base),
                                                  wanted: vm_address_t(poolSize), pageFit: pageFit), vm_address_t(poolSize))
                        guard aFit >= 256 << 20, aFit < vm_address_t(poolSize) else { continue }
                        // B as takeSecondRegion picks it: the largest run in [A's end, ceiling),
                        // the rest of A's own run included.
                        let aEnd = run.base + aFit
                        var bRun: (base: vm_address_t, size: vm_address_t) = (base: aEnd, size: min(run.base + run.size, ceiling) - aEnd)
                        for h in holes where h.base > run.base && h.base < ceiling && min(h.base + h.size, ceiling) - h.base > bRun.size {
                            bRun = (base: h.base, size: min(h.base + h.size, ceiling) - h.base)
                        }
                        let bFit = poolRunSize(available: bRun.size, wanted: vm_address_t(poolSize) - aFit, pageFit: pageFit)
                        if bFit >= 64 << 20 && aFit + bFit > best {
                            best = aFit + bFit
                            pairA = (base: run.base, size: aFit)
                            bestB = (base: bRun.base, size: bFit)
                        }
                    }
                    if let pa = pairA {
                        pairSingle = Int(singleFit)
                        poolSize = Int(pa.size)
                        LogStore.shared.log(String(format: "[pool-split] ml1036 pair above the window: A=0x%lx+%luMB B=0x%lx+%luMB "
                            + "total=%luMB (single best was %luMB at 0x%lx, below the window, where the pool cannot split; "
                            + "pool-pair = 0 turns this off)",
                            Int(pa.base), Int(pa.size >> 20), Int(bestB.base), Int(bestB.size >> 20), Int(best >> 20),
                            Int(singleFit >> 20), Int(s.base)), level: .success)
                        if best < 500 << 20 {
                            LogStore.shared.log("⚠️ SMALL JIT POOL (\(best >> 20)MB) on this launch: expect ~1 s freezes in heavy games. "
                                + "Quit and relaunch the app for a smooth session.", level: .error)
                        }
                        // The debugger allocates first-fit: plug every lower run that could
                        // hold region A (as takeSecondRegion does for B); released after the request.
                        for h in freeRuns(0x100000000, pa.base, minSize: pa.size) {
                            var a = h.base
                            if vm_allocate(mach_task_self_, &a, vm_size_t(h.size), 0 /* VM_FLAGS_FIXED */) == KERN_SUCCESS {
                                if a == h.base {
                                    plugs.append((a, vm_size_t(h.size)))
                                    LogStore.shared.log(String(format: "[pool-split] ml1036 pair: plugged lower run 0x%lx+%luMB so first-fit lands at 0x%lx",
                                                               Int(h.base), Int(h.size >> 20), Int(pa.base)))
                                } else { vm_deallocate(mach_task_self_, a, vm_size_t(h.size)) }
                            }
                        }
                    }
                }
            }
            if pairA == nil && largest < vm_address_t(poolSize) {
                let fit = Int(poolRunSize(available: largest, wanted: vm_address_t(poolSize), pageFit: pageFit))
                if fit >= 256 << 20 {
                    LogStore.shared.log("ml1036: no hole fits a \(poolSize >> 20)MB pool — SHRINKING to \(fit >> 20)MB "
                        + "(the alternative is a pool in the guest window or on top of 0x140000000, "
                        + "both of which are fatal)", level: .error)
                    poolSize = fit
                    // ml1135: ~400MB of the pool is PE image copies, so below ~500MB FEX's
                    // code cache is starved and rolls over every few seconds in game
                    // (ph-rdr90: 432MB pool, 52 rollovers, a ~1 s freeze each).
                    if fit < 500 << 20 {
                        LogStore.shared.log("⚠️ SMALL JIT POOL (\(fit >> 20)MB) on this launch: expect ~1 s freezes in heavy games. "
                            + "Quit and relaunch the app for a smooth session.", level: .error)
                    }
                } else {
                    LogStore.shared.log("ml1036: largest hole is only \(largest >> 20)MB — cannot place a usable pool",
                                        level: .error)
                }
            }
            // ml1040: the debugger allocates first-fit. If a LOWER hole also fits
            // the final pool size it would win and strand the pool below the
            // window again, so plug those for the duration of the request.
            // ml1097: a hole that CONTAINS or ADJOINS the released placeholder is the
            // pool's own landing site, never a "lower hole" -- when the window was not
            // held, the placeholder's run merged with the free space below it and
            // the old test plugged the only hole that fit (every launch of ml1095
            // ended in the guest window). Plug only holes ending below the placeholder.
            // Plug only when a hole at or above the placeholder can take the pool.
            // On an iPhone 17 Pro Max the placeholder got 559MB, the pool was shrunk
            // to the 610MB hole BELOW the window, and that hole was then plugged as
            // a "lower hole" -- so nothing could hold 608MB, all three placements
            // fell into the guest window and the app killed itself. The hole below
            // ends under 0x140000000, so a pool there is safe; steering only helps
            // if the target fits.
            let aboveFits = holes.contains { $0.base + $0.size > earlyPoolBase && $0.size >= vm_address_t(poolSize) }
            if pairA == nil && earlyPoolBase != 0 && windowHeld && !aboveFits {
                LogStore.shared.log("ml1040: no hole above the window fits \(poolSize >> 20)MB — not plugging, the pool takes the hole below it")
            }
            if pairA == nil && earlyPoolBase != 0 && windowHeld && aboveFits {
                for h in holes where h.base + h.size <= earlyPoolBase && h.size >= vm_address_t(poolSize) {
                    var a = h.base
                    if vm_allocate(mach_task_self_, &a, vm_size_t(h.size), 0 /* FIXED */) == KERN_SUCCESS && a == h.base {
                        plugs.append((a, vm_size_t(h.size)))
                        LogStore.shared.log(String(format: "ml1040: plugged lower hole 0x%lx+%luMB so first-fit lands above the window",
                                                   Int(h.base), Int(h.size >> 20)))
                    } else if a != h.base { vm_deallocate(mach_task_self_, a, vm_size_t(h.size)) }
                }
            }
        }

        var rxPtrOpt: UnsafeMutableRawPointer? = nil
        var requestUnanswered = false
        for attempt in 0..<3 {
            guard let p = jit26_prepare_region(nil, poolSize), p != UnsafeMutableRawPointer(bitPattern: 0) else {
                LogStore.shared.log("Debugger failed to allocate RX memory (attempt \(attempt))", level: .error)
                requestUnanswered = true
                break
            }
            let a = Int(bitPattern: p)
            let inGuestWindow = a + poolSize > guestLo && a < guestHi
            // ml1034: a pool covering 0x140000000 displaces a non-relocatable
            // main image, which is fatal later and unrecoverable.
            let hitsExeWindow = overlapsExeWindow(vm_address_t(a), vm_address_t(poolSize))
            if a >= goodLow && !inGuestWindow && !hitsExeWindow {
                rxPtrOpt = p
                break
            }
            LogStore.shared.log(String(format: "BAD POOL placement 0x%lx (%@) — re-rolling (attempt %d)",
                                       a,
                                       a < goodLow ? "mode A low"
                                         : (hitsExeWindow ? "swallows the 0x140000000 executable window"
                                                          : "guest 64G window"),
                                       attempt), level: .error)
            let dkr = vm_deallocate(mach_task_self_, vm_address_t(a), vm_size_t(poolSize))
            LogStore.shared.log(dkr == KERN_SUCCESS
                ? "  bad region freed"
                : "  bad region kept as pin (vm_deallocate kr=\(dkr))")
        }
        // ml1040: the plugs existed only to steer first-fit; give the VA back.
        for (a, sz) in plugs { vm_deallocate(mach_task_self_, a, sz) }
        // madeira-bcd pool-pair: region A must sit at the run chosen by the census and
        // region B must be taken now. Otherwise fall back to the single-region pool the
        // census would have made (pairSingle), as if pool-pair were off.
        poolMid = nil   // pool-mid: set only by takeSecondRegion (here for pool-pair, or below)
        var pairSecond: (base: vm_address_t, size: vm_address_t)? = nil
        if let pa = pairA, let p = rxPtrOpt {
            let got = vm_address_t(bitPattern: p)
            if got == pa.base {
                pairSecond = takeSecondRegion(above: got + vm_address_t(poolSize), want: requestedPoolSize - poolSize, pageFit: pageFit,
                                              exeWindow: (exeWinBase, exeWinSize))
            }
            if let second = pairSecond {
                let midNote = poolMid.map { String(format: ", region M 0x%lx+%luMB (pool-mid)", Int($0.base), Int($0.size >> 20)) } ?? ""
                LogStore.shared.log(String(format: "[pool-split] ml1036 pair placed: region A 0x%lx+%luMB, region B 0x%lx+%luMB%@, "
                    + "%luMB in all (the single-region pool would have been %luMB)",
                    Int(got), poolSize >> 20, Int(second.base), Int(second.size >> 20), midNote,
                    (poolSize + Int(second.size) + Int(poolMid?.size ?? 0)) >> 20, pairSingle >> 20), level: .success)
            } else {
                let why: String = got == pa.base
                    ? "region B was not taken"
                    : String(format: "region A landed at 0x%lx, not 0x%lx", Int(got), Int(pa.base))
                LogStore.shared.log("[pool-split] ml1036 pair FAILED: \(why) — falling back to the single-region "
                    + "\(pairSingle >> 20)MB pool", level: .error)
                if pairSingle > poolSize {
                    // A region that missed A's run may sit in the hole the single pool
                    // needs: give it back first. Region A at its run stays held until the
                    // replacement is good (it cannot be in the way: it is above the window).
                    if got != pa.base {
                        let dkr = vm_deallocate(mach_task_self_, got, vm_size_t(poolSize))
                        LogStore.shared.log("[pool-split] ml1036 pair: region released (kr=\(dkr))")
                        rxPtrOpt = nil
                    }
                    var replaced = false
                    if let q = jit26_prepare_region(nil, pairSingle), q != UnsafeMutableRawPointer(bitPattern: 0) {
                        let qa = Int(bitPattern: q)
                        let qGuest = qa + pairSingle > guestLo && qa < guestHi
                        if qa >= goodLow && !qGuest && !overlapsExeWindow(vm_address_t(qa), vm_address_t(pairSingle)) {
                            if let old = rxPtrOpt { vm_deallocate(mach_task_self_, vm_address_t(bitPattern: old), vm_size_t(poolSize)) }
                            rxPtrOpt = q
                            poolSize = pairSingle
                            replaced = true
                        } else {
                            let dkr = vm_deallocate(mach_task_self_, vm_address_t(qa), vm_size_t(pairSingle))
                            LogStore.shared.log(String(format: "BAD POOL placement 0x%lx for the %luMB fallback — released (kr=%d)",
                                                       qa, pairSingle >> 20, dkr), level: .error)
                        }
                    } else {
                        LogStore.shared.log("Debugger failed to allocate RX memory (pool-pair fallback, \(pairSingle >> 20)MB)", level: .error)
                    }
                    if replaced {
                        LogStore.shared.log("[pool-split] ml1036 pair fallback: the pool is \(poolSize >> 20)MB in one region, "
                            + "as without pool-pair")
                    } else if rxPtrOpt != nil {
                        LogStore.shared.log("[pool-split] ml1036 pair fallback failed: keeping region A alone (\(poolSize >> 20)MB)",
                                            level: .error)
                    } else {
                        LogStore.shared.log("[pool-split] ml1036 pair fallback failed: no pool region", level: .error)
                    }
                }
            }
        }
        guard let rxPtr = rxPtrOpt else {
            if requestUnanswered && !debuggerAttached {
                // Nothing answered the BRK: there is no pool and no placement to
                // re-roll, so the app stays up and says what to do.
                poolFailure = noDebuggerMessage
                LogStore.shared.log("[jit-debugger] the pool request was not answered: no debugger is attached. "
                    + "Enable JIT with Madeira's Enable JIT button, so that StikDebug attaches with Madeira's "
                    + "script and stays attached until the game starts.", level: .error)
                return nil
            }
            poolFailure = requestUnanswered
                ? "The debugger could not allocate the JIT memory. Restart Madeira, enable JIT and try again."
                : "The JIT memory landed at an address Madeira cannot use. Restart Madeira, enable JIT and try again."
            LogStore.shared.log("BAD POOL: no valid placement after retries. Killing in 10s — please relaunch.", level: .error)
            DispatchQueue.global(qos: .userInitiated).asyncAfter(deadline: .now() + 10) {
                LogStore.shared.log("BAD POOL — exiting now. Relaunch the app.", level: .error)
                exit(0)
            }
            return nil
        }
        let rxAddr = Int(bitPattern: rxPtr)
        LogStore.shared.log("RX pool at \(String(format: "%p", rxAddr))")

        // Create RW mapping via vm_remap
        var rwAddr: vm_address_t = 0
        var curProt: vm_prot_t = 0
        var maxProt: vm_prot_t = 0

        // task #35: place the RW alias BELOW the 64GB carveout floor.
        // With VM_FLAGS_ANYWHERE the kernel picks the first free address above
        // the GPU carveout [64G,448G) — which is 0x7000000000 exactly. That is
        // the base of a 16GB jumbo slot, so this 896MB data-only mapping was
        // sterilizing a whole slot that CEF's PartitionAlloc needs. The top
        // window [448G,512G) holds only four such slots and CEF wants at least
        // four pools, so we cannot afford to spend one on ourselves.
        // Data-only (never executed — exec always goes through the RX alias),
        // so placement is unconstrained; fall back to ANYWHERE if all candidates
        // are taken, which restores the previous behaviour exactly.
        // ml91: six hand-picked candidates (8/12/16/24/32/48G) ALL failed —
        // sub-64G is far more crowded than assumed. Sweep the whole region on a
        // 1GB stride instead of guessing. Each failed vm_remap(FIXED) is cheap,
        // so ~58 probes at startup costs nothing and finds any real hole.
        // ml92 measured the real map: there is NO sub-64G space at all. The only
        // "free" region down there (0..0x102454000) is __PAGEZERO, and 4G-64G is
        // fully reserved (malloc xzone) — 58 probes on a 1GB stride found nothing.
        // Usable VA is exactly one ~63GB window, 0x7038000000..0x7fffdf0000.
        //
        // That window holds four 16GB-aligned slots (448/464/480/496G) and CEF's
        // PartitionAlloc wants one pool per slot. Landing here at 0x7000000000
        // spends the 448G slot on an 896MB mapping. Slot 496G is ALREADY ruined
        // by Wine furniture (PE images at ~0x7e874c0000 = 505.8G), so parking at
        // the very top costs nothing that isn't already lost and hands 448G back
        // to PartitionAlloc intact.
        // ml91/ml92/ml93: relocating this alias was tried and REVERTED. The map
        // says usable VA is a single ~63GB window (0x7038000000..0x7fffdf0000);
        // sub-64G is __PAGEZERO plus a fully-reserved 4G-64G band, so 58 probes
        // on a 1GB stride found nothing (ml92). Parking at the top of space
        // instead (0x7fc8000000) DID place, but Wine allocates its furniture
        // top-down — the TEB landed 1.25MB below us at 0x7fc7ec0000, pool copies
        // came out zero-filled, and libarm64ecfex died on 8 exec faults before
        // CEF was even reached (ml93). There is nowhere to put an 896MB mapping
        // that does not cost either a 16GB PartitionAlloc slot or Wine's own
        // furniture. The kernel pick (0x7000000000, base of the window) is the
        // least harmful: it spends the 448G slot but leaves the top — where Wine
        // clusters — alone.
        // ml96 census: CEF needs THREE 16GB pools (48GB), not the 144GB a naive
        // sum suggested — #3/#4/#5 are one pool re-rolling its hint, and the two
        // 32GB requests are that same pool over-reserving for 16GB ALIGNMENT.
        // 48GB fits in the 63GB window, so the third pool fails only because no
        // 16GB-ALIGNED slot is left: 464G and 480G are taken, 496G is broken by
        // Wine furniture, and 448G is spent on this 896MB alias.
        //
        // Freeing 448G should let pool 3 land. ml93 tried that and failed by
        // parking at 0x7fc8000000 — the extreme top, exactly where Wine
        // allocates its furniture top-down (the TEB landed 1.25MB below us and
        // pool copies came back zeroed). The map says 0x7c00000000..0x7e874c0000
        // is free, so take the BOTTOM of the already-broken 496G slot instead
        // and leave the top for Wine.
        // DO NOT relocate this alias without new evidence. Three placements were
        // measured against the default kernel pick (0x7000000000, which the
        // kernel picks because it is the first free address above the GPU
        // carveout):
        //   0x7000000000 (default)  ml94=8, ml96=1  exec faults, reaches libcef
        //   0x7fc8000000 (top)      ml93=8          exec faults, dies before CEF
        //   0x7c00000000 (496G)     ml97=16, ml98=16 exec faults, dies before CEF
        // Same fault class in every case (pool page loses content/exec, on a
        // recycled range) — relocation makes an EXISTING intermittent bug worse
        // rather than introducing a new one. Two mechanisms were proposed and
        // BOTH disproven: Wine furniture collision (ml93) and the reclaim-recover
        // band claiming the alias (ml97; the band exclusion landed in
        // signal_arm64_ios.c and did NOT change the count). Whatever couples the
        // alias base to pool stability is still unidentified.
        //
        // Cost of staying here: the alias occupies the base of the 448G slot, so
        // PartitionAlloc gets only two of the three 16GB-aligned pools it needs
        // (see the ml96 [jumbo#N] census). Freeing that slot is worth doing —
        // but by moving WINE's furniture out of 496G, not by moving this.
        // ml977: RESERVE the x64 executable window, then let the kernel place RW.
        //
        // Every x64 Windows executable defaults to ImageBase 0x140000000, and an
        // image with no relocation directory MUST have it. RDR2.exe is exactly
        // that (ImageBase 0x140000000, BASERELOC rva=0 size=0, DYNAMIC_BASE
        // clear). In rdr40/rdr41 the kernel placed this RW alias adjacent to the
        // RX pool -- RX=0x119eb0000, RW=RX+512MB -- so the alias covered
        // 0x140000000, the loader's no-clobber fixed map failed, the exe was
        // placed elsewhere WITHOUT relocations, and its TLS AddressOfCallBacks
        // stayed 0x1432ba978: an address inside this alias. call_tls_callbacks
        // then read its callback list out of pool backing memory.
        //
        // ml976 tried a list of FIXED candidates (0x150000000 upward) and every
        // one returned KERN_NO_SPACE (=3): those ranges are occupied, so a
        // non-overwriting remap correctly refused. ml976 then returned nil,
        // which aborted pool allocation and stopped Wine from starting at all --
        // "JIT pool allocation FAILED". A placement experiment must never brick
        // the launch; that was the bug, not the refusal.
        //
        // So invert it: RESERVE [0x140000000, +256MB) up front, then ask for RW
        // with VM_FLAGS_ANYWHERE exactly as before. The kernel cannot choose a
        // range that overlaps a mapping we already hold, so adjacency is ruled
        // out without naming any address ourselves, and the reservation also
        // stops unrelated allocations and earlier relocatable images from taking
        // the window first. rwAddr is seeded with 0x150000000 as a floor hint so
        // the search starts just above the window rather than jumping far away
        // (a large alias offset is legal -- FEX derives DualMap::WriteOffset from
        // the real RW-RX distance -- but a near placement stays closest to the
        // measured-good configuration).
        //
        // Failure is never fatal here: if the window cannot be reserved we log it
        // and continue with the kernel's choice, which is the pre-ml976 behaviour.
        // MADEIRA_NO_EXE_WINDOW=1 skips the reservation entirely.
        // ml1034: the reservation and the RX overlap rejection both happen before
        // the pool is allocated now (see above). This is a post-hoc assertion: if
        // it fires, the debugger handed back a range covering a window we held,
        // which should be impossible.
        let rxAddrV = vm_address_t(bitPattern: rxPtr)
        if overlapsExeWindow(rxAddrV, vm_address_t(poolSize)) {
            LogStore.shared.log("ml1034: RX pool STILL overlaps the executable window despite reserving "
                + "it first (windowHeld=\(windowHeld)) — a non-relocatable main image will be displaced",
                level: .error)
        }

        // madeira-bcd POOL-LOW: `pool-low = 1` in the game's own file or in madeira.cfg.
        // Off by default; nothing below runs without it.
        //
        // Every GTA V log has a 416-476MB free run BELOW the executable window (the
        // ml1036 census above), while the pool above it ran its head dry (build 374,
        // 2026-10-04 09:25: 557 of 560MB below the hole, 112MB of the pool spent on
        // FEX code buffers). That run cannot join the pool's span -- the window would
        // then lie inside [RX, RX+size), which ntdll and FEX treat as pool memory --
        // so it becomes a third debugger region, region C, outside the span, with its
        // RW alias at the pool's RX->RW distance (one reservation for C and the pool,
        // mapLowAlias). ntdll carves FEX's code buffers from C first
        // (WINE_IOS_JIT_TAIL_REGION) and the whole pool span is left to the PE image
        // copies. `pool-low-margin` MB (128 by default) of the run stay free for the
        // children's relocatable main exes. Costs C's size in footprint, like region B.
        poolLow = nil
        let lowValue = (MadeiraConfig.gameValue("pool-low") ?? MadeiraConfig.get("pool-low") ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        var lowRegion: (base: vm_address_t, size: vm_address_t)? = nil
        if ["1", "on", "true", "yes"].contains(lowValue) {
            lowRegion = takeLowRegion(poolRx: rxAddrV, exeWindow: (exeWinBase, exeWinSize), pageFit: pageFit)
        }
        // Region C is taken and its alias failed: give it back, the pool works as without it.
        func dropLowRegion(_ why: String) {
            guard let low = lowRegion else { return }
            let dkr = vm_deallocate(mach_task_self_, low.base, vm_size_t(low.size))
            LogStore.shared.log("[pool-low] \(why) -- region C released (kr=\(dkr)); code buffers stay in the pool",
                                level: .error)
            lowRegion = nil
        }
        // The pool and C are mapped: say so and keep C for ContentView.
        func lowReady(_ rwBase: vm_address_t, _ low: (base: vm_address_t, size: vm_address_t), _ rw: vm_address_t) {
            let exemptC = jit_make_region_no_footprint(UnsafeMutableRawPointer(bitPattern: rwBase)!, Int(low.size),
                                                       "pool-RW-alias-low")
            LogStore.shared.log(String(format: "[pool-low] region C RX [0x%lx,0x%lx) %luMB, RW [0x%lx,0x%lx) at the pool's "
                + "distance 0x%lx (one RW reservation from 0x%lx); FEX code buffers come from C first, the pool span is "
                + "left to the image copies (no-footprint %@)",
                Int(low.base), Int(low.base + low.size), Int(low.size >> 20), Int(rwBase), Int(rwBase + low.size),
                Int(rw) - Int(rxAddrV), Int(rwBase), exemptC ? "applied" : "REFUSED"),
                level: exemptC ? .success : .error)
            StikJITHelper.poolLow = (rx: Int(low.base), size: Int(low.size))
        }

        // madeira-bcd SPLIT POOL: `pool-split = 1` in the game's own file or in
        // madeira.cfg. Off by default; nothing below runs without it.
        //
        // Executable memory can only come from the debugger and can only live in
        // the low band under the dyld shared region (0x180000000): everything from
        // there to 0x7000000000 is the shared region, the kernel's reserved range
        // and the GPU carveout, and [0x7000000000, 0x8000000000) is the guest
        // window. Above the 128MB executable window that band holds
        // [0x148000000, 0x180000000) = 896MB, but iOS puts the main thread's stack
        // in it, so the largest run is 560-631MB (2026-10-02: GTA V Enhanced
        // 624/608/592MB, God of War 560MB) and the census above shrinks the pool
        // to it. GTA's Social Club then cannot get the 240MB copy of libcef.dll.
        // The run above the stack (258-325MB in the same logs) is taken here as a
        // second debugger region and both are aliased as ONE pool span with one
        // RX->RW distance, so ntdll and FEX keep a single [RX, RX+size) range;
        // WINE_IOS_JIT_HOLE tells ntdll never to hand out the part in between.
        // Costs the second region's size in footprint (debugger-blessed pages are
        // dirty from birth) -- the total stays within the requested pool size.
        // (splitValue is read before the hole census, which uses it for pool-pair.)
        poolHole = nil
        poolHole2 = nil
        if ["1", "on", "true", "yes"].contains(splitValue) {
            if poolSize >= requestedPoolSize {
                LogStore.shared.log("[pool-split] the pool got its full \(poolSize >> 20)MB in one region — no split needed")
            } else if let second = pairSecond ?? takeSecondRegion(above: rxAddrV + vm_address_t(poolSize), want: requestedPoolSize - poolSize, pageFit: pageFit,
                                                                  exeWindow: (exeWinBase, exeWinSize)) {
                if pageFit {
                    LogStore.shared.log("[pool-split] page-fit A=\(poolSize >> 10)KB B=\(second.size >> 10)KB usable=\((vm_address_t(poolSize) + second.size + (poolMid?.size ?? 0)) >> 10)KB budget=\(requestedPoolSize >> 10)KB; native mappings retained")
                }
                // madeira-bcd pool-low: C, A (pool-mid: M) and B in one RW reservation (C first)
                if let low = lowRegion {
                    var lowRegions: [(rx: vm_address_t, size: vm_address_t)] = [(rx: low.base, size: low.size),
                                                                                (rx: rxAddrV, size: vm_address_t(poolSize))]
                    if let mid = poolMid { lowRegions.append((rx: mid.base, size: mid.size)) }
                    lowRegions.append((rx: second.base, size: second.size))
                    if let rwLow = mapLowAlias(lowRegions) {
                        let span = Int(second.base + second.size - rxAddrV)
                        let holeEnd = Int(second.base - rxAddrV)
                        let rw = rwLow + (rxAddrV - low.base)
                        let rwPtr = UnsafeMutableRawPointer(bitPattern: rw)!
                        LogStore.shared.log("ml977: RX=[\(String(format: "%p", Int(rxAddrV))),\(String(format: "%p", Int(rxAddrV) + span))) "
                            + "RW=[\(String(format: "%p", Int(rw))),\(String(format: "%p", Int(rw) + span))) "
                            + "offset=0x\(String(Int(rw) - Int(rxAddrV), radix: 16)) windowHeld=\(windowHeld) rwOverlap=false",
                            level: .success)
                        let exemptA = jit_make_region_no_footprint(rwPtr, poolSize, "pool-RW-alias")
                        let exemptB = jit_make_region_no_footprint(rwPtr + holeEnd, Int(second.size), "pool-RW-alias-2")
                        let exemptM = poolMid.map { jit_make_region_no_footprint(rwPtr + Int($0.base - rxAddrV), Int($0.size), "pool-RW-alias-mid") } ?? true
                        LogStore.shared.log("[no-footprint] pool applied=\(exemptA && exemptB && exemptM)", level: exemptA && exemptB && exemptM ? .success : .error)
                        splitHoles(aSize: poolSize, bOff: holeEnd, rxBase: rxAddrV)
                        if poolMid == nil {
                        LogStore.shared.log(String(format: "[pool-split] JIT pool = RX [0x%lx,0x%lx) %luMB + [0x%lx,0x%lx) %luMB as one "
                            + "%luMB span; pool offsets [0x%lx,0x%lx) (%luMB, the main thread's stack) are never handed out",
                            Int(rxAddrV), Int(rxAddrV) + poolSize, poolSize >> 20,
                            Int(second.base), Int(second.base + second.size), Int(second.size >> 20),
                            (poolSize + Int(second.size)) >> 20, poolSize, holeEnd, (holeEnd - poolSize) >> 20),
                            level: .success)
                        } else {
                            LogStore.shared.log(midLayoutText(rxA: rxAddrV, sizeA: poolSize, second: second), level: .success)
                        }
                        lowReady(rwLow, low, rw)
                        LogStore.shared.log("JIT pool ready (debugger still attached).", level: .success)
                        poolTaken = true
                        return (rx: rxPtr, rw: rwPtr, size: span)
                    }
                    dropLowRegion("no RW alias for the split pool with region C")
                }
                // pool-mid: A, M and B in one RW reservation; without M (or if that
                // mapping fails, M then given back) the two-region alias as before
                var rwSplit: vm_address_t? = nil
                if let mid = poolMid {
                    rwSplit = mapLowAlias([(rx: rxAddrV, size: vm_address_t(poolSize)), (rx: mid.base, size: mid.size),
                                           (rx: second.base, size: second.size)], tag: "[pool-mid]")
                    if rwSplit == nil {
                        let dkr = vm_deallocate(mach_task_self_, mid.base, vm_size_t(mid.size))
                        poolMid = nil
                        LogStore.shared.log("[pool-split] pool-mid: no RW alias for three regions — third region released (kr=\(dkr))",
                                            level: .error)
                    }
                }
                if rwSplit == nil {
                    rwSplit = mapSplitAlias(rxA: rxAddrV, sizeA: vm_address_t(poolSize), rxB: second.base, sizeB: second.size)
                }
                if let rw = rwSplit {
                    let span = Int(second.base + second.size - rxAddrV)
                    let holeEnd = Int(second.base - rxAddrV)
                    let rwPtr = UnsafeMutableRawPointer(bitPattern: rw)!
                    LogStore.shared.log("ml977: RX=[\(String(format: "%p", Int(rxAddrV))),\(String(format: "%p", Int(rxAddrV) + span))) "
                        + "RW=[\(String(format: "%p", Int(rw))),\(String(format: "%p", Int(rw) + span))) "
                        + "offset=0x\(String(Int(rw) - Int(rxAddrV), radix: 16)) windowHeld=\(windowHeld) rwOverlap=false",
                        level: .success)
                    // one exemption request per region: they are separate VM objects
                    let exemptA = jit_make_region_no_footprint(rwPtr, poolSize, "pool-RW-alias")
                    let exemptB = jit_make_region_no_footprint(rwPtr + holeEnd, Int(second.size), "pool-RW-alias-2")
                    let exemptM = poolMid.map { jit_make_region_no_footprint(rwPtr + Int($0.base - rxAddrV), Int($0.size), "pool-RW-alias-mid") } ?? true
                    LogStore.shared.log("[no-footprint] pool applied=\(exemptA && exemptB && exemptM)", level: exemptA && exemptB && exemptM ? .success : .error)
                    splitHoles(aSize: poolSize, bOff: holeEnd, rxBase: rxAddrV)
                    if poolMid == nil {
                    LogStore.shared.log(String(format: "[pool-split] JIT pool = RX [0x%lx,0x%lx) %luMB + [0x%lx,0x%lx) %luMB as one "
                        + "%luMB span; pool offsets [0x%lx,0x%lx) (%luMB, the main thread's stack) are never handed out",
                        Int(rxAddrV), Int(rxAddrV) + poolSize, poolSize >> 20,
                        Int(second.base), Int(second.base + second.size), Int(second.size >> 20),
                        (poolSize + Int(second.size)) >> 20, poolSize, holeEnd, (holeEnd - poolSize) >> 20),
                        level: .success)
                    } else {
                        LogStore.shared.log(midLayoutText(rxA: rxAddrV, sizeA: poolSize, second: second), level: .success)
                    }
                    LogStore.shared.log("JIT pool ready (debugger still attached).", level: .success)
                    poolTaken = true
                    return (rx: rxPtr, rw: rwPtr, size: span)
                }
                let dkr = vm_deallocate(mach_task_self_, second.base, vm_size_t(second.size))
                LogStore.shared.log("[pool-split] no RW alias for the split pool — second region released (kr=\(dkr)); "
                    + "the pool stays \(poolSize >> 20)MB in one region", level: .error)
                if let mid = poolMid {   // pool-mid: the third region goes with it
                    _ = vm_deallocate(mach_task_self_, mid.base, vm_size_t(mid.size))
                    poolMid = nil
                }
            }
        }

        // madeira-bcd pool-low: C and the one-region pool in one RW reservation (C first)
        if let low = lowRegion {
            if let rwLow = mapLowAlias([(rx: low.base, size: low.size), (rx: rxAddrV, size: vm_address_t(poolSize))]) {
                let rw = rwLow + (rxAddrV - low.base)
                let rwPtr = UnsafeMutableRawPointer(bitPattern: rw)!
                LogStore.shared.log("ml977: RX=[\(String(format: "%p", Int(rxAddrV))),\(String(format: "%p", Int(rxAddrV) + poolSize))) "
                    + "RW=[\(String(format: "%p", Int(rw))),\(String(format: "%p", Int(rw) + poolSize))) "
                    + "offset=0x\(String(Int(rw) - Int(rxAddrV), radix: 16)) windowHeld=\(windowHeld) rwOverlap=false",
                    level: .success)
                let exempt = jit_make_region_no_footprint(rwPtr, poolSize, "pool-RW-alias")
                LogStore.shared.log("[no-footprint] pool applied=\(exempt)", level: exempt ? .success : .error)
                lowReady(rwLow, low, rw)
                LogStore.shared.log("JIT pool ready (debugger still attached).", level: .success)
                poolTaken = true
                return (rx: rxPtr, rw: rwPtr, size: poolSize)
            }
            dropLowRegion("no RW alias for the pool with region C")
        }
        // ml1037: the hint used to be 0x150000000 ("just above the window"), and
        // the alias duly took the 500MB hole there -- the very hole the RX pool
        // now needs. The alias has no placement requirement of its own (FEX
        // derives WriteOffset from the real distance), so send it high, where it
        // lived in every run before ml977, and keep the scarce low gap for RX.
        rwAddr = rwAliasHint()   // 0x7000000000, or 0x7900000000 for Social Club layout 2
        // Layout 2 maps the alias FIXED: an ANYWHERE hint at 0x7900000000 is not
        // honoured (build 338, 2026-10-02 19:33: it landed at 0x7100000000).
        let rwFixed = rwAddr == scLayout2Alias
        var kr1 = vm_remap(
            mach_task_self_,
            &rwAddr,
            vm_size_t(poolSize),
            0,
            rwFixed ? 0 /* VM_FLAGS_FIXED */ : VM_FLAGS_ANYWHERE,
            mach_task_self_,
            vm_address_t(bitPattern: rxPtr),
            0, // copy = false
            &curProt,
            &maxProt,
            VM_INHERIT_NONE
        )
        if rwFixed && kr1 != KERN_SUCCESS {
            rwAliasDrop(kr1)
            rwAddr = 0x7000000000
            kr1 = vm_remap(mach_task_self_, &rwAddr, vm_size_t(poolSize), 0, VM_FLAGS_ANYWHERE,
                           mach_task_self_, vm_address_t(bitPattern: rxPtr), 0, &curProt, &maxProt, VM_INHERIT_NONE)
        } else if kr1 == KERN_SUCCESS && !rwAliasKeep(rwAddr) {
            vm_deallocate(mach_task_self_, rwAddr, vm_size_t(poolSize))
            rwAddr = 0x7000000000
            kr1 = vm_remap(mach_task_self_, &rwAddr, vm_size_t(poolSize), 0, VM_FLAGS_ANYWHERE,
                           mach_task_self_, vm_address_t(bitPattern: rxPtr), 0, &curProt, &maxProt, VM_INHERIT_NONE)
        }

        // A process without the extended-virtual-addressing entitlement has a map
        // that ends at 0xfc0000000 (63 GB). The 0x7000000000 hint is past its end,
        // and an ANYWHERE search that starts past the end of the map does not
        // wrap: every alias failed with KERN_NO_SPACE although ~50 GB was free.
        // Upstream (ba3ab26) then retries once with no hint. The kernel's choice
        // is the LOWEST hole that fits: with a pool small enough for the hole
        // below the executable window, ml1040's plug there is released just
        // before this remap, so a hint-less alias would take [0x11e800000,..),
        // where Wine later maps sub-floor x64 images. So ask just above the RX
        // pool first (0x300000000 on the device's 2026-10-02 census), and only
        // then take the kernel's choice. On a 512 GB map the first request
        // (above: the high hint, or layout 2's fixed alias) succeeds as before.
        // Places the JIT pool's RW alias lower when the 0x7000000000 hint is past the end of the address map (63 GB maps): just above the RX pool, then where the kernel chooses; 0 fails at the hint as before.
        let aliasRetry = MadeiraConfig.flag("MADEIRA_RW_ALIAS_RETRY")
        if kr1 == KERN_NO_SPACE && aliasRetry {
            for hint in [rxAddrV + vm_address_t(poolSize), 0] {
                rwAddr = hint
                kr1 = vm_remap(
                    mach_task_self_,
                    &rwAddr,
                    vm_size_t(poolSize),
                    0,
                    VM_FLAGS_ANYWHERE,
                    mach_task_self_,
                    vm_address_t(bitPattern: rxPtr),
                    0, // copy = false
                    &curProt,
                    &maxProt,
                    VM_INHERIT_NONE
                )
                LogStore.shared.log(String(format: "[rw-alias] high hint out of reach; %@ kr=%d RW=0x%lx",
                                           hint == 0 ? "kernel placement" : String(format: "above the RX pool (hint 0x%lx)", Int(hint)),
                                           kr1, Int(rwAddr)), level: kr1 == KERN_SUCCESS ? .info : .error)
                if kr1 != KERN_NO_SPACE { break }
            }
        }

        guard kr1 == KERN_SUCCESS else {
            LogStore.shared.log("vm_remap failed: \(kr1)", level: .error)
            poolFailure = "Madeira could not map its JIT memory (vm_remap error \(kr1)). Restart Madeira and try again; "
                + "if it keeps happening, send the diagnostic log."
            return nil
        }

        let rwOverlaps = overlapsExeWindow(rwAddr, vm_address_t(poolSize))
        LogStore.shared.log("ml977: RX=[\(String(format:"%p",Int(rxAddrV))),"
            + "\(String(format:"%p",Int(rxAddrV + vm_address_t(poolSize))))) "
            + "RW=[\(String(format:"%p",Int(rwAddr))),"
            + "\(String(format:"%p",Int(rwAddr + vm_address_t(poolSize))))) "
            + "offset=0x\(String(Int(rwAddr) - Int(rxAddrV), radix: 16)) "
            + "windowHeld=\(windowHeld) rwOverlap=\(rwOverlaps)",
            level: rwOverlaps ? .error : .success)

        // Set RW protection
        let kr2 = vm_protect(mach_task_self_, rwAddr, vm_size_t(poolSize), 0, VM_PROT_READ | VM_PROT_WRITE)
        guard kr2 == KERN_SUCCESS else {
            LogStore.shared.log("vm_protect(RW) failed: \(kr2)", level: .error)
            vm_deallocate(mach_task_self_, rwAddr, vm_size_t(poolSize))
            poolFailure = "Madeira could not make its JIT memory writable (vm_protect error \(kr2)). Restart Madeira and try again; "
                + "if it keeps happening, send the diagnostic log."
            return nil
        }

        let rwPtr = UnsafeMutableRawPointer(bitPattern: rwAddr)!
        LogStore.shared.log("RW mapping at \(String(format: "%p", Int(bitPattern: rwPtr)))")

        // ml358: the pool has NEVER been jetsam-exempt. jit_region_create()
        // applies NO_FOOTPRINT, but this path takes its RX pages from the
        // debugger and vm_remaps the RW alias, so every written pool page has
        // counted against phys_footprint in full — which is what killed ml357
        // ("Terminated due to memory issue" with 848MB of pool written). Apply
        // the ledger exemption to the shared object now that both aliases
        // exist; the helper logs footprint either side, so the next log says
        // whether the kernel honoured it. Non-fatal if refused.
        // ml360: the entry must be made over the RW ALIAS, not the RX view —
        // ml360's run showed mach_make_memory_entry_64(READ|WRITE) over the
        // debugger's RX pages fails with KERN_PROTECTION_FAILURE. Same vm
        // object either way; the RW alias actually permits the access.
        let exempt = jit_make_region_no_footprint(rwPtr, poolSize, "pool-RW-alias")
        // ml359: log the verdict through LogStore.log (which appends to the
        // file) — the ml358 run lost it because the jit_log callback only fed
        // the UI view. Detail (kr / footprint delta) is in the jit_log lines.
        LogStore.shared.log("[no-footprint] pool applied=\(exempt)", level: exempt ? .success : .error)

        LogStore.shared.log("JIT pool ready (debugger still attached).", level: .success)
        poolTaken = true

        return (rx: rxPtr, rw: rwPtr, size: poolSize)
    }

    /// Default requests retain the 16MB rounding. The page-fit opt-in never
    /// rounds a request up; A/B stay within their budget and C keeps its margin.
    private static func poolRunSize(available: vm_address_t, wanted: vm_address_t,
                                    pageFit: Bool) -> vm_address_t {
        let granule: vm_address_t = pageFit ? 0x4000 : 16 << 20
        let request: vm_address_t
        if pageFit {
            request = wanted & ~(granule - 1)
        } else {
            guard wanted <= vm_address_t.max - (granule - 1) else { return 0 }
            request = (wanted + granule - 1) & ~(granule - 1)
        }
        return min(available & ~(granule - 1), request)
    }

    /// madeira-bcd split pool: the free runs of at least `minSize` in [lo, hi).
    private static func freeRuns(_ lo: vm_address_t, _ hi: vm_address_t,
                                 minSize: vm_address_t) -> [(base: vm_address_t, size: vm_address_t)] {
        var runs: [(base: vm_address_t, size: vm_address_t)] = []
        var prevEnd = lo
        while prevEnd < hi {
            var addr = prevEnd
            var rsize: vm_size_t = 0
            var info = vm_region_basic_info_data_64_t()
            var cnt = mach_msg_type_number_t(MemoryLayout<vm_region_basic_info_data_64_t>.size / MemoryLayout<Int32>.size)
            var obj: mach_port_t = 0
            let kr = withUnsafeMutablePointer(to: &info) {
                $0.withMemoryRebound(to: Int32.self, capacity: Int(cnt)) {
                    vm_region_64(mach_task_self_, &addr, &rsize, VM_REGION_BASIC_INFO_64, $0, &cnt, &obj)
                }
            }
            let start = kr == KERN_SUCCESS ? min(addr, hi) : hi
            if start > prevEnd && start - prevEnd >= minSize { runs.append((prevEnd, start - prevEnd)) }
            if kr != KERN_SUCCESS || addr >= hi || rsize == 0 { break }
            prevEnd = max(prevEnd, addr + vm_address_t(rsize))
        }
        return runs
    }

    /// madeira-bcd split pool: the pool offsets ntdll never hands out, from region A's
    /// size and region B's offset. One hole [A's end, B); with pool-mid's region M the
    /// part below M becomes poolHole and the part above it poolHole2 (an empty part is
    /// no hole: then the other one is poolHole alone).
    private static func splitHoles(aSize: Int, bOff: Int, rxBase: vm_address_t) {
        poolHole2 = nil
        guard let mid = poolMid else {
            poolHole = bOff > aSize ? (off: aSize, end: bOff) : nil
            return
        }
        let mOff = Int(mid.base - rxBase)
        let mEnd = mOff + Int(mid.size)
        let below: (off: Int, end: Int)? = mOff > aSize ? (off: aSize, end: mOff) : nil
        let above: (off: Int, end: Int)? = bOff > mEnd ? (off: mEnd, end: bOff) : nil
        poolHole = below ?? above
        poolHole2 = below == nil ? nil : above
    }

    /// madeira-bcd pool-mid: the "[pool-split] JIT pool = ..." line for three regions.
    private static func midLayoutText(rxA: vm_address_t, sizeA: Int,
                                      second: (base: vm_address_t, size: vm_address_t)) -> String {
        var text = String(format: "[pool-split] JIT pool = RX [0x%lx,0x%lx) %luMB", Int(rxA), Int(rxA) + sizeA, sizeA >> 20)
        var total = sizeA + Int(second.size)
        if let mid = poolMid {
            text += String(format: " + [0x%lx,0x%lx) %luMB (pool-mid)", Int(mid.base), Int(mid.base + mid.size), Int(mid.size >> 20))
            total += Int(mid.size)
        }
        text += String(format: " + [0x%lx,0x%lx) %luMB as one %luMB span; pool offsets", Int(second.base),
                       Int(second.base + second.size), Int(second.size >> 20), total >> 20)
        if let h = poolHole {
            text += String(format: " [0x%lx,0x%lx) (%luMB, the mapping below the third region)", h.off, h.end, (h.end - h.off) >> 20)
        }
        if let h = poolHole2 {
            text += String(format: " and [0x%lx,0x%lx) (%luMB, the main thread's stack)", h.off, h.end, (h.end - h.off) >> 20)
        }
        return text + " are never handed out"
    }

    /// madeira-bcd split pool: the second debugger region. It is the largest free
    /// run between the first region and the dyld shared region (0x180000000), at
    /// most `want` (rounded up to 16MB by default, down to 16KB with page-fit)
    /// and at least 64MB. The debugger allocates
    /// first-fit, so every lower run that could take it is plugged for the request,
    /// as ml1040 does for the first region. The part between the two regions (the
    /// main thread's stack) gets PROT_NONE placeholders in its free gaps, so
    /// nothing else lands inside the pool's span. Returns nil, holding nothing,
    /// when no run qualifies or the region landed anywhere else.
    private static func takeSecondRegion(above aEnd: vm_address_t, want: Int, pageFit: Bool,
                                         exeWindow: (base: vm_address_t, size: vm_address_t))
        -> (base: vm_address_t, size: vm_address_t)? {
        guard want > 0 else { return nil }
        let ceiling: vm_address_t = 0x180000000           // SHARED_REGION_BASE_ARM64
        let runs = freeRuns(aEnd, ceiling, minSize: 64 << 20)
        let desc = runs.map { String(format: "0x%lx+%luMB", Int($0.base), Int($0.size >> 20)) }.joined(separator: " ")
        guard let best = runs.max(by: { $0.size < $1.size }) else {
            LogStore.shared.log("[pool-split] no free run of 64MB or more between the pool and 0x180000000 — the pool stays "
                + "one region", level: .error)
            return nil
        }
        let size = poolRunSize(available: best.size, wanted: vm_address_t(want), pageFit: pageFit)
        // The part between the regions must never hold the executable window:
        // the fixed-base main image would then sit inside the pool's span.
        let gapHitsWindow = aEnd < exeWindow.base + exeWindow.size && best.base > exeWindow.base
        guard size >= 64 << 20, !gapHitsWindow else {
            LogStore.shared.log("[pool-split] free runs above the pool: \(desc) — "
                + (gapHitsWindow ? "the gap would hold the executable window" : "none fits 64MB")
                + "; the pool stays one region", level: .error)
            return nil
        }
        var plugs: [(vm_address_t, vm_size_t)] = []
        for h in freeRuns(0x100000000, best.base, minSize: size) {
            var a = h.base
            if vm_allocate(mach_task_self_, &a, vm_size_t(h.size), 0 /* VM_FLAGS_FIXED */) == KERN_SUCCESS {
                if a == h.base { plugs.append((a, vm_size_t(h.size))) } else { vm_deallocate(mach_task_self_, a, vm_size_t(h.size)) }
            }
        }
        let got = jit26_prepare_region(nil, Int(size))
        for (a, sz) in plugs { vm_deallocate(mach_task_self_, a, sz) }
        guard let p = got, p != UnsafeMutableRawPointer(bitPattern: 0) else {
            LogStore.shared.log("[pool-split] the debugger did not allocate the second region (\(size >> 20)MB) — the pool "
                + "stays one region", level: .error)
            return nil
        }
        let b = vm_address_t(bitPattern: p)
        if b < aEnd || b + size > ceiling || (aEnd < exeWindow.base + exeWindow.size && b > exeWindow.base) {
            let dkr = vm_deallocate(mach_task_self_, b, vm_size_t(size))
            LogStore.shared.log(String(format: "[pool-split] the second region landed at 0x%lx, not in the run at 0x%lx — "
                + "released (kr=%d); the pool stays one region", Int(b), Int(best.base), dkr), level: .error)
            return nil
        }
        // madeira-bcd pool-mid: the largest free run between the regions, when the
        // budget leaves 64MB for it, as a third debugger region M (see poolHole2).
        // Placed first-fit like B, every lower run that could take it plugged.
        poolMid = nil
        let midText = (MadeiraConfig.gameValue("pool-mid") ?? MadeiraConfig.get("pool-mid") ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let midBudget = want - Int(size)
        if ["1", "on", "true", "yes"].contains(midText) && midBudget >= 64 << 20,
           let run = freeRuns(aEnd, b, minSize: 64 << 20).max(by: { $0.size < $1.size }) {
            let msize = poolRunSize(available: run.size, wanted: vm_address_t(midBudget), pageFit: pageFit)
            if msize >= 64 << 20 {
                var mplugs: [(vm_address_t, vm_size_t)] = []
                for h in freeRuns(0x100000000, run.base, minSize: msize) {
                    var a = h.base
                    if vm_allocate(mach_task_self_, &a, vm_size_t(h.size), 0 /* VM_FLAGS_FIXED */) == KERN_SUCCESS {
                        if a == h.base { mplugs.append((a, vm_size_t(h.size))) } else { vm_deallocate(mach_task_self_, a, vm_size_t(h.size)) }
                    }
                }
                let mgot = jit26_prepare_region(nil, Int(msize))
                for (a, sz) in mplugs { vm_deallocate(mach_task_self_, a, sz) }
                if let mp = mgot, mp != UnsafeMutableRawPointer(bitPattern: 0) {
                    let m = vm_address_t(bitPattern: mp)
                    if m >= run.base && m + msize <= run.base + run.size {
                        poolMid = (base: m, size: msize)
                        LogStore.shared.log(String(format: "[pool-split] pool-mid: third debugger region 0x%lx+%luMB in the free run "
                            + "0x%lx+%luMB between the regions (pool-mid = 1)",
                            Int(m), Int(msize >> 20), Int(run.base), Int(run.size >> 20)), level: .success)
                    } else {
                        let dkr = vm_deallocate(mach_task_self_, m, vm_size_t(msize))
                        LogStore.shared.log(String(format: "[pool-split] pool-mid: the third region landed at 0x%lx, not in the run "
                            + "at 0x%lx — released (kr=%d)", Int(m), Int(run.base), dkr), level: .error)
                    }
                } else {
                    LogStore.shared.log("[pool-split] pool-mid: the debugger did not allocate the third region (\(msize >> 20)MB)",
                                        level: .error)
                }
            }
        }
        // PROT_NONE placeholders over the free gaps between the regions.
        var held = 0
        for g in freeRuns(aEnd, b, minSize: 0x4000) {
            var a = g.base
            if vm_allocate(mach_task_self_, &a, vm_size_t(g.size), 0 /* VM_FLAGS_FIXED */) == KERN_SUCCESS {
                if a == g.base {
                    _ = vm_protect(mach_task_self_, a, vm_size_t(g.size), 1, VM_PROT_NONE)
                    held += Int(g.size)
                } else { vm_deallocate(mach_task_self_, a, vm_size_t(g.size)) }
            }
        }
        LogStore.shared.log(String(format: "[pool-split] second debugger region 0x%lx+%luMB (free runs above the pool: %@); "
            + "between the regions: %luKB, %luKB of it free and now held PROT_NONE",
            Int(b), Int(size >> 20), desc, Int(b - aEnd) >> 10, held >> 10))
        return (b, size)
    }

    /// madeira-bcd pool-low: region C, the third debugger region. It is a free run in
    /// [0x119000000, the executable window) less `pool-low-margin` MB (128 by default)
    /// left free at the run's bottom, where Wine maps the children's relocatable main
    /// exes (PlayGTAV.exe 0x122c20000, Launcher.exe 0x129340000, RockstarService.exe
    /// 0x12ac20000 in the GTA V logs), in 16MB steps by default or 16KB with page-fit,
    /// and at least 64MB; it takes the run's TOP, next to the window. A run with a
    /// free run of the margin's size below it keeps no margin of its own: the children
    /// load bottom-up and find that run first (build 437: 134 + 184 MB, Launcher.exe at
    /// the bottom of the 134 MB run; with the margin counted inside each run neither
    /// qualified, the code buffers went to the pool tail and the image copies ran out).
    /// Of the runs, the one that leaves the largest C is taken. The debugger allocates
    /// first-fit, so the margin and every lower run that could take C are plugged for
    /// the request, as takeSecondRegion does. Only when the pool lies above the
    /// window: C must never be inside the pool's span. Returns nil, holding nothing,
    /// when no run qualifies or the region landed anywhere else.
    private static func takeLowRegion(poolRx: vm_address_t,
                                      exeWindow: (base: vm_address_t, size: vm_address_t),
                                      pageFit: Bool)
        -> (base: vm_address_t, size: vm_address_t)? {
        let lowFloor: vm_address_t = 0x119000000            // the pool's own low bound (mode A, see above)
        let marginText = (MadeiraConfig.gameValue("pool-low-margin") ?? MadeiraConfig.get("pool-low-margin") ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        let marginMB = max(0, min(Int(marginText) ?? 128, 4096))
        let margin = vm_address_t(marginMB) << 20
        guard poolRx >= exeWindow.base + exeWindow.size else {
            LogStore.shared.log(String(format: "[pool-low] the pool starts at 0x%lx, not above the executable window -- "
                + "no region C (the free run below the window is the pool's own)", Int(poolRx)), level: .error)
            return nil
        }
        let runs = freeRuns(lowFloor, exeWindow.base, minSize: 64 << 20)
        let desc = runs.map { String(format: "0x%lx+%luMB", Int($0.base), Int($0.size >> 20)) }.joined(separator: " ")
        // The margin a run keeps at its bottom: none when a lower run alone holds it.
        let ownMargin = { (r: (base: vm_address_t, size: vm_address_t)) -> vm_address_t in
            runs.contains(where: { $0.base < r.base && $0.size >= margin }) ? 0 : margin
        }
        let fits = runs.map { r -> (run: (base: vm_address_t, size: vm_address_t), keep: vm_address_t, size: vm_address_t) in
            let keep = ownMargin(r)
            let available = r.size > keep ? r.size - keep : 0
            return (r, keep, poolRunSize(available: available, wanted: available, pageFit: pageFit))
        }
        let pick = fits.max(by: { $0.size < $1.size })
        let best = pick?.run
        let size = pick?.size ?? 0
        guard let best = best, size >= 64 << 20 else {
            LogStore.shared.log("[pool-low] free runs below the window: \(desc.isEmpty ? "none of 64MB" : desc) -- none "
                + "leaves 64MB after the \(marginMB)MB margin (pool-low-margin); no region C", level: .error)
            return nil
        }
        let target = best.base + best.size - size        // the run's top; the margin stays at its bottom
        var plugs: [(vm_address_t, vm_size_t)] = []
        var plugRuns = freeRuns(0x100000000, best.base, minSize: size)
        if target > best.base { plugRuns.append((base: best.base, size: target - best.base)) }
        for h in plugRuns {
            var a = h.base
            if vm_allocate(mach_task_self_, &a, vm_size_t(h.size), 0 /* VM_FLAGS_FIXED */) == KERN_SUCCESS {
                if a == h.base { plugs.append((a, vm_size_t(h.size))) } else { vm_deallocate(mach_task_self_, a, vm_size_t(h.size)) }
            }
        }
        let got = jit26_prepare_region(nil, Int(size))
        for (a, sz) in plugs { vm_deallocate(mach_task_self_, a, sz) }
        guard let p = got, p != UnsafeMutableRawPointer(bitPattern: 0) else {
            LogStore.shared.log("[pool-low] the debugger did not allocate region C (\(size >> 20)MB) -- code buffers stay "
                + "in the pool", level: .error)
            return nil
        }
        let c = vm_address_t(bitPattern: p)
        if c < lowFloor || c + size > exeWindow.base || c + size > poolRx {
            let dkr = vm_deallocate(mach_task_self_, c, vm_size_t(size))
            LogStore.shared.log(String(format: "[pool-low] region C landed at 0x%lx, not below the window in the run at 0x%lx -- "
                + "released (kr=%d); code buffers stay in the pool", Int(c), Int(best.base), dkr), level: .error)
            return nil
        }
        LogStore.shared.log(String(format: "[pool-low] region C 0x%lx+%luMB (free runs below the window: %@; %luMB of the "
            + "run left free for the low images, pool-low-margin = %ld%@)%@",
            Int(c), Int(size >> 20), desc, Int((best.size - size) >> 20), marginMB,
            (pick?.keep == 0 && margin > 0 ? ", held by a lower run" : "") as String,
            c == target ? "" : String(format: " -- not at the run's top 0x%lx, a plug failed", Int(target))))
        if pageFit {
            LogStore.shared.log("[pool-low] page-fit C=\(size >> 10)KB; run remainder=\((best.size - size) >> 10)KB, pool-low-margin=\(margin >> 10)KB")
        }
        return (c, size)
    }

    /// madeira-bcd pool-low: ONE RW reservation from region C's RX base to the pool's
    /// end, each region aliased at its own RX offset in it, so C and the pool share
    /// the pool's RX->RW distance (FEX has one DualMap::WriteOffset for every code
    /// buffer). `regions` ascend by RX address, C first; the parts between them (the
    /// executable window, the main thread's stack) stay reserved PROT_NONE. Placement
    /// as mapSplitAlias: 0x7000000000 ANYWHERE, or FIXED at 0x7900000000 for Social
    /// Club layout 2 (the reservation then starts there; ntdll reads its base from C).
    /// Returns the reservation's base, or nil with nothing left mapped.
    private static func mapLowAlias(_ regions: [(rx: vm_address_t, size: vm_address_t)],
                                    tag: String = "[pool-low]") -> vm_address_t? {
        guard let first = regions.first, let last = regions.last, regions.count >= 2 else { return nil }
        let span = last.rx + last.size - first.rx
        var rw: vm_address_t = rwAliasHint()
        let rwFixed = rw == scLayout2Alias
        var kr = vm_allocate(mach_task_self_, &rw, vm_size_t(span), rwFixed ? 0 /* VM_FLAGS_FIXED */ : VM_FLAGS_ANYWHERE)
        if rwFixed && kr != KERN_SUCCESS {
            rwAliasDrop(kr)
            rw = 0x7000000000
            kr = vm_allocate(mach_task_self_, &rw, vm_size_t(span), VM_FLAGS_ANYWHERE)
        } else if kr == KERN_SUCCESS && !rwAliasKeep(rw) {
            vm_deallocate(mach_task_self_, rw, vm_size_t(span))
            rw = 0x7000000000
            kr = vm_allocate(mach_task_self_, &rw, vm_size_t(span), VM_FLAGS_ANYWHERE)
        }
        if kr == KERN_NO_SPACE && MadeiraConfig.flag("MADEIRA_RW_ALIAS_RETRY") {
            rw = 0
            kr = vm_allocate(mach_task_self_, &rw, vm_size_t(span), VM_FLAGS_ANYWHERE)
        }
        guard kr == KERN_SUCCESS else {
            LogStore.shared.log("\(tag) could not reserve \(span >> 20)MB for the RW alias (kr=\(kr))", level: .error)
            return nil
        }
        var curProt: vm_prot_t = 0
        var maxProt: vm_prot_t = 0
        var failed: String? = nil
        for r in regions {
            let want = rw + (r.rx - first.rx)
            var a = want
            let krMap = vm_remap(mach_task_self_, &a, vm_size_t(r.size), 0, 0 /* VM_FLAGS_FIXED */ | VM_FLAGS_OVERWRITE,
                                 mach_task_self_, r.rx, 0, &curProt, &maxProt, VM_INHERIT_NONE)
            let krRW = krMap == KERN_SUCCESS
                ? vm_protect(mach_task_self_, a, vm_size_t(r.size), 0, VM_PROT_READ | VM_PROT_WRITE)
                : krMap
            if krMap != KERN_SUCCESS || krRW != KERN_SUCCESS || a != want {
                failed = String(format: "region 0x%lx+%luMB: remap %d, protect %d, at 0x%lx not 0x%lx",
                                Int(r.rx), Int(r.size >> 20), krMap, krRW, Int(a), Int(want))
                break
            }
        }
        if let why = failed {
            vm_deallocate(mach_task_self_, rw, vm_size_t(span))
            LogStore.shared.log(String(format: "%@ RW alias at 0x%lx failed (%@)", tag, Int(rw), why), level: .error)
            return nil
        }
        // the parts between the regions are not pool memory: reserved, never accessible
        for i in 1..<regions.count {
            let gapLo = regions[i - 1].rx + regions[i - 1].size
            if regions[i].rx > gapLo {
                _ = vm_protect(mach_task_self_, rw + (gapLo - first.rx), vm_size_t(regions[i].rx - gapLo), 1, VM_PROT_NONE)
            }
        }
        return rw
    }

    /// madeira-bcd split pool: ONE RW alias for both regions at the same RX->RW
    /// distance, so the pool is a single span for ntdll and FEX. The alias of the
    /// part between them stays reserved and PROT_NONE. Returns the alias base, or
    /// nil with nothing left mapped.
    private static func mapSplitAlias(rxA: vm_address_t, sizeA: vm_address_t,
                                      rxB: vm_address_t, sizeB: vm_address_t) -> vm_address_t? {
        let span = rxB + sizeB - rxA
        // ml1037: the alias goes high, where it always lived (0x7000000000);
        // 0x7900000000 for Social Club layout 2 (rwAliasHint).
        var rw: vm_address_t = rwAliasHint()
        // Layout 2: FIXED at 0x7900000000 (an ANYWHERE hint there is not honoured).
        let rwFixed = rw == scLayout2Alias
        var kr = vm_allocate(mach_task_self_, &rw, vm_size_t(span), rwFixed ? 0 /* VM_FLAGS_FIXED */ : VM_FLAGS_ANYWHERE)
        if rwFixed && kr != KERN_SUCCESS {
            rwAliasDrop(kr)
            rw = 0x7000000000
            kr = vm_allocate(mach_task_self_, &rw, vm_size_t(span), VM_FLAGS_ANYWHERE)
        } else if kr == KERN_SUCCESS && !rwAliasKeep(rw) {
            vm_deallocate(mach_task_self_, rw, vm_size_t(span))
            rw = 0x7000000000
            kr = vm_allocate(mach_task_self_, &rw, vm_size_t(span), VM_FLAGS_ANYWHERE)
        }
        if kr == KERN_NO_SPACE && MadeiraConfig.flag("MADEIRA_RW_ALIAS_RETRY") {
            rw = 0
            kr = vm_allocate(mach_task_self_, &rw, vm_size_t(span), VM_FLAGS_ANYWHERE)
        }
        guard kr == KERN_SUCCESS else {
            LogStore.shared.log("[pool-split] could not reserve \(span >> 20)MB for the RW alias (kr=\(kr))", level: .error)
            return nil
        }
        var curProt: vm_prot_t = 0
        var maxProt: vm_prot_t = 0
        var a = rw
        let krA = vm_remap(mach_task_self_, &a, vm_size_t(sizeA), 0, 0 /* VM_FLAGS_FIXED */ | VM_FLAGS_OVERWRITE,
                           mach_task_self_, rxA, 0, &curProt, &maxProt, VM_INHERIT_NONE)
        var b = rw + (rxB - rxA)
        let krB = krA == KERN_SUCCESS
            ? vm_remap(mach_task_self_, &b, vm_size_t(sizeB), 0, 0 /* VM_FLAGS_FIXED */ | VM_FLAGS_OVERWRITE,
                       mach_task_self_, rxB, 0, &curProt, &maxProt, VM_INHERIT_NONE)
            : krA
        let krHole = vm_protect(mach_task_self_, rw + sizeA, vm_size_t(rxB - rxA - sizeA), 1, VM_PROT_NONE)
        let krRW = krB == KERN_SUCCESS
            ? max(vm_protect(mach_task_self_, rw, vm_size_t(sizeA), 0, VM_PROT_READ | VM_PROT_WRITE),
                  vm_protect(mach_task_self_, b, vm_size_t(sizeB), 0, VM_PROT_READ | VM_PROT_WRITE))
            : krB
        guard krA == KERN_SUCCESS, krB == KERN_SUCCESS, krRW == KERN_SUCCESS, a == rw, b == rw + (rxB - rxA) else {
            vm_deallocate(mach_task_self_, rw, vm_size_t(span))
            LogStore.shared.log(String(format: "[pool-split] RW alias at 0x%lx failed (remap %d/%d, protect %d, hole %d)",
                                       Int(rw), krA, krB, krRW, krHole), level: .error)
            return nil
        }
        return rw
    }

    /// Detach the debugger. Call this after Wine is done loading PE DLLs.
    static func detachDebugger() {
        LogStore.shared.log("Detaching debugger...")
        jit26_detach()
        // task #34: signal in-process waiters (share-probe poller). CS_DEBUGGED
        // is sticky post-detach, so an env flag is the reliable signal.
        setenv("MADEIRA_DETACHED", "1", 1)
        LogStore.shared.log("Debugger detached.", level: .success)
    }
}
