#!/usr/bin/env python3
"""
Objective audio oracle for the io24: plays a test tone into the device's playback
and simultaneously records its 6 capture channels (Mic/Inst + Stream Mix A/B
loopbacks), reporting per-channel RMS. Used to detect whether a native command
actually changed the mix (mute/volume) — no human listening required.

  oracle.py baseline          -> print per-channel RMS (find loopback channels)
  oracle.py measure <secs>    -> same, custom duration
Import: measure_rms(secs) -> list of 6 RMS values (0..1)
"""
import subprocess, struct, math, sys, os, time, threading

CARD = "hw:2,0"
RATE = 48000
CHANS = 6
TONE_WAV = "/tmp/io24_oracle_tone.wav"

def ensure_tone(secs=6, freq=440.0, amp=0.35):
    import wave
    if os.path.exists(TONE_WAV):
        return
    w = wave.open(TONE_WAV, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE)
    buf = bytearray()
    for n in range(int(RATE*secs)):
        v = int(amp*32767*math.sin(2*math.pi*freq*n/RATE)); s = struct.pack("<h", v); buf += s+s
    w.writeframes(bytes(buf)); w.close()

_player = None
def start_tone():
    """Loop the tone into the io24 playback in the background."""
    global _player
    ensure_tone()
    if _player and _player.poll() is None:
        return
    _player = subprocess.Popen(
        ["bash","-c","while true; do aplay -D plughw:2,0 -q %s 2>/dev/null || sleep 0.5; done" % TONE_WAV],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    time.sleep(1.2)

def stop_tone():
    global _player
    subprocess.run(["pkill","-f","io24_oracle_tone"], capture_output=True)
    _player = None

def measure_rms(secs=1.0):
    """Record `secs` of the 6 capture channels; return per-channel RMS (0..1)."""
    n_frames = int(RATE*secs)
    p = subprocess.run(
        ["arecord","-D",CARD,"-f","S32_LE","-r",str(RATE),"-c",str(CHANS),
         "-d",str(max(1,int(math.ceil(secs)))),"-t","raw","-q"],
        capture_output=True)
    raw = p.stdout
    if not raw:
        return [0.0]*CHANS
    n = len(raw)//(4*CHANS)
    acc = [0.0]*CHANS
    fmt = "<%di" % (n*CHANS)
    vals = struct.unpack(fmt, raw[:n*CHANS*4])
    for c in range(CHANS):
        s = 0.0
        for k in range(c, len(vals), CHANS):
            v = vals[k]/2147483648.0
            s += v*v
        acc[c] = math.sqrt(s/max(1,n))
    return acc

def fmt_rms(r):
    def db(x): return "-inf" if x <= 1e-9 else "%6.1fdB" % (20*math.log10(x))
    return "  ".join("ch%d=%s" % (i+1, db(v)) for i, v in enumerate(r))

if __name__ == "__main__":
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    start_tone()
    print("tone playing; measuring %.1fs of all %d capture channels..." % (secs, CHANS))
    r = measure_rms(secs)
    print(fmt_rms(r))
    live = [i+1 for i, v in enumerate(r) if v > 1e-4]
    print("channels carrying signal: %s" % (live or "NONE"))
    stop_tone()
