#!/usr/bin/env python3
"""ml1098: convert Madeira frame-capture raw files to PNG.

Pull the capture directory from the phone first:
  xcrun devicectl device copy from --device <UDID> --source Documents/capture \\
      --destination /tmp/capture --domain-type appDataContainer --domain-identifier com.willfaust.madeora

Then:  python3 build/tools/capture-to-png.py /tmp/capture [outdir]

File names: f<frame>_e<enc>_<kind><idx>_<W>x<H>_pf<metal pixel format>_dx<dxgi format>_<name>.raw
The encoder number matches the "enc#" of the draw-dump lines in the log for the
same frame, so each image is "what that pass left in that attachment".
"""
import os, re, sys, struct
import numpy as np
from PIL import Image

NAME = re.compile(r"f(\d+)_e(\d+)_([a-z]+)(\d+)_(\d+)x(\d+)_pf(\d+)_dx(\d+)_(.*)\.raw$")

# Metal pixel formats we expect from a D3D12 title's attachments (WMTPixelFormat numbering).
FORMATS = {
    10: ("R8Unorm", 1, "u8"), 13: ("R8Uint", 1, "u8"), 20: ("R16Unorm", 2, "u16"), 23: ("R16Uint", 2, "u16"), 25: ("R16Float", 2, "f16"),
    30: ("RG8Unorm", 2, "u8"), 53: ("R32Float", 4, "f32"), 53+0: ("R32Float", 4, "f32"), 60: ("RG16Unorm", 4, "u16"), 65: ("RG16Float", 4, "f16"),
    70: ("RGBA8Unorm", 4, "u8"), 71: ("RGBA8Unorm_sRGB", 4, "u8"), 80: ("BGRA8Unorm", 4, "bgra8"), 81: ("BGRA8Unorm_sRGB", 4, "bgra8"),
    90: ("RGB10A2Unorm", 4, "rgb10a2"), 92: ("RG11B10Float", 4, "rg11b10"), 93: ("RGB9E5Float", 4, "rgb9e5"),
    105: ("RG32Float", 8, "f32"), 110: ("RGBA16Unorm", 8, "u16"), 115: ("RGBA16Float", 8, "f16"), 125: ("RGBA32Float", 16, "f32"),
    252: ("Depth32Float", 4, "depth"), 260: ("Depth32Float_Stencil8", 4, "depth"), 253: ("Stencil8", 1, "stencil"), 250: ("Depth16Unorm", 2, "u16"),
}

def tonemap(x):
    x = np.nan_to_num(x.astype(np.float32), nan=0.0, posinf=1e4, neginf=0.0)
    x = np.clip(x, 0, None)
    return (x / (1.0 + x)) ** (1 / 2.2)

# ml1141: block-compressed SAMPLED textures (capture-cs / capture-ps inputs),
# decoded by build/tools/bc-decode.m on the Mac's GPU.
BC_FORMATS = {130: "BC1", 131: "BC1_sRGB", 132: "BC2", 133: "BC2_sRGB", 134: "BC3", 135: "BC3_sRGB",
              140: "BC4_R", 141: "BC4_Rsnorm", 142: "BC5_RG", 143: "BC5_RGsnorm",
              150: "BC6H_signed", 151: "BC6H", 152: "BC7", 153: "BC7_sRGB"}

def bc_decode(raw, w, h, pf):
    import subprocess, tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    tool = os.path.join(tempfile.gettempdir(), "madeira-bc-decode")
    src = os.path.join(here, "bc-decode.m")
    if not os.path.exists(tool) or os.path.getmtime(tool) < os.path.getmtime(src):
        subprocess.check_call(["clang", "-O1", "-fobjc-arc", "-framework", "Metal", "-framework", "Foundation", "-o", tool, src])
    with tempfile.TemporaryDirectory() as td:
        i, o = os.path.join(td, "in.raw"), os.path.join(td, "out.f32")
        open(i, "wb").write(raw)
        subprocess.check_call([tool, i, str(w), str(h), str(pf), o])
        v = np.fromfile(o, dtype=np.float32).reshape(h, w, 4)
    name = BC_FORMATS[pf]
    if pf in (141, 143): v = v * 0.5 + 0.5                      # snorm -> displayable
    if pf in (140, 141): img = np.repeat(v[:, :, :1], 3, axis=2)
    elif pf in (142, 143): img = np.stack([v[:, :, 0], v[:, :, 1], np.full((h, w), 1.0, np.float32)], axis=2)   # normal map XY
    elif pf in (150, 151): return name, (tonemap(v[:, :, :3]) * 255).astype(np.uint8)
    else: img = v[:, :, :3]
    return name, (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)

def decode(raw, w, h, pf):
    if pf in BC_FORMATS: return bc_decode(raw, w, h, pf)
    name, bpp, kind = FORMATS.get(pf, (None, None, None))
    if name is None:
        # unknown: guess from bytes per pixel
        bpp = len(raw) // (w * h)
        kind = {1: "u8", 2: "u16", 4: "u8", 8: "f16", 16: "f32"}.get(bpp, "u8")
        name = "pf%d(guess bpp %d)" % (pf, bpp)
    if kind == "depth" and len(raw) == w * h * 2: bpp = 2
    a = np.frombuffer(raw, dtype=np.uint8)[: w * h * bpp].reshape(h, w, bpp)
    if kind == "u8":
        img = a[:, :, :3] if bpp >= 3 else np.repeat(a[:, :, :1], 3, axis=2)
        return name, img
    if kind == "bgra8":
        return name, a[:, :, [2, 1, 0]]
    if kind == "u16":
        v = a.view(np.uint16).reshape(h, w, bpp // 2)
        img = (v[:, :, :3] if v.shape[2] >= 3 else np.repeat(v[:, :, :1], 3, axis=2)) >> 8
        return name, img.astype(np.uint8)
    if kind == "f16":
        v = a.view(np.float16).reshape(h, w, bpp // 2).astype(np.float32)
        img = v[:, :, :3] if v.shape[2] >= 3 else np.repeat(v[:, :, :1], 3, axis=2)
        return name, (tonemap(img) * 255).astype(np.uint8)
    if kind == "f32" and name != "Depth32Float":
        v = a.view(np.float32).reshape(h, w, bpp // 4)
        img = v[:, :, :3] if v.shape[2] >= 3 else np.repeat(v[:, :, :1], 3, axis=2)
        return name, (tonemap(img) * 255).astype(np.uint8)
    if kind == "depth":
        if bpp == 2:   # a 16-bit depth target (Depth16Unorm) was written with 2 bytes/pixel
            d = a.view(np.uint16).reshape(h, w).astype(np.float32) / 65535.0
        else:
            d = a.view(np.float32).reshape(h, w)
        d = np.nan_to_num(d, nan=1.0)
        # reverse-Z friendly: stretch whatever range is present
        lo, hi = np.percentile(d, 1), np.percentile(d, 99)
        n = np.clip((d - lo) / max(hi - lo, 1e-9), 0, 1)
        return name + " (1..99 pct stretch %.5f..%.5f)" % (lo, hi), np.repeat((n * 255).astype(np.uint8)[:, :, None], 3, axis=2)
    if kind == "stencil":
        s = a.reshape(h, w)
        return name, np.repeat(((s != 0) * 255).astype(np.uint8)[:, :, None], 3, axis=2)
    if kind == "rgb10a2":
        v = a.view(np.uint32).reshape(h, w)
        r, g, b = (v & 1023) >> 2, ((v >> 10) & 1023) >> 2, ((v >> 20) & 1023) >> 2
        return name, np.stack([r, g, b], axis=2).astype(np.uint8)
    if kind == "rg11b10":
        v = a.view(np.uint32).reshape(h, w)
        def f11(x):  # 5-bit exponent, 6-bit mantissa
            e = ((x >> 6) & 31).astype(np.float32); m = (x & 63).astype(np.float32)
            return np.where(e == 0, m / 64 * 2.0 ** -14, (1 + m / 64) * 2.0 ** (e - 15))
        def f10(x):
            e = ((x >> 5) & 31).astype(np.float32); m = (x & 31).astype(np.float32)
            return np.where(e == 0, m / 32 * 2.0 ** -14, (1 + m / 32) * 2.0 ** (e - 15))
        img = np.stack([f11(v & 2047), f11((v >> 11) & 2047), f10((v >> 22) & 1023)], axis=2)
        return name, (tonemap(img) * 255).astype(np.uint8)
    if kind == "rgb9e5":
        v = a.view(np.uint32).reshape(h, w)
        e = ((v >> 27) & 31).astype(np.float32)
        s = 2.0 ** (e - 15 - 9)
        img = np.stack([(v & 511) * s, ((v >> 9) & 511) * s, ((v >> 18) & 511) * s], axis=2)
        return name, (tonemap(img) * 255).astype(np.uint8)
    return name, a[:, :, :3]

def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(src, "png")
    os.makedirs(out, exist_ok=True)
    files = sorted(f for f in os.listdir(src) if f.endswith(".raw"))
    index = []
    for f in files:
        m = NAME.match(f)
        if not m:
            print("skip", f); continue
        frame, enc, kind, idx, w, h, pf, dx, name = m.groups()
        w, h, pf = int(w), int(h), int(pf)
        if kind in ("vb", "ib", "iargs"):
            index.append((int(frame), int(enc), kind, int(idx), w, h, "raw bytes", dx, name, f)); continue
        raw = open(os.path.join(src, f), "rb").read()
        try:
            fmt, img = decode(raw, w, h, pf)
        except Exception as ex:
            print("FAILED", f, ex); continue
        png = f[:-4] + ".png"
        Image.fromarray(np.ascontiguousarray(img)).save(os.path.join(out, png))
        index.append((int(frame), int(enc), kind, int(idx), w, h, fmt, dx, name, png))
    with open(os.path.join(out, "index.txt"), "w") as fh:
        for row in sorted(index):
            fh.write("frame %d enc#%05d %s%d %dx%d %s dxgi=%s %s -> %s\n" % row)
    print("wrote %d images to %s (index.txt lists them in pass order)" % (len(index), out))

if __name__ == "__main__":
    main()
