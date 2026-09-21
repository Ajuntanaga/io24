#!/usr/bin/env python3
"""
io24 mixer laws -- volume taper ('fader'), pan law, source-slot map, 'mprm' batch.

Everything here is transcribed from PreSonus Universal Control
hwaccess/dspusbdevice.dll (PE32+, imagebase 0x180000000).  Key addresses:

  taper name -> ctor registry ....... 0x18000a900..0x18000b400
  'fader' ctor ...................... 0x18000c030   (min -84, max +10, tbl 0x1800e9378, n 5)
  'fader' setRange (picks table) .... 0x18000ba50
  'fadercurve' ctor ................. 0x18000c130   (min -144, max +10, tbl 0x1800e9350, n 5)
  'metercurve' ctor ................. 0x18000c1b0   (min -144, max +10, tbl 0x1800e9280, n 5)
  'gaterange' ctor .................. 0x18000c0b0   (min -84,  max 0,   tbl 0x1800e92b0, n 15)
  table normalized -> value (dB) .... 0x18005cfe0
  table value (dB) -> normalized .... 0x18005d080
  same pair, but +/- 20*log10 ....... 0x18000bab0 / 0x18000bb70   ("linear gain" interface)
  mixer link computeDb .............. 0x1800570e0
  mixer link isMuted ................ 0x180056f40
  pan-law constant K = -0.831783f ... 0x18049eb48 (0xbf54efbc)

Stdlib only.  `python3 io24_mixer_laws.py` runs the self-test.
"""
import math
import struct

# --------------------------------------------------------------------------
# 1.  Piecewise-linear "fader" taper tables.
#
# Layout in the DLL: array of { f32 normalized; f32 dB; }, `count` entries.
# The FIRST entry is (0.0, min_dB) and the LAST is (1.0, max_dB).
# --------------------------------------------------------------------------

# 0x1800e9328 -- installed by setRange() when (min,max) == (-96, +10).
# This is the one the io24 mixer uses: descriptors `volume` (id 106),
# `aux1` (124), `aux2` (125), `FXA` (145) are all float, min -96, max +10,
# unit "gain", taper "fader".
FADER_96 = ((0.000, -96.0),
            (0.004, -60.0),
            (0.090, -40.0),
            (0.470, -10.0),
            (1.000, +10.0))

# 0x1800e9378 -- the 'fader' constructor's default, used when (min,max) == (-84,+10).
FADER_84 = ((0.000, -84.0),
            (0.004, -60.0),
            (0.090, -40.0),
            (0.470, -10.0),
            (1.000, +10.0))

# 0x1800e9280 / 0x1800e9350 -- 'metercurve' / 'fadercurve', (min,max) == (-144,+10)
FADER_144 = ((0.000, -144.0),
             (0.040,  -60.0),
             (0.160,  -40.0),
             (0.520,  -10.0),
             (1.000,  +10.0))

# 0x1800e92b0 -- 'gaterange', (min,max) == (-84, 0); descriptor `range` id 5.
GATERANGE = ((0.00, -84.0), (0.07, -72.0), (0.14, -61.0), (0.21, -51.0),
             (0.29, -42.0), (0.36, -34.0), (0.43, -27.0), (0.50, -21.0),
             (0.57, -16.0), (0.64, -12.0), (0.71,  -9.0), (0.76,  -6.0),
             (0.89,  -4.0), (0.93,  -2.0), (1.00,   0.0))


def _f32(x):
    """Round a Python float to IEEE-754 single precision (the host is all float)."""
    return struct.unpack('<f', struct.pack('<f', x))[0]


def taper_norm_to_db(norm, table=FADER_96):
    """normalized 0..1  ->  dB.   Transcription of 0x18005cfe0."""
    lo, hi = table[0][1], table[-1][1]
    if hi - lo <= 0.0:
        return 0.0
    x = 0.0 if norm < 0.0 else min(norm, 1.0)
    for i in range(len(table) - 1):
        if x <= table[i + 1][0]:
            n0, d0 = table[i]
            n1, d1 = table[i + 1]
            return _f32((x - n0) / (n1 - n0) * (d1 - d0) + d0)
    return hi                       # "not found" branch returns max


def taper_db_to_norm(db, table=FADER_96):
    """dB  ->  normalized 0..1.   Transcription of 0x18005d080."""
    lo, hi = table[0][1], table[-1][1]
    if hi - lo <= 0.0:
        return 0.0
    v = lo if lo > db else min(hi, db)          # clamp(db, min, max)
    for i in range(len(table) - 1):
        if v <= table[i + 1][1]:
            n0, d0 = table[i]
            n1, d1 = table[i + 1]
            return _f32((v - d0) / (d1 - d0) * (n1 - n0) + n0)
    return 1.0                      # "not found" branch returns 1.0


# The same object also exposes a *linear gain* interface (0x18000bab0 /
# 0x18000bb70) used by the audio/meter code -- identical table walk with a
# dB<->linear conversion bolted on and a hard floor at -144 dB.
_FLOOR_DB = -144.0
_FLOOR_LIN = _f32(10.0 ** (-144.0 / 20.0))      # 6.30957e-08, 0x33877f3f


def taper_norm_to_gain(norm, table=FADER_96):
    db = taper_norm_to_db(norm, table)
    if db < _FLOOR_DB:
        return _FLOOR_LIN
    return _f32(math.pow(10.0, _f32(db * 0.05)))


def taper_gain_to_norm(gain, table=FADER_96):
    db = _FLOOR_DB if gain < _FLOOR_LIN else _f32(20.0 * math.log10(gain))
    return taper_db_to_norm(db, table)


# --------------------------------------------------------------------------
# 2.  Pan law.  0x1800570e0, constant at 0x18049eb48 = 0xbf54efbc.
#
#     g(x) = K*x^2 + (1-K)*x        K = -0.83178312...
#     g(0)=0, g(1)=1, g(0.5)=10^(-3/20)   ->  a -3.0 dB centre pan law.
#
#     mode 0 : no pan term at all (what dspusbdevice.dll actually installs)
#     mode 1 : LEFT  leg, gain = g(1 - pan);  hard-muted when pan == 1.0
#     mode 2 : RIGHT leg, gain = g(pan);      hard-muted when pan == 0.0
# --------------------------------------------------------------------------
PAN_K = struct.unpack('<f', bytes.fromhex('bcef54bf'))[0]      # -0.8317831158638


def pan_gain(pan, mode):
    """Linear gain contributed by the pan law.  pan in [0,1], 0.5 = centre."""
    if mode == 1:
        x = _f32(1.0 - pan)
    elif mode == 2:
        x = _f32(pan)
    else:
        return 1.0                                            # mode 0: no pan
    return _f32(_f32(_f32(x * PAN_K) + _f32(1.0 - PAN_K)) * x)


def pan_db(pan, mode):
    g = pan_gain(pan, mode)
    if g < _FLOOR_LIN:
        return _FLOOR_DB
    return _f32(20.0 * math.log10(g))


# --------------------------------------------------------------------------
# 3.  The value the mixer actually receives.   0x1800570e0.
# --------------------------------------------------------------------------
OFF_SENTINEL = -145.0


def mixer_send_db(volume_db, bus_db=0.0, blend=1.0, pan=None, pan_mode=0,
                  muted=False):
    """Reproduce MixerLink::computeDb().

    volume_db : the channel's own level for this bus
                (`volume` id 106 for the main mix, `aux1`/`aux2` 124/125 for
                 Mix A / Mix B) -- already in dB.
    bus_db    : the destination bus's own `volume` (id 106), in dB.
    blend     : the channel's `monitorBlend` (id 107), LINEAR 0..1.
    pan/pan_mode : never wired up in dspusbdevice.dll; pass mode 0 for the io24.
    """
    if muted:
        return OFF_SENTINEL
    g = _FLOOR_LIN if volume_db < _FLOOR_DB else _f32(math.pow(10.0, _f32(volume_db * 0.05)))
    g = _f32(g * blend)
    db = _FLOOR_DB if g < _FLOOR_LIN else _f32(20.0 * math.log10(g))
    db = _f32(db + bus_db)
    if pan is not None and pan_mode in (1, 2):
        db = _f32(db + pan_db(pan, pan_mode))
    return db if db >= _FLOOR_DB else _FLOOR_DB


# --------------------------------------------------------------------------
# 4.  Wire encoding.
# --------------------------------------------------------------------------
BLOCK_MIXER = 100
BLOCKINDEX = {'main': 0, 'auxA': 1, 'auxB': 2}     # aux child index + 1

#  wire paramId  <-  channel's index inside its route group   (0x18003df19..)
SOURCE_SLOT = {
    ('line',     0): 3,     # line/ch1
    ('line',     1): 4,     # line/ch2
    ('line',     2): 6,     # line/ch3  (no such channel on the io24)
    ('return',   0): 0,     # return/ch1
    ('return',   1): 1,
    ('return',   2): 2,
    ('fxreturn', 0): 5,
}


def para_blob(param_id, gain_db, index=0):
    """SetP | block 100 | blockIndex B | 'Para' size 0x14 | index | paramId | f32"""
    return struct.pack('<IIIIf', 0x50617261, 0x14, index, param_id, gain_db)


def mprm_blob(entries, index=0):
    """'mprm' batch: 60 x {u32 paramId, f32 gainDb}, count at +0x1ec, size 0x1f0."""
    if len(entries) > 60:
        raise ValueError('mprm holds at most 60 entries')
    b = bytearray(0x1f0)
    struct.pack_into('<III', b, 0, 0x6d70726d, 0x1f0, index)
    for i, (pid, db) in enumerate(entries):
        struct.pack_into('<If', b, 0x0c + 8 * i, pid, db)
    struct.pack_into('<I', b, 0x1ec, len(entries))
    return bytes(b)


# --------------------------------------------------------------------------
if __name__ == '__main__':
    ok = 0

    def chk(cond, msg):
        global ok
        assert cond, msg
        ok += 1

    # -- the -96 table reproduces oddbear's VolumeValue.cs exactly ----------
    def oddbear_to_db(value):
        a, b, c, dd, e = 1.0, 0.47, 0.09, 0.004, 0.0
        if value >= b:
            return (value - b) / (a - b) * 20.0 - 10.0
        if value >= c:
            return (value - c) / (b - c) * 30.0 - 40.0
        if value >= dd:
            return (value - dd) / (c - dd) * 20.0 - 60.0
        return (value - e) / (dd - e) * 36.0 - 96.0

    for i in range(1001):
        n = i / 1000.0
        chk(abs(taper_norm_to_db(n) - oddbear_to_db(n)) < 2e-4,
            'oddbear mismatch at %.3f' % n)

    # -- breakpoints -------------------------------------------------------
    for n, db in FADER_96:
        chk(abs(taper_norm_to_db(n) - db) < 1e-3, 'breakpoint %s' % (n,))
        chk(abs(taper_db_to_norm(db) - n) < 1e-6, 'inverse breakpoint %s' % (db,))

    # -- round trip --------------------------------------------------------
    for i in range(0, 1001):
        n = i / 1000.0
        chk(abs(taper_db_to_norm(taper_norm_to_db(n)) - n) < 1e-4, 'roundtrip %f' % n)

    chk(abs(taper_norm_to_db(0.5) - (-8.867925)) < 1e-3, '0.5 -> -8.8679 dB')
    chk(abs(taper_db_to_norm(0.0) - 0.735) < 1e-4, '0 dB -> 0.735')
    chk(taper_norm_to_db(0.0) == -96.0 and taper_norm_to_db(1.0) == 10.0, 'ends')

    # -- gaterange cross-check: descriptor range is [-84, 0] ---------------
    chk(taper_norm_to_db(0.0, GATERANGE) == -84.0, 'gaterange min')
    chk(taper_norm_to_db(1.0, GATERANGE) == 0.0, 'gaterange max')

    # -- pan law -----------------------------------------------------------
    chk(abs(pan_gain(0.5, 1) - 10 ** (-3.0 / 20.0)) < 1e-6, 'pan centre = -3 dB')
    chk(abs(pan_gain(0.5, 2) - 10 ** (-3.0 / 20.0)) < 1e-6, 'pan centre = -3 dB (mode2)')
    chk(abs(pan_db(0.5, 1) + 3.0) < 1e-4, 'pan centre dB')
    chk(abs(pan_gain(0.0, 1) - 1.0) < 1e-6, 'mode1 pan=0 -> unity (hard left)')
    chk(abs(pan_gain(1.0, 1) - 0.0) < 1e-6, 'mode1 pan=1 -> silence')
    chk(abs(pan_gain(1.0, 2) - 1.0) < 1e-6, 'mode2 pan=1 -> unity (hard right)')
    chk(abs(pan_gain(0.0, 2) - 0.0) < 1e-6, 'mode2 pan=0 -> silence')
    for i in range(101):
        p = i / 100.0
        chk(abs(pan_gain(p, 1) ** 2 + pan_gain(p, 2) ** 2 - 1.0) < 0.06,
            'roughly constant power at %.2f' % p)

    # -- send dB -----------------------------------------------------------
    chk(mixer_send_db(0.0) == 0.0, 'unity')
    chk(mixer_send_db(0.0, muted=True) == -145.0, 'off sentinel')
    chk(abs(mixer_send_db(0.0, blend=0.5) + 6.0206) < 1e-3, 'blend halves = -6 dB')
    chk(abs(mixer_send_db(-10.0, bus_db=-6.0) + 16.0) < 1e-3, 'bus adds in dB')
    chk(mixer_send_db(-200.0) == -144.0, 'floor')

    # -- blobs -------------------------------------------------------------
    b = para_blob(3, 0.0)
    chk(len(b) == 0x14 and b[:4] == b'araP', 'Para blob')
    m = mprm_blob([(3, 0.0), (4, -6.0)])
    chk(len(m) == 0x1f0 and m[:4] == b'mrpm', 'mprm blob')
    chk(struct.unpack_from('<I', m, 0x1ec)[0] == 2, 'mprm count')
    chk(struct.unpack_from('<If', m, 0x0c) == (3, 0.0), 'mprm entry 0')
    chk(struct.unpack_from('<If', m, 0x14) == (4, -6.0), 'mprm entry 1')

    print('PAN_K = %.17g  (0x%08x)' % (PAN_K, struct.unpack('<I', struct.pack('<f', PAN_K))[0]))
    print('pan centre gain = %.9f  -> %.6f dB' % (pan_gain(0.5, 1), pan_db(0.5, 1)))
    print()
    print(' norm      dB          |  dB        norm')
    for n in (0.0, 0.004, 0.05, 0.09, 0.25, 0.47, 0.5, 0.735, 0.75, 1.0):
        print('  %-8.3f %-10.4f  |' % (n, taper_norm_to_db(n)), end='')
        d = -96 + n * 106
        print('  %-9.2f %.6f' % (d, taper_db_to_norm(d)))
    print()
    print('%d assertions passed' % ok)
