/* ml1149: AMD AGS shader-intrinsic 64-bit atomics -> native SM6.6 64-bit atomics.
 *
 * D3D12 titles written before shader model 6.6 reached 64-bit atomics through
 * vendor extensions. AMD's (AGS) form is a sequence of 32-bit
 * InterlockedCompareExchange calls on a "magic" RWByteAddressBuffer in register
 * space 0x7FFF0ADE: the byte offset of each call is an encoded instruction, and
 * the compare/value operands carry the arguments. The driver pattern-matches the
 * sequence into one hardware 64-bit atomic. For a 2D/3D texture target
 * (ags_shader_intrinsics_dx12.hlsl, AmdExtD3DShaderIntrinsics_AtomicOp):
 *
 *   ret.x = magic.CmpXchg(instr phase 0, address.x, address.y)
 *   ret.y = magic.CmpXchg(instr phase 1, address.z, value.lo)
 *   uav[ret.x, ret.x(, ret.x)] = ret.y          <- names the target resource
 *   ret.y = magic.CmpXchg(instr phase 2, value.hi, ret.y)
 *   return ret                                  <- original 64-bit value
 *
 * Apple's converter knows none of this: it refuses such a shader outright (the
 * magic space is in no root signature), and even with it bound the sequence
 * would only scribble on a scratch buffer. This pass rewrites the DXIL module
 * itself (LLVM 15 reads DXIL bitcode and its writer's output converts) into what
 * DXC emits for a native InterlockedMax on a RWTexture2D<uint64_t>:
 *   dx.op.atomicBinOp.i64(78, target, op, x, y, z, hi << 32 | lo)
 * with the target retyped as a 64-bit atomic resource (i64 element, the
 * Atomic64Use tag), the shader flags that say so, and the magic buffer removed.
 * Handles and the declared shader model stay as they were: the converter takes
 * the i64 atomic from a 6.0 createHandle module (measured, tests/offline/atomic64).
 * The one hard rule: nothing may read the atomic's result, because Metal's
 * 64-bit texture atomics return none and the converter then rejects the
 * shader ("unsupported instruction: dx.op.atomicBinOp.i64").
 * The semantics follow vkd3d-proton's dxil-spirv (dxil_ags.cpp), which does the
 * same translation for Vulkan.
 *
 * Returns 1 and a malloc'd container when something was rewritten, 0 when the
 * shader uses no AGS intrinsics (nothing allocated), -1 when it does but the
 * pass could not translate it (note says why; the caller keeps the original). */
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <string>

#include "llvm/Bitcode/BitcodeReader.h"
#include "llvm/Bitcode/BitcodeWriter.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/Dominators.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Metadata.h"
#include "llvm/IR/Module.h"
#include "llvm/Support/Error.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/raw_ostream.h"

using namespace llvm;

namespace {

constexpr uint32_t kAgsSpace = 0x7FFF0ADEu;      /* AmdExtD3DShaderIntrinsicsSpaceId */
constexpr uint32_t kAgsMagic = 0x5u;
constexpr uint32_t kAgsOpAtomicU64 = 0x18u;
constexpr unsigned kOpCreateHandle = 57, kOpTextureStore = 67, kOpAtomicBinOp = 78, kOpAtomicCmpXchg = 79;
constexpr unsigned kClassUAV = 1;
constexpr uint64_t kFlagInt64Ops = 1ull << 20, kFlagAtomicInt64Typed = 1ull << 27;   /* DXIL module flags */
constexpr uint64_t kSfi0Int64Ops = 0x8000, kSfi0AtomicInt64Typed = 0x400000;        /* SFI0 feature bits */

struct note_t { char *buf; size_t cap; };
static void say(note_t &n, const char *fmt, const char *a = "", unsigned b = 0)
{
    if (n.buf && n.cap) snprintf(n.buf, n.cap, fmt, a, b);
}

static uint32_t rd32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }
static void wr32(uint8_t *p, uint32_t v) { memcpy(p, &v, 4); }

static bool is_dx_op(const CallInst *ci, unsigned op)
{
    const Function *f = ci->getCalledFunction();
    if (!f || !f->getName().startswith("dx.op.")) return false;
    auto *c = dyn_cast<ConstantInt>(ci->getArgOperand(0));
    return c && c->getZExtValue() == op;
}
static uint64_t cint(const Value *v, bool *ok)
{
    auto *c = dyn_cast<ConstantInt>(v);
    if (!c) { *ok = false; return 0; }
    return c->getZExtValue();
}

/* dx.resources = !{srvs, uavs, cbvs, samplers}; each entry's operand 0 is its
 * range ID (what createHandle's rangeId refers to), 3 its space, 6 its shape. */
static MDTuple *uav_list(Module &m)
{
    NamedMDNode *res = m.getNamedMetadata("dx.resources");
    if (!res || res->getNumOperands() != 1) return nullptr;
    auto *top = dyn_cast<MDTuple>(res->getOperand(0));
    if (!top || top->getNumOperands() < 2) return nullptr;
    return dyn_cast_or_null<MDTuple>(top->getOperand(1).get());
}
static uint64_t md_int(const MDOperand &o, bool *ok)
{
    auto *c = dyn_cast_or_null<ConstantAsMetadata>(o.get());
    if (!c) { *ok = false; return 0; }
    return cint(c->getValue(), ok);
}

struct seq_t { CallInst *ph[3] = {nullptr, nullptr, nullptr}; CallInst *marker = nullptr; };

static unsigned map_op(uint32_t ags_op, bool *ok)
{
    switch (ags_op) {   /* AmdExtD3DShaderIntrinsicsAtomicOp_* -> DXIL AtomicBinOpCode */
    case 0x01: return 6;   /* MinU64 -> UMin */
    case 0x02: return 7;   /* MaxU64 -> UMax */
    case 0x03: return 1;   /* AndU64 -> And */
    case 0x04: return 2;   /* OrU64 -> Or */
    case 0x05: return 3;   /* XorU64 -> Xor */
    case 0x06: return 0;   /* AddU64 -> Add */
    case 0x07: return 8;   /* XchgU64 -> Exchange */
    default: *ok = false; return 0;   /* CmpXchgU64 needs the other intrinsic shape */
    }
}

static int rewrite_module(Module &m, note_t &note, unsigned *n_rewritten, unsigned *n_used_result)
{
    LLVMContext &ctx = m.getContext();
    MDTuple *uavs = uav_list(m);
    if (!uavs) return 0;

    /* The magic buffer's range ID, and each UAV range's shape. */
    int64_t magic_id = -1;
    std::vector<std::pair<uint64_t, uint64_t>> shapes;   /* (id, shape) */
    for (const MDOperand &op : uavs->operands()) {
        auto *e = dyn_cast_or_null<MDTuple>(op.get());
        if (!e || e->getNumOperands() < 7) continue;
        bool ok = true;
        uint64_t id = md_int(e->getOperand(0), &ok), space = md_int(e->getOperand(3), &ok), shape = md_int(e->getOperand(6), &ok);
        if (!ok) continue;
        if (space == kAgsSpace) magic_id = (int64_t)id;
        shapes.push_back({id, shape});
    }
    if (magic_id < 0) return 0;

    /* Handles to the magic buffer, and the range ID behind any UAV handle. */
    auto uav_range = [&](Value *h) -> int64_t {
        auto *ci = dyn_cast<CallInst>(h);
        if (!ci || !is_dx_op(ci, kOpCreateHandle)) return -1;
        bool ok = true;
        uint64_t cls = cint(ci->getArgOperand(1), &ok), rid = cint(ci->getArgOperand(2), &ok);
        return ok && cls == kClassUAV ? (int64_t)rid : -1;
    };

    std::vector<seq_t> seqs;
    for (Function &f : m) {
        if (f.isDeclaration()) continue;
        for (BasicBlock &bb : f) {
            seq_t cur;
            int want = 0;
            for (Instruction &in : bb) {
                auto *ci = dyn_cast<CallInst>(&in);
                if (!ci) continue;
                if (is_dx_op(ci, kOpAtomicCmpXchg) && uav_range(ci->getArgOperand(1)) == magic_id) {
                    bool ok = true;
                    uint32_t code = (uint32_t)cint(ci->getArgOperand(2), &ok);
                    if (!ok || (code >> 28) != kAgsMagic) { say(note, "AGS magic write with a non-constant or foreign instruction%s", ""); return -1; }
                    uint32_t opcode = code & 0xff, phase = (code >> 24) & 3;
                    if (opcode != kAgsOpAtomicU64) { say(note, "AGS opcode %s0x%x is not translated", "", opcode); return -1; }
                    if ((int)phase != want) { say(note, "AGS AtomicU64 phases out of order (saw %sphase %u)", "", phase); return -1; }
                    cur.ph[phase] = ci;
                    want = phase + 1;
                    if (want == 3) {
                        if (!cur.marker) { say(note, "AGS AtomicU64 without a target store%s", ""); return -1; }
                        seqs.push_back(cur); cur = seq_t(); want = 0;
                    }
                } else if (want == 2 && !cur.marker && is_dx_op(ci, kOpTextureStore) && ci->getArgOperand(2) == cur.ph[0]) {
                    cur.marker = ci;
                }
            }
            if (want != 0) { say(note, "AGS AtomicU64 sequence split across blocks%s", ""); return -1; }
        }
    }
    if (seqs.empty()) { say(note, "magic AGS buffer declared but only used by other intrinsics%s", ""); return -1; }

    /* Target resources: every use of each must be one of our markers, since the
     * resource changes type from uint2 to uint64. */
    std::vector<int64_t> targets;
    for (seq_t &s : seqs) {
        int64_t rid = uav_range(s.marker->getArgOperand(1));
        if (rid < 0) { say(note, "AGS target is not a plain UAV handle%s", ""); return -1; }
        bool seen = false;
        for (int64_t t : targets) seen |= t == rid;
        if (!seen) targets.push_back(rid);
    }
    for (Function &f : m) for (BasicBlock &bb : f) for (Instruction &in : bb) {
        auto *ci = dyn_cast<CallInst>(&in);
        if (!ci || !is_dx_op(ci, kOpCreateHandle)) continue;
        int64_t rid = uav_range(ci);
        bool is_target = false;
        for (int64_t t : targets) is_target |= t == rid;
        if (!is_target) continue;
        for (User *u : ci->users()) {
            bool is_marker = false;
            for (seq_t &s : seqs) is_marker |= u == s.marker;
            if (!is_marker) { say(note, "AGS target UAV %sis also read or written directly (id %u)", "", (unsigned)rid); return -1; }
        }
    }

    /* Rewrite each sequence at its phase-2 call, where every operand dominates. */
    Type *i32 = Type::getInt32Ty(ctx), *i64 = Type::getInt64Ty(ctx);
    Type *handle_ty = seqs[0].marker->getArgOperand(1)->getType();
    FunctionCallee binop = m.getOrInsertFunction("dx.op.atomicBinOp.i64",
        FunctionType::get(i64, {i32, handle_ty, i32, i32, i32, i32, i64}, false));
    if (auto *bf = dyn_cast<Function>(binop.getCallee())) bf->addFnAttr(Attribute::NoUnwind);

    for (seq_t &s : seqs) {
        bool ok = true;
        unsigned op = map_op((uint32_t)(cast<ConstantInt>(s.ph[0]->getArgOperand(2))->getZExtValue() >> 8) & 0xffff, &ok);
        if (!ok) { say(note, "AGS AtomicU64 variant %snot translated", ""); return -1; }
        int64_t rid = uav_range(s.marker->getArgOperand(1));
        uint64_t shape = 2;
        for (auto &sh : shapes) if ((int64_t)sh.first == rid) shape = sh.second;
        Value *undef = UndefValue::get(i32);
        Value *x = s.ph[0]->getArgOperand(5), *y = s.ph[0]->getArgOperand(6), *z = s.ph[1]->getArgOperand(5);
        if (shape == 1) { y = undef; z = undef; }                  /* Texture1D */
        else if (shape == 2 || shape == 3) z = undef;              /* Texture2D(MS) */
        Value *lo = s.ph[1]->getArgOperand(6), *hi = s.ph[2]->getArgOperand(5);

        IRBuilder<> b(s.ph[2]);
        Value *v = b.CreateOr(b.CreateShl(b.CreateZExt(hi, i64), 32), b.CreateZExt(lo, i64));
        Value *r = b.CreateCall(binop, {ConstantInt::get(i32, kOpAtomicBinOp), s.marker->getArgOperand(1),
                                        ConstantInt::get(i32, op), x, y, z, v});

        /* Metal's 64-bit texture atomics return nothing, and the converter
         * refuses the whole shader if the original value is read even by dead
         * code. Nanite never reads it; only materialise it when something does. */
        s.marker->eraseFromParent();
        bool used = !s.ph[2]->use_empty() || !s.ph[0]->use_empty();
        for (User *u : s.ph[1]->users()) used |= u != s.ph[2];
        if (used) {
            Value *old_lo = b.CreateTrunc(r, i32), *old_hi = b.CreateTrunc(b.CreateLShr(r, 32), i32);
            s.ph[2]->replaceAllUsesWith(old_hi);
            s.ph[1]->replaceAllUsesWith(old_hi);   /* ret.y is overwritten by phase 2 */
            s.ph[0]->replaceAllUsesWith(old_lo);
            (*n_used_result)++;
        }
        s.ph[2]->eraseFromParent();
        s.ph[1]->eraseFromParent();
        s.ph[0]->eraseFromParent();
    }

    /* The results now come from the phase-2 point; every remaining use must be
     * dominated by it (in AGS code the results are only used afterwards). */
    for (Function &f : m) {
        if (f.isDeclaration()) continue;
        DominatorTree dt(f);
        for (BasicBlock &bb : f) for (Instruction &in : bb)
            for (Use &u : in.operands()) {
                auto *def = dyn_cast<Instruction>(u.get());
                if (def && !dt.dominates(def, u)) { say(note, "rewrite broke dominance in %s", f.getName().str().c_str()); return -1; }
            }
    }

    /* Drop the magic handles, then the magic resource, renumbering the UAV range
     * IDs above it (createHandle refers to ranges by ID). */
    std::vector<CallInst *> dead;
    for (Function &f : m) for (BasicBlock &bb : f) for (Instruction &in : bb) {
        auto *ci = dyn_cast<CallInst>(&in);
        if (ci && is_dx_op(ci, kOpCreateHandle) && uav_range(ci) == magic_id) {
            if (!ci->use_empty()) { say(note, "magic AGS buffer still used after the rewrite%s", ""); return -1; }
            dead.push_back(ci);
        }
    }
    for (CallInst *ci : dead) ci->eraseFromParent();
    for (Function &f : m) for (BasicBlock &bb : f) for (Instruction &in : bb) {
        auto *ci = dyn_cast<CallInst>(&in);
        int64_t rid = ci && is_dx_op(ci, kOpCreateHandle) ? uav_range(ci) : -1;
        if (rid > magic_id) ci->setArgOperand(2, ConstantInt::get(i32, rid - 1));
    }

    StructType *t64 = StructType::getTypeByName(ctx, "class.RWTexture2D<unsigned long long>");
    std::vector<Metadata *> kept;
    for (const MDOperand &op : uavs->operands()) {
        auto *e = dyn_cast_or_null<MDTuple>(op.get());
        if (!e) continue;
        bool ok = true;
        int64_t id = (int64_t)md_int(e->getOperand(0), &ok);
        if (id == magic_id) continue;
        std::vector<Metadata *> f(e->op_begin(), e->op_end());
        if (id > magic_id) f[0] = ConstantAsMetadata::get(ConstantInt::get(i32, id - 1));
        bool is_target = false;
        for (int64_t t : targets) is_target |= t == id;
        if (is_target) {
            /* uint64 element: DXC types it as { i64 }, element type U32 plus the
             * Atomic64Use tag (3) in the extended properties. */
            const char *nm = "class.RWTexture2D<unsigned long long>";
            uint64_t shape = 2;
            for (auto &sh : shapes) if ((int64_t)sh.first == id) shape = sh.second;
            if (shape == 4) nm = "class.RWTexture3D<unsigned long long>";
            else if (shape == 7) nm = "class.RWTexture2DArray<unsigned long long>";
            else if (shape == 1) nm = "class.RWTexture1D<unsigned long long>";
            t64 = StructType::getTypeByName(ctx, nm);
            if (!t64) t64 = StructType::create(ctx, {i64}, nm);
            f[1] = ConstantAsMetadata::get(UndefValue::get(PointerType::get(t64, 0)));
            std::vector<Metadata *> props;
            if (f.size() > 10 && f[10]) {
                auto *p = cast<MDTuple>(f[10]);
                for (unsigned i = 0; i + 1 < p->getNumOperands(); i += 2) {
                    bool ok2 = true;
                    uint64_t tag = md_int(p->getOperand(i), &ok2);
                    if (ok2 && tag == 3) continue;
                    props.push_back(p->getOperand(i)); props.push_back(p->getOperand(i + 1));
                }
            } else {
                props.push_back(ConstantAsMetadata::get(ConstantInt::get(i32, 0)));
                props.push_back(ConstantAsMetadata::get(ConstantInt::get(i32, 5)));
            }
            props.push_back(ConstantAsMetadata::get(ConstantInt::get(i32, 3)));
            props.push_back(ConstantAsMetadata::get(ConstantInt::get(i32, 1)));
            while (f.size() < 11) f.push_back(nullptr);
            f[10] = MDTuple::get(ctx, props);
        }
        kept.push_back(MDTuple::get(ctx, f));
    }
    {
        NamedMDNode *res = m.getNamedMetadata("dx.resources");
        auto *top = cast<MDTuple>(res->getOperand(0));
        std::vector<Metadata *> t(top->op_begin(), top->op_end());
        t[1] = kept.empty() ? nullptr : MDTuple::get(ctx, kept);
        MDTuple *ntop = MDTuple::get(ctx, t);
        res->setOperand(0, ntop);
        /* dx.entryPoints = !{fn, name, signatures, resources, properties}: point
         * operand 3 at the new list and OR the 64-bit atomic flags into tag 0. */
        if (NamedMDNode *eps = m.getNamedMetadata("dx.entryPoints")) {
            for (unsigned i = 0; i < eps->getNumOperands(); i++) {
                auto *ep = cast<MDTuple>(eps->getOperand(i));
                std::vector<Metadata *> e(ep->op_begin(), ep->op_end());
                if (e.size() < 5) e.resize(5, nullptr);
                if (e[3]) e[3] = ntop;
                std::vector<Metadata *> props;
                bool have_flags = false;
                if (e[4]) {
                    auto *p = cast<MDTuple>(e[4]);
                    for (unsigned k = 0; k + 1 < p->getNumOperands(); k += 2) {
                        bool ok = true;
                        uint64_t tag = md_int(p->getOperand(k), &ok);
                        Metadata *val = p->getOperand(k + 1);
                        if (ok && tag == 0) {
                            bool ok2 = true;
                            uint64_t fl = md_int(p->getOperand(k + 1), &ok2);
                            val = ConstantAsMetadata::get(ConstantInt::get(i64, fl | kFlagInt64Ops | kFlagAtomicInt64Typed));
                            have_flags = true;
                        }
                        props.push_back(p->getOperand(k)); props.push_back(val);
                    }
                }
                if (!have_flags) {
                    props.insert(props.begin(), ConstantAsMetadata::get(ConstantInt::get(i64, kFlagInt64Ops | kFlagAtomicInt64Typed)));
                    props.insert(props.begin(), ConstantAsMetadata::get(ConstantInt::get(i32, 0)));
                }
                e[4] = MDTuple::get(ctx, props);
                eps->setOperand(i, MDTuple::get(ctx, e));
            }
        }
    }
    {   /* declarations nothing calls any more (createHandle, the magic CmpXchg...) */
        std::vector<Function *> unused;
        for (Function &f : m) if (f.isDeclaration() && f.use_empty() && f.getName().startswith("dx.op.")) unused.push_back(&f);
        for (Function *f : unused) f->eraseFromParent();
    }
    *n_rewritten = (unsigned)seqs.size();
    return 1;
}

}  // namespace

extern "C" int madeira_ags_rewrite(const void *bc, size_t len, void **out, size_t *out_len,
                                   char *note_buf, size_t note_cap)
{
    note_t note{note_buf, note_cap};
    const uint8_t *d = (const uint8_t *)bc;
    *out = nullptr; *out_len = 0;
    if (note_buf && note_cap) note_buf[0] = 0;
    if (len < 32 || memcmp(d, "DXBC", 4)) return 0;
    uint32_t nparts = rd32(d + 28);
    if (32 + 4ull * nparts > len) return 0;

    /* Cheap reject: the magic space never appears in the bytes of a shader that
     * does not declare it (the bitcode stores it as a plain 32-bit literal in a
     * VBR, so scan PSV0's resource table instead: space is a raw uint32 there). */
    const uint8_t *dxil = nullptr; uint32_t dxil_size = 0;
    bool magic = false;
    for (uint32_t i = 0; i < nparts; i++) {
        uint32_t off = rd32(d + 32 + 4 * i);
        if (off + 8 > len) return 0;
        uint32_t sz = rd32(d + off + 4);
        if (off + 8ull + sz > len) return 0;
        if (!memcmp(d + off, "DXIL", 4)) { dxil = d + off + 8; dxil_size = sz; }
        if (!memcmp(d + off, "PSV0", 4))
            for (uint32_t k = 0; k + 4 <= sz; k += 4) magic |= rd32(d + off + 8 + k) == kAgsSpace;
    }
    if (getenv("MADEIRA_AGS_ROUNDTRIP_ONLY")) magic = true;
    if (!dxil || !magic || dxil_size < 24) return 0;
    uint32_t bc_off = rd32(dxil + 16), bc_size = rd32(dxil + 20);
    if (8ull + bc_off + bc_size > dxil_size) return 0;

    LLVMContext ctx;
    ctx.setOpaquePointers(false);   /* DXIL is typed-pointer IR; keep it that way on the way out */
    auto mb = MemoryBuffer::getMemBuffer(StringRef((const char *)dxil + 8 + bc_off, bc_size), "dxil", false);
    auto mod = parseBitcodeFile(mb->getMemBufferRef(), ctx);
    if (!mod) {
        std::string err = toString(mod.takeError());
        say(note, "bitcode reader: %s", err.c_str());
        return -1;
    }
    unsigned n = 0, n_used = 0;
    int rc = getenv("MADEIRA_AGS_ROUNDTRIP_ONLY") ? 1 : rewrite_module(**mod, note, &n, &n_used);   /* offline control */
    if (rc <= 0) return rc;

    SmallVector<char, 0> nb;
    { raw_svector_ostream os(nb); WriteBitcodeToFile(**mod, os); }
    while (nb.size() & 3) nb.push_back(0);

    /* Rebuild the container: the new DXIL part, SFI0 with the 64-bit atomic
     * feature bits, PSV0 with the magic resource dropped from its bind table,
     * everything else as it was except HASH (stale) and the debug/statistics
     * copies of the old bitcode (ILDB, STAT). */
    std::vector<std::pair<uint32_t, std::vector<uint8_t>>> parts;
    for (uint32_t i = 0; i < nparts; i++) {
        uint32_t off = rd32(d + 32 + 4 * i), sz = rd32(d + off + 4);
        uint32_t cc; memcpy(&cc, d + off, 4);
        std::vector<uint8_t> p(d + off + 8, d + off + 8 + sz);
        if (!memcmp(&cc, "HASH", 4) || !memcmp(&cc, "ILDB", 4) || !memcmp(&cc, "STAT", 4)) continue;
        if (!memcmp(&cc, "DXIL", 4)) {
            std::vector<uint8_t> q(24 + nb.size());
            memcpy(q.data(), p.data(), 16);                         /* program version, size, 'DXIL', dxil version */
            wr32(q.data() + 4, (uint32_t)(q.size() / 4));
            wr32(q.data() + 16, 16);
            wr32(q.data() + 20, (uint32_t)nb.size());
            memcpy(q.data() + 24, nb.data(), nb.size());
            p.swap(q);
        } else if (!memcmp(&cc, "SFI0", 4) && p.size() >= 8) {
            uint64_t fl; memcpy(&fl, p.data(), 8); fl |= kSfi0Int64Ops | kSfi0AtomicInt64Typed; memcpy(p.data(), &fl, 8);
        } else if (!memcmp(&cc, "PSV0", 4) && p.size() >= 4) {
            /* PSV0: u32 runtime-info size, runtime info, u32 resource count,
             * [u32 bind-info size], bind infos {type, space, lower, upper[, kind, flags]}. */
            uint32_t ri = rd32(p.data());
            size_t at = 4 + ri;
            if (at + 4 <= p.size()) {
                uint32_t cnt = rd32(p.data() + at);
                if (cnt && at + 8 <= p.size()) {
                    uint32_t bsz = rd32(p.data() + at + 4);
                    size_t base = at + 8;
                    if (bsz >= 16 && base + (size_t)cnt * bsz <= p.size()) {
                        for (uint32_t k = 0; k < cnt; k++) {
                            uint8_t *b = p.data() + base + (size_t)k * bsz;
                            if (rd32(b + 4) == kAgsSpace) {
                                memmove(b, b + bsz, p.size() - (size_t)(b + bsz - p.data()));
                                p.resize(p.size() - bsz);
                                wr32(p.data() + at, cnt - 1);
                                break;
                            }
                        }
                    }
                }
            }
        }
        parts.push_back({cc, std::move(p)});
    }
    size_t total = 32 + 4 * parts.size();
    for (auto &p : parts) total += 8 + p.second.size();
    uint8_t *o = (uint8_t *)malloc(total);
    if (!o) return -1;
    memcpy(o, d, 24);
    memset(o + 4, 0, 16);                     /* digest: the converter does not check it */
    wr32(o + 24, (uint32_t)total);
    wr32(o + 28, (uint32_t)parts.size());
    size_t w = 32 + 4 * parts.size();
    for (size_t i = 0; i < parts.size(); i++) {
        wr32(o + 32 + 4 * i, (uint32_t)w);
        memcpy(o + w, &parts[i].first, 4);
        wr32(o + w + 4, (uint32_t)parts[i].second.size());
        memcpy(o + w + 8, parts[i].second.data(), parts[i].second.size());
        w += 8 + parts[i].second.size();
    }
    *out = o; *out_len = total;
    if (n_used) snprintf(note_buf, note_cap, "rewrote %u AGS 64-bit atomic(s); %u read the old value (Metal cannot return it)", n, n_used);
    else say(note, "rewrote %s%u AGS 64-bit atomic(s)", "", n);
    return 1;
}
