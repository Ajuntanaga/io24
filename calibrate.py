#!/usr/bin/env python3
"""
calibrate.py — measurements that need a stable, known input signal.

Two questions are open in PROTOCOL.md that speech cannot answer, because they
need a signal whose level does not move between readings:

  mixer   the 0 -> -6 dB step measured only -2.55 dB while every step below it
          was accurate. Bus dynamics, or wrong gain near unity?
  comp    the compressor's dB-in/dB-out transfer curve has never been measured;
          only that reduction responds to threshold and ratio.

Usage:
  calibrate.py tone [secs] [hz]     play a steady tone out of the io24
  calibrate.py level                report input/bus meters (check your setup)
  calibrate.py mixer                sweep mixer levels, measure the bus
  calibrate.py comp                 sweep compressor threshold, measure reduction

Signal path: anything steady on input 1 works. A cable from a main output back
into input 1 is ideal (fully controlled); a tone played into the mic is fine too,
as long as the level holds still.

BETTER, for anything living in the mixer or the buses: the device's own USB
playback return. `usbtone` plays a tone that arrives inside the device as
`return/ch1` at EXACTLY unity gain — a -26 dBFS tone measures -26.00 dBFS on the
bus — with no cable, no microphone, and nothing for a human to hold still. That
is how the mixer gain law was verified to 0.03 dB over a 106 dB range.

It cannot test the per-channel DSP chain or the FX, though: the FX send takes
from the mic/line inputs, and the USB return reaches it 49 dB down, i.e. not at
all. Those still need a real signal on a physical input.

  calibrate.py usbtone [secs] [hz] [dbfs]   calibrated tone via the USB return
"""
import math
import os
import struct
import signal
import subprocess
import sys
import time
import wave

from io24 import Io24

TONE = "/tmp/io24_cal_tone.wav"
IN_SLOT = 4          # ch1 input level
BUS_SLOT = 14        # Mix A bus L — deliberately NOT main (12): with a
                     # main-out -> input-1 loopback cable, measuring ch1 into
                     # the MAIN bus closes an acoustic feedback loop. Mix A does
                     # not feed the main output, so the loop stays open.


def make_tone(path=TONE, secs=6, freq=440.0, amp=0.25, rate=48000):
    w = wave.open(path, "wb")
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
    buf = bytearray()
    for n in range(int(rate * secs)):
        v = int(amp * 32767 * math.sin(2 * math.pi * freq * n / rate))
        s = struct.pack("<h", v)
        buf += s + s
    w.writeframes(bytes(buf)); w.close()
    return path


USB_TONE = "/tmp/io24_usb_tone.wav"


def make_usb_tone(path=USB_TONE, secs=4.0, freq=1000.0, dbfs=-26.0, rate=48000):
    """A 6-channel S32 tone for the io24's USB playback endpoint.

    Six channels because that is what the device exposes (see
    /proc/asound/card*/stream0). ALSA's `plughw` converts as needed and the
    result lands on the mixer's `return/ch1`.
    """
    amp = 10.0 ** (dbfs / 20.0)
    w = wave.open(path, "wb")
    w.setnchannels(6); w.setsampwidth(4); w.setframerate(rate)
    buf = bytearray()
    for n in range(int(rate * secs)):
        v = int(amp * 2147483647 * math.sin(2 * math.pi * freq * n / rate))
        frame = struct.pack("<i", v) * 2 + struct.pack("<i", 0) * 4
        buf += frame
    w.writeframes(bytes(buf)); w.close()
    return path


def start_usb_tone(freq=1000.0, dbfs=-26.0):
    """Loop a calibrated tone into the device's USB return. Exact unity gain."""
    global _TONE_PROC
    stop_tone()
    make_usb_tone(freq=freq, dbfs=dbfs)
    _TONE_PROC = subprocess.Popen(
        ["bash", "-c",
         "while true; do aplay -D plughw:CARD=R24 -q %s 2>/dev/null || sleep 0.5; done"
         % USB_TONE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    return _TONE_PROC


_TONE_PROC = None


def start_tone(freq=440.0, amp=0.25):
    """Loop the tone in its own process group so it can be killed as a unit."""
    global _TONE_PROC
    stop_tone()
    make_tone(freq=freq, amp=amp)
    _TONE_PROC = subprocess.Popen(
        ["bash", "-c",
         "while true; do aplay -D plughw:CARD=R24 -q %s 2>/dev/null || sleep 0.5; done" % TONE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    return _TONE_PROC


def stop_tone():
    """Kill the whole process group.

    Killing `aplay` alone is not enough — it runs inside a `while true` wrapper
    that immediately respawns it, so the tone appears to survive `pkill aplay`.
    And `pkill -f io24_cal_tone` is worse than useless here: it matches any shell
    whose command line contains that string, including the one invoking it.
    """
    global _TONE_PROC
    if _TONE_PROC is not None:
        try:
            os.killpg(os.getpgid(_TONE_PROC.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        _TONE_PROC = None
        return
    # no handle (separate process): find the wrapper and the player by cmdline
    out = subprocess.run(["ps", "-eo", "pid,cmd"], capture_output=True,
                         text=True).stdout
    me = os.getpid()
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        pid, cmd = parts
        if (TONE in cmd or USB_TONE in cmd) and int(pid) != me and "ps -eo" not in cmd:
            try:
                os.killpg(os.getpgid(int(pid)), signal.SIGKILL)
            except Exception:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except Exception:
                    pass


def db(x):
    return float("-inf") if x <= 1e-12 else 20 * math.log10(x)


def measure(dev, n=25, settle=0.25):
    """Mean input and bus level. Means (not peaks) because the signal is steady."""
    time.sleep(settle)
    si = sb = 0.0
    k = 0
    for _ in range(n):
        rsp = dev.read_state(0x100)
        if rsp is None:
            continue
        f = dev.floats(rsp)
        si += f[IN_SLOT]; sb += f[BUS_SLOT]; k += 1
        time.sleep(0.02)
    if not k:
        return None, None
    return si / k, sb / k


def cmd_level(dev):
    i, b = measure(dev)
    print("  input  slot %d : %.4e  (%.1f dBFS)" % (IN_SLOT, i, db(i)))
    print("  MixA   slot %d : %.4e  (%.1f dBFS)" % (BUS_SLOT, b, db(b)))
    if i is None or i < 1e-6:
        print("\n  NO USABLE SIGNAL on input 1 — raise the gain or the source level.")
    elif i > 0.5:
        print("\n  Input is very hot (%.1f dBFS); back it off to avoid clipping." % db(i))
    else:
        print("\n  Signal looks usable. Stability matters more than level.")


def cmd_mixer(dev):
    """Does the mixer's dB scaling hold near unity, or does something compress it?"""
    print("Sweeping line/ch1 -> MIX A (main is muted to keep the loopback open).\n")
    rows = []
    for x in (0.0, -3.0, -6.0, -10.0, -15.0, -20.0, -30.0):
        dev.set_mix_db("line/ch1", x, bus="mixa")
        i, b = measure(dev)
        rows.append((x, i, b))
        print("  set %+6.1f dB  input %.3e  bus %.3e  (bus %.1f dBFS)" % (x, i, b, db(b)))
    dev.set_mix_db("line/ch1", 0.0, bus="mixa")
    ref_x, ref_i, ref_b = rows[0]
    print("\n  asked      measured    error    (bus level referenced to the 0 dB point)")
    for x, i, b in rows[1:]:
        # normalise by the input in case it drifted at all
        meas = db((b / i) / (ref_b / ref_i))
        print("   %+6.1f     %+7.2f    %+6.2f %s" % (x, meas, meas - x,
              "" if abs(meas - x) < 1.0 else "  <-- deviates"))
    print("\n  If the deviation is confined to the top of the range, it is bus")
    print("  dynamics. If it scales with level, the gain law is wrong.")


def cmd_comp(dev):
    """Measure gain reduction against threshold at a fixed input level."""
    print("Sweeping compressor threshold on ch1. Steady input required.\n")
    i, _ = measure(dev, n=15)
    print("  input level: %.3e (%.1f dBFS)\n" % (i, db(i)))
    print("  threshold   ratio   reduction      implied")
    for thr in (-60.0, -50.0, -40.0, -30.0, -20.0):
        dev.set_compressor(1, model=0, instance=0, on=True, threshold_db=thr,
                           ratio=4.0, attack_s=0.005, release_s=0.1, gain_db=0.0,
                           softknee=False, automode=False, keyfilter_hz=0.0,
                           keylisten=False)
        time.sleep(0.8)
        r = dev.read_reduction("comp", 1)
        gr = db(r[0]) if r else float("nan")
        over = db(i) - thr                    # how far above threshold we are
        want = -over * (1 - 1 / 4.0) if over > 0 else 0.0
        print("   %+6.1f dB   4:1    %+6.2f dB    expected %+6.2f (%.1f dB over)"
              % (thr, gr, want, over))
    dev.compressor_off(1)
    print("\n  A 4:1 compressor should reduce by 0.75 dB per dB above threshold.")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__); return
    cmd = args[0]
    if cmd == "usbtone":
        secs = float(args[1]) if len(args) > 1 else 20.0
        freq = float(args[2]) if len(args) > 2 else 1000.0
        dbfs = float(args[3]) if len(args) > 3 else -26.0
        print("playing %.0f Hz at %.1f dBFS via the USB return for %.0fs"
              % (freq, dbfs, secs))
        print("  it arrives inside the device as return/ch1 at unity gain")
        start_usb_tone(freq, dbfs); time.sleep(secs); stop_tone(); return
    if cmd == "tone":
        secs = float(args[1]) if len(args) > 1 else 20.0
        freq = float(args[2]) if len(args) > 2 else 440.0
        print("playing %.0f Hz for %.0fs — Ctrl-C to stop" % (freq, secs))
        start_tone(freq); time.sleep(secs); stop_tone(); return
    dev = Io24()
    try:
        {"level": cmd_level, "mixer": cmd_mixer, "comp": cmd_comp}.get(
            cmd, lambda d: print("unknown command %r" % cmd))(dev)
    finally:
        dev.close()


if __name__ == "__main__":
    main()
