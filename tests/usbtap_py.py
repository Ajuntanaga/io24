#!/usr/bin/env python3
"""Record this project's own USB traffic, for use as the capture BASELINE.

The companion `usbtap.c` interposes on libusb with LD_PRELOAD, which is what
Wine needs (Wine's wineusb links libusb normally, so its calls go through the
PLT). That does NOT work for this driver: pyusb loads libusb through
`ctypes.CDLL`, and a dlsym against that specific handle resolves to libusb's
own symbol rather than the preloaded one. So the baseline is taken here
instead, by wrapping pyusb's endpoint objects.

Both taps write the same usbmon text format, so `usbmon_decode.py` reads
either one and the two captures diff directly.

    python3 tests/usbtap_py.py out.txt          # records model parameters only
    python3 tests/usbmon_decode.py out.txt
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import usb.core  # noqa: E402
import io24      # noqa: E402

_seq = 0


def _emit(fh, dirtag, ep, data):
    global _seq
    b = bytes(data)
    if not b:
        return
    groups = " ".join(b.hex()[i:i + 8] for i in range(0, len(b.hex()), 8))
    fh.write("ffff8800%08x %d S %s:1:004:%02x -115 %d = %s\n"
             % (_seq, int(time.monotonic() * 1e6), dirtag, ep & 0x7f,
                len(b), groups))
    fh.flush()
    _seq += 1


def install(fh):
    """Wrap Endpoint.write/read so every transfer is logged in usbmon form."""
    Ep = usb.core.Endpoint
    real_w, real_r = Ep.write, Ep.read

    def write(self, data, timeout=None):
        _emit(fh, "Bo", self.bEndpointAddress, data)
        return real_w(self, data, timeout)

    def read(self, size_or_buffer, timeout=None):
        r = real_r(self, size_or_buffer, timeout)
        _emit(fh, "Bi", self.bEndpointAddress, r)
        return r

    Ep.write, Ep.read = write, read


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "baseline.txt"
    fh = open(out, "w")
    install(fh)

    d = io24.Io24()
    print("Recording Voice FX model parameters; activation remains unresolved.")
    d.configure_voice_fx_intent(
        True, "vocoder", carrier_type=1, carrier_freq=220.0, vol=1.0, mix=1.0)
    time.sleep(0.3)
    # Every other model keeps the baseline vocabulary complete. This deliberately
    # records no gate or reverb-route write.
    for m in ("transformer", "detuner", "ringmod", "filters", "delay"):
        try:
            d.configure_voice_fx_intent(True, m)
        except Exception as e:
            print("  %s: %s" % (m, e))
        time.sleep(0.15)
    d.read_params()
    d.close()
    fh.close()
    n = sum(1 for _ in open(out))
    print("wrote %d transfers to %s" % (n, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
