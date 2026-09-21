#!/usr/bin/env python3
"""PreSonus Revelator io24 -- 'comp' ('cpxt') and 'gate' DSP coefficient blobs.

Self-contained, stdlib only.  Every value the host puts on the wire is computed
here in the same order and the same precision as dspusbdevice.dll does it:
  * the biquad designer (0x1800128e0) works in DOUBLE and narrows with cvtpd2ps
  * everything else is SINGLE precision throughout (movss / mulss / powf / expf)

Verified against dspusbdevice.dll (imagebase 0x180000000) and the embedded io24
firmware (Thumb-2, load VA 0x60020000).  See the accompanying spec for the
address of every claim.

    python3 io24_dsp.py       # self-test + worked examples
"""

import math
import struct

# --------------------------------------------------------------------------
# float32 helpers.  The host is a 32-bit-float program; reproducing that
# exactly is what makes the blobs byte-identical to Universal Control's.
# --------------------------------------------------------------------------

def f32(x):
    """Round a Python float to IEEE-754 binary32, as a Python float."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


def bits(x):
    """The 32-bit pattern that would go on the wire for float x."""
    return struct.unpack("<I", struct.pack("<f", f32(x)))[0]


def _mul(a, b):   return f32(f32(a) * f32(b))
def _div(a, b):   return f32(f32(a) / f32(b))
def _add(a, b):   return f32(f32(a) + f32(b))
def _sub(a, b):   return f32(f32(a) - f32(b))


def _powf(base, exp):
    """MSVC powf(float, float) -> float."""
    return f32(f32(base) ** f32(exp))


def _expf(x):
    """MSVC expf(float) -> float."""
    return f32(math.exp(f32(x)))


# host constants, given by their exact bit patterns in .rdata
C_P05     = f32(0.05000000074505806)      # 0x3d4ccccd  @0x180481870
C_M05     = f32(-0.05000000074505806)     # 0xbd4ccccd  @0x180481bf0
GAIN_FLOOR = f32(6.309573308271865e-08)   # 0x33877f3f  @0x1804817dc  == 10^(-144/20)
TWO_PI    = f32(6.2831854820251465)       # stored negated, 0xc0c90fdb @0x180481c20
KF_OFF    = f32(40.000999450683594)       # 0x42200106  @0x180481a4c
KF_MIN    = f32(40.0)                     # 0x42200000  @0x180481a48

FS_DEFAULT = 48000.0


def _db_to_lin(db):
    """host 'gain' -> linear:  db < -144 ? 10^-7.2 : powf(10, db * +0.05f)"""
    db = f32(db)
    if db < -144.0:
        return GAIN_FLOOR
    return _powf(10.0, _mul(db, C_P05))


def _db_to_invlin(db):
    """host 'gain' -> INVERSE linear:  db > 144 ? 10^-7.2 : powf(10, db * -0.05f)"""
    db = f32(db)
    if db > 144.0:
        return GAIN_FLOOR
    return _powf(10.0, _mul(db, C_M05))


# --------------------------------------------------------------------------
# The shared biquad designer, dspusbdevice.dll 0x1800128e0.
#
# Preamble (0x180013123):  w0 = 2 * f * (pi/fs);  sincos(w0);  alpha = 0.5*sin(w0)/Q
# Type 7  (0x1800131d8):   RBJ band-pass, constant 0 dB peak gain
# Type 11 (0x1800132c9):   RBJ peaking EQ, but alpha = 0.5*w0/Q  (NOT sin-based)
# default (0x180013832):   identity [1,0,0,0,0]
#
# Output order is the device's 'Bqdf' order [b0, -a1, b1, -a2, b2]; that order
# is proved by the firmware, which demultiplexes w0,w2,w4 into the DSP's
# {b0,b1,b2} slots and w1,w3 into its {-a1,-a2} slots
# ('comp' 0x60076226, 'gate' 0x60071102).
# --------------------------------------------------------------------------

IDENTITY_BIQUAD = [1.0, 0.0, 0.0, 0.0, 0.0]


def biquad_bandpass(freq_hz, q, fs=FS_DEFAULT):
    """Designer type 7 -- RBJ BPF, constant 0 dB peak gain."""
    w0 = 2.0 * float(freq_hz) * (math.pi / float(fs))
    alpha = 0.5 * math.sin(w0) / float(q)
    norm = 1.0 / (1.0 + alpha)
    return [f32(alpha * norm),                  # b0
            f32(2.0 * math.cos(w0) * norm),     # -a1
            f32(0.0),                           # b1
            f32((alpha - 1.0) * norm),          # -a2
            f32(-(alpha * norm))]               # b2


def biquad_peaking(freq_hz, q, gain_db, fs=FS_DEFAULT):
    """Designer type 11 -- RBJ peaking EQ with the host's alpha = w0/(2Q)."""
    w0 = 2.0 * float(freq_hz) * (math.pi / float(fs))
    alpha = 0.5 * w0 / float(q)                 # note: w0, not sin(w0)
    A = 10.0 ** (float(gain_db) * 0.025)        # pow(10, gain/40)
    norm = A / (A + alpha)
    c2 = 2.0 * math.cos(w0)
    return [f32((1.0 + A * alpha) * norm),      # b0
            f32(c2 * norm),                     # -a1
            f32(-(c2 * norm)),                  # b1
            f32(-((1.0 - alpha / A) * norm)),   # -a2
            f32((1.0 - A * alpha) * norm)]      # b2


def key_filter(freq_hz, q, fs=FS_DEFAULT):
    """The 'Key Filter' knob -> biquad.  <= 40.000999... Hz means OFF.

    Used verbatim by the gate (Q = 8.0) and by the COMP and FET compressor
    models (Q = 0.70710678).  Handlers: gate 0x18001ee88, COMP 0x18000ea30,
    FET 0x18000eff3 -- all three compare against 0x42200106 and clamp with
    maxss against 40.0 before designing type 7.
    """
    v = f32(freq_hz)
    if not (v > KF_OFF):
        return list(IDENTITY_BIQUAD)
    return biquad_bandpass(max(KF_MIN, v), q, fs)


# ==========================================================================
# 'comp' block -- the 'cpxt' blob (0x40 bytes)
# ==========================================================================

TAG_CPXT = 0x63707874          # on the wire: 74 78 70 63
TAG_GATE = 0x67617465          # on the wire: 65 74 61 67

COMP_Q = f32(0.70710677)       # 0x3f3504f3, written by all three ctors


def cpxt_blob(index, biquad, attack_s, release_s, slope, knee_db,
              threshold_db, makeup_lin, on, keylisten):
    """Pack a 'cpxt' blob.  index is the sub-instance (0 or 1) -- the firmware
    does NOT bounds-check it (0x600762ba does a bare mla), so clamp here."""
    index = max(0, min(1, int(index)))
    if len(biquad) != 5:
        raise ValueError("biquad must be 5 coefficients [b0,-a1,b1,-a2,b2]")
    if not knee_db > 0.0:
        # firmware 0x600760cc: knee_a = 0.5/sqrt(K).  K == 0 yields +inf.
        raise ValueError("knee must be > 0 (device divides by sqrt(knee))")
    if not attack_s > 0.0:
        # firmware: attack_coef = 1/(attack*fs) -> +inf
        raise ValueError("attack must be > 0 (device divides by attack*fs)")
    if not release_s > 0.0:
        # firmware: release_coef = exp(-2pi/(release*fs)) -> exp(-inf) = 0
        raise ValueError("release must be > 0")
    b = struct.pack("<III", TAG_CPXT, 0x40, index)
    b += struct.pack("<5f", *[f32(c) for c in biquad])
    b += struct.pack("<6f", f32(attack_s), f32(release_s), f32(slope),
                     f32(knee_db), f32(threshold_db), f32(makeup_lin))
    b += struct.pack("<II", 1 if on else 0, 1 if keylisten else 0)
    assert len(b) == 0x40
    return b


# ---- model 0  "Standard" / short name COMP -------------------------------
#      {870D04F7-212E-4F9C-ADBB-39A97216433F}
#      host factory 0x18004a750, setParameter 0x18000e8d0, builder 0x18000ed70
def cpxt_comp(index=0, on=False, threshold_db=0.0, ratio=2.0,
              attack_s=0.02, release_s=0.15, gain_db=0.0,
              softknee=False, automode=False,
              keyfilter_hz=20.0, keylisten=False, fs=FS_DEFAULT):
    """StudioLive Compressor XT.  Ranges (host descriptors @0x1800efe00):
         threshold -56..0 dB (def 0)      ratio    1..20     (def 2)
         attack 0.0002..0.15 s (def 0.02) release  0.0025..0.9 s (def 0.15)
         gain 0..28 dB (def 0)            keyfilter 40..16000 Hz (def 20 = off)
       'kneewidth' (id 9) exists in the descriptor table but its setter is a
       no-op (jump-table entry 9 == the default return at 0x18000eae3);
       the knee is chosen solely by the softknee toggle.
    """
    if automode:                                  # 0x18000ed82
        attack_s, release_s = 0.01, 0.15
    ratio = f32(ratio)
    slope = _sub(1.0, _div(1.0, ratio)) if ratio > 0.0 else 0.0   # 0x18000edba
    knee = 3.0 if softknee else 0.01                              # 0x18000e938
    makeup = _db_to_lin(gain_db)                                  # 0x18000e97e
    bq = key_filter(keyfilter_hz, COMP_Q, fs)
    return cpxt_blob(index, bq, attack_s, release_s, slope, knee,
                     threshold_db, makeup, on, keylisten)


# ---- model 1  "Tube" (LA-2A topology) ------------------------------------
#      {7F8A4262-D377-48E3-9D48-15D82C400A71}
#      host factory 0x18004a9f0, setParameter 0x18000f590, builder 0x18000f840
TUBE_KNEE = 3.0            # 0x18004ab2a, never rewritten
TUBE_RELEASE = f32(0.3799999952316284)   # 0x3ec28f5c, hard-coded @0x18000f6ec
TUBE_K_COMPRESS = f32(0.0555555559694767)  # 0x3d638e39   (1/18)
TUBE_K_LIMIT    = f32(0.0833333358168602)  # 0x3daaaaab   (1/12)


def cpxt_tube(index=0, on=False, peak=0.0, gain=40.0, limit_mode=False,
              keyfilter_hz=0.0, keylisten=False, fs=FS_DEFAULT):
    """StudioLive Tube Compressor.  Ranges (host descriptors @0x1800ecfa0):
         mode  0 = Compress, 1 = Limit      gain 0..100  (def 40)
         peak ("Peak Reduction") 0..100 (def 0)
         keyfilter 40..16000 Hz (def 0 = off)
       Release and knee are fixed; attack and threshold follow the peak knob.
    """
    peak = f32(peak)
    k = TUBE_K_LIMIT if limit_mode else TUBE_K_COMPRESS
    threshold = _sub(1.0, _mul(peak, 0.5))                       # 0x18000f6a2
    if peak > 0.0:                                               # 0x18000f6cc
        slope = _sub(1.0, _div(1.0, _add(_mul(peak, k), 2.5)))
    else:
        slope = 1.0
    attack = _add(_mul(peak, f32(0.0005000000237487257)), f32(0.019999999552965164))
    makeup = _db_to_lin(_mul(_sub(gain, 40.0), 0.5))             # 0x18000f5f4

    # key-filter selection, builder 0x18000f856
    kf = f32(keyfilter_hz)
    if kf > KF_OFF:
        bq = biquad_bandpass(max(KF_MIN, kf), COMP_Q, fs)
    elif kf < KF_OFF and keylisten:
        bq = list(IDENTITY_BIQUAD)                               # 0x18000f890
    else:
        # Tube's own fixed sidechain emphasis: peaking, 15 kHz, Q 0.5, +7 dB,
        # with b0/b1/b2 then halved (0x18000f9dc .. 0x18000fa84).
        p = biquad_peaking(15000.0, 0.5, 7.0, fs)
        bq = [_mul(p[0], 0.5), p[1], _mul(p[2], 0.5), p[3], _mul(p[4], 0.5)]

    return cpxt_blob(index, bq, attack, TUBE_RELEASE, slope, TUBE_KNEE,
                     threshold, makeup, on, keylisten)


# ---- model 2  "FET" (1176 topology) --------------------------------------
#      {1F831EC1-B8AC-4EE9-AD53-54227AF53D58}
#      host factory 0x18004ac40, setParameter 0x18000ef10, builder 0x18000f300
FET_KNEE  = 2.5                                                   # 0x18000f391
FET_RATIO = [f32(v) for v in (6.5, 9.899999618530273, 14.0, 22.0, 20.0)]
FET_TB    = [f32(v) for v in (3.75, 2.0, 1.100000023841858, 0.0, 2.0)]
FET_TC    = [f32(v) for v in (-3.0, -1.7000000476837158, -1.2000000476837158,
                              0.0, -1.7000000476837158)]
FET_RATIO_NAMES = ["4:1", "8:1", "12:1", "20:1", "All"]


def cpxt_fet(index=0, on=False, input_db=-43.0, output_db=0.0,
             attack_s=0.0001, release_s=0.25, ratio_index=0,
             keyfilter_hz=20.0, keylisten=False, fs=FS_DEFAULT):
    """StudioLive FET Compressor.  Ranges (host descriptors @0x1800eca50):
         input  -56..0 dB (def -43)     output -56..0 dB (def 0)
         attack 2.1e-5..8e-4 s (def 1e-4)  release 0.05..1.1 s (def 0.25)
         ratio_index 0..4 = 4:1 8:1 12:1 20:1 All   keyfilter 40..16000 (def 20)
       There is no threshold knob: the 1176's threshold is fixed and 'input'
       drives the signal into it, which is what the quadratic below models.
    """
    i = max(0, min(4, int(ratio_index)))
    attack = _mul(attack_s, 5.0 if i == 4 else 1.0)     # 0x18000f37c
    release = _mul(release_s, 10.0)                      # 0x18000f359
    slope = _sub(1.0, _div(1.0, FET_RATIO[i]))           # 0x18000f3b0

    A = _sub(-40.0, input_db)                            # 0x18000ef7f
    thr = _add(_mul(_mul(A, A), f32(0.007860999554395676)),
               _mul(A, f32(1.5199999809265137)))
    thr = _add(thr, f32(6.130000114440918))
    thr = _sub(thr, FET_TB[i])

    B = f32(output_db)
    mk = _add(_mul(_add(_mul(B, f32(0.005727000068873167)),
                        f32(1.434999942779541)), B),
              f32(6.591000080108643))
    mk = _add(_add(_sub(mk, thr), 4.0), FET_TC[i])
    makeup = _db_to_lin(mk)

    bq = key_filter(keyfilter_hz, COMP_Q, fs)
    return cpxt_blob(index, bq, attack, release, slope, FET_KNEE,
                     thr, makeup, on, keylisten)


COMP_MODELS = {
    0: ("Standard", "StudioLive Compressor XT",
        "{870D04F7-212E-4F9C-ADBB-39A97216433F}", cpxt_comp),
    1: ("Tube", "StudioLive Tube Compressor",
        "{7F8A4262-D377-48E3-9D48-15D82C400A71}", cpxt_tube),
    2: ("FET", "StudioLive FET Compressor",
        "{1F831EC1-B8AC-4EE9-AD53-54227AF53D58}", cpxt_fet),
}


def cpxt_safe_off(index=0):
    """A 'comp' blob that switches the compressor off without poking the
    firmware's divisions.  Do NOT use the literal power-on struct
    (0x60079288 leaves it all zero but makeup = 1.0): a zero knee/attack/
    release makes 0x600760cc store +inf into the derived coefficients.
    enable = 0 also makes the firmware store 1.0 into the 'Redu' slot, so the
    write is self-verifying."""
    return cpxt_blob(index, IDENTITY_BIQUAD, 0.02, 0.15, 0.0, 3.0,
                     0.0, 1.0, False, False)


# ==========================================================================
# 'gate' block -- the 'gate' blob (0x48 bytes)
# ==========================================================================

GATE_Q = f32(8.0)                                  # 0x18004a4cd, overwrites 0.7071
GATE_ATTACK_MIN  = f32(1.9999999494757503e-05)     # 0x37a7c5ac
GATE_RELEASE_MIN = f32(9.999999747378752e-05)      # 0x38d1b717


def _ceil_i32(x):
    """cvtps2dq with MXCSR RC = round-toward-+inf (0x18001f384..0x18001f3bb)."""
    return int(math.ceil(f32(x)))


def gate_blob(index, on=False, threshold_db=-84.0, range_db=-84.0,
              attack_s=0.005, release_s=0.7, keyfilter_hz=20.0,
              expander=False, keylisten=False, fs=FS_DEFAULT):
    """Pack a 'gate' blob.  Host builder 0x18001f200, setParameter 0x18001edb0.

    Descriptor ranges/defaults (@file 0xe9e50 = VA 0x1800eac50):
        on/keylisten/expander  bool, default 0
        keyfilter  40..16000 Hz  (default 20 -> off)
        threshold  -84..0 dB     (default -84)
        range      -84..0 dB     (default -84; -21 is the taper midpoint)
        attack     2e-5..0.5 s   (default 0.005)
        release    0.05..2.0 s   (default 0.7)
    'ratio' (id 8) and 'reduction' (id 9) are read-only.
    """
    index = max(0, min(1, int(index)))
    fs = f32(fs)
    bq = key_filter(keyfilter_hz, GATE_Q, fs)

    rng = _db_to_lin(range_db)          # 0x18001ef27  linear floor gain
    thr = _db_to_invlin(threshold_db)   # 0x18001eed4  INVERSE linear

    atk = max(f32(attack_s), GATE_ATTACK_MIN)     # maxss 0x18001f2e5
    rel = max(f32(release_s), GATE_RELEASE_MIN)   # maxss 0x18001f2f1
    rate = _mul(fs, 0.25)                         # detector runs at fs/4
    atk_coef = _expf(_div(_div(-TWO_PI, atk), rate))
    k = 1.0 if expander else 0.5                  # 0x18001f321
    krel = _mul(k, rel)
    rel_coef = _expf(_div(_div(-TWO_PI, krel), rate))
    hold = max(1, _ceil_i32(_mul(_mul(krel, fs), 0.5)))

    b = struct.pack("<III", TAG_GATE, 0x48, index)
    b += struct.pack("<5f", *bq)
    b += struct.pack("<6f", rng, thr, atk, rel, atk_coef, rel_coef)
    b += struct.pack("<iiii", hold, 1 if on else 0,
                     1 if expander else 0, 1 if keylisten else 0)
    assert len(b) == 0x48
    return b


def gate_blob_poweron(index):
    """Byte-exact firmware power-on state, from initialiser 0x60076be8:
    identity key filter, all six floats 0.0, hold = 3000, on = 0,
    expander = 1, keylisten = 0.  Unlike 'comp' this is safe to send --
    the gate carries its coefficients precomputed, so the device performs no
    division on them."""
    index = max(0, min(1, int(index)))
    b = struct.pack("<III", TAG_GATE, 0x48, index)
    b += struct.pack("<5f", *IDENTITY_BIQUAD)
    b += struct.pack("<6f", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    b += struct.pack("<iiii", 3000, 0, 1, 0)
    assert len(b) == 0x48
    return b


# ==========================================================================
# what the device does with it -- for prediction and 'Redu' cross-checks
# ==========================================================================

def comp_firmware_derive(attack_s, release_s, knee_db, fs=FS_DEFAULT):
    """Firmware 0x600760cc, writing compobj+0xb0+0x18*i."""
    return {
        "+0x00 attack_coef":  f32(1.0 / (f32(attack_s) * f32(fs))),
        "+0x04 release_coef": f32(math.exp(-TWO_PI / (f32(release_s) * f32(fs)))),
        "+0x10 knee_a":       f32(0.5 / math.sqrt(f32(knee_db))),
        "+0x14 knee_b":       f32(0.5 * math.sqrt(f32(knee_db))),
    }


def limiter_release_coef(release_s=0.4, fs=FS_DEFAULT):
    """Host 0x18001fad0 computes expf(-15.707963943481445 / fs) = exp(-5*pi/fs),
    which is exactly exp(-2*pi/(0.4*fs)).  At 48 kHz this is 0x3f7fea8f, the
    value already verified on hardware."""
    return _expf(-TWO_PI / (f32(release_s) * f32(fs)))


def limiter_inv_threshold(threshold_db):
    """Host 0x18001f8c0.  NOTE: single precision.  io24.py's
    10.0 ** (-threshold_db / 20.0) is 1 ULP high (0x41c8f36f vs 0x41c8f36e
    at -28 dB)."""
    return _db_to_invlin(threshold_db)


# ==========================================================================

def _hexdump(b):
    return " ".join("%02x" % c for c in b)


def _unpack_cpxt(b):
    tag, size, idx = struct.unpack_from("<III", b, 0)
    w = struct.unpack_from("<11f", b, 0x0c)
    en, kl = struct.unpack_from("<II", b, 0x38)
    return dict(tag=tag, size=size, index=idx, biquad=list(w[0:5]),
                attack=w[5], release=w[6], slope=w[7], knee=w[8],
                threshold=w[9], makeup=w[10], on=en, keylisten=kl)


def _selftest():
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print("  %-52s %s" % (name, "OK" if good else "FAIL got=%r want=%r" % (got, want)))

    print("float32 / host-arithmetic reproduction")
    check("limiter release coef @48k == 0x3f7fea8f",
          bits(limiter_release_coef(0.4, 48000.0)), 0x3F7FEA8F)
    check("limiter release coef == exp(-5*pi/fs)",
          bits(limiter_release_coef(0.4, 48000.0)),
          bits(_expf(-15.707963943481445 / 48000.0)))
    check("limiter invThreshold(-28) == 0x41c8f36e",
          bits(limiter_inv_threshold(-28.0)), 0x41C8F36E)
    check("io24.py's double form differs (1 ULP)",
          bits(10.0 ** (28.0 / 20.0)), 0x41C8F36F)
    check("gain floor bit pattern", bits(GAIN_FLOOR), 0x33877F3F)

    print("\nblob framing")
    c = cpxt_comp(on=True)
    check("cpxt length", len(c), 0x40)
    check("cpxt wire tag bytes", _hexdump(c[:4]), "74 78 70 63")
    check("cpxt size field", struct.unpack_from("<I", c, 4)[0], 0x40)
    g = gate_blob(0, on=True)
    check("gate length", len(g), 0x48)
    check("gate wire tag bytes", _hexdump(g[:4]), "65 74 61 67")
    check("gate size field", struct.unpack_from("<I", g, 4)[0], 0x48)

    print("\nbiquad designer")
    ident = key_filter(20.0, COMP_Q)
    check("keyfilter 20 Hz -> identity", ident, IDENTITY_BIQUAD)
    check("keyfilter 40.0 Hz -> identity (not > 40.000999)",
          key_filter(40.0, COMP_Q), IDENTITY_BIQUAD)
    bp = biquad_bandpass(1000.0, 0.70710678, 48000.0)
    check("BPF b1 == 0", bp[2], 0.0)
    check("BPF b2 == -b0", bp[4], f32(-bp[0]))
    # |H(f0)| of a constant-0dB-peak BPF is 1
    w = 2 * math.pi * 1000.0 / 48000.0
    z = complex(math.cos(-w), math.sin(-w))
    num = bp[0] + bp[2] * z + bp[4] * z * z
    den = 1.0 - bp[1] * z - bp[3] * z * z
    check("BPF |H(f0)| == 1 (0 dB peak gain)", round(abs(num / den), 5), 1.0)
    # Tube's emphasis biquad has DC gain exactly 0.5 after the b-scaling
    p = biquad_peaking(15000.0, 0.5, 7.0, 48000.0)
    e = [f32(p[0] * 0.5), p[1], f32(p[2] * 0.5), p[3], f32(p[4] * 0.5)]
    dc = (e[0] + e[2] + e[4]) / (1.0 - e[1] - e[3])
    check("Tube emphasis DC gain == 0.5", round(dc, 6), 0.5)

    print("\ncompressor model maths")
    d = _unpack_cpxt(cpxt_comp(on=True, threshold_db=-24.0, ratio=4.0,
                               attack_s=0.01, release_s=0.2, gain_db=6.0,
                               softknee=True, keyfilter_hz=120.0))
    check("COMP slope(ratio 4) == 0.75", d["slope"], 0.75)
    check("COMP knee(softknee) == 3.0", d["knee"], 3.0)
    check("COMP makeup(+6 dB)", bits(d["makeup"]), bits(_db_to_lin(6.0)))
    d = _unpack_cpxt(cpxt_comp(on=True, automode=True, attack_s=9.0, release_s=9.0))
    check("COMP automode forces attack 0.01", d["attack"], f32(0.01))
    check("COMP automode forces release 0.15", d["release"], f32(0.15))
    check("COMP knee(!softknee) == 0.01", d["knee"], f32(0.01))

    d = _unpack_cpxt(cpxt_tube(on=True, peak=50.0, gain=55.0))
    check("TUBE threshold == 1 - 0.5*peak", d["threshold"], f32(-24.0))
    check("TUBE release fixed 0.38", bits(d["release"]), 0x3EC28F5C)
    check("TUBE knee fixed 3.0", d["knee"], 3.0)
    check("TUBE attack == 0.02 + peak*0.0005", d["attack"], f32(0.045))
    check("TUBE slope(compress,50)",
          round(d["slope"], 7), round(f32(1 - 1 / (50 * TUBE_K_COMPRESS + 2.5)), 7))
    d0 = _unpack_cpxt(cpxt_tube(on=True, peak=0.0))
    check("TUBE slope == 1.0 when peak == 0", d0["slope"], 1.0)

    d = _unpack_cpxt(cpxt_fet(on=True, input_db=-20.0, output_db=-10.0, ratio_index=1))
    check("FET knee fixed 2.5", d["knee"], 2.5)
    check("FET slope(8:1 -> 9.9)", round(d["slope"], 7), round(f32(1 - 1 / 9.9), 7))
    check("FET release = knob * 10", d["release"], f32(2.5))
    d = _unpack_cpxt(cpxt_fet(on=True, ratio_index=4, attack_s=0.0001))
    check("FET 'All' multiplies attack by 5", d["attack"], _mul(5.0, 0.0001))
    # descriptor default input -43 dB should leave the compressor effectively idle
    d = _unpack_cpxt(cpxt_fet(on=True, input_db=-43.0))
    check("FET default input -43 -> threshold above 0 dBFS", d["threshold"] > 0.0, True)

    print("\nguards (firmware would divide by zero)")
    for kw in (dict(knee_db=0.0), dict(attack_s=0.0), dict(release_s=0.0)):
        try:
            cpxt_blob(0, IDENTITY_BIQUAD, kw.get("attack_s", 0.02),
                      kw.get("release_s", 0.15), 0.5, kw.get("knee_db", 3.0),
                      -20.0, 1.0, True, False)
            check("rejects %s" % list(kw)[0], False, True)
        except ValueError:
            check("rejects %s" % list(kw)[0], True, True)

    print("\ngate")
    g = gate_blob(0, on=True, threshold_db=-28.0, range_db=-60.0,
                  attack_s=0.005, release_s=0.7, keyfilter_hz=730.0,
                  expander=True)
    tag, size, idx = struct.unpack_from("<III", g, 0)
    bq = struct.unpack_from("<5f", g, 0x0c)
    rng, thr, atk, rel, ac, rc = struct.unpack_from("<6f", g, 0x20)
    hold, on_, exp_, kl = struct.unpack_from("<iiii", g, 0x38)
    check("gate range == 10^(-60/20)", bits(rng), bits(_db_to_lin(-60.0)))
    check("gate threshold == 10^(+28/20)", bits(thr), bits(_db_to_invlin(-28.0)))
    check("gate hold == ceil(k*rel*fs*0.5)", hold, math.ceil(1.0 * f32(0.7) * 48000 * 0.5))
    check("gate expander flag", exp_, 1)
    ge = gate_blob(0, release_s=0.7, expander=False)
    hold2 = struct.unpack_from("<i", ge, 0x38)[0]
    check("expander off halves the hold", hold2, math.ceil(0.5 * f32(0.7) * 48000 * 0.5))
    check("attack clamped to 2e-5",
          struct.unpack_from("<f", gate_blob(0, attack_s=0.0), 0x28)[0], GATE_ATTACK_MIN)
    check("release clamped to 1e-4",
          struct.unpack_from("<f", gate_blob(0, release_s=0.0), 0x2c)[0], GATE_RELEASE_MIN)
    p = gate_blob_poweron(1)
    check("power-on hold == 3000", struct.unpack_from("<i", p, 0x38)[0], 3000)
    check("power-on expander == 1", struct.unpack_from("<i", p, 0x40)[0], 1)
    check("power-on biquad identity", list(struct.unpack_from("<5f", p, 0x0c)),
          IDENTITY_BIQUAD)

    print("\nsample-rate independence")
    for fs in (44100.0, 48000.0, 88200.0, 96000.0):
        gate_blob(0, on=True, keyfilter_hz=730.0, fs=fs)
        cpxt_comp(on=True, keyfilter_hz=730.0, fs=fs)
        cpxt_tube(on=True, fs=fs)
        cpxt_fet(on=True, fs=fs)
    check("all four models build at 44.1/48/88.2/96 kHz", True, True)

    print("\n%s" % ("ALL CHECKS PASSED" if ok else "*** FAILURES ***"))
    return ok


def _demo():
    print("\n" + "=" * 74)
    print("worked examples (fs = 48000)")
    print("=" * 74)
    ex = [
        ("COMP thr=-24 ratio=4 atk=10ms rel=200ms gain=+6 softknee kf=120Hz",
         cpxt_comp(0, on=True, threshold_db=-24, ratio=4, attack_s=0.01,
                   release_s=0.2, gain_db=6, softknee=True, keyfilter_hz=120)),
        ("TUBE peak=50 gain=55 Compress (internal 15 kHz emphasis)",
         cpxt_tube(0, on=True, peak=50, gain=55)),
        ("FET input=-20 output=-10 ratio=8:1",
         cpxt_fet(0, on=True, input_db=-20, output_db=-10, ratio_index=1)),
    ]
    for name, b in ex:
        d = _unpack_cpxt(b)
        print("\n%s" % name)
        print("  bq      = [%.8f, %.8f, %.8f, %.8f, %.8f]" % tuple(d["biquad"]))
        print("  attack  = %-12.8g release = %-12.8g slope = %.8f"
              % (d["attack"], d["release"], d["slope"]))
        print("  knee    = %-12.8g thresh  = %-12.8g makeup= %.8f"
              % (d["knee"], d["threshold"], d["makeup"]))
        print("  device  : %s" % comp_firmware_derive(d["attack"], d["release"], d["knee"]))
        print("  wire    : %s" % _hexdump(b))

    g = gate_blob(0, on=True, threshold_db=-47.5, range_db=-60.0,
                  attack_s=0.025, release_s=0.7, keyfilter_hz=730.0002,
                  expander=True)
    print("\nGATE 'Broadcast' preset (thr -47.5, range -60, atk 25ms, rel 700ms,"
          " kf 730 Hz, expander)")
    print("  wire    : %s" % _hexdump(g))
    print("\nGATE power-on restore, index 0")
    print("  wire    : %s" % _hexdump(gate_blob_poweron(0)))


if __name__ == "__main__":
    good = _selftest()
    _demo()
    raise SystemExit(0 if good else 1)
