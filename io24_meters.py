#!/usr/bin/env python3
"""io24_spec.py -- UCNET metering datagrams, mixer taper/pan laws, reverb+FX blobs.

Everything here was re-derived from hwaccess/dspusbdevice.dll (PE32+, imagebase
0x180000000) and the io24 Cortex-M firmware embedded in it (load 0x60020000,
file 0x216030).  Self-test at the bottom; `python3 io24_spec.py` must print OK.
"""
import math
import struct

# ---------------------------------------------------------------- helpers
def f32(x):
    return struct.unpack('<f', struct.pack('<f', float(x)))[0]


# ======================================================================
# 1. METERING  --  UCNET 'MS' datagrams
# ======================================================================
# Builder: dspusbdevice.dll VA 0x180034030-0x180034ce8 (file 0x33430-0x340e8),
# slot 33 of the device vtable at 0x180437da0.
#
# Source struct = the 'JaSt' GetP reply BLOB, verified: the handler at
# 0x180033db0 tests `[r8]=='Appl'` and `[rdx]=='JaSt'` and passes rdx straight
# through.  blob+0x10 == payload+0x1c == repo slot 0, so
#          blob_offset = 0x10 + 4*slot          slot = (blob_offset-0x10)/4
# The io24 firmware (base JaSt serializer 0x6004df78) does
#          memcpy(blob+8, dev+0x116c, 0xa0)     -> 40 floats = slots -2..37
# so slots -2 and -1 (payload +0x14 / +0x18) are REAL meter values, not the
# echoed request header.  They are the Playback L/R pair.

MAGIC = b"UC\x00\x01"

# slot numbering is the repo's: slot N is at JaSt reply payload offset 0x1c+4N.
S_PLAYBACK_L, S_PLAYBACK_R = -2, -1      # payload +0x14, +0x18
S_VIRTA_L, S_VIRTA_R = 0, 1
S_VIRTB_L, S_VIRTB_R = 2, 3
S_IN1, S_IN2 = 4, 6
S_X, S_Y = 10, 11                        # always 0 on the io24
S_MAIN_L, S_MAIN_R = 12, 13
S_MIXA_L, S_MIXA_R = 14, 15
S_MIXB_L, S_MIXB_R = 16, 17
S_RED_MAIN = [18, 19]                    # main L/R gain reduction
S_RED_MIX = [20, 21, 22, 23]             # MixA L/R, MixB L/R
S_RED_CH = [24, 27, 30, 33]              # +0 gate, +1 comp, +2 lim

GID_INPUT, GID_RETURN, GID_MIX, GID_MAIN = 0, 1, 4, 7
ST_TOTAL, ST_GATE, ST_COMP, ST_LIM = 0x0000, 0x0100, 0x0200, 0x0400


def q16(f):
    """float -> u16, verbatim from the sender (comiss/mulss/cvttss2si)."""
    try:
        f = float(f)
    except (TypeError, ValueError):
        return 0
    if f != f:
        return 0
    if f >= 1.0:
        return 0xFFFF
    if f <= 0.0:
        return 0
    return int(f * 65535.0)              # cvttss2si == truncate toward zero


def meter_datagram(fourcc, groups, src=107, dst=104, port_field=0xDB6C):
    """fourcc: b'levl' | b'redu'.  groups: [(group_id, [float,...]), ...]"""
    values, table = [], []
    for gid, gv in groups:
        table.append((gid, len(values), len(gv)))
        values.extend(gv)
    assert len(values) <= 1024 and len(table) <= 42     # sender's own caps
    body = fourcc + struct.pack('<HH', 0, len(values))
    body += b''.join(struct.pack('<H', q16(v)) for v in values)
    body += bytes([len(table)])
    for gid, start, cnt in table:
        body += struct.pack('<HHH', gid, start, cnt)
    return (MAGIC + struct.pack('<H', port_field) + b'MS'
            + struct.pack('<HH', src, dst) + body)


class JaSt:
    """Slot accessor over a raw JaSt reply payload (or a float list)."""

    def __init__(self, payload):
        if isinstance(payload, (bytes, bytearray)):
            n = (len(payload) - 0x14) // 4
            self.v = list(struct.unpack_from('<%df' % n, payload, 0x14))
            self.base = -2                       # self.v[0] is slot -2
        else:
            self.v = list(payload)
            self.base = -2 if len(payload) == 40 else 0

    def __getitem__(self, slot):
        i = slot - self.base
        return self.v[i] if 0 <= i < len(self.v) else 0.0


def levl_groups(s, link=True):
    """s: JaSt (peak-held).  link=True -> 18 values / 81-byte datagram."""
    g0 = [s[S_IN1], s[S_IN2]]
    if link:                                     # flags bit 0x1000 == channelLink
        g0 += [s[S_IN1], s[S_IN2]]
    g0 += [s[S_X], s[S_Y]]
    return [
        (GID_INPUT,  g0),
        (GID_RETURN, [s[S_PLAYBACK_L], s[S_PLAYBACK_R],
                      s[S_VIRTA_L], s[S_VIRTA_R], s[S_VIRTB_L], s[S_VIRTB_R]]),
        (GID_MIX,    [s[S_MIXA_L], s[S_MIXA_R], s[S_MIXB_L], s[S_MIXB_R]]),
        (GID_MAIN,   [s[S_MAIN_L], s[S_MAIN_R]]),
    ]


def redu_groups(s):
    """s: JaSt (min-held).  22 values / 101-byte datagram."""
    gate = [s[b + 0] for b in S_RED_CH]
    comp = [s[b + 1] for b in S_RED_CH]
    lim = [s[b + 2] for b in S_RED_CH]
    total = [gate[i] * comp[i] * lim[i] for i in range(4)]
    return [
        (GID_INPUT | ST_GATE, gate),
        (GID_INPUT | ST_COMP, comp),
        (GID_INPUT | ST_LIM,  lim),
        (GID_INPUT | ST_TOTAL, total),
        (GID_MIX,  [s[x] for x in S_RED_MIX]),
        (GID_MAIN, [s[x] for x in S_RED_MAIN]),
    ]


class MeterHold:
    """levl peak-holds (max), redu min-holds; each set is reset after its frame."""

    SLOTS = range(-2, 38)

    def __init__(self):
        self.reset_levels()
        self.reset_reduction()

    def reset_levels(self):
        self.lvl = {k: 0.0 for k in self.SLOTS}

    def reset_reduction(self):
        self.red = {k: 1.0 for k in self.SLOTS}

    def feed(self, s):
        for k in self.SLOTS:
            v = s[k]
            if v > self.lvl[k]:
                self.lvl[k] = v
            if v < self.red[k]:
                self.red[k] = v

    def take_levels(self):
        out = JaSt([self.lvl[k] for k in self.SLOTS])
        self.reset_levels()
        return out

    def take_reduction(self):
        out = JaSt([self.red[k] for k in self.SLOTS])
        self.reset_reduction()
        return out


# ======================================================================
# 2. MIXER  --  'fader' taper, pan law, block 100 wire form, 'mprm'
# ======================================================================
# taper tables: .rdata 0x1800e9328 (file 0xe8528) for [-96,+10]
#               .rdata 0x1800e9378 (file 0xe8578) for [-84,+10]
# selected by setRange (0x18000ba50); descriptors volume(106)/aux1(124)/
# aux2(125)/FXA(145) are all min=-96 max=+10 taper="fader".
FADER_96 = ((0.000, -96.0), (0.004, -60.0), (0.090, -40.0),
            (0.470, -10.0), (1.000, +10.0))
FADER_84 = ((0.000, -84.0), (0.004, -60.0), (0.090, -40.0),
            (0.470, -10.0), (1.000, +10.0))


def taper_norm_to_db(norm, table=FADER_96):     # 0x18005cfe0
    lo, hi = table[0][1], table[-1][1]
    if hi - lo <= 0.0:
        return 0.0
    x = norm if norm >= 0.0 else 0.0
    if x > 1.0:
        x = 1.0
    for i in range(len(table) - 1):
        if x <= table[i + 1][0]:
            n0, d0 = table[i]
            n1, d1 = table[i + 1]
            return f32((x - n0) / (n1 - n0) * (d1 - d0) + d0)
    return hi


def taper_db_to_norm(db, table=FADER_96):       # 0x18005d080
    lo, hi = table[0][1], table[-1][1]
    if hi - lo <= 0.0:
        return 0.0
    v = lo if lo > db else (hi if db > hi else db)
    for i in range(len(table) - 1):
        if v <= table[i + 1][1]:
            n0, d0 = table[i]
            n1, d1 = table[i + 1]
            return f32((v - d0) / (d1 - d0) * (n1 - n0) + n0)
    return 1.0


PAN_K = f32(-0.8317830562591553)                # f32 0xbf54efbc @ 0x18049eb48
OFF_DB = -145.0                                 # @ 0x180481c54
FLOOR_DB = -144.0                               # @ 0x180481c50
FLOOR_LIN = f32(6.309573308271865e-08)          # @ 0x1804817dc


def pan_gain(pan, mode):
    """mode 1 = LEFT leg, mode 2 = RIGHT leg, 0 = no pan term."""
    if mode == 1:
        x = 1.0 - pan
    elif mode == 2:
        x = pan
    else:
        return 1.0
    return (x * PAN_K + (1.0 - PAN_K)) * x


def pan_db(pan, mode):
    g = pan_gain(pan, mode)
    return FLOOR_DB if g < FLOOR_LIN else 20.0 * math.log10(g)


def mixer_send_db(volume_db, bus_db=0.0, blend=1.0,
                  pan=None, pan_mode=0, muted=False):
    """computeDb 0x1800570e0 -- the float that actually goes on the wire."""
    if muted:
        return OFF_DB
    g = FLOOR_LIN if volume_db < FLOOR_DB else 10.0 ** (volume_db * 0.05)
    g *= blend
    db = FLOOR_DB if g < FLOOR_LIN else 20.0 * math.log10(g)
    db += bus_db
    if pan is not None and pan_mode in (1, 2):
        db += pan_db(pan, pan_mode)
    return db if db >= FLOOR_DB else FLOOR_DB


# --- wire form ---------------------------------------------------------
MIX_SLOT = {('return', 1): 0, ('return', 2): 1, ('return', 3): 2,
            ('line', 1): 3, ('line', 2): 4, ('fxreturn', 1): 5,
            ('line', 3): 6}
MIX_BUS = {'main': 0, 'mixa': 1, 'mixb': 2}


def para_blob(param_id, value_f32, index=0):
    return struct.pack('<IIIIf', 0x50617261, 0x14, index, param_id, value_f32)


def mprm_blob(entries, index=0):
    """entries: [(paramId, gain_db), ...] up to 60."""
    assert len(entries) <= 60
    b = bytearray(0x1f0)
    struct.pack_into('<III', b, 0, 0x6d70726d, 0x1f0, index)
    for i, (pid, db) in enumerate(entries):
        struct.pack_into('<If', b, 0x0c + 8 * i, pid, db)
    struct.pack_into('<I', b, 0x1ec, len(entries))
    return bytes(b)


# ======================================================================
# 3. REVERB (block 202) and INSERT FX (block 201)
# ======================================================================
def hdr(payload, uid=1):
    return struct.pack('<HBBBBH', len(payload) + 8, 1, 1, uid, 0, 0) + payload


def setp(block, blob, blockindex=0, uid=1):
    return hdr(struct.pack('<III', 0x53657450, block, blockindex) + blob, uid)


def rbj_hp2(freq, fs=48000.0, Q=0.7):
    """Designer 0x180010d30 type 3 -> 0x180011f5d, EXACTLY as disassembled:
       K=tan(pi*f/fs); norm=1+K/Q+K^2
       [b0, -a1, b1, -a2, b2] = [1/n, 2(1-K^2)/n, -2/n, (K/Q-1-K^2)/n, 1/n]"""
    K = math.tan(math.pi * freq / fs)
    n = 1.0 + K / Q + K * K
    return [f32(1.0 / n), f32(2.0 * (1.0 - K * K) / n), f32(-2.0 / n),
            f32((K / Q - 1.0 - K * K) / n), f32(1.0 / n)]


def reverb_blob(on=True, size=0.15, mix=0.5, hp_freq=200.0, predelay=0.02,
                fs=48000.0, index=0):
    on = 1 if on else 0
    size = min(max(size, 0.0), 1.0)
    mix = min(max(mix, 0.0), 1.0)
    hp_freq = min(max(hp_freq, 0.0), 500.0)
    predelay = min(max(predelay, 0.0001), 0.25)
    pd_en = 1 if predelay > 0.0001 else 0
    c = rbj_hp2(hp_freq, fs, 0.7) if hp_freq > 0.1 else [1.0, 0.0, 0.0, 0.0, 0.0]
    b = struct.pack('<IIIIfIfff', 0x76727662, 0x38, index,
                    on, mix, pd_en, predelay, size, hp_freq)
    b += struct.pack('<5f', *c)
    assert len(b) == 0x38
    return b


def set_reverb(**kw):
    return setp(202, reverb_blob(**kw))


def set_fx_model(model):
    assert 0 <= model <= 5
    return setp(201, struct.pack('<IIII', 0x566f4678, 0x10, 0, model))


def fx_delay(on, time_s, feedback, mix):
    """model 5, tag 'vech', size 0x1c. Fully traced: setParam 0x180020920,
       push 0x1800209c0 -> payload [on, mix, feedback*0.5, time]."""
    return struct.pack('<III', 0x76656368, 0x1c, 0) + struct.pack(
        '<Ifff', 1 if on else 0, mix, f32(feedback * 0.5), time_s)


# ======================================================================
# self-test
# ======================================================================
if __name__ == '__main__':
    # -- metering: trailers must equal oddbear's hard-coded constants --------
    s = JaSt([0.0] * 40)
    lv = meter_datagram(b'levl', levl_groups(s, link=True))
    rd = meter_datagram(b'redu', redu_groups(JaSt([1.0] * 40)))
    assert len(lv) == 81 and len(rd) == 101, (len(lv), len(rd))
    assert lv[56:].hex().upper() == \
        '0400000000060001000600060004000C000400070010000200'
    assert rd[64:].hex().upper() == \
        ('0600010000040000020400040000040800040000000C000400040010000400'
         '070014000200')
    lv77 = meter_datagram(b'levl', levl_groups(s, link=False))
    assert len(lv77) == 77
    assert lv[12:16] == b'levl' and rd[12:16] == b'redu'
    assert q16(1.0) == 0xFFFF and q16(0.0) == 0 and q16(0.5) == 32767
    assert q16(0.0316) == 0x0816 and q16(0.99991) == 0xFFF9

    # field positions must match MonitorService.cs's 81-byte branch
    f = [0.0] * 40
    fl = JaSt(f)

    def put(slot, v):
        f[slot + 2] = v
    put(S_IN1, .1); put(S_IN2, .2)
    put(S_PLAYBACK_L, .3); put(S_PLAYBACK_R, .4)
    put(S_VIRTA_L, .5); put(S_VIRTA_R, .6)
    put(S_VIRTB_L, .7); put(S_VIRTB_R, .8)
    put(S_MIXA_L, .11); put(S_MIXA_R, .12)
    put(S_MIXB_L, .13); put(S_MIXB_R, .14)
    put(S_MAIN_L, .15); put(S_MAIN_R, .16)
    d = meter_datagram(b'levl', levl_groups(JaSt(f), link=True))
    g = lambda off: struct.unpack_from('<H', d, off)[0]
    assert g(20) == q16(.1) and g(22) == q16(.2)          # Microphone_L/R
    assert g(32) == q16(.3) and g(34) == q16(.4)          # Playback_L/R
    assert g(36) == q16(.5) and g(38) == q16(.6)          # VirtualOutputA
    assert g(40) == q16(.7) and g(42) == q16(.8)          # VirtualOutputB
    assert g(44) == q16(.11) and g(46) == q16(.12)        # StreamMix1
    assert g(48) == q16(.13) and g(50) == q16(.14)        # StreamMix2
    assert g(52) == q16(.15) and g(54) == q16(.16)        # Main

    r = [1.0] * 40
    r[24 + 2] = 0.7079458   # ch1 gate  -3 dB
    r[25 + 2] = 0.5011872   # ch1 comp  -6 dB
    dr = meter_datagram(b'redu', redu_groups(JaSt(r)))
    gr = lambda off: struct.unpack_from('<H', dr, off)[0]
    assert gr(20) == q16(0.7079458)                       # gateL_A
    assert gr(28) == q16(0.5011872)                       # compressor VU
    assert gr(44) == q16(0.7079458 * 0.5011872)           # GainReductionMeter_L
    assert gr(46) == 0xFFFF                               # GainReductionMeter_R

    # -- mixer taper -------------------------------------------------------
    assert abs(taper_norm_to_db(0.735) - 0.0) < 1e-4
    assert abs(taper_norm_to_db(0.470) + 10.0) < 1e-4
    assert abs(taper_norm_to_db(0.090) + 40.0) < 1e-4
    assert abs(taper_db_to_norm(0.0) - 0.735) < 1e-6
    assert abs(taper_db_to_norm(-6.0) - 0.576) < 1e-6
    assert taper_norm_to_db(0.0) == -96.0 and taper_norm_to_db(1.0) == 10.0
    for k in range(1001):                 # round trip
        n = k / 1000.0
        assert abs(taper_db_to_norm(taper_norm_to_db(n)) - n) < 2e-6, n
    # oddbear VolumeValue.cs equivalence
    A = (1.0, 0.47, 0.09, 0.004, 0.0)
    B = (10.0, -10.0, -40.0, -60.0, -96.0)

    def volumevalue(v):
        for i in range(4):
            if v >= A[i + 1]:
                return B[i + 1] + (v - A[i + 1]) / (A[i] - A[i + 1]) * (B[i] - B[i + 1])
        return -96.0
    assert max(abs(volumevalue(k / 1000.0) - taper_norm_to_db(k / 1000.0))
               for k in range(1001)) < 2e-4

    # -- pan law -----------------------------------------------------------
    assert abs(pan_db(0.5, 1) + 3.0) < 1e-4 and abs(pan_db(0.5, 2) + 3.0) < 1e-4
    assert abs(pan_gain(0.0, 1) - 1.0) < 1e-6 and pan_gain(0.0, 2) == 0.0
    assert mixer_send_db(0.0) == 0.0
    assert mixer_send_db(-10.0, bus_db=-6.0) == -16.0
    assert mixer_send_db(0.0, muted=True) == -145.0
    assert abs(mixer_send_db(0.0, blend=0.5) + 6.0206) < 1e-3

    # -- mprm --------------------------------------------------------------
    m = mprm_blob([(3, 0.0), (4, -10.0)])
    assert len(m) == 0x1f0
    assert struct.unpack_from('<III', m, 0) == (0x6d70726d, 0x1f0, 0)
    assert struct.unpack_from('<If', m, 0x0c) == (3, 0.0)
    assert struct.unpack_from('<If', m, 0x14) == (4, -10.0)
    assert struct.unpack_from('<I', m, 0x1ec)[0] == 2

    # -- reverb ------------------------------------------------------------
    rb = reverb_blob()
    assert len(rb) == 0x38 and rb[:4] == b'bvrv'
    msg = set_reverb()
    assert len(msg) == 8 + 12 + 0x38 == 76
    assert struct.unpack_from('<I', msg, 8)[0] == 0x53657450
    assert struct.unpack_from('<I', msg, 12)[0] == 202
    off = reverb_blob(hp_freq=0.0)
    assert struct.unpack_from('<5f', off, 0x24) == (1.0, 0.0, 0.0, 0.0, 0.0)
    # HP2 designer matches the repo's already-verified 'filt' formula shape
    c = rbj_hp2(200.0, 48000.0, 0.7)
    assert abs(c[0] - c[4]) < 1e-9 and abs(c[2] + 2 * c[0]) < 1e-6
    vf = set_fx_model(5)
    assert vf[8:12] == b'PteS' and struct.unpack_from('<I', vf, 12)[0] == 201
    assert vf[20:24] == b'xFoV' and struct.unpack_from('<I', vf, 24)[0] == 0x10
    assert struct.unpack_from('<I', vf, 32)[0] == 5

    print("OK  --", len(lv), "byte levl,", len(rd), "byte redu,",
          len(set_reverb()), "byte reverb SetP")
    print("levl:", lv.hex())
    print("redu:", rd.hex())
    print("rvrb:", set_reverb().hex())
