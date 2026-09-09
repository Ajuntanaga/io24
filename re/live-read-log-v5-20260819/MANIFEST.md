# io24 v5 durable-log live-read

Performed exactly once on 2026-08-19 PDT after the user explicitly authorized
one bounded v5 live-read. The authorization covered this run only. It did not
authorize a retry, control write, interface claim or detach, timeout change,
event-loop interruption, full Universal Control, Voice FX, firmware work, or
use of the protected Wine prefix.

## Fresh preflight

- The exact staged v5 artifact passed the controlled durable-log contract,
  every existing completion/STALL/submit-error/event-loop contract, and real
  libusb init/exit inside a hardware-empty Bubblewrap namespace.
- Active `out/usbtap.so` and versioned `out/usbtap-log-v5.so` both matched
  SHA-256
  `9734fd0d09254f8717059b5abb0e05089ddf0cf024a526fc8965ebb0dc6341fc`.
- Exactly one `194f:0422`, serial `AB7C22200355`, was present at sysfs `1-2`
  and `/dev/bus/usb/001/003`, configuration 1, authorized at 480 Mbit/s.
- Interfaces 0 through 4 were owned by `snd-usb-audio`; interfaces 5 and 6
  were unclaimed. No Wine, UC, Xvfb, or project io24 process was running.
- The official and staged `PaeDSPUSB.sys` files byte-matched at SHA-256
  `fcd8b46d5af756172cb740386f89373e4129d0baa7f6ecb1ff1a173aed49c7bb`.
  All existing Wine overlay hashes also matched their harness pins.
- The protected prefix remained at
  `2026-08-12 00:31:35.825186221 -0700`; the disposable prefix was at
  `2026-08-19 00:56:36.730245956 -0700`.
- The filesystem had 145,920,450,560 bytes and 29,402,052 inodes free.

The non-opening isolation gate passed as transient unit
`io24-wine-live-audit-481073.service`, invocation
`fc88c8b0ea8f4ca999121815e4ba2723`: one io24 node was visible while audio,
GPU, host home, session bus, udev control, and external network remained
inaccessible. It used 6 MiB peak memory, 72 ms CPU, and zero swap.

Every v4 run output byte-matched its checkpoint before the current 584-byte
capture was atomically preserved as:

`out/live-service-usb-libusb-v4-20260819T005725PDT.txt`

That archive retains SHA-256
`d1a0faa893c348a53bfe4ef4160c8ecbaf9e90c84f8547fb974929d4100e8885`
and its original timestamp.

## One authorized run

Exactly this command was executed once and was not retried:

```bash
./tests/uc_wine_sandbox.sh live-read \
  /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.statusprobe-20260816
```

Observed result:

- transient unit `io24-wine-live-read-483042.service`, invocation
  `516b0a6e1b944a15a5e5f96d5e2978b8`;
- containment again exposed only the exact io24 node and printed
  `libusb debug level: 4`;
- installer and loader diagnostic status 255;
- registered `PreSonus Hardware Access Service` reached `RUNNING` on
  readiness check 1;
- no UCNET `DA` arrived within 8 seconds and `synchronize.json` was absent;
- final status 1 after 19.618 seconds, 3.011 seconds CPU, 103.2 MiB peak
  memory, and zero swap.

Service `RUNNING` is not synchronization evidence.

## V5 capture and immediate cause

The entire v5 capture is four lines, 244 bytes, SHA-256
`5f258683dafedb114ea95e358f6d414efeb20bb6c19b9a2ff8896ce632fc30c6`:

```text
# usbtap pid=74 tid=86 event=R-init object=unknown symbol=libusb_init
# usbtap pid=74 tid=86 event=L-global-unavailable
# usbtap pid=204 tid=217 event=R-init object=unknown symbol=libusb_init
# usbtap pid=204 tid=217 event=L-global-unavailable
```

There is no `L-global-installed`, native libusb message, `R-submit`, `S`, `C`,
`E`, `H-enter`, or `H-return`. In `service-install.log`, Wine reports:

```text
err:wineusb:usb_init Failed to initialize libusb: Operation not supported or unimplemented on this platform
```

That string is libusb status `-12`, which v5 deliberately returns when either
`dlsym(RTLD_NEXT, "libusb_init")` or
`dlsym(RTLD_NEXT, "libusb_set_log_cb")` is unavailable. `R-init` naming an
unknown object proves the real initializer lookup itself returned null.

V5 therefore failed closed before native libusb initialization and issued no
libusb USB transfer. This run does **not** test or change the v4 conclusion
about accepted requests that never produced callbacks. It exposes an
instrumentation loader-scope defect, not new device behavior.

## Root-cause reproduction

The staged Wine `wineusb.so` has direct PLT calls to `libusb_init()`,
`libusb_submit_transfer()`, and `libusb_handle_events()`, and a `DT_NEEDED`
dependency on `libusb-1.0.so.0`. The wrapper was selected for the init call,
but its `RTLD_NEXT` lookup could not see the dependency from its own loader
scope.

The earlier positive real-libusb contract explicitly promoted libusb with
`RTLD_GLOBAL`; that did not model Wine's private/local Unix-library scope. New
test files reproduce the relevant loader shape without hardware:

- `../../tests/usbtap_local_scope_contract.c` SHA-256:
  `254a34bbd67fe60f52a9ad8b27a751903d16081348e43472a712a1d229566177`;
- `../../tests/usbtap_local_scope_contract.sh` SHA-256:
  `a5ba2a62c506fb6535fa21473c2f7b3e74f8ad4ef957e8de6200b69057778ef3`.

The exact staged v5 bytes fail that offline contract with the same result:

```text
FAIL: local-scope libusb initialization returned -12
# usbtap pid=... tid=... event=R-init object=unknown symbol=libusb_init
# usbtap pid=... tid=... event=L-global-unavailable
```

This is an intentionally RED next-gate contract. No resolver change or v6
artifact was implemented during this live-read procedure.

## Postflight and checkpoint

At `2026-08-19T02:30:03-07:00`, the exact device remained at the same node,
configuration, authorization, and speed. Interfaces 5 and 6 remained
unclaimed; no Wine, UC, Xvfb, or project io24 process survived. The protected
prefix timestamp was unchanged. The disposable prefix changed as expected to
`2026-08-19 02:29:19.824265966 -0700`.

The kernel-journal window from 02:28:45 through 02:30:05 PDT contained no
entries. In particular, no recorded USB or xHCI reset/error accompanied the
run; journal absence is not stronger evidence than that bounded lookup.

All run artifacts and the retained unit/kernel journal windows are checksummed
at:

`out/checkpoints/live-read-log-v5-20260819T022919PDT/`

`SHA256SUMS` itself has SHA-256
`2a336af5345b137a24a4b40dc6ff826287f53fed1bac202bdb1e8d0d8d4fe94a`.
Key files are:

- `live-service-usb.txt`:
  `5f258683dafedb114ea95e358f6d414efeb20bb6c19b9a2ff8896ce632fc30c6`;
- `service-install.log`:
  `b49df6b497cf5da391460597bdb6a24572fa813b44710dc82c474ce539dab4f7`;
- `service-loader.log`:
  `46fa3be25ad8c77e377bb99d750df52ab39d75f34429afec670526bf833b368b`;
- `probe.log`:
  `74c9bc89c032995f8c92475ca61ba052cd806169dc592dee76db9a178e3f4018`;
- `run-journal.log`:
  `ecb7bdf704ca8c0c6f3b22eac25320e473160f1df4e08ac69f981cef8a8f7b2a`;
- `usbtap.so`:
  `9734fd0d09254f8717059b5abb0e05089ddf0cf024a526fc8965ebb0dc6341fc`.

## Gate

The one-run v5 authorization is consumed. Keep the current v5 capture and its
checkpoint in place and do not retry `live-read` automatically.

The next step is offline only: make the local-scope contract GREEN with a
handle-specific, provenance-checked resolution of the already loaded real
libusb, while keeping the existing global-scope, async, fail-closed, and
hardware-empty contracts green. Only after an exact v6 artifact is built,
hash-pinned, and staged should another one-run authorization be requested.
Do not broaden the scope to writes, interface claims, driver detach, timeout
changes, event-loop interruption, full Universal Control, or Voice FX.
