#!/usr/bin/env python3
"""
io24d — a control daemon for the PreSonus Revelator io24.

The USB control interface can only be claimed by ONE process at a time, so a
long-running holder is needed for several tools to share the device. This is the
Linux equivalent of the role PreSonusHardwareAccessService.exe plays on Windows.

It holds the device open and exposes it over a Unix domain socket using
newline-delimited JSON, one request per line:

    {"cmd": "status"}
    {"cmd": "meters"}
    {"cmd": "set", "param": "gain",    "channel": 1, "value": 40}
    {"cmd": "set", "param": "hpvol",                 "value": 0.7}
    {"cmd": "set", "param": "phantom", "channel": 1, "value": true}
    {"cmd": "set", "param": "limiter", "channel": 1, "value": true, "threshold": -28}
    {"cmd": "reduction", "block": "lim ", "channel": 1}
    {"cmd": "savepreset", "path": "/home/me/vocal.json"}
    {"cmd": "loadpreset", "path": "/home/me/vocal.json"}
    {"cmd": "ping"}

Replies are one JSON object per line, always with "ok": true|false.

  io24d.py [--socket PATH] [--poll SECONDS] [--wait]
  io24d.py --client '<json>'      one-shot request against a running daemon
  --wait                          block until the device appears, rather
                                  than exiting if it is not plugged in

State is cached and refreshed by a background poller so that many clients reading
status do not each trigger USB traffic.
"""
import json
import os
import socket
import socketserver
import sys
import threading
import time

from io24 import Io24

DEFAULT_SOCKET = os.environ.get(
    "IO24D_SOCKET", os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "io24d.sock"))


def _unchanged(value):
    """Pass enum names through to setters that validate their own vocabulary."""
    return value


# param name -> (driver method, takes channel, coerce)
SETTERS = {
    "gain":     ("set_gain",         True,  float),
    "hpvol":    ("set_hp_volume",    False, float),
    "mainvol":  ("set_main_volume",  False, float),
    "blend":    ("set_monitor_mix",  False, float),
    "fxmix":    ("set_fx_mix",       True,  float),
    "phantom":  ("set_phantom",      True,  bool),
    "mute":     ("set_mute",         True,  bool),
    "hpmute":   ("set_hp_mute",      False, bool),
    "phonesrc": ("set_phones_source", False, _unchanged),
    "hpf":      ("set_highpass",     True,  bool),
    "link":     ("set_channel_link", False, bool),
    "hpfreq":   ("set_highpass_freq", True, float),
}


class Device:
    """Serialises all USB access and caches the last known state."""

    def __init__(self, poll_interval=0.5):
        # RLock, not Lock: Device's own methods take this lock, and callers
        # (the GTK app's worker thread) legitimately hold it while invoking
        # them. With a plain Lock that self-deadlocks the worker forever on the
        # first control change, which looks exactly like "the app cannot drive
        # the hardware".
        self.lock = threading.RLock()
        self.dev = Io24()
        self.state = None
        self.state_time = 0.0
        self.poll_interval = poll_interval
        self.running = True
        self.thread = threading.Thread(target=self._poll, daemon=True)
        self.thread.start()

    def _poll(self):
        while self.running:
            try:
                with self.lock:
                    p = self.dev.read_params()
                if p:
                    self.state, self.state_time = p, time.time()
            except Exception:
                pass
            time.sleep(self.poll_interval)

    def status(self, max_age=1.5):
        if self.state and (time.time() - self.state_time) < max_age:
            return self.state
        with self.lock:
            p = self.dev.read_params()
        if p:
            self.state, self.state_time = p, time.time()
        return self.state

    def reduction(self, block, channel):
        with self.lock:
            return self.dev.read_reduction(block, channel)

    def apply(self, param, channel, value, extra):
        if param == "limiter":
            with self.lock:
                self.dev.set_limiter(channel, bool(value),
                                     float(extra.get("threshold", -28.0)))
            return
        if param == "order":
            with self.lock:
                self.dev.set_comp_eq_order(channel, bool(value))
            return
        if param not in SETTERS:
            raise KeyError("unknown param %r" % param)
        name, needs_ch, coerce = SETTERS[param]
        fn = getattr(self.dev, name)
        with self.lock:
            fn(channel, coerce(value)) if needs_ch else fn(coerce(value))

    def save_preset(self, path):
        with self.lock:
            return self.dev.save_preset(path)

    def load_preset(self, path):
        with self.lock:
            return self.dev.load_preset(path)

    def close(self):
        self.running = False
        try:
            self.dev.close()
        except Exception:
            pass


DEVICE = None


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        for raw in self.rfile:
            raw = raw.strip()
            if not raw:
                continue
            try:
                req = json.loads(raw)
            except Exception as e:
                self._send({"ok": False, "error": "bad json: %s" % e}); continue
            try:
                self._send(self.dispatch(req))
            except Exception as e:
                self._send({"ok": False, "error": "%s: %s" % (type(e).__name__, e)})

    def _send(self, obj):
        self.wfile.write((json.dumps(obj) + "\n").encode()); self.wfile.flush()

    def dispatch(self, req):
        cmd = req.get("cmd")
        if cmd == "ping":
            return {"ok": True, "pong": True}
        if cmd in ("status", "meters"):
            st = DEVICE.status()
            if st is None:
                return {"ok": False, "error": "no state"}
            if cmd == "meters":
                return {"ok": True, "levels": {"in1": st["input1Level"],
                                               "in2": st["input2Level"]},
                        "reduction": {b.strip(): DEVICE.reduction(b, 1)
                                      for b in ("gate", "comp", "lim ")}}
            return {"ok": True, "state": st}
        if cmd == "reduction":
            return {"ok": True,
                    "values": DEVICE.reduction(req.get("block", "lim "),
                                               int(req.get("channel", 1)))}
        if cmd == "set":
            param = req.get("param")
            DEVICE.apply(param, int(req.get("channel", 1)), req.get("value"), req)
            time.sleep(0.25)
            return {"ok": True, "param": param, "state": DEVICE.status(max_age=0)}
        if cmd in ("savepreset", "loadpreset"):
            path = req.get("path")
            if not path:
                return {"ok": False, "error": "savepreset/loadpreset need a path"}
            if cmd == "savepreset":
                snap = DEVICE.save_preset(path)
                return {"ok": True, "path": path, "live": len(snap["live"]),
                        "settings": len(snap["calls"])}
            n_live, n_calls = DEVICE.load_preset(path)
            time.sleep(0.25)
            return {"ok": True, "path": path, "live": n_live, "settings": n_calls,
                    "state": DEVICE.status(max_age=0)}
        return {"ok": False, "error": "unknown cmd %r" % cmd}


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


def client(sock_path, payload):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sock_path)
    s.sendall((payload.strip() + "\n").encode())
    data = s.makefile("rb").readline()
    s.close()
    print(data.decode().rstrip())


def wait_for_device(poll, timeout=None):
    """Open the device, optionally waiting for it to appear.

    Under systemd the daemon can easily start before the interface is plugged in
    (or survive a replug); exiting in that case would just spin the restart
    counter, so `--wait` blocks here instead, quietly, until the device shows up.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    announced = False
    while True:
        try:
            return Device(poll_interval=poll)
        except SystemExit:
            if deadline is not None and time.monotonic() >= deadline:
                raise
            if not announced:
                print("waiting for the io24 to appear...", flush=True)
                announced = True
            time.sleep(2.0)


def main():
    argv = sys.argv[1:]
    if argv and argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    sock_path, poll = DEFAULT_SOCKET, 0.5
    if "--socket" in argv:
        sock_path = argv[argv.index("--socket") + 1]
    if "--poll" in argv:
        poll = float(argv[argv.index("--poll") + 1])
    if "--client" in argv:
        client(sock_path, argv[argv.index("--client") + 1]); return

    global DEVICE
    if len(sock_path.encode()) > 107:      # sun_path is 108 bytes, NUL included
        raise SystemExit("socket path is too long for AF_UNIX (%d bytes):\n  %s"
                         % (len(sock_path.encode()), sock_path))
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    DEVICE = wait_for_device(poll, timeout=None if "--wait" in argv else 0.0)
    srv = Server(sock_path, Handler)
    os.chmod(sock_path, 0o600)
    print("io24d listening on %s (protocol=%d maxCmd=%d)"
          % (sock_path, DEVICE.dev.proto, DEVICE.dev.max_cmd), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close(); DEVICE.close()
        if os.path.exists(sock_path):
            os.unlink(sock_path)
        print("io24d stopped")


if __name__ == "__main__":
    main()
