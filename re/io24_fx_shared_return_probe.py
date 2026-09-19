#!/usr/bin/env python3
"""Does block 201 process audio on the bus its output actually reaches?

Every CP34 block-201 measurement ratioed the JaSt `main`/`mixa`/`mixb` meters
against Input 1 without opening the channel FX send or assigning
`fxreturn/ch1` into the bus it measured.  That is the channel's DIRECT path.
Hardware, 2026-07-28 (`memory/io24-native-protocol-CRACKED.md`): block 201 is
NOT a true insert -- it needs the same send (`'Para'` id 4) and the same return
(mixer paramId 5, `fxreturn/ch1`) as the reverb, an armed Delay is silent with
either closed, and restoring both brings it back immediately.  So the campaign's
nulls were taken on the one path the block does not reach.

This probe observes the return, and it gates its own stimulus: bursts of tone
plus noise separated by silence.  A silent gap is the strongest evidence there
is, because nothing but an effect's own tail can put energy into it -- a level
ratio over a continuous signal is blind to four of the six models, and a
continuous tone defeats the autocorrelation test outright, since a tone is
already self-similar at every lag that is a whole number of its periods.

  delay        energy at burst end + k * 250 ms, inside the gap
  reverb       a decaying tail in the gap -- the in-run positive control
  ring mod     sidebands at |f +/- carrier| within the bursts, two carriers
  de-tuner     a partner partial at f * 2**(-8/12)
  transformer  broadband level only; retained for continuity, never votes

If the reverb does not put a tail in the gap, the run is invalid and says
nothing about block 201.  That is the mistake this probe exists to stop
repeating.

RIG (user-prepared, 2026-09-15): Main Out L -> Input 1, input gain 23 dB,
monitors at medium, MUTE off, and a deliberate mild feedback loop.  The loop's
own decay is short and lives in the first tens of milliseconds of each gap, so
the gap analysis starts after a guard interval and the loop is excluded by
construction rather than by assumption.

SAFETY, by construction
  * Nothing that feeds Main is written.  The only SetP frames are block 100 at
    the Mix A bus index, block 202 (reverb) and block 201 (the FX models).  A
    single 'Appl' write -- gain, volume, processing scalar, slot, phantom, link
    -- or any mixer frame at the Main bus index fails the run;
    `validate_transport_log` makes that checkable afterwards, so the loop gain
    the user set is the loop gain throughout.
  * The probe refuses to run if Channel 1 is bypassed, rather than un-bypassing
    it: that would change what reaches Main, and so the loop.
  * Control writes and audio streams are strictly serialised.  Concurrent
    streaming plus control writes is the known cause of this unit dropping to
    its bootloader, so no write is ever issued while arecord or aplay runs.
  * The FX return is assigned into Mix A only -- a USB capture bus, which
    cannot feed the loop -- so a fully wet delay cannot run away through the
    user's monitors.

Mixer sends are write-only on this firmware.  The prior Mix A return level
cannot be read back; the Host shadow is consulted for an exact prior value and,
absent one, restoration writes the off sentinel and says so.

Live execution requires --execute.
"""

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
RE_DIR = Path(__file__).resolve().parent
for _directory in (ROOT, RE_DIR):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import numpy as np  # noqa: E402

import io24_fx  # noqa: E402
import io24_loopback_foundation as foundation  # noqa: E402


SCHEMA = "io24-fx-shared-return-probe-v2"

RATE = foundation.RATE
CHANNELS = foundation.CHANNELS
MIX_A_CHANNELS = foundation.MIX_A_CHANNELS
CAPTURE_ENDPOINT = foundation.CAPTURE_ENDPOINT
# Capture can open the card directly, but PipeWire holds the playback
# substream (`/dev/snd/pcmC1D0p`), so `aplay -D hw:` fails "Device or resource
# busy". Playback therefore goes through PipeWire, targeted at the io24 sink by
# name. The target is resolved and checked against the expected serial rather
# than trusted: sending the stimulus to the laptop speakers instead would
# produce a silent, confident null -- the exact class of error this probe
# exists to end.
PLAYBACK_SINK_SUBSTRING = foundation.EXPECTED_SERIAL

# The gated stimulus.  Bursts long enough to resolve sidebands, gaps long
# enough to hold three delay repeats at 250 ms.
BURST_SECONDS = 0.5
GAP_SECONDS = 1.0
CYCLES = 5
STIMULUS_LEAD_SECONDS = 0.35
EDGE_SECONDS = 0.005
STIMULUS_RMS_DBFS = -30.0
STIMULUS_CHANNELS = 2                # front left carries it; the cable is Main L
STIMULUS_TONES = (800.0, 1234.0)     # unrelated, so their sidebands are distinct
STIMULUS_NOISE_BELOW_DB = 12.0       # broadband bed for the time-domain tests
CAPTURE_SECONDS = 10
SETTLE_SECONDS = 1.0

RETURN_SOURCE = "fxreturn/ch1"
RETURN_BUS = "mixa"
RETURN_DB = 0.0

ALLOWED_BLOCKS = (100, 201, 202)
MIXER_BLOCK = 100
ALLOWED_MIXER_BUS_INDEX = 1          # io24.Io24.MIXER_BUSES["mixa"]

REVERB_CONTROL = {"size": 0.95, "mix": 1.0, "predelay": 0.02,
                  "hp_freq": 200.0}

RINGMOD_CARRIERS = (146.85, 313.7)
DETUNE_INDEX = 0                     # index 0 = -8 semitones
DETUNE_RATIO = 2.0 ** (-8.0 / 12.0)
DELAY_TIME_S = 0.25
DELAY_TAPS = (1, 2, 3)

# Skip the head of each gap: the user's analog loop decays there, and so does
# the burst's own release.  Everything measured after it can only be a tail the
# device generated.
GAP_GUARD_SECONDS = 0.06
GAP_ANALYSIS_SECONDS = 0.85
TAP_WINDOW_SECONDS = 0.04

MIN_BURST_PEAK_DBFS = -70.0
MIN_BURSTS = 3
CONTROL_MIN_GAP_RISE_DB = 4.0
GAP_MIN_RISE_DB = 4.0
TAP_MIN_RISE_DB = 6.0
OFF_DRIFT_MAX_DB = 2.0
SIDEBAND_MIN_DB = 6.0
GUARD_MAX_DB = 3.0
AUTOCORR_MIN_DELTA = 0.10
AUTOCORR_TONAL_MAX = 0.80
BAND_HALF_WIDTH_HZ = 6.0
# Digital silence has no dB value. Levels need arithmetic, so an all-zero
# segment reads as this floor rather than as unknown; spectral bands keep None,
# where "no component" is the honest answer.
SILENCE_FLOOR_DBFS = -200.0
MIN_GATE_CONTRAST_DB = 6.0


class FxReturnProbeError(RuntimeError):
    """Fail closed; no further mutation is attempted."""


def _now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def _dbfs(value):
    return None if value is None or value <= 0.0 else 20.0 * math.log10(value)


# ----------------------------------------------------------------- stimulus

def resolve_playback_sink(dump=None, runner=subprocess.run,
                          expect=PLAYBACK_SINK_SUBSTRING):
    """Return the io24's PipeWire sink node name, or fail closed.

    Never falls back to a default sink: a default that is the laptop's own
    output would send the stimulus nowhere near the unit and every model would
    read as a confident null.
    """
    if dump is None:
        completed = runner(["pw-dump"], capture_output=True, text=True)
        if completed.returncode != 0:
            raise FxReturnProbeError(
                "pw-dump failed: %s" % (completed.stderr or "").strip())
        dump = completed.stdout
    try:
        objects = json.loads(dump)
    except ValueError as error:
        raise FxReturnProbeError("pw-dump output was not JSON: %s" % error)
    matches = []
    for entry in objects:
        props = ((entry.get("info") or {}).get("props") or {})
        name = props.get("node.name") or ""
        if str(props.get("media.class", "")).startswith("Audio/Sink") \
                and expect in name:
            matches.append(name)
    if not matches:
        raise FxReturnProbeError(
            "no PipeWire sink carries %s; refusing to play the stimulus into "
            "an unknown output" % expect)
    if len(set(matches)) > 1:
        raise FxReturnProbeError(
            "several PipeWire sinks carry %s: %s" % (expect, ", ".join(matches)))
    return matches[0]


def build_stimulus(path, rate=RATE, channels=STIMULUS_CHANNELS):
    """Write the gated stimulus: silence, then CYCLES of burst plus gap.

    Deterministic, so two runs are comparable byte for byte.  The signal goes
    on playback channel 0 only, because the cable is Main Out L -> Input 1.
    """
    path = Path(path)
    if path.exists():
        raise FxReturnProbeError("stimulus path already exists: %s" % path)
    burst = int(round(BURST_SECONDS * rate))
    gap = int(round(GAP_SECONDS * rate))
    lead = int(round(STIMULUS_LEAD_SECONDS * rate))
    total = lead + CYCLES * (burst + gap)
    mono = np.zeros(total, dtype=np.float64)

    t = np.arange(burst) / float(rate)
    shape = np.zeros(burst)
    for hz in STIMULUS_TONES:
        shape += np.sin(2.0 * math.pi * hz * t)
    rng = np.random.default_rng(0x1024)
    noise = rng.normal(0.0, 1.0, burst)
    noise *= (np.sqrt(np.mean(np.square(shape))) /
              np.sqrt(np.mean(np.square(noise)))) * \
        10.0 ** (-STIMULUS_NOISE_BELOW_DB / 20.0)
    shape = shape + noise
    shape *= 10.0 ** (STIMULUS_RMS_DBFS / 20.0) / \
        np.sqrt(np.mean(np.square(shape)))
    edge = max(1, int(round(EDGE_SECONDS * rate)))
    ramp = 0.5 * (1.0 - np.cos(np.linspace(0.0, math.pi, edge)))
    shape[:edge] *= ramp
    shape[-edge:] *= ramp[::-1]

    for cycle in range(CYCLES):
        start = lead + cycle * (burst + gap)
        mono[start:start + burst] = shape

    frames = np.zeros((total, channels), dtype=np.float64)
    frames[:, 0] = mono
    pcm = np.rint(np.clip(frames, -1.0, 1.0) * (2 ** 31 - 1)).astype("<i4")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(4)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())
    return path


# ----------------------------------------------------------------- analysis

def read_capture(path):
    """Return (rate, frames) as float64 in -1..1, shaped (n, channels)."""
    with wave.open(str(path), "rb") as handle:
        if handle.getsampwidth() != 4:
            raise FxReturnProbeError("capture must be 32-bit")
        channels = handle.getnchannels()
        rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    data = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    if channels <= 0 or data.size % channels:
        raise FxReturnProbeError("capture frame count is not a whole number")
    return rate, data.reshape(-1, channels)


def bus_signal(frames, channels=MIX_A_CHANNELS):
    """One mono view of a stereo bus, as the mean of its two capture legs."""
    return frames[:, list(channels)].mean(axis=1)


def rms_dbfs(signal):
    if signal.size == 0:
        return None
    value = float(np.sqrt(np.mean(np.square(signal))))
    return SILENCE_FLOOR_DBFS if value <= 0.0 else 20.0 * math.log10(value)


def envelope(signal, rate=RATE, window_s=0.02):
    """Moving-RMS envelope, for finding where the bursts are."""
    width = max(1, int(round(window_s * rate)))
    kernel = np.ones(width) / float(width)
    return np.sqrt(np.convolve(np.square(signal), kernel, mode="same"))


def find_bursts(signal, rate=RATE, minimum_s=0.25):
    """Locate the stimulus bursts from the capture's own envelope.

    Found rather than assumed: arecord and aplay start independently, so the
    burst offsets in the capture are not known in advance.
    """
    env = envelope(signal, rate)
    peak = float(np.percentile(env, 99.0))
    if peak <= 0.0:
        return []
    above = env >= peak * 0.25
    minimum = int(round(minimum_s * rate))
    bursts = []
    start = None
    for index, flag in enumerate(above):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            if index - start >= minimum:
                bursts.append((start, index))
            start = None
    if start is not None and above.size - start >= minimum:
        bursts.append((start, int(above.size)))
    return bursts


def align_bursts(signal, rate=RATE):
    """Find the gate by matching the known pattern, not by thresholding.

    An effect with a tail puts energy into the gaps, which moves an envelope
    threshold's idea of where a burst ENDS -- the delay's own repeats were
    being absorbed into a longer "burst" and its tap windows pushed into the
    next cycle. The stimulus pattern is known exactly, so every window is
    derived from a single alignment offset and is therefore the same window in
    the armed and unarmed captures.
    """
    step = max(1, rate // 1000)                   # a 1 ms envelope is plenty
    env = envelope(signal, rate)[::step]
    burst = int(round(BURST_SECONDS * 1000))
    gap = int(round(GAP_SECONDS * 1000))
    one = np.concatenate([np.ones(burst), -np.ones(gap)])
    template = np.tile(one, CYCLES)
    if env.size <= template.size:
        return [], None
    scores = np.correlate(env, template, mode="valid")
    offset = int(np.argmax(scores))
    period = burst + gap
    length = int(round(BURST_SECONDS * rate))
    bursts = []
    for cycle in range(CYCLES):
        start = (offset + cycle * period) * step
        if start + length <= signal.size:
            bursts.append((start, start + length))
    return bursts, float(scores[offset])


def burst_slices(signal, bursts):
    """The stimulus itself, concatenated, for the spectral tests."""
    if not bursts:
        return np.zeros(0)
    return np.concatenate([signal[start:stop] for start, stop in bursts])


def gap_slices(signal, bursts, rate=RATE):
    """The silences after each burst, past the guard interval.

    Only an effect's own tail can live here. The guard skips the burst release
    and the analog loop's short decay.
    """
    guard = int(round(GAP_GUARD_SECONDS * rate))
    length = int(round(GAP_ANALYSIS_SECONDS * rate))
    pieces = []
    for index, (_start, stop) in enumerate(bursts):
        begin = stop + guard
        end = begin + length
        limit = bursts[index + 1][0] if index + 1 < len(bursts) else signal.size
        end = min(end, limit)
        if end - begin > rate // 20:
            pieces.append(signal[begin:end])
    return np.concatenate(pieces) if pieces else np.zeros(0)


def tap_windows(signal, bursts, lag_seconds=DELAY_TIME_S, taps=DELAY_TAPS,
                rate=RATE):
    """Short windows where a delay's repeats must land, per tap number."""
    half = max(1, int(round(TAP_WINDOW_SECONDS * rate / 2)))
    result = {}
    for tap in taps:
        offset = int(round(tap * lag_seconds * rate))
        pieces = []
        for index, (_start, stop) in enumerate(bursts):
            centre = stop + offset
            begin, end = centre - half, centre + half
            limit = bursts[index + 1][0] if index + 1 < len(bursts) \
                else signal.size
            if begin < 0 or end > limit:
                continue
            pieces.append(signal[begin:end])
        result[tap] = np.concatenate(pieces) if pieces else np.zeros(0)
    return result


def spectrum(signal, rate=RATE):
    """Hann-windowed magnitude spectrum, normalised so a full-scale sine is 1."""
    if signal.size < 1024:
        raise FxReturnProbeError("segment is too short to analyse")
    window = np.hanning(signal.size)
    mags = np.abs(np.fft.rfft(signal * window)) * (4.0 / signal.size)
    freqs = np.fft.rfftfreq(signal.size, 1.0 / rate)
    return freqs, mags


def band_dbfs(freqs, mags, centre, half_width_hz=BAND_HALF_WIDTH_HZ):
    """The strongest component within +/- half_width of a frequency, in dBFS."""
    if centre <= 0.0 or centre >= freqs[-1]:
        return None
    mask = np.abs(freqs - centre) <= half_width_hz
    if not mask.any():
        return None
    return _dbfs(float(mags[mask].max()))


def dominant_partial(freqs, mags, low_hz=60.0, high_hz=6000.0):
    """The stimulus partial the spectral tests are referenced to."""
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    if not mask.any():
        raise FxReturnProbeError("no analysable band in the capture")
    index = int(np.argmax(np.where(mask, mags, 0.0)))
    return {"hz": float(freqs[index]), "dbfs": _dbfs(float(mags[index]))}


def autocorrelation_at(signal, lag_seconds, rate=RATE, tolerance_s=0.02):
    """Normalised autocorrelation near one lag."""
    lag = int(round(lag_seconds * rate))
    span = int(round(tolerance_s * rate))
    if lag + span >= signal.size:
        raise FxReturnProbeError("segment is shorter than the tested lag")
    centred = signal - signal.mean()
    best = 0.0
    for offset in range(max(1, lag - span), lag + span + 1):
        first, second = centred[offset:], centred[:-offset]
        # Normalise by the energy of the OVERLAPPING segments. Dividing by the
        # whole signal's energy scales every value by the overlap fraction, so
        # a perfectly self-similar tone reads well under 1.0 and the tonality
        # gate never fires.
        scale = math.sqrt(float(np.dot(first, first)) *
                          float(np.dot(second, second)))
        if scale <= 0.0:
            continue
        best = max(best, float(np.dot(first, second)) / scale)
    return best


def analyse_stage(path, channels=MIX_A_CHANNELS):
    """Everything one capture contributes, with no comparison yet."""
    rate, frames = read_capture(path)
    signal = bus_signal(frames, channels)
    bursts, alignment = align_bursts(signal, rate)
    inside = burst_slices(signal, bursts)
    gaps = gap_slices(signal, bursts, rate)
    stage = {
        "capture": Path(path).name,
        "rate_hz": rate,
        "frames": int(frames.shape[0]),
        "bursts_found": len(bursts),
        "gate_alignment_score": alignment,
        "burst_seconds": inside.size / float(rate),
        "gap_seconds": gaps.size / float(rate),
        "rms_dbfs": rms_dbfs(signal),
        "burst_rms_dbfs": rms_dbfs(inside),
        "gap_rms_dbfs": rms_dbfs(gaps),
        "channel_rms_dbfs": [rms_dbfs(frames[:, index])
                             for index in range(frames.shape[1])],
        "tap_rms_dbfs": {},
        "_signal": signal,
        "_bursts": bursts,
        "_inside": inside,
        "_gaps": gaps,
    }
    for tap, segment in tap_windows(signal, bursts, rate=rate).items():
        stage["tap_rms_dbfs"][str(tap)] = rms_dbfs(segment)
    if inside.size >= 1024:
        freqs, mags = spectrum(inside, rate)
        stage["_freqs"], stage["_mags"] = freqs, mags
        stage["dominant_partial"] = dominant_partial(freqs, mags)
    else:
        stage["_freqs"] = stage["_mags"] = None
        stage["dominant_partial"] = {"hz": None, "dbfs": None}
    return stage


def _delta(after, before):
    if after is None or before is None:
        return None
    return after - before


def classify_gap_energy(off, on, minimum_db=GAP_MIN_RISE_DB):
    """Tail evidence: energy in the silence that was not there before."""
    rise = _delta(on["gap_rms_dbfs"], off["gap_rms_dbfs"])
    return {
        "off_gap_rms_dbfs": off["gap_rms_dbfs"],
        "on_gap_rms_dbfs": on["gap_rms_dbfs"],
        "delta_db": rise,
        "burst_delta_db": _delta(on["burst_rms_dbfs"], off["burst_rms_dbfs"]),
        "detected": bool(rise is not None and rise >= minimum_db),
    }


def classify_repeat_taps(off, on):
    """Delay evidence at its most direct: is there a repeat where one is due?

    The gated stimulus is what makes this readable — each tap window sits in
    silence, so a rise there is a copy of the burst arriving late and can be
    nothing else.
    """
    taps = {}
    rises = []
    for tap in DELAY_TAPS:
        key = str(tap)
        before = off["tap_rms_dbfs"].get(key)
        after = on["tap_rms_dbfs"].get(key)
        rise = _delta(after, before)
        taps[key] = {
            "at_s": tap * DELAY_TIME_S,
            "off_rms_dbfs": before,
            "on_rms_dbfs": after,
            "delta_db": rise,
        }
        if rise is not None:
            rises.append(rise)
    return {
        "lag_s": DELAY_TIME_S,
        "taps": taps,
        "max_rise_db": max(rises) if rises else None,
        "detected": bool(rises and max(rises) >= TAP_MIN_RISE_DB),
    }


def classify_sidebands(off, on, partial_hz, carrier_hz):
    """Ring-mod evidence: new energy at |f0 +/- carrier| and nowhere empty.

    The guard bands sit at half the carrier offset, where a ring modulator puts
    nothing.  A broadband level change lifts guards and sidebands together and
    therefore does not qualify.
    """
    if partial_hz is None or off["_freqs"] is None or on["_freqs"] is None:
        return {"carrier_hz": carrier_hz, "partial_hz": partial_hz,
                "inconclusive": True, "detected": False,
                "reason": "no analysable burst content"}
    targets = {"lower_hz": abs(partial_hz - carrier_hz),
               "upper_hz": partial_hz + carrier_hz}
    guards = {"guard_lower_hz": abs(partial_hz - carrier_hz / 2.0),
              "guard_upper_hz": partial_hz + carrier_hz / 2.0}
    result = {"carrier_hz": carrier_hz, "partial_hz": partial_hz,
              "bands": {}, "guards": {}, "inconclusive": False}
    rises, guard_rises = [], []
    for name, centre in targets.items():
        before = band_dbfs(off["_freqs"], off["_mags"], centre)
        after = band_dbfs(on["_freqs"], on["_mags"], centre)
        rise = _delta(after, before)
        result["bands"][name] = {"hz": centre, "off_dbfs": before,
                                 "on_dbfs": after, "delta_db": rise}
        rises.append(rise)
    for name, centre in guards.items():
        before = band_dbfs(off["_freqs"], off["_mags"], centre)
        after = band_dbfs(on["_freqs"], on["_mags"], centre)
        rise = _delta(after, before)
        result["guards"][name] = {"hz": centre, "off_dbfs": before,
                                  "on_dbfs": after, "delta_db": rise}
        guard_rises.append(rise)
    usable = [value for value in rises if value is not None]
    guard_usable = [value for value in guard_rises if value is not None]
    result["max_sideband_rise_db"] = max(usable) if usable else None
    result["max_guard_rise_db"] = max(guard_usable) if guard_usable else None
    result["detected"] = bool(
        usable and guard_usable and max(usable) >= SIDEBAND_MIN_DB
        and max(guard_usable) <= GUARD_MAX_DB)
    return result


def classify_shift(off, on, partial_hz, ratio=DETUNE_RATIO):
    """De-tuner evidence: a partner partial at a fixed frequency ratio."""
    if partial_hz is None or off["_freqs"] is None or on["_freqs"] is None:
        return {"partial_hz": partial_hz, "inconclusive": True,
                "detected": False, "reason": "no analysable burst content"}
    centre = partial_hz * ratio
    guard = partial_hz * ((1.0 + ratio) / 2.0)
    before = band_dbfs(off["_freqs"], off["_mags"], centre)
    after = band_dbfs(on["_freqs"], on["_mags"], centre)
    guard_before = band_dbfs(off["_freqs"], off["_mags"], guard)
    guard_after = band_dbfs(on["_freqs"], on["_mags"], guard)
    rise = _delta(after, before)
    guard_rise = _delta(guard_after, guard_before)
    return {
        "partial_hz": partial_hz, "shifted_hz": centre, "ratio": ratio,
        "off_dbfs": before, "on_dbfs": after, "delta_db": rise,
        "guard": {"hz": guard, "off_dbfs": guard_before,
                  "on_dbfs": guard_after, "delta_db": guard_rise},
        "inconclusive": False,
        "detected": bool(rise is not None and guard_rise is not None
                         and rise >= SIDEBAND_MIN_DB
                         and guard_rise <= GUARD_MAX_DB),
    }


def classify_autocorrelation(off, on, lag_seconds=DELAY_TIME_S, rate=RATE):
    """A third delay reading, over the whole capture.

    Reports inconclusive, not a null, when the signal is too self-similar at
    the tested lag for an echo to change it.
    """
    before = autocorrelation_at(off["_signal"], lag_seconds, rate)
    after = autocorrelation_at(on["_signal"], lag_seconds, rate)
    tonal = before >= AUTOCORR_TONAL_MAX
    return {
        "lag_s": lag_seconds,
        "off_autocorrelation": before, "on_autocorrelation": after,
        "delta": after - before,
        "stimulus_too_tonal": bool(tonal), "inconclusive": bool(tonal),
        "detected": bool(not tonal and after - before >= AUTOCORR_MIN_DELTA),
    }


def classify_level(off, on):
    """The old broadband metric, reported for continuity and never voting.

    Four of the six models are close to energy-preserving, so this number is as
    capable of a false null as of a false positive from ordinary bus drift.
    """
    delta = _delta(on["rms_dbfs"], off["rms_dbfs"])
    return {"off_rms_dbfs": off["rms_dbfs"], "on_rms_dbfs": on["rms_dbfs"],
            "delta_db": delta, "detected": None}


def classify_run(stages, trials):
    """Decide the run: rig validity first, then each model on its own evidence."""
    baseline = stages["return_open"]
    control_off = stages["control_off"]
    control_on = stages["control_reverb"]

    partial = baseline["dominant_partial"]
    contrast = _delta(baseline["burst_rms_dbfs"], baseline["gap_rms_dbfs"])
    stimulus_ok = bool(baseline["bursts_found"] >= MIN_BURSTS
                       and partial["dbfs"] is not None
                       and partial["dbfs"] >= MIN_BURST_PEAK_DBFS
                       and contrast is not None
                       and contrast >= MIN_GATE_CONTRAST_DB)
    control = classify_gap_energy(control_off, control_on,
                                  CONTROL_MIN_GAP_RISE_DB)
    control_ok = bool(control["detected"])
    off_drift = _delta(control_off["gap_rms_dbfs"], baseline["gap_rms_dbfs"])
    drift_ok = bool(off_drift is not None
                    and abs(off_drift) <= OFF_DRIFT_MAX_DB)

    verdicts = {}
    for name, trial in trials.items():
        voting = {key: test for key, test in trial.items() if key != "level"}
        detected = any(test.get("detected") for test in voting.values())
        inconclusive = bool(voting) and all(
            test.get("inconclusive") for test in voting.values())
        verdicts[name] = {
            "tests": dict(trial),
            "processing_detected": bool(detected),
            "inconclusive": bool(not detected and inconclusive),
            "fired_tests": sorted(key for key, test in voting.items()
                                  if test.get("detected")),
        }
    decisive = [name for name, value in verdicts.items()
                if not value["inconclusive"]]
    inconclusive = sorted(name for name, value in verdicts.items()
                          if value["inconclusive"])

    if not stimulus_ok:
        if (contrast is not None and contrast < MIN_GATE_CONTRAST_DB
                and baseline["bursts_found"] >= MIN_BURSTS):
            # The gaps are not silent. On this rig that means the deliberate
            # Main-to-Input-1 feedback loop is sustaining, and it buries any
            # tail an effect puts into a gap.
            status = "BLOCKED_GAPS_NOT_SILENT_BREAK_THE_FEEDBACK_LOOP"
        else:
            status = "BLOCKED_NO_USABLE_STIMULUS_ON_THE_RETURN"
    elif not control_ok:
        status = "INVALID_REVERB_CONTROL_PUT_NO_TAIL_IN_THE_GAP"
    elif not drift_ok:
        status = "INVALID_OFF_STATE_DRIFTED"
    elif any(value["processing_detected"] for value in verdicts.values()):
        status = "BLOCK201_PROCESSING_DETECTED_ON_THE_SHARED_RETURN"
    elif not decisive:
        status = "INCONCLUSIVE_NO_TEST_APPLIED_TO_THE_STIMULUS"
    else:
        status = "NO_BLOCK201_EFFECT_ON_THE_SHARED_RETURN"
    return {
        "status": status,
        "run_valid": bool(stimulus_ok and control_ok and drift_ok),
        "stimulus": {"bursts_found": baseline["bursts_found"],
                     "gate_contrast_db": contrast,
                     "gate_alignment_score": baseline["gate_alignment_score"],
                     "dominant_partial": partial,
                     "burst_rms_dbfs": baseline["burst_rms_dbfs"],
                     "gap_rms_dbfs": baseline["gap_rms_dbfs"],
                     "usable": stimulus_ok},
        "reverb_control": dict(control, fired=control_ok),
        "off_state_gap_drift_db": off_drift,
        "off_state_held": drift_ok,
        "models": verdicts,
        "decisive_models": sorted(decisive),
        "inconclusive_models": inconclusive,
    }


def validate_transport_log(events):
    """Every SetP must have addressed the Mix A send, the reverb, or block 201.

    The executable form of "nothing that feeds Main was written". An 'Appl'
    frame (block 0) is what would move a gain, a volume, the per-channel
    processing scalar, a slot or the link; a block-100 frame at bus index 0 is
    Main itself.
    """
    def offends(event):
        if event.get("command") != "SetP":
            return False
        block = event.get("block")
        if block not in ALLOWED_BLOCKS:
            return True
        return (block == MIXER_BLOCK
                and event.get("block_index") != ALLOWED_MIXER_BUS_INDEX)

    offending = [event for event in events if offends(event)]
    return {
        "setp_frames": sum(1 for event in events
                           if event.get("command") == "SetP"),
        "blocks": sorted({event.get("block") for event in events
                          if event.get("command") == "SetP"},
                         key=lambda value: (value is None, value)),
        "mixer_bus_indexes": sorted(
            {event.get("block_index") for event in events
             if event.get("command") == "SetP"
             and event.get("block") == MIXER_BLOCK},
            key=lambda value: (value is None, value)),
        "allowed_blocks": list(ALLOWED_BLOCKS),
        "allowed_mixer_bus_index": ALLOWED_MIXER_BUS_INDEX,
        "offending_frames": offending,
        "main_path_untouched": not offending,
    }


# -------------------------------------------------------------- live plumbing

def _enabled(params, channel):
    bit = 5 if channel == 1 else 6
    return not bool(int(params["flags"]) >> bit & 1)


def readable_state(params):
    if params is None:
        raise FxReturnProbeError("JaSt read failed")
    return {
        "flags": int(params["flags"]),
        "input1_gain_db": float(params["input1Gain"]),
        "input2_gain_db": float(params["input2Gain"]),
        "headphone_volume": float(params["hpVolume"]),
        "main_volume": float(params["mainVolume"]),
        "input1_processing_channel": int(params["input1ProcessingChannel"]),
        "input2_processing_channel": int(params["input2ProcessingChannel"]),
        "input1_phantom": bool(params["input1PhantomPower"]),
        "input2_phantom": bool(params["input2PhantomPower"]),
        "input1_processing_enabled": _enabled(params, 1),
        "input2_processing_enabled": _enabled(params, 2),
        "channel_linked": bool(int(params["flags"]) >> 12 & 1),
    }


def assert_guards(state):
    if state["input1_phantom"] or state["input2_phantom"]:
        raise FxReturnProbeError("phantom must be off on both inputs")
    if state["channel_linked"]:
        raise FxReturnProbeError("stereo link must be off before any write")
    if (state["input1_processing_channel"],
            state["input2_processing_channel"]) != (0, 1):
        raise FxReturnProbeError(
            "processing-channel permutation must remain 0/1")
    if not state["input1_processing_enabled"]:
        raise FxReturnProbeError(
            "Channel 1 is bypassed. The probe will not un-bypass it: that "
            "changes what reaches Main, and so the user's feedback loop. "
            "Clear Channel 1 bypass first, then re-run")


def known_prior_state(shadow_path):
    """Exact prior FX / reverb / return-send values, when the Host knows them.

    Mixer sends, the reverb and block 201 are all write-only on this firmware,
    so what the Host last wrote is the only record of them. Anything absent is
    reported as unknown rather than guessed.
    """
    prior = {"source": str(shadow_path), "fx": None, "reverb": None,
             "return_send": None, "available": False}
    try:
        with Path(shadow_path).open(encoding="utf-8") as handle:
            shadow = json.load(handle)
    except (OSError, ValueError) as error:
        prior["error"] = str(error)
        return prior
    prior["available"] = True
    entry = shadow.get("set_fx")
    if isinstance(entry, dict) and isinstance(entry.get("kwargs"), dict):
        kwargs = dict(entry["kwargs"])
        model = str(kwargs.pop("model", "")).lower()
        if model and hasattr(io24_fx, "set_fx_" + model):
            getattr(io24_fx, "set_fx_" + model)(**kwargs)   # pure validation
            prior["fx"] = {"model": model, "kwargs": kwargs}
    entry = shadow.get("set_reverb")
    if isinstance(entry, dict) and isinstance(entry.get("kwargs"), dict):
        prior["reverb"] = dict(entry["kwargs"])
    for entry in shadow.values():
        if not isinstance(entry, dict) or entry.get("fn") not in (
                "set_send_db", "set_mix_db"):
            continue
        kwargs = entry.get("kwargs")
        if not isinstance(kwargs, dict):
            continue
        if kwargs.get("source") == RETURN_SOURCE and \
                kwargs.get("bus") == RETURN_BUS:
            prior["return_send"] = dict(kwargs)
    return prior


def capture_stage(label, output_dir, stimulus, seconds=CAPTURE_SECONDS,
                  capture_endpoint=CAPTURE_ENDPOINT,
                  playback_sink=None,
                  popen=subprocess.Popen, sleep=time.sleep):
    """Record one stage while the gated stimulus plays.

    No control write may be in flight: see the header. Both streams are closed
    before this returns, so the next write happens with the card idle.
    """
    path = Path(output_dir) / ("%s.wav" % label)
    if path.exists():
        raise FxReturnProbeError("capture path already exists: %s" % path)
    recorder = popen(
        ["arecord", "-q", "-D", capture_endpoint, "-t", "wav", "-f", "S32_LE",
         "-r", str(RATE), "-c", str(CHANNELS), "-d", str(seconds), str(path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        sleep(0.4)
        if recorder.poll() is not None:
            _out, err = recorder.communicate(timeout=2)
            raise FxReturnProbeError(
                "arecord failed to start: %s" % (err or "").strip())
        player = popen(["pw-play", "--target", str(playback_sink),
                        str(stimulus)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                       text=True)
        _out, player_err = player.communicate(timeout=seconds + 15)
        if player.returncode != 0:
            raise FxReturnProbeError(
                "pw-play failed: %s" % (player_err or "").strip())
    finally:
        try:
            _out, err = recorder.communicate(timeout=seconds + 15)
        except subprocess.TimeoutExpired:
            recorder.kill()
            raise FxReturnProbeError("arecord did not finish")
    if recorder.returncode != 0:
        raise FxReturnProbeError("arecord failed: %s" % (err or "").strip())
    return path


def run_sequence(device, output_dir, stimulus, capture=capture_stage,
                 settle=time.sleep, progress=lambda _message: None,
                 stages=None, trials=None):
    """Stage the run: baseline, return open, reverb control, then each model.

    Every armed state is bracketed by an off capture, so a verdict is always a
    difference against its own neighbour rather than against a distant one.
    """
    # The caller may pass these in so a run that dies part way through still
    # reports the stages it did capture. The first attempt lost two good
    # captures to an exception and had to be re-read off disk.
    stages = {} if stages is None else stages
    trials = {} if trials is None else trials

    def observe(label):
        progress("capturing %s" % label)
        settle(SETTLE_SECONDS)
        stages[label] = analyse_stage(capture(label, output_dir, stimulus))
        return stages[label]

    observe("baseline")

    progress("assigning %s -> Mix A at %.1f dB" % (RETURN_SOURCE, RETURN_DB))
    device.set_send_db(RETURN_SOURCE, RETURN_BUS, RETURN_DB)
    device.set_send_assigned(RETURN_SOURCE, RETURN_BUS, True)
    observe("return_open")

    progress("positive control: shared reverb on")
    device.set_reverb(on=True, fs=float(RATE), **REVERB_CONTROL)
    observe("control_reverb")
    progress("positive control: shared reverb off")
    device.reverb_off()
    observe("control_off")

    def bracket(label, arm, disarm):
        progress("arming %s" % label)
        arm()
        on_stage = observe(label)
        disarm()
        off_stage = observe(label + "_off")
        return off_stage, on_stage

    for carrier in RINGMOD_CARRIERS:
        label = "ringmod_%s" % ("%.2f" % carrier).replace(".", "p")
        kwargs = {"carrier_hz": carrier, "dist": 0.5, "vol": 1.0,
                  "carrier2": False, "carrier2_hz": 50.0, "mix": 1.0}
        off_stage, on_stage = bracket(
            label,
            lambda k=kwargs: device.set_fx("ringmod", on=True, **k),
            lambda k=kwargs: device.set_fx("ringmod", on=False, **k))
        trials[label] = {
            "sidebands": classify_sidebands(
                off_stage, on_stage,
                off_stage["dominant_partial"]["hz"], carrier),
            "gap_energy": classify_gap_energy(off_stage, on_stage),
            "level": classify_level(off_stage, on_stage),
        }

    kwargs = {"detune": DETUNE_INDEX, "mix": 1.0}
    off_stage, on_stage = bracket(
        "detuner",
        lambda k=kwargs: device.set_fx("detuner", on=True, **k),
        lambda k=kwargs: device.set_fx("detuner", on=False, **k))
    trials["detuner"] = {
        "shift": classify_shift(off_stage, on_stage,
                                off_stage["dominant_partial"]["hz"]),
        "gap_energy": classify_gap_energy(off_stage, on_stage),
        "level": classify_level(off_stage, on_stage),
    }

    kwargs = {"time_s": DELAY_TIME_S, "feedback": 0.5, "mix": 1.0}
    off_stage, on_stage = bracket(
        "delay",
        lambda k=kwargs: device.set_fx("delay", on=True, **k),
        lambda k=kwargs: device.set_fx("delay", on=False, **k))
    trials["delay"] = {
        "repeat_taps": classify_repeat_taps(off_stage, on_stage),
        "gap_energy": classify_gap_energy(off_stage, on_stage),
        "autocorrelation": classify_autocorrelation(off_stage, on_stage),
        "level": classify_level(off_stage, on_stage),
    }

    kwargs = {"lows": 1.0, "width": 1.0, "mix": 1.0, "fs": float(RATE)}
    off_stage, on_stage = bracket(
        "transformer",
        lambda k=kwargs: device.set_fx("transformer", on=True, **k),
        lambda k=kwargs: device.set_fx("transformer", on=False, **k))
    trials["transformer"] = {
        "gap_energy": classify_gap_energy(off_stage, on_stage),
        "level": classify_level(off_stage, on_stage),
    }

    return stages, trials


def restore(device, prior, progress=lambda _message: None):
    """Put back everything this probe wrote, and say what could not be known."""
    notes = []
    progress("restoring")
    if prior.get("fx"):
        device.set_fx(prior["fx"]["model"], **prior["fx"]["kwargs"])
        notes.append("Host-known Voice FX state resent")
    else:
        device.set_fx("transformer", on=False, lows=1.0, width=1.0, mix=1.0,
                      fs=float(RATE))
        notes.append("no Host-known Voice FX state; block 201 left off")
    if prior.get("reverb"):
        device.set_reverb(**prior["reverb"])
        notes.append("Host-known reverb state resent")
    else:
        device.reverb_off()
        notes.append("no Host-known reverb state; reverb left off")
    send = prior.get("return_send")
    level = None if send is None else send.get("gain_db", send.get("value"))
    if level is None:
        device.set_send_db(RETURN_SOURCE, RETURN_BUS, None)
        device.set_send_assigned(RETURN_SOURCE, RETURN_BUS, False)
        notes.append(
            "the prior %s -> Mix A level is write-only and was not Host-known; "
            "it was returned to the off sentinel" % RETURN_SOURCE)
    else:
        device.set_send_db(RETURN_SOURCE, RETURN_BUS, level)
        notes.append("Host-known %s -> Mix A level %s dB resent"
                     % (RETURN_SOURCE, level))
    return notes


def needs_restoration(events):
    """Did this run actually write anything that has to be put back?"""
    return any(event.get("command") == "SetP" for event in events)


def _strip_arrays(value):
    """Drop the numpy views so the report is JSON and diffable."""
    if isinstance(value, dict):
        return {key: _strip_arrays(item) for key, item in value.items()
                if not key.startswith("_")}
    if isinstance(value, list):
        return [_strip_arrays(item) for item in value]
    return value


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def plan():
    """The exact writes this probe would issue, without opening anything."""
    return {
        "schema": SCHEMA,
        "stimulus": {
            "shape": "GATED_BURSTS",
            "burst_s": BURST_SECONDS,
            "gap_s": GAP_SECONDS,
            "cycles": CYCLES,
            "tones_hz": list(STIMULUS_TONES),
            "noise_below_db": STIMULUS_NOISE_BELOW_DB,
            "rms_dbfs": STIMULUS_RMS_DBFS,
            "playback_channel": 0,
            "why": "only an effect's own tail can put energy in a silent gap",
        },
        "writes": [
            "set_send_db(%r, %r, %.1f)" % (RETURN_SOURCE, RETURN_BUS,
                                           RETURN_DB),
            "set_send_assigned(%r, %r, True)" % (RETURN_SOURCE, RETURN_BUS),
            "set_reverb(on=True, **%r) then reverb_off()" % (REVERB_CONTROL,),
            "set_fx('ringmod', carrier_hz in %r) on then off" % (
                RINGMOD_CARRIERS,),
            "set_fx('detuner', detune=%d) on then off" % DETUNE_INDEX,
            "set_fx('delay', time_s=%.2f, feedback=0.5, mix=1.0) on then off"
            % DELAY_TIME_S,
            "set_fx('transformer', lows=1.0, width=1.0, mix=1.0) on then off",
        ],
        "never_written": [
            "any 'Appl' parameter: gain, main/headphone volume, the "
            "per-channel processing scalar, slot index, phantom, link",
            "any send into main or mixb",
            "processingChannel",
            "preset slot bodies or selection",
        ],
        "allowed_blocks": list(ALLOWED_BLOCKS),
        "allowed_mixer_bus_index": ALLOWED_MIXER_BUS_INDEX,
        "capture_seconds": CAPTURE_SECONDS,
        "stages": 14,
    }


def run_live(output_dir, battery_path, shadow_path,
             progress=lambda _message: None):
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise FxReturnProbeError("output directory must exist and be empty")
    report = {
        "schema": SCHEMA,
        "status": "LIVE_FAILED",
        "started": _now(),
        "device": {"serial": foundation.EXPECTED_SERIAL,
                   "bcd_device": "%04x" % foundation.EXPECTED_BCD_DEVICE},
        "plan": plan(),
        "rig": {
            "cable": "MAIN_OUT_L_TO_INPUT_1",
            "input1_gain_db_reported_by_user": 23.0,
            "monitors": "MEDIUM_MUTE_OFF",
            "feedback_loop": "USER_ESTABLISHED_DELIBERATE_MILD",
            "headphones": "NOT_CONNECTED",
            "stimulus": "GATED_BURSTS_FROM_USB_PLAYBACK_THROUGH_MAIN",
            "observation": "NATIVE_6CH_CAPTURE_OF_MIX_A_RETURN",
        },
        "capture_endpoint": CAPTURE_ENDPOINT,
        "playback_endpoint": PLAYBACK_ENDPOINT,
        "serialisation": "NO_CONTROL_WRITE_WHILE_ARECORD_OR_APLAY_RUNS",
        "processing_channel": "UNTOUCHED_IDENTITY_0_1_REQUIRED",
        "preset_slots": "UNTOUCHED",
    }
    device = None
    stages, trials = {}, {}
    try:
        report["prior_host_known_state"] = known_prior_state(shadow_path)
        battery = foundation._battery(battery_path)
        report["battery_before"] = battery
        if battery <= foundation.BATTERY_FLOOR:
            report["status"] = "BLOCKED_BATTERY"
            return report
        stimulus = build_stimulus(output_dir / "stimulus.wav")
        sink = resolve_playback_sink()
        report["playback_sink"] = sink
        device = foundation._open_checked()
        before = readable_state(device.read_params())
        report["readable_state_before"] = before
        assert_guards(before)

        run_sequence(device, output_dir, stimulus,
                     capture=lambda label, out, stim: capture_stage(
                         label, out, stim, playback_sink=sink),
                     progress=progress, stages=stages, trials=trials)
        report["verdict"] = _strip_arrays(classify_run(stages, trials))
        report["status"] = report["verdict"]["status"]
    except BaseException as error:                  # noqa: BLE001 - fail closed
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        # Whatever was captured before a failure is still evidence.
        report["stages"] = _strip_arrays(stages)
        if device is not None:
            # Restoration belongs here, not at the end of the happy path: a
            # Ctrl+C part way through a nine-stage run would otherwise leave
            # the return assigned and a model armed. It is skipped only when
            # the transport log proves nothing was ever written -- a run that
            # failed its guards must not "restore" state it never disturbed.
            if needs_restoration(device.transport_log):
                try:
                    report["restoration_notes"] = restore(
                        device, report.get("prior_host_known_state") or {},
                        progress=progress)
                    after = readable_state(device.read_params())
                    report["readable_state_after"] = after
                    report["readable_state_matches"] = (
                        after == report.get("readable_state_before"))
                    if not report["readable_state_matches"]:
                        report["status"] = "RESTORATION_FAILED"
                except BaseException as error:      # noqa: BLE001
                    report["restoration_error"] = {
                        "type": type(error).__name__, "message": str(error)}
                    report["status"] = "RESTORATION_FAILED"
            else:
                report["restoration_notes"] = [
                    "nothing was written; no restoration was required"]
            report["transport"] = list(device.transport_log)
            report["transport_validation"] = validate_transport_log(
                report["transport"])
            if not report["transport_validation"]["main_path_untouched"]:
                report["status"] = "SAFETY_INVARIANT_VIOLATED"
            try:
                device.close()
            except BaseException as error:          # noqa: BLE001
                report["close_error"] = {"type": type(error).__name__,
                                         "message": str(error)}
                report["status"] = "RESTORATION_FAILED"
        try:
            report["battery_after"] = foundation._battery(battery_path)
        except BaseException as error:              # noqa: BLE001
            report["battery_after_error"] = str(error)
        report["finished"] = _now()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="perform the live run; without it, print the plan")
    parser.add_argument("--output-dir")
    parser.add_argument("--battery-path",
                        default="/sys/class/power_supply/BAT0/capacity")
    parser.add_argument("--shadow-path",
                        default=str(Path.home() / ".cache" / "io24"
                                    / "shadow.json"))
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("--execute requires --output-dir")
    report = run_live(args.output_dir, args.battery_path, args.shadow_path,
                      progress=lambda message: print(message, flush=True))
    _write_json(Path(args.output_dir) / "live-report.json", report)
    print(json.dumps({key: report[key] for key in
                      ("status", "battery_before", "battery_after", "error")
                      if key in report}, indent=2, sort_keys=True))
    if report.get("verdict"):
        print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    return 0 if report.get("status", "").startswith(
        ("BLOCK201_PROCESSING_DETECTED", "NO_BLOCK201_EFFECT")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
