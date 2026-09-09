# io24 local-scope libusb resolver v6

Built, tested, and staged offline on 2026-08-19 PDT after the single v5
live-read failed closed at symbol resolution. This work did not run Wine or
Universal Control, open a USB node, or modify either Wine prefix. The only
real-libusb checks ran in a Bubblewrap namespace whose probe rejects visible
`/dev/bus/usb`, `/sys/bus/usb/devices`, and `/run/udev` paths.

## Root cause and narrow fix

The v5 capture proved that the interposed `libusb_init()` ran, but
`dlsym(RTLD_NEXT, "libusb_init")` returned null in both contained Wine
processes. The staged Wine `wineusb.so` directly depends on
`libusb-1.0.so.0`, but that dependency is in Wine's private/local loader
scope. The earlier positive integration test had explicitly loaded libusb
`RTLD_GLOBAL`, so it did not reproduce Wine's namespace shape.

V6 retains `RTLD_NEXT` as the first resolution path. If that result is absent
or fails provenance validation, the resolver:

1. serializes access to its retained handle with a C11 `atomic_flag`;
2. calls `dlopen("libusb-1.0.so.0", RTLD_NOW | RTLD_LOCAL | RTLD_NOLOAD)`;
3. resolves the requested symbol through that explicit handle; and
4. accepts the address only when `dladdr()` reports the exact requested symbol
   and an ELF base different from the interposer itself.

`RTLD_NOLOAD` means the fallback can only acquire an already-resident libusb;
`RTLD_LOCAL` neither promotes it into the global scope nor changes Wine's
loader topology. The handle is retained for the process lifetime. Resolution
is applied consistently to `libusb_init`, `libusb_set_log_cb`, the bulk,
interrupt, and control sync calls, `libusb_submit_transfer`, and
`libusb_handle_events`. Any unresolved callable target returns libusb status
`-12` instead of making a null call.

The ELF has no `DT_NEEDED` dependency on libusb; its sole needed library is
`libc.so.6`. It therefore cannot introduce libusb into a process on load.

## RED-GREEN and regression contracts

The local-scope fixture gives its fake library the real
`libusb-1.0.so.0` SONAME, loads a client and dependency `RTLD_LOCAL`, then
exercises initialization, callback installation, asynchronous submit and
completion, and event-loop entry/return. The exact staged v5 bytes were first
observed RED at the intended boundary:

```text
FAIL: local-scope libusb initialization returned -12
# usbtap pid=... tid=... event=R-init object=unknown symbol=libusb_init
# usbtap pid=... tid=... event=L-global-unavailable
```

After the resolver change, the source build, exact build artifact, and exact
staged artifact each passed:

```text
usbtap local-scope contract: pass
usbtap durable libusb log contract: pass
callback contract (completed): pass
callback contract (stall): pass
callback contract (submit-error): pass
usbtap async control contract: pass
libusb durable-log empty-device contract: pass
```

The real-libusb contract now loads the installed library `RTLD_LOCAL`, rather
than masking this bug with `RTLD_GLOBAL`. It calls only `libusb_init()` and
`libusb_exit()` with v6 preloaded, and requires the real library's resolver
provenance, callback installation, durable initialization and shutdown
records, no escaped native stderr record, and no visible hardware or udev
path.

Relevant source hashes after the change:

- `../../tests/usbtap.c`:
  `d0048220e950527c0054a259c64de0d014b2060f0b560bfd1058c10dac876b4a`;
- `../../tests/usbtap_local_scope_contract.c`:
  `7fda902fc8b8edeb8552f3e8e1a5fc1c4869711ec690cd65fbe41c699040f8fb`;
- `../../tests/usbtap_local_scope_contract.sh`:
  `92e957a4112b8dcbe4cdec47f7f7f663f0616ece7470872637e36d708450ea46`;
- `../../tests/libusb_debug_contract.c`:
  `760d9ff67e091d31413c0a9f06fa71261ce4b711f1ed77c872c27dd8e7407de9`;
- `../../tests/libusb_debug_contract.sh`:
  `29ac765bc91358dea2cfc8d4d8f57ed39fc6dff4071e57b1eea402f0b1a28c82`;
- `../../tests/usbtap_log_contract.c`:
  `3d6ba95ef3897f0599b97e74c0e9d692bd4cabc4883c9c6561f881800a7a9d81`;
- `../../tests/usbtap_log_contract.sh`:
  `cd7962f8b1a043626a2e42b4cba1439e345f8864354d852c2d906a4d986f2dae`;
- `../../tests/usbtap_async_contract.c`:
  `95e2d13dd4daddbcdea364ef358a1587fdac7980110601a70170174bd61cb965`;
- `../../tests/usbtap_async_contract.sh`:
  `3c235c4d91d00dcd3ddbdd11f17e6e507c60b0bf4c34a1d1a5738fdacfba2f03`;
- `../../tests/uc_wine_sandbox.sh`:
  `54aa7b599b32037056725d58d79ada9a3757e35695972933790f6555774bca85`.

## Artifact and staging provenance

Build command:

```bash
cc -std=c11 -Wall -Wextra -Werror -shared -fPIC -O2 \
  tests/usbtap.c -ldl \
  -o /tmp/io24-usbtap-resolver-v6.so
```

- compiler: `cc (Ubuntu 15.2.0-16ubuntu1) 15.2.0`;
- size: 21,584 bytes;
- artifact SHA-256:
  `dbce256b328b53866dd13dbe382c28b216a1baf64bdb47fc746b722375e86977`;
- ELF build ID: `fdc6614838445964b3dbc8ab55726fd894268be1`.

Two independent invocations of the exact build command produced byte-identical
ELFs. The exact artifact was staged only in the disposable sandbox as both
`out/usbtap-resolver-v6.so` and active `out/usbtap.so`; both byte-match the
build artifact and the hash above. V5 remains recoverable as
`out/usbtap-log-v5.so`, SHA-256
`9734fd0d09254f8717059b5abb0e05089ddf0cf024a526fc8965ebb0dc6341fc`.

The harness has exactly one `USBTAP_RESOLVER_V6_SHA256` pin and refuses to
launch a `live-read` service unless active `out/usbtap.so` matches it. It also
refuses to overwrite an existing `out/live-service-usb.txt` capture.

## Preserved evidence and gate

The current four-line v5 capture remains in place at 244 bytes, SHA-256
`5f258683dafedb114ea95e358f6d414efeb20bb6c19b9a2ff8896ce632fc30c6`,
inode 4063250, and timestamp
`2026-08-19 02:29:19.120659945 -0700`. Its checkpoint copy has the same hash at
`out/checkpoints/live-read-log-v5-20260819T022919PDT/`; that checkpoint's
`SHA256SUMS` remains
`2a336af5345b137a24a4b40dc6ff826287f53fed1bac202bdb1e8d0d8d4fe94a`.
The archived v4 capture also remains at SHA-256
`d1a0faa893c348a53bfe4ef4160c8ecbaf9e90c84f8547fb974929d4100e8885`.

Disposable `prefix/system.reg` retained size 3,735,107 bytes, inode 4063238,
and timestamp `2026-08-19 02:29:19.820654317 -0700` across staging and exact
artifact verification. No Wine or UC process was started or survived.

This is an offline instrumentation result, not a live-device result. The v5
authorization was consumed by the v5 run; v6 staging does not renew it. Keep
the current capture in place and do not run or retry `live-read` without a new
explicit one-run authorization, fresh live preflight, and deliberate capture
preservation. Do not broaden scope to control writes, interface claims, driver
detach, timeout changes, event-loop interruption, full Universal Control, or
Voice FX.
