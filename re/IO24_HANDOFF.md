# io24 Wine driver checkpoint — 2026-08-18

This is the durable checkpoint for the next `resume io24`.

## Scope and safety boundary

- Target: the user's PreSonus Revelator IO 24 (`194f:0422`), for Linux
  interoperability research while preserving the working device.
- Continue passive/read-only-first. Do not write device state, guess PnP
  instances, modify license data, repeat `live-read`, or expose
  audio/GPU/session-bus access without a new, explicit gate authorization.
- Protect the real prefix at `/home/ajuntanaga/.wine-io24`.
- Use only the disposable, USB-hidden sandbox:
  `/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.statusprobe-20260816`.

## Root cause and fix

The former `STATUS_OBJECT_NAME_NOT_FOUND` (`0xc0000034`) driver-load failure is
localized and corrected in the disposable overlay.

1. `PaeDSPUSB.sys` opens its `License` key once.
2. It makes consecutive `RtlQueryRegistryValues` calls with
   `RTL_REGISTRY_HANDLE` and the same caller-owned handle.
3. Packaged Wine Staging 11.15 unconditionally closes `topkey` on return from
   the first call.
4. The next required query therefore failed with `0xc0000034`.

The source-equivalent fix preserves a caller-owned key when
`RTL_REGISTRY_HANDLE` is set:

```c
if (!(RelativeTo & RTL_REGISTRY_HANDLE))
    NtClose(topkey);
```

Project artifacts:

- Regression test: `re/wine-11.15-rtl-registry-handle-test.patch`
  (`c9716224cc294aeb844173fd8adb5c2e52a63c5842fd313142ea71b5813b6500`).
- Source fix: `re/wine-11.15-rtl-registry-handle-fix.patch`
  (`a442fa947143cc6408205f59b8621cb7c5462d7c0b59157065ff77f2916691f4`).
- Exact driver-sequence probe: `tests/io24_registry_probe.c`
  (`1528adf6ab11af660cae902aab6a016f683376a9477eb3ec6613be6777fb965f`).

The staged overlay is:

`out/wine-rtl-registry-handle/x86_64-windows/ntdll.dll`

Its SHA-256 is
`35729f3c03ed11c4a6ad33605d00b7280bc83f1d93044dd169132e0c673740de`.
It is the same size as packaged ntdll and differs only in the guarded call and
15-byte trampoline documented by
`out/wine-rtl-registry-handle/source/MANIFEST.md` (19 byte positions differ;
the unchanged call opcode is not counted). The packaged ntdll and real prefix
remain unmodified. The manifest records that the patched upstream runtime
passed `dlls/ntdll/tests/reg.ok`; its temporary source/build tree and raw test
log are no longer present, so recreate that build before making an upstream
submission claim.

## Fresh offline validation

On 2026-08-18 at approximately 17:19 PDT, this command was rerun:

```bash
IO24_DRIVER_REGISTRY_TRACE=1 ./tests/uc_wine_sandbox.sh driver-load \
  /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.statusprobe-20260816
```

Observed result:

- Harness isolation: `offline isolation verified: no host home, hardware, bus, or network`.
- Exact same-handle probe: status 0; `format`, `options`, and `customer` passed;
  the caller-owned License handle also closed successfully afterward.
- Driver: `start_status=0`, `query_status=0`, service state `RUNNING` during the
  bounded check.
- Trace: corrected `RtlIsNtDdiVersionAvailable 0x6010000`, corrected
  `ExIsProcessorFeaturePresent 10`, then `init done for L"PaeDSPUSB"`.
- No `c0000034`, license-read failure, PaeDSPUSB `ZwLoadDriver` failure, or
  reverted Wine stub appeared in the focused checks.
- Transient systemd unit: success in 11.259 seconds; 119.3 MiB memory peak;
  zero swap.
- Cleanup: no Wine, wineserver, Xvfb, UC, or PaeDSPUSB process survived.

Current evidence paths in the disposable sandbox:

- `out/registry-probe.log`
- `out/driver-load-registry.log`
- `out/driver-load-registry-status.txt`
- `out/driver-query-registry.log`
- `out/wine-rtl-registry-handle/source/MANIFEST.md`

The real prefix timestamp remained
`2026-08-12 00:31:35.825186221 -0700`. The device was present in sysfs as
`194f:0422`, serial `AB7C22200355`, but was not exposed to the run.

## Interpretation

The Wine registry-handle defect is now supported by independent evidence:

- the pre-fix driver trace ended at `0xc0000034`;
- the focused probe exercises the driver's tag and consecutive same-handle
  query sequence;
- the guarded overlay preserves the handle;
- the fresh USB-hidden driver gate initializes PaeDSPUSB successfully.

This is a Wine compatibility correction, not a license bypass. Do not change
the official tag, registry values, or proprietary validation.

## Live isolation audit — passed

The user explicitly authorized the `live-audit` gate on 2026-08-18 while the
interface was connected. Immediately before the run, host-side preflight found:

- exactly one `194f:0422` device at sysfs `3-1`;
- PreSonus Revelator IO 24 serial `AB7C22200355`, USB 2.0 high speed;
- current node `/dev/bus/usb/003/008`, accessible to the audit process;
- vendor-specific interface `3-1:1.5` present and unclaimed;
- audio interfaces 0–4 still owned by `snd-usb-audio`.

Only this command was authorized and run:

```bash
./tests/uc_wine_sandbox.sh live-audit \
  /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.statusprobe-20260816
```

The audit does not start Wine or open the USB node; its inner path only prepares
private directories and asserts containment. Result:

- `live isolation verified: one io24 node; no audio, GPU, home, bus, or external network`;
- transient unit `io24-wine-live-audit-843987.service`, invocation
  `4416065f28834698901e2f1f6a8ef16a`;
- success in 370 ms; 62 ms CPU; 5.5 MiB memory peak; zero swap.

Postflight at `2026-08-18T17:26:13-07:00` confirmed the same node, interface 5
still unclaimed, zero relevant Wine/UC/Xvfb process groups, unchanged real
prefix timestamp, and no `live-service-usb.txt` capture. No live-read traffic
or device write occurred.

## Live-read gate — attempted once, stopped safely

The user explicitly authorized `live-read` on 2026-08-18 while the interface
was connected. Static preflight reconfirmed that the application-layer probe
can send only `UM`, `JM Subscribe`, and `KA`; it has no `PV`, `PS`, or control
write path. A fresh optimized build of `tests/usbtap.c` matched the staged
interposer byte-for-byte at
`64ddfe1412ea2bf823374db17a726fd8cf74920456b1d396d9e5e114e37c166a`.

Immediately before the run, host-side preflight again found exactly one
`194f:0422`, serial `AB7C22200355`, at sysfs `3-1`, current node
`/dev/bus/usb/003/008`, with interface 5 unclaimed and no conflicting
Wine/UC process. The official and staged driver hashes matched at
`fcd8b46d5af756172cb740386f89373e4129d0baa7f6ecb1ff1a173aed49c7bb`.

Only this command was run:

```bash
./tests/uc_wine_sandbox.sh live-read \
  /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.statusprobe-20260816
```

Containment passed, and the disposable service reached `RUNNING`, but the
gate failed because no UCNET `DA` announcement arrived within 8 seconds:

- transient unit `io24-wine-live-read-859474.service`, invocation
  `e59ffe9c7a324494be9af2177459abf7`;
- exit-code result in 20.131 seconds; 3.122 seconds CPU; 182.1 MiB memory peak;
  zero swap;
- `live-service-usb.txt` absent: the interposer captured no libusb control,
  bulk, interrupt, or submitted-transfer payload;
- `synchronize.json` absent: no UCNET synchronization occurred;
- postflight found the same node, interface 5 still unclaimed, zero relevant
  process groups, and the real-prefix timestamp unchanged.

The run is preserved at:

`out/checkpoints/live-read-20260818T1735PDT/`

Key evidence hashes:

- `service-install.log`:
  `a94ddb646699f407d6aaf29e7d068d7a05682901531c98057873f9c8b9ceb607`;
- `service-loader.log`:
  `d40527559e3b6ccccec07f92a8730d48eaeefeee3ccef5acab655beb180256a4`;
- `probe.log`:
  `74c9bc89c032995f8c92475ca61ba052cd806169dc592dee76db9a178e3f4018`.

## Current live blocker (offline patch prepared)

The live trace and offline disassembly now localize the first live blocker
after successful registry/license handling:

1. Wine enumerates the exact physical composite instance and loads
   `PaeDSPUSB` for `MI_00` and `MI_03`; `init_driver` and both `AddDevice`
   calls succeed.
2. During device start, the driver issues three `IRP_MJ_PNP` minor `0x08`
   requests to the parent USB PDO. Wine reports each as
   `wineusb:pdo_pnp Unhandled minor function 0x8`.
3. Driver disassembly at `0x14002398c`, `0x1400239bd`, and `0x1400239ed`
   shows fallback queries for the same embedded GUID
   `{b1a96a13-3de0-4574-9b01-c08feab318d6}`, requesting interface versions
   3, 2, and 1 with sizes `0x60`, `0x50`, and `0x48` respectively.
4. The query helper at `0x140005610` initializes the IRP result to
   `STATUS_NOT_SUPPORTED` (`0xc00000bb`). All three calls return failure, and
   the next branch emits the driver's embedded message
   `Query Bus Interface failed.` The 27-character UTF-16 message explains the
   observed 96-byte `IoAllocateErrorLogEntry` attempt, which Wine stubs out.

Microsoft documents minor `0x08` as `IRP_MN_QUERY_INTERFACE` and requires the
bus driver to handle supported interfaces for its child PDO. Microsoft's USB
documentation identifies this request pattern as how a USB client obtains
`USB_BUS_INTERFACE_USBDI`; the version-3 structure is provided by the USB hub
driver for direct calls to hub routines:

- <https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/irp-mn-query-interface>
- <https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/querying-for-usb-interfaces>
- <https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbbusif/ns-usbbusif-_usb_bus_interface_usbdi_v3>

Therefore the current incompatibility is Wine 11.15 `wineusb` not exporting
the USB bus interface this driver requires. The former registry-handle defect
is no longer the active failure. This conclusion identifies the first blocker;
additional driver/Wine incompatibilities may appear after it is corrected.

## Offline Wine USBDI V1 gate — passed

On 2026-08-18, a signature-verified Wine 11.15 source tree was patched with a
minimal `IRP_MN_QUERY_INTERFACE` implementation for
`GUID_USB_BUS_INTERFACE_USBDI`. The implementation intentionally rejects
versions 3 and 2, allowing PaeDSPUSB's observed fallback to the exact
0x48-byte V1 ABI. It exports the V1 callback table, takes the required
interface reference, and derives high-speed state from the actual libusb
operating speed. Unobserved timing, isochronous, and bus-information callbacks
return `STATUS_NOT_SUPPORTED` rather than invented values.

Durable project artifacts:

- source patch: `re/wine-11.15-wineusb-usbdi-v1.patch`, SHA-256
  `9e1c3b88a428e3bdd245ee5cdda9dfa423e77ad4abe08c7423bf14dceb073e91`;
- focused contract test: `tests/wineusb_usbdi_contract.c` and
  `tests/wineusb_usbdi_contract.sh`;
- staged builtin overlay and full provenance:
  `re/wineusb-usbdi-v1/MANIFEST.md`.

The contract test was first red against pristine Wine because the helper did
not exist. After the patch it passed the GUID/version/undersize rejection,
0x48-byte ABI, callback-table, reference, and guard-buffer checks. A proper
out-of-tree Wine configure then compiled all three changed translation units
and linked the complete `dlls/wineusb.sys/all` target under `make -j1`, low
CPU/I/O priority, a 2 GiB address-space ceiling, and a hard timeout. No package
was installed; four pinned build packages were extracted under `/tmp` only.

Because this host has no MinGW compiler, the staged result is Wine's supported
builtin layout, not a standalone native-PE replacement:

- fake PE `x86_64-windows/wineusb.sys`:
  `b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e`;
- builtin `x86_64-unix/wineusb.sys.so`:
  `f6e8bc0bb15b1d29e94ccb49a09ddb0ae801aaacbdace62d6144b176444fbb07`;
- Unix library `x86_64-unix/wineusb.so`:
  `8d45157a7ba70479e95c27ec844601d83e5df85e34e73c7bfff36b4ab9df0b0e`.

The sandbox harness now hash-pins all three artifacts, forces the builtin
load, and read-only overlays the fake PE and Unix library only inside
bubblewrap. A fresh USB-hidden `driver-load` passed at 23:38 PDT:

- transient unit `io24-wine-driver-load-152291.service`, invocation
  `70ca6891a5154ccc8ebee1b10a0d24bc`;
- success in 17.537 seconds; 3.319 seconds CPU; 112.1 MiB memory peak; zero
  swap;
- Wine recognized the fake `wineusb.sys`, loaded its only available staged
  builtin, and completed `init_driver` for `wineusb`;
- the exact registry probe, corrected Windows 7 NT DDI/SSE2 paths, and
  PaeDSPUSB start/query all remained green;
- log SHA-256 `cba17477fa4dcfc1ee40bf1faef66de23494671802b95db5d762b45e0fc8bb6a`.

This gate used a private empty `/sys` and no `/dev/bus/usb`, so it could not
exercise the USB PDO or the new query-interface path. The connected device was
separately rechecked only through sysfs at `1-2`, `194f:0422`, serial
`AB7C22200355`, authorized at 480 Mbit/s. No Wine/UC/Xvfb process survived and
the real-prefix timestamp remained `2026-08-12 00:31:35.825186221 -0700`.

## Patched live-read — authorized once, stopped safely

The user explicitly authorized one patched `live-read` on 2026-08-18. Fresh
preflight reconfirmed the hash-pinned USBDI overlay, the read-only UCNET probe,
and exactly one connected `194f:0422` at sysfs `1-2`, node
`/dev/bus/usb/001/003`, serial `AB7C22200355`, authorized at 480 Mbit/s.
Interfaces 0–4 remained owned by `snd-usb-audio`; interfaces 5 and 6 were
unclaimed. No conflicting Wine/UC process existed, and the real-prefix
timestamp was unchanged.

Exactly this command was run once:

```bash
./tests/uc_wine_sandbox.sh live-read \
  /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.statusprobe-20260816
```

Observed result:

- containment reported `one io24 node; no audio, GPU, home, bus, or external
  network`;
- transient unit `io24-wine-live-read-163451.service`, invocation
  `49205ae8ae314bbc9ab7a1db1e42c5b7`;
- the diagnostic installer and loader phases returned 255, but the registered
  `PreSonus Hardware Access Service` reported `RUNNING` during three readiness
  checks;
- the UCNET probe returned status 1 because no `DA` announcement arrived
  within 8 seconds; `synchronize.json` was not created;
- the transient unit ended with status 1 after 31.738 seconds, 6.274 seconds
  CPU, 181.6 MiB memory peak, and zero swap.

Postflight found the same device identity, configuration, speed, and driver
ownership. No Wine, wineserver, Xvfb, PaeDSPUSB, or Universal Control process
survived. The real prefix remained at
`2026-08-12 00:31:35.825186221 -0700`. Do not treat service `RUNNING` as
synchronization evidence.

### USB evidence and interpretation

Unlike the first live-read, the patched run produced three 26-byte async
libusb submissions. Every submission begins with this USB setup packet:

```text
80 06 00 01 00 00 12 00
```

That decodes as device-to-host `GET_DESCRIPTOR`, device descriptor index 0,
requesting 18 bytes. It is a standard read request, not a proprietary control
write. The submit-only `tests/usbtap.c` build used for that run labeled every
async endpoint-zero submission as `Bo` based only on the endpoint direction
bit and recorded the buffer before calling real libusb. Consequently, the
historical capture proves that three descriptor reads were submitted; it does
not record their completion status or prove that a descriptor response
arrived. The trailing buffer bytes must not be treated as transmitted data for
this IN request.

The former query-interface blocker is absent from the new log: there are no
`wineusb:pdo_pnp Unhandled minor function 0x8` messages and no
`Query Bus Interface failed.` path. The patched driver therefore advanced
beyond `IRP_MN_QUERY_INTERFACE` into USB descriptor I/O.

The next driver error is represented twice by a 100-byte
`IoAllocateErrorLogEntry`. Wine stubs out the record, so its text is not
printed. The best-supported offline correlation is the driver's embedded
29-character message `Get Device Descriptor failed.`: the prior 96-byte
record mapped the same way to the 27-character query-interface message, and
the new record occurs immediately after the descriptor-request sequence. The
active blocker is therefore the device-descriptor request/completion path,
not the USBDI interface query. The precise libusb/Wine completion status is
not captured yet.

The raw run is preserved byte-for-byte at:

`out/checkpoints/live-read-usbdi-20260818T163451PDT/`

Key evidence hashes:

- `service-install.log`:
  `2f2a50c3ad8c9e558715d67d703663ddfa71c7b21470f953a5f6c8c8ee9393b8`;
- `service-loader.log`:
  `ef62704ea586a850033660035d99accda73ebf41e363dd977e216e4ba10fa1dd`;
- `probe.log`:
  `74c9bc89c032995f8c92475ca61ba052cd806169dc592dee76db9a178e3f4018`;
- `live-service-usb.txt`:
  `189078c8e36e68f32cedea126895d2192b02279a00ac1564a4ab3fd853ff2af9`.

## Offline async-control completion instrumentation — passed

On 2026-08-19, `tests/usbtap.c` was upgraded offline to distinguish async
control transfers and retain their callback result. It now:

- derives `Ci` versus `Co` from the control setup packet's `bmRequestType`,
  rather than endpoint zero;
- correlates `S` submit with `C` callback or immediate `E` submit error using
  one record ID;
- records numeric libusb callback status and `actual_length`;
- excludes stale receive-buffer bytes from IN submissions and records returned
  IN bytes, when present, alongside the callback's success or error status;
- restores the original callback and `user_data` before returning control to
  Wine;
- uses atomic IDs and whole-record stream locking for concurrent callbacks.

The real LD_PRELOAD interposer was tested against deterministic fake libusb
for callback success, asynchronous STALL, and immediate submit rejection. The
test was first observed RED against the historical submit-only implementation,
then passed both a fresh source build and the exact staged artifact. Full
provenance is in `re/usbtap-async-v2/MANIFEST.md`.

The staged artifact SHA-256 is
`fdd1a418be106ec91bafefbad8680eaec7ea8404148a18998178de630cfad916`.
It is active only as the disposable sandbox's `out/usbtap.so`; the former
submit-only bytes remain recoverable as
`out/usbtap-submit-only-64ddfe1412ea.so`. No Wine process or USB access was
used while staging, and the disposable prefix timestamp did not change.

Retained Wine 11.15 source provides a sharper decision boundary. Its
GET_DESCRIPTOR path logs an error when `libusb_submit_transfer` rejects
immediately; that error is absent from the preserved live log. The prior
request was therefore accepted for asynchronous processing. Wine then maps
the callback's `transfer->status` into `UrbHeader.Status` and copies descriptor
data only for `LIBUSB_TRANSFER_COMPLETED`. The new tap will reveal that missing
callback status and returned length without inventing the next Wine patch.

## Async-v2 live-read — authorized once, no callback observed

The user subsequently gave a new explicit authorization for exactly one
instrumented live-read. Fresh preflight on 2026-08-19 reconfirmed exactly one
`194f:0422` at sysfs `1-2`, `/dev/bus/usb/001/003`, serial
`AB7C22200355`, configuration 1, authorized at 480 Mbit/s. Interfaces 0–4
remained owned by `snd-usb-audio`; interfaces 5 and 6 were unclaimed. The v2
tap and all patched Wine overlays matched their staged hashes, no conflicting
process existed, and the protected real prefix was unchanged.

The harness first preserved the former submit-only capture as
`out/live-service-usb-submit-only-20260818T163451PDT.txt`, whose SHA-256
remains
`189078c8e36e68f32cedea126895d2192b02279a00ac1564a4ab3fd853ff2af9`.
It then ran this command once and did not retry:

```bash
./tests/uc_wine_sandbox.sh live-read \
  /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.statusprobe-20260816
```

Observed result:

- transient unit `io24-wine-live-read-209983.service`, invocation
  `de67df16755a422d99e444df453490ed`;
- containment exposed one io24 and no audio, GPU, home, session bus, or
  external network;
- installer status 255 and loader-diagnostic status 255, while the registered
  service reached `RUNNING` on readiness check 1;
- the read-only UCNET probe returned status 1 because no `DA` announcement
  arrived within 8 seconds; `synchronize.json` was not created;
- the unit ended with status 1 after 21.823 seconds, using 3.481 seconds CPU,
  101.8 MiB peak memory, and zero swap.

Postflight found the same device identity, configuration, speed, and interface
ownership. No Wine, wineserver, Xvfb, PaeDSPUSB, or UC process survived. The
protected real prefix remained unchanged. The disposable prefix changed only
as expected from this contained run, to
`2026-08-19 00:15:12.496283080 -0700`.

### Decisive USB evidence

The v2 capture is four lines, 276 bytes, SHA-256
`0cbd3983e846eba64b9e1b0a7732408d7c82f80d2c7818f0d20950b91836f0b8`:

```text
ffff880000000000 7329741567 S Ci:1:004:00 -115 8 = 80060001 00001200
ffff880000000001 7330134096 S Ci:1:004:00 -115 8 = 80060001 00001200
ffff880000000000 7346138180 S Ci:1:004:00 -115 8 = 80060001 00001200
ffff880000000001 7346437762 S Ci:1:004:00 -115 8 = 80060001 00001200
```

Every record is an accepted standard IN `GET_DESCRIPTOR(Device)` submission
requesting 18 bytes. There is no `E` immediate libusb submission failure and
no `C` callback of any status. Thus the requests crossed Wine's URB dispatch
and were accepted by libusb, but no callback reached the interposer during
either bounded installer process. This is not evidence for `COMPLETED`,
`STALL`, `TIMED_OUT`, or any other callback status; none was observed.

The repeated 0/1 IDs are best explained by the harness's two separate process
launches: the second pair begins about 16 seconds after the first, matching the
15-second installer boundary followed by the loader diagnostic. V2 did not
record PID, so retain this as a timing-supported inference rather than direct
process attribution.

The new service log contains two 100-byte `IoAllocateErrorLogEntry` attempts,
consistent with the driver's `Get Device Descriptor failed.` path. The older
`IRP_MN_QUERY_INTERFACE` / `Query Bus Interface failed.` blocker is absent,
and there is no `Failed to submit GET_DESCRIPTOR transfer` error.

Retained Wine 11.15 source shows a dedicated event thread initially
enumerating the device on Wine thread `00cc`; Wine's separate PnP manager
thread `00ac` loads PaeDSPUSB and issues the descriptor URBs. The event thread
then calls `libusb_handle_events(NULL)`, whose callback queues
`USB_EVENT_TRANSFER_COMPLETE` before Wine completes the IRP. The current trace
does not show whether that event call stayed blocked, returned without
delivery, or stopped for another reason, so an event-loop cause is localized
but not yet proven.

The run and every copied file were byte-verified at:

`out/checkpoints/live-read-async-v2-20260819T001451PDT/`

Key hashes:

- `service-install.log`:
  `8b14064ca26197c16f7efe2bc31e50d10d0e9f962db850ef624cca3964013230`;
- `service-loader.log`:
  `227cd5ae07760606ed6d318fefa2bb4fa7a94e36f035932d08d61de243f7c9c7`;
- `probe.log`:
  `74c9bc89c032995f8c92475ca61ba052cd806169dc592dee76db9a178e3f4018`;
- `usbtap.so`:
  `fdd1a418be106ec91bafefbad8680eaec7ea8404148a18998178de630cfad916`.

## Offline event-loop instrumentation v3 — passed and staged

The missing discriminator was prepared offline without another USB open.
`tests/usbtap.c` now wraps the exact `libusb_handle_events()` entry point and
adds comment records for PID, TID, correlated transfer phase, event-handler
entry, and event-handler return status. The usbmon data records remain
unchanged and `tests/usbmon_decode.py` ignores the comment records.

The contract was first observed red against v2 because PID/TID and event-loop
markers were absent. V3 then passed callback success, asynchronous STALL,
immediate submit rejection, normal event-handler return, and a deliberately
blocked event handler. The blocked case must emit one `H-enter` and no
fabricated `H-return`. Full provenance is in
`re/usbtap-event-v3/MANIFEST.md`.

The v3 artifact SHA-256 is
`bfc1a6ff8553c65e207c240eef8fdc59b50ef7ba8e9c7d89961d81ee6f48dd42`.
The exact bytes are staged as both disposable `out/usbtap-event-v3.so` and
active `out/usbtap.so`; v2 remains preserved as `out/usbtap-async-v2.so`.
The active artifact passed the exact contract after staging, and the
disposable prefix timestamp did not change during this offline work.

The live-read harness now hash-pins v3. Because an `H-enter` comment can make
the log nonempty without any USB request, the synchronization-success gate was
also tightened to require a real non-comment `S`, `C`, or `E` usbmon record.
`bash -n` passes.

## Event-loop v3 live-read — authorized once, pump wait confirmed

The user explicitly authorized one v3 event-loop live-read. Fresh preflight
again proved the exact `194f:0422`, serial `AB7C22200355`, at sysfs `1-2` and
host node `/dev/bus/usb/001/003`; interfaces 5 and 6 were unclaimed. Both
source and exact staged-v3 contracts passed, the probe remained read-only, no
conflicting process existed, and both prefixes had the expected timestamps.
The managed diagnostic shell hid `/dev/bus/usb`, so host-node existence and
access were separately verified through the authorized host-side surface.

The v2 capture was byte-matched to its checkpoint and preserved as
`out/live-service-usb-async-v2-20260819T001451PDT.txt`, SHA-256
`0cbd3983e846eba64b9e1b0a7732408d7c82f80d2c7818f0d20950b91836f0b8`.
The harness then ran `live-read` exactly once and did not retry:

- unit `io24-wine-live-read-242096.service`, invocation
  `4284822ee4034c42aaac05d6e09360ce`;
- containment again exposed one io24 and no audio, GPU, host home, session
  bus, or external network;
- installer and loader diagnostic returned 255, while the registered service
  reached `RUNNING` on readiness check 1;
- no UCNET `DA` arrived within 8 seconds and `synchronize.json` was absent;
- status 1 after 21.378 seconds, 3.400 seconds CPU, 102.1 MiB peak memory, and
  zero swap.

The 10-line v3 capture directly resolves the prior PID and event-entry
uncertainty. Contained process 74 entered `libusb_handle_events()` on thread
86, while thread 78 submitted two descriptor reads. Process 203 entered the
same handler on thread 215, while thread 207 submitted two more. All four
requests were accepted standard IN `GET_DESCRIPTOR(Device)` requests for 18
bytes. Neither process emitted an immediate `E`, callback `C`, or event-handler
`H-return` before bounded teardown.

Therefore Wine did start a dedicated libusb event handler in each process,
but the handler remained inside libusb while the descriptor transfers were
outstanding and no completion event reached Wine. This proves event wait, not
its underlying cause: `libusb_handle_events()` is intentionally blocking and
these transfers have an infinite libusb timeout, so current evidence cannot
distinguish a USB/device request that never completed from a usbfs/libusb
notification or reap failure.

No matching USB, xHCI, reset, stall, timeout, warning, or error appeared in
the kernel journal during the run. The two 100-byte PaeDSPUSB error records
again align with `Get Device Descriptor failed.` The former registry and
USBDI-query blockers remain absent.

Postflight found the same device, node access, speed, configuration, and
interface ownership; no Wine/UC/Xvfb process survived. The protected real
prefix remains at `2026-08-12 00:31:35.825186221 -0700`; the disposable
prefix changed as expected to `2026-08-19 00:33:48.706786759 -0700`.

The raw capture is 584 bytes, SHA-256
`4f685e2a74fe94bdac896c025c89cf6a45d9f518a19410ffd422435c1847fdca`.
Every checkpoint copy byte-matched its source at:

`out/checkpoints/live-read-event-v3-20260819T003432PDT/`

Full authorization, capture, hash, and interpretation details are in
`re/live-read-event-v3-20260819/MANIFEST.md`.

## Offline native-libusb debug stage v4 — passed

The requested continuation was interpreted as the offline next step, not a
new live authorization. The selected discriminator is native libusb level-4
logging rather than a broad `ioctl` interposer: it exposes submit, event,
poll/reap, URB status, and backend errors without changing the descriptor
transfer, timeout, callback, or Wine control flow.

The installed Ubuntu `libusb-1.0-0` is 1.0.29-2build1; its exact
`libusb-1.0.so.0` SHA-256 is
`e422dc361a501e8175a94e16228704de7ca6376037fc29a0e7272e8fe2c8edc1`.
Its binary contains diagnostics for `op_submit_transfer`,
`op_handle_events`, `reap_for_handle`, submit/reap errno, URB status/length,
and completed reaping.

`tests/uc_wine_sandbox.sh` now sets `LIBUSB_DEBUG=4` only in the outer
`live-read` Bubblewrap block. The inner live-USB service fails closed unless it
sees exactly level 4 and prints the level before starting Wine. Debug output
will follow the existing service log redirections while the unchanged v3 tap
continues recording correlated event and transfer markers.

An empty-device contract was first observed RED because the harness had zero
debug settings. After the patch it passed against real libusb inside
Bubblewrap with no `/dev/bus/usb`, empty `/sys`, `/run`, `/home`, and `/tmp`,
no udev runtime, no network, and only `/usr` plus the probe mounted read-only.
The probe refuses to initialize if a USB, sysfs USB, or udev path is visible,
then requires native debug records for both `libusb_init()` and
`libusb_exit()`.

Durable files and full hashes are in `re/libusb-debug-v4/MANIFEST.md`. Neither
Wine prefix nor the current v3 capture timestamp changed, and no Wine/UC/Xvfb
process survived because none was started.

## Native-libusb v4 live-read — authorized once, logger gap confirmed

The user explicitly authorized one v4 native-libusb-debug live-read. All
offline contracts, device/node identity, interface ownership, process,
artifact, prefix, capacity, and live-isolation gates passed. Every current v3
output byte-matched its checkpoint before the capture was preserved as
`out/live-service-usb-event-v3-20260819T003432PDT.txt`.

The harness ran `live-read` exactly once and did not retry:

- unit `io24-wine-live-read-276864.service`, invocation
  `ecec6039bf7a47469653600460105d2a`;
- containment exposed only the exact io24 node and printed
  `libusb debug level: 4`;
- the registered service reached `RUNNING` on readiness check 1;
- no UCNET `DA` arrived within 8 seconds and `synchronize.json` was absent;
- status 1 after 21.455 seconds, 3.422 seconds CPU, 103.4 MiB peak memory,
  and zero swap.

The 584-byte tap capture has SHA-256
`d1a0faa893c348a53bfe4ef4160c8ecbaf9e90c84f8547fb974929d4100e8885`.
After normalizing only timestamps it is identical to v3: two event-handler
entries, four accepted `GET_DESCRIPTOR(Device)` submissions, and no immediate
submit error, callback, or event-handler return.

Native libusb produced two identical 94-record initialization sequences. The
`service-install.log` libusb thread `0x56` is tap thread 86; the
`service-stop.log` libusb thread `0xd7` is tap thread 215. Both sequences found
usbfs/sysfs, enumerated sysfs `1-2` as bus 1 address 3, successfully opened the
sole exposed node, added its event source, and parsed its configuration. The
`ENOENT` opens belong only to other sysfs-enumerated devices whose USB nodes
were deliberately hidden by containment.

No native `libusb_submit_transfer`, backend submit, event, reap, URB status,
or completion record reached those logs. This does not mean submission was
skipped: the tap called the real submit function and all four calls returned
zero. The installed library contains a level-4 submit-entry record, so v4
instead exposes a native logging coverage gap after enumeration/open. A log
level change or sink disconnect remains possible and unproven.

Postflight found the same device/node/configuration/speed, interfaces 5 and 6
still unclaimed, no surviving Wine/UC/Xvfb process, no matching kernel USB or
xHCI event, and the protected prefix unchanged. The disposable prefix changed
as expected to `2026-08-19 00:56:36.730245956 -0700`.

All copied artifacts byte-match the new checkpoint at
`out/checkpoints/live-read-libusb-v4-20260819T005725PDT/`. Full hashes,
authorization, raw capture, thread correlation, and interpretation are in
`re/live-read-libusb-v4-20260819/MANIFEST.md`.

## Next gate

The one v4 run authorization is consumed. Do not move the current v4 capture,
retry live-read, proceed to full Universal Control, touch Voice FX, detach a
kernel driver, claim an interface, alter timeouts, interrupt the event
handler, or send a control write without a new explicit authorization.

The safest next step is offline: stage a dedicated native libusb log callback
or equivalently narrow file sink, prove submit/event/reap coverage without
hardware, and only then request another bounded live-read. If durable native
logging still cannot see backend progress, stage a narrow usbfs
submit/poll/reap interposer offline before considering another run.

For upstream-quality Wine work, separately recreate the Wine 11.15 source
tree with MinGW and retain raw build/test logs beside the source patches. The
current Wine patch is diagnostic-quality and deliberately limited to USBDI
V1; do not make an upstream-submission claim from it.

## Durable libusb callback v5 — staged offline, live gate closed

The v4 gap has now been addressed offline. Upstream libusb 1.0.29 emits a
debug record at exported `libusb_submit_transfer()` entry and routes enabled
messages through a global callback instead of stderr when one is installed.
The retained Wine `wineusb.so` calls `libusb_init(NULL)`, so v5 interposes that
entry point, installs a durable global callback before the real initializer,
and records `dladdr()` provenance for the actual init and submit targets.
Failure to resolve either native initializer or callback API fails closed.

A controlled fake-libusb contract was first RED against v3 because no global
callback was installed. The revised source and exact artifact now pass durable
init/submit/event capture, stderr exclusion, real-submit routing, and every
existing completion, STALL, immediate-submit-error, and event-loop contract.
The exact artifact also passes a real-libusb init/exit contract inside a
hardware-empty Bubblewrap namespace with no USB tree, sysfs USB tree, udev
runtime, or network access.

The v5 ELF has SHA-256
`9734fd0d09254f8717059b5abb0e05089ddf0cf024a526fc8965ebb0dc6341fc`
and ELF build ID `acad8398130205bf1c5e97c56fe8bbabac37053d`. It is staged
only in the disposable sandbox as `out/usbtap-log-v5.so` and active
`out/usbtap.so`; the harness hash-pins those exact bytes. V3 remains at
`out/usbtap-event-v3.so`.

No Wine/UC live-read ran during v5 work. The current 584-byte v4 capture is
unchanged at SHA-256
`d1a0faa893c348a53bfe4ef4160c8ecbaf9e90c84f8547fb974929d4100e8885`
with timestamp `2026-08-19 00:56:36.133867593 -0700`; disposable
`prefix/system.reg` also retained its v4 timestamp. Full source hashes,
contracts, staging provenance, and interpretation are in
`re/usbtap-log-v5/MANIFEST.md`.

The v4 authorization is consumed and v5 staging does not renew it. The next
step, if explicitly authorized, is one newly bounded v5 `live-read` after a
fresh full preflight and preservation of the current capture. Do not run it
automatically or broaden scope to writes, interface claims, driver detach,
timeout changes, event-loop interruption, full Universal Control, or Voice FX.

## Durable-log v5 live-read — authorized once, failed closed at resolution

The user explicitly authorized one bounded v5 live-read. Every offline,
device/node, interface ownership, process, artifact, overlay, driver, prefix,
capacity, evidence-preservation, and isolation gate passed. The prior v4
capture was byte-verified and preserved as
`out/live-service-usb-libusb-v4-20260819T005725PDT.txt`.

The harness ran exactly once as unit
`io24-wine-live-read-483042.service`, invocation
`516b0a6e1b944a15a5e5f96d5e2978b8`, and was not retried. It again exposed
only the exact io24 node, reached service `RUNNING`, received no UCNET `DA`,
and exited status 1 after 19.618 seconds. CPU was 3.011 seconds, peak memory
103.2 MiB, and swap zero.

The 244-byte capture contains only two identical process sequences:
`R-init object=unknown` followed by `L-global-unavailable`. Wine explicitly
reports that `usb_init` failed with operation-not-supported, matching v5's
fail-closed `-12`. There is no callback installation, native libusb message,
submit resolution, transfer, or event-loop record. V5 therefore stopped before
libusb initialization and did not issue a libusb USB transfer. This is an
instrumentation result, not new evidence about the device or the v4 pending
transfers.

An offline local-scope loader contract now reproduces the exact `-12` and
unknown-target sequence against the staged v5 bytes. The prior positive
integration contract explicitly loaded libusb `RTLD_GLOBAL`, masking Wine's
private/local dependency scope. The new contract remains intentionally RED;
no v6 implementation or second hardware run occurred.

Postflight found the exact device unchanged, interfaces 5 and 6 unclaimed, no
surviving Wine/UC/Xvfb/io24 process, and the protected prefix unchanged. Full
authorization, preflight, capture, root-cause evidence, hashes, and bounded
interpretation are in `re/live-read-log-v5-20260819/MANIFEST.md`. Exact run
artifacts verify at
`out/checkpoints/live-read-log-v5-20260819T022919PDT/`.

The v5 authorization is consumed. Keep the current capture in place and do
not retry. The next gate is offline: resolve the already loaded real libusb by
an explicit handle/provenance path, make the new local-scope contract GREEN,
keep every prior contract GREEN, then build and hash-pin v6 before requesting
another one-run authorization. No writes, claims, detach, timeout changes,
event-loop interruption, full Universal Control, or Voice FX are authorized.

## Local-scope libusb resolver v6 — passed and staged offline

The v5 loader-scope defect is now resolved without changing Wine's loader
topology. V6 first honors a provenance-validated `RTLD_NEXT` result, then
falls back to an explicit handle obtained with
`RTLD_NOW | RTLD_LOCAL | RTLD_NOLOAD`. It accepts only the exact requested
symbol from an ELF base other than the interposer, retains the handle for the
process lifetime, and returns `-12` when a callable target remains unresolved.
The same resolver now covers initialization, callback installation, sync
transfers, async submit, and event handling.

The tightened local-scope fixture gives its fake dependency the real libusb
SONAME, loads it privately, and exercises init, callback, submit/completion,
and event handling. Exact v5 was first RED with the same unknown `R-init` and
`-12` observed live. V6 then passed that contract plus the durable-log,
completed/STALL/submit-error, event-loop, and real-libusb init/exit contracts
as a source build, exact build artifact, and exact staged artifact. The
real-libusb contract now uses `RTLD_LOCAL` and still runs with USB, USB sysfs,
udev, and network paths absent.

The reproducible 21,584-byte v6 ELF has SHA-256
`dbce256b328b53866dd13dbe382c28b216a1baf64bdb47fc746b722375e86977`
and build ID `fdc6614838445964b3dbc8ab55726fd894268be1`. Those exact bytes are
staged only in the disposable sandbox as `out/usbtap-resolver-v6.so` and
active `out/usbtap.so`; the harness pins that hash. V5 remains recoverable as
`out/usbtap-log-v5.so`.

No Wine, UC, or live-device run occurred. The current 244-byte v5 capture and
its checkpoint still byte-match SHA-256
`5f258683dafedb114ea95e358f6d414efeb20bb6c19b9a2ff8896ce632fc30c6`;
the capture inode/timestamp and disposable `prefix/system.reg`
inode/timestamp were unchanged by staging. Full hashes, contracts, build
provenance, and exact staging evidence are in
`re/usbtap-resolver-v6/MANIFEST.md`.

The v5 authorization remains consumed, and the existing capture makes the
harness refuse a new run before service launch. Do not archive it or run v6
without a fresh live preflight and explicit one-run authorization. No retry,
control write, interface claim, driver detach, timeout change, event-loop
interruption, full Universal Control, or Voice FX is authorized.

## Resolver v6 live-read — completed once and checkpointed

The user subsequently explicitly authorized one bounded v6 live-read. It ran
exactly once as `io24-wine-live-read-560914.service` and was not retried. The
exact v6 resolver worked: two contained Wine processes installed the real
libusb callback, issued 137 asynchronous control-IN descriptor requests, and
received 137 status-zero callbacks. There are no immediate-submit errors,
bulk/interrupt transfers, control-OUT payloads, interface claims,
or detach operations in the capture.

The service reached `RUNNING`, but no UCNET `DA` arrived, so this is not a
synchronization result. It exited status 1 after 22.234 seconds, 3.630 seconds
CPU, and 106.6 MiB peak memory. The 224,247-byte capture has SHA-256
`f7bb87af84915b94a201d7762af0f2f27c017762981c8387175bf2face56c576`.
Every run artifact verifies under
`out/checkpoints/live-read-resolver-v6-20260819T030035PDT/`.

The prior descriptor-completion blocker is removed. The next repeatable Wine
failures are unsupported `URB_FUNCTION_CLASS_INTERFACE` (`0x1b`), followed by
unsupported `URB_FUNCTION_SELECT_INTERFACE` (`0x01`). The first correlates
with the driver's `Audio Controller initialization failed.` path and the
second with `Set Configuration failed.`, but the exact class-request fields
were not logged. Static driver analysis shows both IN and OUT class requests
and multiple candidate call sites, so do not guess or implement one from the
binary alone. Select-interface semantics would cross the existing no-claim,
no-alternate-setting boundary.

Full run facts, capture counts, hashes, static/dynamic evidence separation,
and the new gate are in `re/live-read-resolver-v6-20260819/MANIFEST.md`.

## Prior checkpoint: WineUSB observation v2 — source staged, not built

This historical checkpoint is superseded by the completed offline gate in the
next section.

`re/wine-11.15-wineusb-urb-observe-v2.patch` is a narrow observation-only
patch against the retained Wine 11.15 plus USB-DI-v1 source. It logs the
class-interface request tuple and select-interface structure, then still
returns `STATUS_NOT_IMPLEMENTED`. It adds no submission, buffer dump, device
write, interface claim/detach, or alternate-setting operation. It passed a
zero-fuzz dry application; details are in
`re/wineusb-urb-observe-v2/MANIFEST.md`.

No overlay was built because the retained tree is not configured and current
build prerequisites are absent. No package install or dependency download was
attempted. At the resume check, the same device remained at sysfs `1-2` (now
devnum 2), interfaces 0-4 stayed with `snd-usb-audio`, 5-6 stayed unclaimed,
no Wine/UC/Xvfb/io24 process survived, the sealed v6 checkpoint verified, and
the protected prefix timestamp was unchanged.

The one-run v6 authorization is consumed. The next step is offline only:
recreate pinned build inputs without changing host packages, compile and test
the observation overlay in USB-hidden containment, then hash-pin and stage it.
Do not run it live without a new explicit one-run authorization. Semantic URB
support, device writes, claims/detach, alternate-setting changes, full UC,
Voice FX, and the protected prefix remain out of scope.

## WineUSB observation v2 — reproducible overlay staged; live gate closed

The offline gate above is complete. Wine 11.15 was independently extracted,
patched with USB-DI v1 followed by observation v2 at zero fuzz, configured, and
built twice in networkless Bubblewrap namespaces with USB, sysfs, udev, host
home, and the protected prefix absent. The two build logs and all three output
artifacts are byte-identical. No package was installed on the host.

The staged artifacts are:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  re/wineusb-urb-observe-v2/x86_64-windows/wineusb.sys
e5d4d22ec48ac4321627b30fb014133193d7d77bff3f296e867c1cafe7e07520  re/wineusb-urb-observe-v2/x86_64-unix/wineusb.sys.so
03a4c63ec669bf4f05789dfffd42c55e10d9e0ef990a1cc0622c1a0ab7812826  re/wineusb-urb-observe-v2/x86_64-unix/wineusb.so
```

Both independent builds and the exact staged bytes passed the USB-DI and
observation contracts with USB hidden. The observation contract enforces
logging-only handling and the common `STATUS_NOT_IMPLEMENTED` return; it
rejects libusb submission, transfer-buffer copying, or success semantics.

`tests/uc_wine_sandbox.sh` now hash-pins this exact triplet for driver modes
(SHA-256
`d0efc42a017bde60763976d5fa0985253b4acb19c6b8fe963244ea14caaf20d0`).
The sealed v6 sandbox was cloned rather than reused. A single offline
`driver-load` in `io24-wine-sandbox.observe-v2-20260819` completed status 0 as
unit `io24-wine-driver-load-599712.service`, invocation
`03b94be02d374ab0b7b7bc08bcd6d385`. Isolation, registry-handle, Windows 7 NT
DDI, and SSE2 gates passed; PaeDSPUSB start/query returned 0 and reported
`RUNNING`. Zero observation markers appeared, as expected without a USB PDO.
The unit was collected and no Wine/Xvfb/PreSonus process survived.

Exact run evidence verifies under
`out/checkpoints/driver-load-observe-v2-20260819T192259PDT/` in the cloned
sandbox; its `SHA256SUMS` file hashes to
`4fbaa428e453c34757ce40c129b5e38103ad9f96799ad16c9fe40e3d0544aaad`.
Project checkpoints CP0 through CP3 and the complete interpretation are under
`re/wineusb-urb-observe-v2/`.

Postflight still found no connected io24. The protected prefix is unchanged,
and the original sealed v6 sandbox retains the same `system.reg` and
224,247-byte capture hashes. The cloned prefix changed only as part of its
disposable driver-load run.

Stop at this checkpoint. A device is required only for a future observation
trace. Reconnection alone is not authorization: perform a fresh preflight and
obtain explicit one-run approval before `live-read`. Do not implement either
URB, issue writes, claim/detach an interface, select an alternate setting,
alter timeouts, run full UC or Voice FX, or touch the protected prefix.

## WineUSB observation v2 live-read — completed once; class tuple identified

The user subsequently authorized one bounded observation-only `live-read` and
reported the io24 connected. Fresh preflight and a separate non-opening
isolation audit passed: exactly one `194f:0422`, serial `AB7C22200355`, was at
sysfs `1-2` and `/dev/bus/usb/001/005`, configuration 1, 480 Mbit/s;
interfaces 0-4 remained on `snd-usb-audio`, 5-6 remained unclaimed; no
competing process existed; and the pinned overlays, logger, harness, driver,
prior capture, sealed v6 sandbox, CP3 checkpoint, protected prefix, and
capacity gates passed.

The inherited v6 capture was preserved before launch. The observation overlay
then ran exactly once as `io24-wine-live-read-625692.service`, invocation
`2c5ad2102bd24c11bc1e76ed60b844f6`, and was not retried. The registered
service reached `RUNNING`, but no UCNET `DA` arrived. The bounded run exited
status 1 after 30.151 seconds, 5.758 seconds CPU, 110.6 MiB peak memory, and
zero swap.

The new 1,723-line capture has SHA-256
`f7ae3a97696dfd1ceff7b511c307d054422250e481deceb7b180167538762a67`.
It contains 106 accepted control-IN descriptor submissions, 106 status-zero
callbacks, and no OUT, bulk, interrupt, or immediate-submit-error record.

Observation v2 logged two identical `URB_FUNCTION_CLASS_INTERFACE` requests:

```text
flags=0x3 length=256 reserved=0 request=0x02 value=0x0100 index=0x0500
```

It returned `STATUS_NOT_IMPLEMENTED` both times, so neither request reached the
device. Combined with the returned UAC2 AudioControl descriptor—interface 0
and Clock Source/entity ID 5—the tuple identifies a high-confidence Clock
Source Sampling Frequency `RANGE` read: `a1 02 00 01 00 05 00 01` as the
eight setup-packet bytes on the wire. This is an inferred setup packet, not a
captured transfer or response.

The overlay also twice observed `URB_FUNCTION_SELECT_INTERFACE` with a null
configuration handle and zeroed interface tuple, then failed closed. Do not
infer or implement select-interface semantics yet; that path could change
alternate-setting/interface state.

Postflight found the same device/configuration and interface ownership, no
surviving Wine/UC/Xvfb/io24 process, unchanged protected prefix, and unchanged
original sealed v6 evidence. The disposable clone's registry changed only as
expected from its live service run.

Full facts are in `re/live-read-observe-v2-20260819/MANIFEST.md`; project
checkpoint CP4 is
`re/wineusb-urb-observe-v2/checkpoints/CP4_LIVE_OBSERVATION.md`. Exact evidence
verifies under
`out/checkpoints/live-read-observe-v2-20260819T194220PDT/` in the clone; its
`SHA256SUMS` file hashes to
`45f75278cca8a31fbb70e659efc47849d43f4160ddf0272d99efc6b779f41634`.

The one-run live authorization is consumed. Do not retry or replace the active
capture. The next safe checkpoint is offline class-interface-IN design and
fake-libusb contracts, followed by reproducible build and hash-pinning. The
device is not needed for that work. A later device test requires a new explicit
one-run authorization. Semantic URB support, writes, claims/detach,
select-interface/alternate-setting behavior, full UC, Voice FX, and the
protected prefix remain out of scope.

## WineUSB class-interface-IN v1 — staged and driver-loaded offline

The offline class-IN gate is complete. A fake-libusb RED baseline was followed
by a narrow implementation accepting only the observed IN request
`flags=0x3 request=0x02 value=0x0100 index=0x0500 length=256`; all altered,
unknown, missing-buffer, or OUT forms fail before submission. Completion,
cancellation, STALL, overrun, immediate-error cleanup, and ten rejection cases
are covered. Select-interface remains fail-closed and unimplemented.

Two independent clean Wine 11.15 builds produced a byte-identical triplet.
Both builds and the staged bytes passed the class-IN fake-libusb/source/binary
contract and USB-DI v1 in USB-hidden containment. The staged hashes are:

```text
b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  x86_64-unix/wineusb.sys.so
d5cbdf21f773488523c16bec90af8d83f9c7a9464afc39dceefdea16e399edbc  x86_64-unix/wineusb.so
```

The harness now hash-pins that triplet for driver modes (SHA-256
`4706b84e5ea5daff2b274af28f6faf051fc66797cb5d569ecc9237ea4effaf7c`).
The observation sandbox was preserved and cloned to
`/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.class-in-v1-20260819`.
Exactly one offline driver-load ran there as
`io24-wine-driver-load-822720.service`, invocation
`0233fe7e28e94120ad439220eaff61fa`. Isolation and registry/NT-DDI/SSE2 gates
passed, PaeDSPUSB start/query returned 0, it reported `RUNNING`, and cleanup
unloaded it. Runtime was 22.922 seconds, peak memory 57.3 MiB, and swap zero.

No USB PDO existed, so there were zero class-IN, class-OUT, or observation
markers. This validates only the offline overlay/driver load path, not a device
response or synchronization. Exact evidence verifies under
`out/checkpoints/driver-load-class-in-v1-20260819T231029PDT/` in the new clone;
its `SHA256SUMS` hashes to
`4e9e14779bf20a8a8f76a00a4ebb261268764624b6f8a135198832275e6270c1`.
Full interpretation is in `re/wineusb-class-interface-in-v1/MANIFEST.md` and
project checkpoint `checkpoints/CP8_STAGED_OFFLINE.md`.

Postflight found no io24 and no surviving Wine/UC/Xvfb process. The protected
prefix and source observation sandbox remain unchanged; the new clone's
registry changed only as expected during its disposable driver run, while its
inherited capture remained hash-identical.

Stop at this checkpoint. A future class-IN live-read requires the device, a
fresh full preflight, capture preservation, and new explicit one-run
authorization. Reconnection alone is not authorization. Do not add class OUT,
select-interface/alternate-setting semantics, claims/detach, timeout changes,
full Universal Control, Voice FX, or protected-prefix access.

## WineUSB class-interface-IN v1 live-read — completed once; usbfs EBUSY

The user subsequently authorized exactly one bounded class-IN live-read. It
was launched once against
/home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.class-in-v1-20260819
as unit io24-wine-live-read-854561.service, invocation
cb532c4af3a04271bf4c2c4ce92affb3. The user said pause while it was in flight,
so no immediate analysis or postflight ran in that turn. The command later
completed status 1 after 38.982 seconds, with 7.985 seconds CPU, 105.3 MiB
peak memory, and zero swap. It was not retried.

Containment exposed one exact io24 node and no audio, GPU, host home, session
bus, or external network. The registered PreSonus service reached RUNNING,
but no UCNET DA arrived within 8 seconds and synchronize.json is absent.
RUNNING remains service-state evidence only.

The 149,021-byte capture has SHA-256
c05811fb8f488a3ae28574792e3951f6e4cf91fedc7a88824e4eb9af774978c5.
It contains 96 asynchronous control-IN submissions, 94 status-zero callbacks,
and two immediate errors. There are no control-OUT, bulk, or interrupt
records.

Both errors are the exact CP8 class request:

    a1 02 00 01 00 05 00 01

libusb accepted the call path but USBDEVFS_SUBMITURB returned errno 16, EBUSY,
twice. Each produced an immediate E record with no callback or response bytes,
and Wine logged Failed to submit io24 class-interface IN transfer:
Input/Output Error. Select-interface remained fail-closed and unimplemented
twice.

The active blocker is Linux interface ownership. a1 is an interface-recipient
class IN request, and usbfs masks wIndex 0x0500 to low-byte interface 0 before
checking ownership. The high byte is entity or clock-source ID 5. usbfs then
tries to claim interface 0, but snd-usb-audio already owns it, so USB core
returns EBUSY. Interface 5 being unclaimed does not make this request
available. The CP8 Wine implementation reached the intended native submit;
the request itself did not reach the device.

Delayed postflight on 2026-08-21 found no surviving Wine/UC/Xvfb/io24
process, the transient unit collected, the same serial AB7C22200355 currently
at sysfs 3-1 and /dev/bus/usb/003/003, interfaces 0 through 4 still on
snd-usb-audio, and 5 through 6 unclaimed. The protected prefix retained inode
3427833 and timestamp 2026-08-12 00:31:35.825186221 -0700. CP8 and the
staged triplet still verify. This proves current clean state; the pause means
there was no immediate postflight record.

Exact evidence verifies under
out/checkpoints/live-read-class-in-v1-20260819T233401PDT/ in the class-IN
clone. Its SHA256SUMS hashes to
8e7d4ae8dafb22c650abce9abe05a0fdcc18991b6682fcce805087c7f03c0287. Full interpretation is in
re/live-read-class-in-v1-20260819/MANIFEST.md and CP9 is
re/wineusb-class-interface-in-v1/checkpoints/CP9_LIVE_EBUSY.md.

The one-run authorization is consumed. Do not retry or clear/move the active
capture. Detaching or claiming interface 0 would disrupt the working ALSA
device and is not authorized. An offline search found no exact UAC2 RANGE
response in retained project captures or current procfs ALSA state. Linux
snd-usb-audio parses the returned subranges into a rate table and frees the raw
payload (https://github.com/torvalds/linux/blob/master/sound/usb/format.c).
ALSA's 44.1, 48, 88.2, and 96 kHz list therefore cannot reconstruct the
original response and must not be synthesized into one.

The safest next candidate is a separately authorized passive usbmon capture
while a user-controlled device reconnect causes snd-usb-audio to perform its
normal enumeration. Do not reconnect the device or start that live capture
without a new explicit authorization. Select-interface, alternate settings,
writes, full Universal Control, Voice FX, and the protected prefix remain out
of scope.

## Passive usbmon reconnect v1 — pipeline ready; no reconnect observed

On 2026-08-21 the user explicitly authorized the passive usbmon candidate.
Offline staging added a bounded wrapper and a pcap RANGE extractor. The
extractor passed a synthetic 50-byte UAC2 RANGE contract; the wrapper plan
selected only control URBs on usbmon3, a 512-byte snap length, at most 20,000
packets, and a 120-second window. It contains no device-node open, sysfs
write, detach, claim, reset, audio, Wine, or network operation.

The first privileged launch failed before readiness because tcpdump's local
AppArmor profile denied creation of a pcap beneath hidden `.cache`. It restored
the previously absent usbmon module and requested no physical action. The
corrected wrapper changed only the output destination to the non-hidden
project evidence directory and was revalidated offline.

The corrected run reported ready once at 02:28:55 PDT. No physical disconnect
or reconnect was detected before its bounded window ended at 02:30:55 PDT.
tcpdump captured 18 control-URB events with zero kernel drops. The exact
extractor found zero matching `a1 02`, `wValue=0x0100`, `wIndex=0x0500`
requests and zero complete RANGE responses. This validates capture readiness
and cleanup only; it does not reveal any device response.

Postflight found the same serial AB7C22200355 at sysfs 3-1, interfaces 0
through 4 on snd-usb-audio and 5 through 6 unclaimed. usbmon was unloaded,
no capture/Wine/UC process remained, and the protected prefix retained inode
3427833 and timestamp 2026-08-12 00:31:35.825186221 -0700. Evidence and
interpretation are under
`re/io24-passive-usbmon/passive-usbmon-range-v1-20260821T022855-0700/`.

Do not retry automatically. A fresh bounded window requires the user to be at
the device and explicitly say to launch it. The passive-only boundaries remain
unchanged.

## Passive usbmon reconnect v2 — exact Clock Source RANGE captured

The user then confirmed physical readiness and explicitly renewed one bounded
passive-capture authorization. The wrapper reported ready at 02:36:41 PDT,
observed the disconnect at 02:36:53, the expected device reconnect at sysfs
3-1 at 02:37:03, and stopped cleanly at 02:37:15. The io24 returned as bus 3
device 4 with serial AB7C22200355.

tcpdump captured 316 control-URB events, received all 316 through the filter,
and reported zero kernel drops. snd-usb-audio issued the following count
request twice, with each status-zero completion returning `04 00`:

    a1 02 00 01 00 05 02 00

It then issued the 50-byte RANGE request twice:

    a1 02 00 01 00 05 32 00

Both status-zero completions returned the same exact bytes:

    04 00
    44 ac 00 00 44 ac 00 00 00 00 00 00
    80 bb 00 00 80 bb 00 00 00 00 00 00
    88 58 01 00 88 58 01 00 00 00 00 00
    00 77 01 00 00 77 01 00 00 00 00 00

This is UAC2 `wNumSubRanges=4`: discrete 44.1, 48, 88.2, and 96 kHz
triplets, each minimum=maximum with resolution zero. The project extractor
found both complete responses, and independent tcpdump hex output confirmed
the setup packets, status-zero completions, and payloads directly in the
pcap.

The pcap SHA-256 is
`194a4b2619e0bddcdeef2108b0969cf13c029b3d2516309123c6567437b2922d`.
Full evidence is under
`re/io24-passive-usbmon/passive-usbmon-range-v1-20260821T023641-0700/`;
the milestone is `re/io24-passive-usbmon/CP10_RANGE_CAPTURED.md`, and the
pinned payload is `re/io24-passive-usbmon/clock-source-5-range-v1.hex`.

Postflight found usbmon absent, no capture/Wine/UC process, the expected
interface bindings, and the protected prefix unchanged. This resolves the
missing exact-response evidence but authorizes no new live Wine run. Continue
offline only: contract an exact-tuple captured response for this GET_RANGE
case and keep every other class request, select-interface operation, write,
and broader behavior fail-closed.

## WineUSB exact captured RANGE v2 — CP11 GREEN offline

On 2026-08-21 the user said to proceed with the offline-only step identified
after CP10. A new v2 contract was written before production changes and run
against the preserved class-IN-v1 build. It failed cleanly in eight expected
ways: the old path returned pending, allocated and submitted libusb once,
returned no captured bytes, left length 256 and USBD status unset, and retained
a pending transfer and cancel handle.

The minimal v2 backend now accepts only the existing PaeDSPUSB tuple:

    function=0x1b flags=0x3 reserved=0 request=0x02
    value=0x0100 index=0x0500 receive_capacity=256

For that tuple only, it synchronously copies the exact CP10 50-byte response,
sets returned length 50 and USBD success, clears the unused cancel handle, and
returns STATUS_SUCCESS. It performs no libusb allocation, submission,
cancellation, or device I/O. The captured bytes are:

    040044ac000044ac00000000000080bb000080bb000000000000885801008858010000000000007701000077010000000000

The real compiled Unix call table passed the exact response, bounds, status,
zero-libusb, and ten fail-closed cases. USB-DI v1 also passed. Both GREEN suites
were rerun inside networkless, hardware-hidden Bubblewrap containment. The
patch applies with fuzz zero to Wine 11.15 plus USB-DI v1 and observation v2,
and reproduces the three changed sources byte-for-byte:

    461f68de736ddba876cfaa4d0e385c8eaa0002bd22df05932987ad3f4fe7fe8f  re/wine-11.15-wineusb-class-interface-range-v2.patch

The original v1 contract files and development workspace were restored to
their prior hashes, the staged CP8 triplet still verifies, and no v2 binary or
harness change is staged. CP10's manifest now points to a byte-identical
handoff snapshot rather than the evolving active handoff and verifies fully.

Full CP11 evidence is in `re/wineusb-class-interface-range-v2/`. The next
offline gate is two independent clean A/B builds, both contract suites, and
byte-for-byte artifact comparison. Do not stage v2 or change the sandbox
selector until that passes. No live Wine run, device-node access, class OUT,
select-interface semantics, interface claim/detach, alternate setting, USB
write, Universal Control, Voice FX, or protected-prefix access is authorized.

## WineUSB exact captured RANGE v2 — CP12 reproducible clean builds

On 2026-08-21 the user authorized the next offline-only gate. Two independent
source trees were freshly extracted from the retained Wine 11.15 archive, and
USB-DI v1, observation v2, and exact captured RANGE v2 were each applied in
order with fuzz zero. The complete 12,445-file A/B trees compare identical,
contain no symbolic links, and have no patch leftovers.

Both trees were configured and built independently with identical virtual
paths, SOURCE_DATE_EPOCH=1787101002, pinned Bison/M4/libusb inputs, and
make -j1. Each run was networkless and hardware-hidden, used a private /dev
and empty /sys, dropped every capability, and remained below 138 MiB peak RSS
with zero swap. Configure and build logs, generated Makefiles, and compile
databases match. Normalized config.log files also match.

The independently produced candidate triplets compare byte-for-byte:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  wineusb.sys.so
    9518320f495ace5cabc27ef4e740f182b3840700fba3e9371b36b7e12538dea2  wineusb.so

Build A and B separately passed the compiled fake-libusb exact-RANGE
behavioral contract, source/binary fail-closed contract, and retained USB-DI
V1 contract. The tests ran in separate hardware-hidden namespaces, each
exited zero in 0.29 seconds, peaked below 38 MiB RSS, and used zero swap.

CP11's former active manifest was frozen byte-for-byte before CP12 advanced
it, so CP11 remains independently verifiable. Full CP12 evidence is in
re/wineusb-class-interface-range-v2/checkpoints/CP12_REPRODUCIBLE_BUILDS.md
and its neighboring logs and checksum manifest.

Stop at CP12. No v2 artifact is staged, tests/uc_wine_sandbox.sh remains at
SHA-256 4706b84e5ea5daff2b274af28f6faf051fc66797cb5d569ecc9237ea4effaf7c
and still selects class-IN v1, and the protected prefix retained inode 3427833
and timestamp 2026-08-12 00:31:35.825186221 -0700.

The next candidate is a separately authorized offline staging gate using only
this exact triplet, followed by a fresh disposable-sandbox USB-hidden
driver-load. No live Wine run, device access, class OUT, select-interface
semantics, claim/detach, alternate setting, USB write, Universal Control,
Voice FX, or protected-prefix access is authorized. The prior one-run
live-read authorization remains consumed.

## WineUSB exact captured RANGE v2 — CP13 staged offline

On 2026-08-21 the user authorized the exact offline gate named after CP12:
stage the reproduced RANGE-v2 triplet, update and hash-pin the selector, clone
a fresh disposable sandbox, and perform one USB-hidden driver-load. No live
mode was authorized.

CP12's prior manifest and harness were frozen byte-for-byte first, so its
48-entry checksum seal remains valid. The exact CP12 triplet is now staged:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    404a07ffccb44e4fc34dd5b42df0aef8e96eb44ad2878ffc417f7a75e409abaa  x86_64-unix/wineusb.sys.so
    9518320f495ace5cabc27ef4e740f182b3840700fba3e9371b36b7e12538dea2  x86_64-unix/wineusb.so

A real-harness selector contract recorded RED against the old class-IN-v1
path and GREEN after the minimal RANGE-v2 change. The staged exact-RANGE and
USB-DI contracts passed in hardware-hidden containment, and all three staged
files match clean build B. The current harness SHA-256 is
7a6beb27534114bdc125bc498d5a13fba13b6609a0545dc073081ef013da15e1.

The unchanged observation baseline was independently cloned, fully compared,
and atomically promoted to:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.range-v2-20260821

Exactly one driver-load ran as io24-wine-driver-load-865198.service,
invocation 2ac650364d6b47d5800532bd0f13eeb1. Isolation and the
registry/Windows-7-NT-DDI/SSE2 gates passed; WineUSB and PaeDSPUSB loaded,
PaeDSPUSB reported RUNNING, and cleanup unloaded it. The unit succeeded in
12.924 seconds, used 2.026 CPU seconds, peaked at 112 MiB, and used zero swap.

No USB PDO existed in the hidden namespace, so zero class-IN,
captured-RANGE, rejection, class-OUT, or observation markers ran. This proves
only offline overlay selection, load compatibility, and cleanup—not a live
device response or synchronization.

The 31-entry evidence seal verifies at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.range-v2-20260821/out/checkpoints/driver-load-range-v2-20260821T033607PDT/

Its SHA256SUMS hash is
45087b770cdb8bf2405423b7a8a0183497881039f08c96a83b0c49da2988cfba.
Postflight found the unit collected, no surviving candidate process, the
source sandbox unchanged, and the protected prefix still at inode 3427833 and
timestamp 2026-08-12 00:31:35.825186221 -0700.

Stop at CP13. The prior one-run live-read authorization remains consumed.
Device connection alone does not authorize anything. A future RANGE-v2
live-read requires a fresh full preflight and new explicit one-run
authorization. Do not expose USB, detach/claim, change alternate settings,
add class OUT, write to the device, start full Universal Control or Voice FX,
or access the protected prefix without separate authorization.

## WineUSB exact captured RANGE v2 — CP14 live-read stopped at new class-IN boundary

On 2026-08-21 the user said `Save checkpoint and proceed` after the RANGE-v2
live gate and its one-run safety boundary were restated. This renewed exactly
one bounded live-read authorization. CP13 was first made immutable by copying
its prior active manifest and harness to `CP13_MANIFEST_SNAPSHOT.md` and
`CP13_HARNESS_SNAPSHOT.sh`; the revised CP13 seal verifies with SHA-256
`4bad0a5d0f5f5a0a392d0d1a9b40283c03be14ff6a27c5143f35a7b910853ddb`.

Two complete preflight passes bracketed a successful 348 ms non-opening
`live-audit`. They verified the CP13 and runtime-evidence seals, active
selector and RANGE-v2 triplet, corrected Wine runtime, staged official
driver, preserved inherited capture, no conflicting process or live unit,
and the current device:

    vendor:product=194f:0422
    serial=AB7C22200355
    sysfs=3-1
    node=/dev/bus/usb/003/004
    configuration=1
    speed=480
    interfaces=7
    interface-5=unclaimed

The only live-read was `io24-wine-live-read-903434.service`, invocation
`9b2b5f66d03b43fbba457abead1c3701`. It started at
2026-08-21T03:52:39.441062-07:00 and ended at 03:53:01.743180-07:00 with
status 1. It ran 22.301 seconds, used 3.661 CPU seconds, peaked at 116.4 MiB,
and used zero swap. It was not retried.

Containment passed and the registered PreSonus Hardware Access Service
reported `RUNNING`, but the eight-second bounded probe received no UCNET `DA`
announcement. No `synchronize.json` was produced. Treat `RUNNING` as process
state only, not communication or synchronization evidence.

The exact RANGE success line is a disabled WineUSB `TRACE`, so the result is
supported by high-confidence structural comparison rather than a direct
runtime marker. The current first cycle is aligned with the prior observation
through the same `IofCallDriver` at line 3268. The old line 3269 printed the
exact request and returned `STATUS_NOT_IMPLEMENTED`, followed by a 120-byte
driver error allocation at line 3277. The new IRP completes immediately at
line 3269, allocates no driver error entry, and advances to three new
fail-closed class-IN reads. The second device cycle follows the same path.
This matches the staged implementation, whose only silent class-interface
success is the exact captured RANGE tuple.

The newly exposed requests are each repeated twice:

    flags=0x3 length=4 request=0x01 value=0x0100 index=0x0500
    flags=0x3 length=4 request=0x01 value=0x0700 index=0x0200
    flags=0x3 length=4 request=0x01 value=0x0700 index=0x0300

The log has six total `IO24_CLASS_IN reject` lines, zero driver error-log
allocations, zero select-interface observation markers, and four
`Failed to clear halt: Entity not found` errors. RANGE-v2 therefore cleared
the prior exact-RANGE boundary, but initialization remains incomplete. Do not
guess the three response values from this run.

The new USB capture is 2,662 lines and 276,104 bytes, SHA-256
`8e8b62209d8cec8838b686e0da0b9851b4af992361acc9f62b8db699bbcbd93e`.
It records 172 accepted submissions and 172 status-zero callbacks across two
contained Wine processes. Every transfer is a standard endpoint-zero
control-IN descriptor request. There is no control OUT, bulk, interrupt,
interface claim, kernel-driver detach, alternate-setting change,
configuration change, or immediate-submit error. The RANGE response is
internal to WineUSB and is not a libusb transfer.

Postflight found the unit collected and no candidate process. The device
retained its bus/device identity, serial, configuration, node inode, and
interface bindings, with interface 5 still unclaimed. The node mtime changed
from `2026-08-21 02:37:03.129570110 -0700` to run-end time
`2026-08-21 03:53:01.139746713 -0700`; the filtered kernel window has no
reset, disconnect, reconnect, or binding event, so this metadata change is
recorded without assigning a cause. The protected prefix remained inode
3427833 and timestamp `2026-08-12 00:31:35.825186221 -0700`. The observation
source sandbox and retained capture stayed hash-identical.

Full 47-entry evidence is sealed at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.range-v2-20260821/out/checkpoints/live-read-range-v2-20260821T035239PDT/

Its `SHA256SUMS` hash is
`cb18c9f9706038d61257df69c1279461a2fe184c7c900f431c391ca8ab01dfed`.
The immutable project checkpoint is
`re/wineusb-class-interface-range-v2/checkpoints/CP14_LIVE_READ.md`; its
16-entry chain is `CP14_SHA256SUMS`, SHA-256
`50a2f31cf6c1b3bc7c042133d690b66eebdb7af2e7603c8f39b19ce3e97791e6`.

Stop at CP14. The one-run live authorization is consumed. Safe next work is
offline evidence gathering for the three new response values and the
clear-halt path. Any device query, retry, interface claim/detach,
alternate-setting change, class OUT, USB write, full Universal Control,
Voice FX, or protected-prefix access requires separate explicit authorization
and a fresh complete preflight.

## CP15 — offline class-IN evidence resolves to pipe/stream path

On 2026-08-21, `resume io24` restored the live project handoff at CP14 rather
than the older CP8 memory snapshot. Both the 16-entry CP14 project chain and
the 47-entry retained runtime evidence reverified. A fresh host postflight
found no candidate process and no matching user-systemd unit. The protected
prefix remained inode 3427833 with timestamp
`2026-08-12 00:31:35.825186221 -0700`.

The same owned io24 serial `AB7C22200355` was present at sysfs `3-1`, now
re-enumerated at `/dev/bus/usb/003/002`. Interfaces 0-4 remained bound to
`snd-usb-audio`; interfaces 5-6 remained unclaimed; every interface was at
alternate setting 0. Reconnection is state evidence, not live authorization.

A test-first offline analyzer was added at
`tests/io24_usbmon_class_in_evidence.py`, with its contract at
`tests/io24_usbmon_class_in_evidence_contract.py`. Applied to the sealed
passive reconnect pcap, it found 14 status-zero clock-source-5
sampling-frequency `GET_CUR` completions: 11 returned 48,000 Hz and three
returned 96,000 Hz. No terminal-2 or terminal-3 latency request appears.
The target's complete UAC2 descriptor advertises `bmControls=0x0000` for
terminal entities 2 and 3, so latency selector 7 is not present.

Do not synthesize the three CP14 replies: a fixed clock response would
misrepresent live state, and terminal latency values would contradict the
descriptor. The retained CP14 log also shows PaeDSPUSB continuing past all
three fail-closed rejects in each cycle, so those reads are not demonstrated
fatal boundaries.

The four clear-halt errors are not propagated as NTSTATUS failures: the exact
WineUSB source logs `libusb_clear_halt` failure and then unconditionally
returns `STATUS_SUCCESS`. The stronger unresolved area is pipe/stream setup.
The capture has no bulk or interrupt submission; the log has eight null-return
`MmMapLockedPagesSpecifyCache` stubs and eight non-dispatching
`KeInsertQueueDpc` stubs; WineUSB `SELECT_CONFIGURATION` initializes only the
first embedded interface record; and the io24 bulk endpoints `0x81`/`0x01`
belong to interface 5 alternate setting 1 while the current interface remains
at alternate setting 0. Existing evidence cannot yet rank those causes.

The full analysis is
`re/wineusb-class-interface-range-v2/checkpoints/CP15_OFFLINE_EVIDENCE.md`.
Its 18-entry chain is `CP15_SHA256SUMS`, SHA-256
`e3ccd6e45f6b6deeda6de38d91e2a1e1a3191ef5387ddc4103bad04785a1de31`.
The former active manifest is now preserved byte-for-byte as
`CP15_MANIFEST_SNAPSHOT.md`, so later work cannot invalidate CP15.

Stop at CP15. No WineUSB behavior or staged binary changed, and no live action
occurred. Safe next work is an offline, contract-tested observation patch for
the full `SELECT_CONFIGURATION` interface list, pipe handles,
bulk/interrupt metadata, and MDL mapping result. The CP14 one-run live
authorization remains consumed. Any future device query or live-read still
requires new explicit authorization and a fresh complete preflight; claim,
detach, alternate-setting change, class OUT, USB write, full Universal
Control, Voice FX, and protected-prefix access remain separately gated.

## CP16 — observation-only pipe diagnostics development build

On 2026-08-21, the user requested three continuing checkpoints, authorized
connected-device testing, and set a mandatory pause threshold at 10% battery.
CP16 itself remained device-free; battery was 58% when it was sealed.

A test-first pipe-observation contract was written and made to fail for the
missing runtime marker before production changes. The new patch adds stable
`IO24_PIPE_OBSERVE` key/value events for the complete bounded
SELECT_CONFIGURATION interface/pipe list before and after the Unix call,
pipe-handle encoding, bulk/interrupt MDL or direct-buffer mapping, decoded
route, clear-halt result, and immediate libusb submission result. It logs no
buffer contents and adds no USB action.

The patch layers on top of exact captured RANGE v2 and has SHA-256:

    ce4507d1b789e87195965b71e88c76d02a7de5ab504b52d41e1c431c560d949d  re/wine-11.15-wineusb-pipe-observe-v3.patch

It applies with fuzz zero, changes only `wineusb.c` and `unixlib.c`, and
reproduces the development source exactly. A contained incremental build
completed without a warning in either changed unit. The new runtime contract,
retained exact-RANGE behavior/source/binary contract, USB-DI v1 contract, and
CP15 evidence contract all pass with hardware and networking hidden. The
behavior contract proves the prior return values, decoded endpoints/types,
invalid-handle rejection, and first-interface-only backend scope are
unchanged. Binary comparison finds no new undefined dynamic symbols.

The complete checkpoint is
`re/wineusb-pipe-observe-v3/checkpoints/CP16_PIPE_OBSERVE_DEVELOPMENT.md`.
Its 26-entry chain is `CP16_SHA256SUMS`, SHA-256
`8802ebd252caa534dd5ac8a4a6fbc6424d589b9c3f9a7084c2d3b68669bc7424`.

CP16 is complete and work is advancing to CP17. No candidate binary is staged
yet. CP17 must independently extract, patch, build, test, and byte-compare two
clean trees before CP18 may stage anything. The user's live authorization is
reserved for a bounded CP18 run after offline selector and driver-load gates.
Never touch the protected `.wine-io24` prefix, perform firmware operations, or
continue at 10% battery or lower.

## CP17 — two independent clean builds reproduce exactly

CP17 completed on 2026-08-21 with battery at 54%. Two separate hardware-hidden
and networkless invocations independently extracted the pinned Wine 11.15
archive and applied USB-DI v1, observation v2, exact RANGE v2, and pipe-observe
v3 with fuzz zero. Both 12,445-file source trees are identical and contain no
symlink or patch leftover.

Two separate empty builds used the same virtual paths, pinned tools,
`SOURCE_DATE_EPOCH=1787101002`, and `make -j1`. Both configurations and builds
exited zero, used zero swap, and produced byte-identical logs, generated
Makefiles, compile databases, build IDs, and candidate triplets:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    90d060571d9f8a56aea8d91485802fe500920f741fb5787543a8c141ae104eb9  wineusb.so

Both sides independently pass the pipe-observe behavior/source/binary/runtime
contract, exact RANGE-v2 contract, USB-DI v1 contract, and CP15 analyzer
contract. Neither changed translation unit emitted a warning.

The durable report is
`re/wineusb-pipe-observe-v3/checkpoints/CP17_REPRODUCIBLE_BUILDS.md`.
Its 38-entry chain is `CP17_SHA256SUMS`, SHA-256
`b2624030366226c57a7018ada9b8eb87bd0497e69613576921b3e9fef1c8b066`.
The additional sealed entry is the byte-for-byte frozen CP17 harness at
`re/wineusb-pipe-observe-v3/CP17_HARNESS_SNAPSHOT.sh`.

CP17 is complete and CP18 may stage only this exact triplet. The current
harness still selects RANGE v2 and no staging, Wine, sandbox, or device action
occurred at CP17. Before a live diagnostic, CP18 must first pass a test-first
selector contract, exact staged contract reruns, a fresh disposable clone, and
one USB-hidden driver-load. The protected `.wine-io24` prefix and firmware
remain out of scope; pause at 10% battery or lower.

## CP18 — staged pipe observation and one live diagnostic

CP18 completed on 2026-08-21 as the third and final checkpoint requested in
this run. Battery remained above the mandatory pause threshold throughout; it
was discharging at 43% when the checkpoint evidence was sealed.

The exact byte-identical CP17 triplet was staged under
`re/wineusb-pipe-observe-v3/`. A test-first real-harness selector contract first
failed because the harness still selected RANGE v2, then passed after the
harness was minimally changed to hash-pin and mount only pipe-observe v3.
Shell syntax and the staged pipe-observe, exact RANGE-v2, and USB-DI contracts
passed in hardware-hidden, networkless containment.

A fresh disposable clone was independently verified against the unchanged
observation-v2 baseline and promoted to:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.pipe-observe-v3-20260821

One USB-hidden driver-load completed successfully in systemd, with PaeDSPUSB
start/query both zero and state RUNNING. After two complete preflight passes
and one non-opening audit, exactly one authorized live-read ran as
`io24-wine-live-read-230235.service`, invocation
`458992c0b9484d138d0c4e32d0ed707d`. The bounded service reached RUNNING but
exited 1 after 29.729 seconds because no UCNET `DA` announcement arrived; it
produced no synchronization document and was not retried.

The added markers make the boundary decisive. Each of two valid 256-byte
SELECT_CONFIGURATION requests contained all seven interfaces. Only interface
4 had pipes (`0x02` and `0x82`, bulk, packet 512, transfer 4,096), but WineUSB
processed only interface 0, which had none. It created zero pipe handles, so
all eight 512-byte bulk/interrupt URBs decoded a null handle as endpoint 0,
control type 0, route `invalid`, and none reached `libusb_submit_transfer`.
Independently, all eight requests had non-null MDLs but null mapped buffers.
The log also retains eight non-dispatching DPC stubs. At least two separate
pre-libusb blockers therefore remain: full embedded-interface pipe-handle
population and MDL mapping; fixing either one alone does not establish a
working transfer path.

The 178,467-byte capture has SHA-256
`80dd4b39dc35bed5e33551186a6abbb013518a160855558cdd112fe94f8b3d4f`.
Its 105 submissions and 105 status-zero callbacks are all standard endpoint-0
descriptor control-IN. It contains no bulk, interrupt, control OUT, claim,
detach, alternate-setting change, configuration change, or capture error.

Postflight found no surviving unit or candidate process. The single io24
retained serial `AB7C22200355`, sysfs path `3-1`, host node
`/dev/bus/usb/003/002`, configuration 1, alternate setting 0 everywhere,
snd-usb-audio bindings on interfaces 0–4, and unclaimed interfaces 5–6. The
protected `.wine-io24` prefix and source sandbox remained unchanged.

The complete report is
`re/wineusb-pipe-observe-v3/checkpoints/CP18_STAGED_LIVE_DIAGNOSTIC.md`. Its
26-entry project chain is `CP18_SHA256SUMS`, SHA-256
`5cdf8da3040a52b27168153b2c85bc96b165641b261d8aff7e06e67bc38ebeec`.
The 65-entry runtime evidence is rooted at
`out/checkpoints/live-read-pipe-observe-v3-20260821T053410PDT/` in the fresh
clone; its `SHA256SUMS` SHA-256 is
`ff38e017ec8c554af08d0357c88bf583c7be743ffd834b134c3bfd807a4af87d`.

Stop at CP18. No additional live run is authorized by or needed for this
three-checkpoint request. The next safe work is offline, test-first work on the
variable-length interface handle population and, separately, the MDL/DPC
kernel compatibility paths. Firmware, full Universal Control, Voice FX, and
the protected prefix remain untouched. Pause at 10% battery or lower.

## CP19 — full interface pipe-handle population, offline

On 2026-08-22 the user authorized continued connected-device testing. CP18's
seal reverified, but CP19 remained hardware-free. The same serial
`AB7C22200355` was present at sysfs `3-1`, re-enumerated as USB device 4;
battery was charging at 39% when CP19 was sealed.

A new real-Unix-library/fake-libusb contract first failed against CP18 because
WineUSB processed only the empty first interface, left every later-interface
handle null, accepted a malformed later interface after partially mutating an
earlier pipe, and returned handles with uninitialized high bytes. A two-pass
parser now validates the complete bounded request before mutation and then
populates every embedded interface with deterministic handles.

A separate safety RED proved that CP18 would allocate and submit a 512-byte
bulk transfer when given a valid handle but a null mapped buffer. The new
candidate rejects that exact condition with `STATUS_INVALID_PARAMETER` before
any libusb allocation or submission. This keeps MDL compatibility separate
and makes a future handle-population diagnostic fail closed.

The patch is:

    f7fab610716f7a0cc2349cffe4f3a3edf45ada1a4527c451c7a0c71f718facde  re/wine-11.15-wineusb-multi-interface-handles-v1.patch

It applies over pipe-observe v3 with fuzz zero, changes only `unixlib.c`, adds
no USB API, and reproduces the 12,445-file development source exactly. The
contained development build emitted no changed-unit warning. The PE and
builtin remain byte-identical to CP17; the new Unix library is:

    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  wineusb.so

The new behavior/safety contract, pipe-observe contract, exact RANGE-v2
contract, USB-DI v1 contract, and CP15 analyzer contract all pass with empty
`/sys`, minimal `/dev`, and no network. The complete report is
`re/wineusb-multi-interface-handles-v1/checkpoints/CP19_MULTI_INTERFACE_HANDLES_DEVELOPMENT.md`.
Its 28-entry chain is `CP19_SHA256SUMS`, SHA-256
`5f9f0b008677388333435c5b13f447cf7e8939bb04661f9adad87263a883c621`.

Stop at CP19. Nothing is staged and no live device action occurred. CP20 must
independently extract, apply all five patches with fuzz zero, build, test, and
byte-compare two clean trees before any selector or device work. Firmware,
full Universal Control, Voice FX, interface claims/detaches, alternate-setting
changes, and the protected prefix remain out of scope; pause at 10% battery or
lower.

## CP20 — two independent clean builds reproduce exactly

CP20 completed offline on 2026-08-22 with battery charging at 50%. Two
hardware-hidden, networkless namespaces independently extracted the pinned
Wine 11.15 archive and applied USB-DI v1, observation v2, exact RANGE v2,
pipe-observe v3, and multi-interface handles v1 with fuzz zero. Both complete
12,445-file trees match each other and CP19's development source exactly.

Build A's first two empty configure attempts exposed missing paths for the
pinned tool bundle: Bison's data directory, then its M4 executable. Both
pre-build failures are preserved. After setting
`BISON_PKGDATADIR=/run/io24-tools/usr/share/bison` and
`M4=/run/io24-tools/usr/bin/m4`, build A was recreated empty. Final A and B
configurations and `make -j1 dlls/wineusb.sys/all` runs used identical virtual
paths, `SOURCE_DATE_EPOCH=1787101002`, low CPU/I/O priority, a 2 GiB
address-space cap, hard timeouts, private devices/sysfs/home, and no network.

Their configure and build output, Makefiles, compile databases, build IDs, and
candidate triplets are byte-identical and match CP19:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  wineusb.so

Each side independently passes the new handle/safety contract, pipe-observe,
exact RANGE-v2, USB-DI v1, and CP15 analyzer contracts in fresh containment.
Raw test logs differ only in randomized IRP/buffer pointers; normalized output
is byte-identical.

The complete report is
`re/wineusb-multi-interface-handles-v1/checkpoints/CP20_REPRODUCIBLE_BUILDS.md`.
Its 45-entry chain is `CP20_SHA256SUMS`, SHA-256
`ceb829b32832d6615a00a501bc5d5c0b967c25a2fa2d7aeae57b3f578841acfb`.
The additional sealed entry is the frozen pre-CP21 harness at
`re/wineusb-multi-interface-handles-v1/CP20_HARNESS_SNAPSHOT.sh`.

Stop at CP20. No artifact is staged and no device action occurred. CP21 may
stage only this exact triplet after a real-harness selector RED/GREEN, then
must use a fresh verified disposable clone and one USB-hidden driver-load.
The null-buffer guard must remain active so a bounded live diagnostic cannot
submit bulk data. All prior protected-prefix, firmware, Voice FX,
claim/detach, alternate-setting, and 10% battery gates remain in force.

## CP21 — staged multi-interface handles and one live diagnostic

CP21 completed on 2026-08-22 as the third checkpoint in the requested
CP19-CP21 sequence. Battery stayed above the mandatory pause boundary: 63%
and charging at the live gate, 70% and charging at final postflight.

Only the exact CP20 triplet was staged under
`re/wineusb-multi-interface-handles-v1/`:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  x86_64-unix/wineusb.sys.so
    96f5a63a76d5f0e9a73425717d81e17d1fd6883c7a909508e703897a22fe4039  x86_64-unix/wineusb.so

The real-harness selector contract recorded RED against pipe-observe v3 and
GREEN after the minimal multi-interface-handles v1 selector change. The exact
executed harness is frozen as `CP21_HARNESS_SNAPSHOT.sh`; both it and the
active harness have SHA-256
`908d9c900c0f4e9bb0cb2c2b68b2d1af478a6295eb4019de2dc321f65ecc02f5`.

The observation-v2 baseline was freshly cloned and fully compared at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.multi-interface-handles-v1-20260822

Content and metadata matched across 5,097 files, 41 symlinks, and 708
directories. A first driver-load wrapper invocation failed before unit
creation because the calling shell lacked its user-bus environment; it has no
unit, journal, process, or device action and is retained as prelaunch evidence.
After restoring only that environment, exactly one USB-hidden candidate load
ran as `io24-wine-driver-load-435682.service`, invocation
`0a2500d4972c4e1da3402e3ab6e21f54`. Registry probe, PaeDSPUSB start, and query
all returned zero; the query reported RUNNING. The unit succeeded in 14.562
seconds, used 2.454 CPU seconds, peaked at 55.9 MiB, and used zero swap.

Two complete live preflights bracketed a successful 488 ms non-opening audit.
Exactly one live-read then ran as `io24-wine-live-read-464970.service`,
invocation `59fd56a3262a46d5b59922ce0600257b`. The PreSonus service reached RUNNING,
but no UCNET `DA` announcement arrived within eight seconds and no
`synchronize.json` exists. The unit exited 1 after 25.639 seconds, used 4.492
CPU seconds, peaked at 103.8 MiB, used zero swap, and was not retried.

The new markers directly clear CP18's handle blocker. Each of two valid
256-byte SELECT_CONFIGURATION requests described all seven interfaces and two
pipes. Both were validated and populated without rejection. Interface 4's
bulk endpoints received stable handles:

    endpoint 0x02 -> handle 0x202
    endpoint 0x82 -> handle 0x282

All eight 512-byte bulk-IN URBs then carried `0x282` and decoded to endpoint
`0x82`. Each non-null MDL immediately hit Wine's
`MmMapLockedPagesSpecifyCache` stub and mapped to null. The safety guard
rejected all eight before allocation or submission. Eight
`KeInsertQueueDpc` stubs remain. Handle population is therefore live-validated,
but MDL mapping, DPC dispatch, and interface routing are separate unresolved
boundaries. In particular, these selected endpoints belong to host interface
4, still bound to `snd-usb-audio`, while prior descriptor evidence placed the
vendor pair on interface 5 alternate 1.

The 237,649-byte capture has SHA-256
`db25dc188d5cd568fc2082eb8cf34912b12eb3b8b7aabb10cad53a494817e6f9`.
It records 146 submissions and 146 successful completions, all control-IN.
There is no bulk, interrupt, or control-OUT bus transaction and no claim,
detach, alternate-setting change, or configuration change. Six clear-halt
ioctls targeted endpoints `0x82`/`0x02`; all failed `EBUSY`. The matching six
kernel messages say interface 4 was not claimed, with no reset, disconnect,
reconnect, or binding event.

Immediate and final postflight found no surviving candidate process or test
unit. Serial `AB7C22200355` remained at sysfs `3-1`, node
`/dev/bus/usb/003/004`, configuration 1, speed 480, and alternate 0 everywhere;
interfaces 0-4 remained on `snd-usb-audio`, interfaces 5-6 unclaimed. The
protected prefix remained inode 3427833 with timestamp
`2026-08-12 00:31:35.825186221 -0700`, and the source clone retained all three
pinned hashes.

The 77-entry runtime evidence verifies at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.multi-interface-handles-v1-20260822/out/checkpoints/live-read-multi-interface-handles-v1-20260822T103059PDT/

Its `SHA256SUMS` hash is
`38061a271ece0f9d4d90d6c11ec467fdef79c7ca1e8395ac42ab0264ed1ec026`.
The project report is
`re/wineusb-multi-interface-handles-v1/checkpoints/CP21_STAGED_LIVE_DIAGNOSTIC.md`.
Its 47-entry chain is `CP21_SHA256SUMS`, SHA-256
`83d52645be59c7a926cc322971cb12231a2ed2146379271e1e30de4b8ff84f03`.

Stop at CP21. The requested three checkpoints are complete and the single live
diagnostic is consumed. Safe next work is offline, test-first MDL, DPC, and
interface/alternate routing analysis. A noninteractive future harness call
must restore the user-bus environment before `systemd-run`; this does not by
itself authorize another live run. The harness help text still names the prior
pipe-observe overlay, but the selector, hashes, and frozen invocation prove
multi-interface-handles v1 was used. Firmware, full Universal Control, Voice
FX, claim/detach, alternate-setting changes, and the protected prefix remain
out of scope.

## CP22 — nonpaged-pool MDL compatibility, offline

CP22 completed offline on 2026-08-22 with battery full at 100%. The CP21
project and runtime seals first reverified. No build or contract namespace had
access to host USB or sysfs, no Wine service was launched, and the connected
io24 was untouched.

CP21's live log records 24 512-byte `IoAllocateMdl` calls immediately followed
by 24 `MmBuildMdlForNonPagedPool stub` events. The eight later bulk-IN URBs
then reached the independent `MmMapLockedPagesSpecifyCache` stub and were
rejected on its null result by the existing WineUSB guard. Wine's inline
`MmGetSystemAddressForMdlSafe` already returns `MappedSystemVa` for a
nonpaged-pool MDL, locating this compatibility defect upstream of WineUSB.

The new Wine kernel test allocates the exact 512-byte nonpaged buffer, builds
its MDL, and asserts the source flag, unlocked semantics, first PFN, safe
mapped address, and source aliasing. With matching fake-PE/Unix-builtin pairs,
the corrected pre-MDL kernel reports the same 13 unrelated baseline failures
plus exactly three new RED failures: missing source flag, zero first PFN, and
null mapped address. The candidate removes all three and retains only the 13
baseline failures. The successful map executes one additional alias assertion.

The isolated patch is:

    ccbf6d0cff8b9f59cecfb6f18497705ff81599b3796d1b5f6185a6bba43c309b  re/wine-ntoskrnl-mdl-nonpaged-v1/wine-11.15-ntoskrnl-mdl-nonpaged-v1.patch

It applies to pinned Wine 11.15 with fuzz zero after the unchanged NTDDI and
processor-feature prerequisites, changes only the builder and its test, and
introduces no USB action. The contained development outputs are:

    259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e  x86_64-windows/ntoskrnl.exe
    3c338b34e2f33f3d50772cbea3bd3654bbe9ccaf235b5c16081ed8e9cebd6026  ntoskrnl.exe.so
    0c2c004c751c98c4ee389df4d9ddb5175cd4275d065da282fc9f7a002871d155  ntoskrnl.exe_test.exe.so

The fake PE is unchanged. The candidate Unix builtin is 1,572,656 bytes with
build ID `662e3f85c5d166e4e004b59c8e27e48e2e184118` and the same six undefined
dynamic symbols as its predecessor.

The report is
`re/wine-ntoskrnl-mdl-nonpaged-v1/checkpoints/CP22_MDL_NONPAGED_DEVELOPMENT.md`.
Its 30-entry chain is `CP22_SHA256SUMS`, SHA-256
`7de8b0fa3fe01f4400c6b110496f5aedacae5b0df91dbd55a3020624435b485c`.

Proceed to CP23 independent extraction/build/test before staging. Current user
authorization permits a later bounded live diagnostic, but CP22 itself is not
staged. Retain matching fake-PE/builtin selection, the WineUSB OUT/null-buffer
guards, the protected-prefix exclusion, and all no-firmware/no-claim/no-detach/
no-alternate-setting boundaries.

## CP23 — two independent clean kernel builds reproduce exactly

CP23 completed offline on 2026-08-22. Battery was 96% and discharging, well
above the mandatory 10% pause threshold. CP22's 30-entry chain first
reverified. No build or test namespace exposed host USB, sysfs, networking, a
host Wine prefix, or the protected `.wine-io24` prefix, and no Wine service
was launched.

Two separate source trees independently extracted the pinned Wine 11.15
archive and applied the NTDDI, processor-feature, and nonpaged-MDL patches in
order with fuzz zero. They were partial state at resume and were re-audited
before use: all inputs rehashed, both complete trees compared, and no `.orig`
or `.rej` file found. The 12,443-file trees have identical content and
metadata digests. Their configured Makefiles, config.status files, and compile
databases are byte-identical; config logs differ only in randomized compiler
temporary names and compare identical after normalization.

Build A and build B then ran sequentially in separate networkless,
hardware-hidden namespaces with one make job, low CPU/I/O priority, a 2 GiB
address-space ceiling, and hard timeouts. Both exited zero and reproduce CP22
exactly:

    259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e  x86_64-windows/ntoskrnl.exe
    3c338b34e2f33f3d50772cbea3bd3654bbe9ccaf235b5c16081ed8e9cebd6026  ntoskrnl.exe.so
    0c2c004c751c98c4ee389df4d9ddb5175cd4275d065da282fc9f7a002871d155  ntoskrnl.exe_test.exe.so

Each side independently ran the test with its matching fake PE and Unix
builtin in a fresh isolated prefix. Both executed 26,476 assertions and
retained the same 13 established environment-sensitive failures; neither
emitted a new nonpaged-MDL failure. After normalizing only temporary driver
names, Wine process prefixes, and thread IDs, their full output is
byte-identical with SHA-256
`5f998d45f04a5c623d0696885111f99b21d97fa8dd85d78db15123b3f3f563c3`.

Direct `nm`/`objdump` inspection finds five undefined dynamic names in the
unchanged Unix builtin, not the six stated in CP22 prose. Since both the bytes
and build ID exactly match CP22, this is a documentation counting correction,
not artifact drift.

The report is
`re/wine-ntoskrnl-mdl-nonpaged-v1/checkpoints/CP23_REPRODUCIBLE_BUILDS.md`.
Its 34-entry chain is `CP23_SHA256SUMS`, SHA-256
`d54fd537d9319e5dc4394ab202a340295a269d09181a17da4f460a4e4455ef37`.
The pre-CP24 harness is frozen as `CP23_HARNESS_SNAPSHOT.sh`, SHA-256
`908d9c900c0f4e9bb0cb2c2b68b2d1af478a6295eb4019de2dc321f65ecc02f5`.

Stop at CP23. Nothing is staged and no device action occurred. CP24 may stage
only the reproduced fake-PE/Unix-builtin pair after a real-harness selector
RED/GREEN, contained contracts, a fresh disposable clone, and one USB-hidden
driver-load. Retain the staged WineUSB multi-interface candidate and its
OUT/null-buffer guards. Any later device-visible diagnostic must be bounded,
read-only, collision-free, supported by the existing explicit authorization,
and preceded by a fresh full preflight; reconnection alone is not
authorization. Firmware, full Universal Control, Voice FX, interface
claims/detaches, alternate-setting changes, and the protected prefix remain
out of scope. Pause at 10% battery or lower.

## CP24 — staged nonpaged-MDL kernel and consumed live diagnostic

CP24 completed on 2026-08-22. Battery was 71% and discharging at the final
live gate, 69% immediately afterward, and 76% and charging at final
postflight, always above the mandatory 10% pause boundary.

The exact CP23 kernel pair is now staged under
`re/wine-ntoskrnl-mdl-nonpaged-v1/`:

    259d80fc4c68df9db3202f6aee7eb42e36bed11593480527f044decf84029c2e  x86_64-windows/ntoskrnl.exe
    3c338b34e2f33f3d50772cbea3bd3654bbe9ccaf235b5c16081ed8e9cebd6026  x86_64-unix/ntoskrnl.exe.so

The exact CP21 WineUSB triplet remains selected. The real-harness kernel
selector recorded RED/GREEN, the WineUSB selector now requires the combined
kernel/WineUSB `WINEDLLPATH`, and all staged contracts pass with hardware
hidden. The executed harness is frozen as `CP24_HARNESS_SNAPSHOT.sh`; both
copies hash to
`720a780bb9bde1c24064ad848b86472dde66e19a230920402ab2d589c765304a`.

The observation-v2 source was freshly copied to the collision-free clone:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.ntoskrnl-mdl-nonpaged-v1-20260822

Two setup attempts failed before copying because their private namespace
lacked `/run`; the retained target was empty after both. The corrected clone
unit `io24-sandbox-clone-mdl-nonpaged-v1-20260822.service`, invocation
`145e647a11ff45caa21359ecdf097512`, succeeded. A full rsync comparison found
no differences across 5,097 files, 41 symlinks, and 708 directories, with
independent root and registry storage. The inherited live capture was
preserved under a historical filename before the live gate.

Exactly one USB-hidden driver load ran as
`io24-wine-driver-load-178058.service`, invocation
`31e47b47f6ed4f24af0cf80a4540aa0e`. Registry probe, start, and query all
returned zero, the query captured RUNNING, and postflight was clean. Two full
live preflights then bracketed a successful 606 ms non-opening audit.

The existing one-run authorization was consumed by exactly one live-read:
`io24-wine-live-read-197499.service`, invocation
`8f9790c96bc84b8a9d331c11949d15e4`. It exited 1 after 29.906 seconds and was
not retried. The service reported RUNNING, but no UCNET `DA` arrived and no
`synchronize.json` exists, so there was no synchronization.

The kernel compatibility change worked live. Both 256-byte configuration
requests were validated and populated, the interface-4 endpoints received
handles `0x202`/`0x282`, and all eight 512-byte bulk-IN URBs on handle `0x282`
mapped their nonpaged MDLs successfully. There was no null mapping or
null-buffer rejection.

All eight then failed immediately in `libusb_submit_transfer()` with errno 16
because interface 4 remained bound to `snd-usb-audio` and was not claimed.
WineUSB nevertheless returned `STATUS_PENDING` for each. Its bulk path keeps
the failed transfer in DriverContext, does not free the transfer/context or
set failure status, and returns pending even though no callback can occur.
No `KeInsertQueueDpc` call happened in CP24. Immediate-submit error cleanup
and status propagation is therefore the first demonstrated software blocker;
DPC behavior is later. Descriptor and vendor-control paths share the pattern
and need the same offline audit.

The 187,249-byte capture has SHA-256
`ab998beda7e6544cf56d574b66212ee3129d17e4f7b97cf3378582d5ef105da8`.
It records 109 successful control-IN submissions/completions and no bulk,
interrupt, or control-OUT transaction. Eight bulk submissions and four
clear-halt calls failed before bus acceptance. No claim, release, detach,
automatic detach, alternate-setting change, or configuration change occurred.
The kernel window has twelve interface-4-not-claimed messages and no reset,
disconnect, reconnect, or rebinding.

Final postflight found no candidate Wine process or test unit. The standing
`io24-crashwatch.service` is the pre-existing telemetry monitor and was left
untouched. Device identity, configuration, all alternate settings, and all
bindings remained unchanged; the source hashes and protected-prefix inode and
timestamp also remained unchanged.

The 110-entry runtime evidence verifies at:

    /home/ajuntanaga/.cache/io24/sandboxes/io24-wine-sandbox.ntoskrnl-mdl-nonpaged-v1-20260822/out/checkpoints/live-read-ntoskrnl-mdl-nonpaged-v1-20260822T145019PDT/

Its `SHA256SUMS` hash is
`2717a3f6cabfaf65acccbc03a6b8b1e540620cce82e9ecc0b7dbd0b688591807`.
The project report is
`re/wine-ntoskrnl-mdl-nonpaged-v1/checkpoints/CP24_STAGED_LIVE_DIAGNOSTIC.md`.
Its 76-entry chain is `CP24_SHA256SUMS`, SHA-256
`6d4f31ada0350d2ae63382b77d653e586a32ce90b05ab6885dce1feca814e30c`.

Stop at CP24. The one live authorization is consumed; do not retry. Safe next
work is offline and test-first: reproduce and repair immediate-submit failure
cleanup/status handling, audit the descriptor and vendor siblings, and keep
interface routing separate. A claim, detach, alternate-setting change,
configuration change, firmware access, Voice FX, class-OUT, protected-prefix
access, full Universal Control, or any future device-visible action requires
new explicit authorization and a fresh full preflight. Reconnection is not
authorization. Pause at 10% battery or lower.

## CP25 — immediate-submit cleanup developed offline

CP25 completed offline on 2026-08-22. CP24's complete seal first reverified.
No Wine process or service was launched, no hardware namespace was exposed,
and CP24's consumed live authorization was not reused.

A new device-free behavior contract loads the real WineUSB Unix call table
against a pinned fake libusb SONAME. Its first RED exactly reproduced the CP24
lifetime defect on bulk, GET_DESCRIPTOR, and vendor-interface requests: an
immediate libusb submission rejection returned `STATUS_PENDING`, retained the
IRP cancellation handle, and leaked the transfer context and control buffer.
Further RED/GREEN cycles covered invalid-pipe and real control-buffer allocation
failure branches that left stale freed cancellation handles.

The isolated patch clears `DriverContext[0]`, sets
`USBD_STATUS_REQUEST_FAILED`, frees all transfer-owned allocations, and returns
`STATUS_UNSUCCESSFUL` when submission fails synchronously. It changes only
`dlls/wineusb.sys/unixlib.c` and adds no device operation:

    081975cfffea75a2a6058836829ceb5c1508e8c52e8b98065ba9e9a153f7b876  re/wine-11.15-wineusb-immediate-submit-cleanup-v1.patch

The new contract and all predecessor WineUSB contracts pass in a networkless,
USB-hidden namespace. The report is
`re/wineusb-immediate-submit-cleanup-v1/checkpoints/CP25_IMMEDIATE_SUBMIT_CLEANUP_DEVELOPMENT.md`.

## CP26 — two clean builds reproduce the cleanup exactly

CP26 completed offline on 2026-08-22. Two independently prepared source trees
applied the complete pinned WineUSB patch sequence with fuzz zero and match the
development and patch-check trees exactly. Independent contained `make -j1`
builds reproduce the development outputs byte-for-byte:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    93a30fce04fc59fb034d9c88b6becd9931c56892cf97f5eca7f27db99aa68264  wineusb.so

Each clean side independently passed the immediate-submit, multi-interface,
pipe-observe, exact RANGE-v2, USB-DI, and CP15 analyzer contracts with hardware,
sysfs, networking, host prefixes, and user runtime paths hidden.

The report is
`re/wineusb-immediate-submit-cleanup-v1/checkpoints/CP26_REPRODUCIBLE_BUILDS.md`.
Its 15-entry chain is `CP26_SHA256SUMS`, SHA-256
`5d4ad56359bb3b7a5f555a3a2cd06f136bd8906aafd3e398a61907ad4bc9b951`.

Stop at CP26 for this software lineage. The triplet is reproducible but is not
staged or selected. A later stage needs a new selector RED/GREEN; a later live
run separately needs new explicit authorization and full preflight.

## CP27 — interface-4 routing and firmware scope resolved offline

CP27 completed offline on 2026-08-22. It inspected only sealed passive/runtime
evidence, exact Wine sources, the PaeDSPUSB installation inputs, and the
installed Universal Control hardware-access module. No device-visible call,
Wine prefix, firmware image extraction, or hardware action occurred.

The passive descriptor analyzer proves four function collections:

    {0,1,2}  IAD-grouped UAC2 audio
    {3,4}    UAC1 AudioControl plus MIDIStreaming
    {5}      vendor-specific; alt 1 bulk endpoints 0x81/0x01
    {6}      DFU class/subclass/protocol fe/01/01

Interface 3's AudioControl header directly declares interface 4 as its sole
streaming subordinate. Interface 4 directly declares the bulk pair `0x02` and
`0x82`. The PID 0422 PaeDSPUSB INF binds MI03 as `Revelator IO 24 MIDI` and
names two cables on it: CTRL In/Out and MIDI In/Out. Interface 4 is therefore
the correct CTRL/MIDI transport, not a firmware interface. Redirecting
PaeDSPUSB from interface 4 to interface 5 would be incorrect.

CP24's routing defect is duplicate scope, not the interface number. The MI00
driver cycle at log lines 2238-4033 and MI03 cycle at lines 5499-7162 each
receive all seven interfaces, construct the same interface-4 handles
`0x202`/`0x282`, and issue four reads on endpoint `0x82`. The intended MI03
cycle is duplicated because MI00 is also shown interface 4.

The exact Wine source explains why. Wine creates a separate child for every raw
interface even where USBCCGP would honor IAD/function collections, gives every
child the same physical libusb handle, and retains an interface index that is
not passed into URB dispatch. GET_DESCRIPTOR and SELECT_CONFIGURATION are thus
physical-device-wide rather than function-scoped. The required repair shape is
USBCCGP-equivalent collection modeling plus partial configuration descriptors
and function-scoped pipe/claim ownership. For this device MI00 should see only
`{0,1,2}` and MI03 only `{3,4}`.

Interface 5 is out of the PaeDSPUSB/interface-4 blocker, but not proven out of
the full Universal Control path. Static model data in `dspusbdevice.dll`
associates interfaces 5 and 6 of PID 0422 with `WINUSB`, imports the WinUSB
control/read/write APIs, and contains bulk-subdevice and DFU routines. This
supports, but does not live-prove, MI05 as the vendor bulk application channel
and MI06 as the DFU channel. CP24 independently records no compatible driver
for MI05 at line 7878 or MI06 at line 8168. Neither was observed opened.

Firmware is now correctly bounded to offline installed-artifact analysis and
primarily interface 6/DFU. Current evidence does not show a bad firmware
version, require a firmware transition, or justify a device read/write. Host
transport still has two demonstrated gaps before firmware can be blamed:
composite-function leakage and absent MI05/MI06 WinUSB discovery. There was
still no UCNET `DA` and no `synchronize.json`.

The test-first analyzer is:

    tests/io24_usbmon_function_topology.py
    tests/io24_usbmon_function_topology_contract.py

It rejects incomplete configuration-header captures and passes both its
synthetic contract and the sealed passive pcap. The full report is
`re/io24-interface-routing-v1/checkpoints/CP27_INTERFACE4_ROUTING_ANALYSIS.md`.
Its 14-entry chain is `CP27_SHA256SUMS`, SHA-256
`72e3c97cd46af5fefc97a6170c0056b1fc26162ceba2219dedb6642bef39dc13`.

Stop at CP27. The next safe work is offline and test-first: specify the four
function collections and exact partial descriptors, implement and reproduce
function-scoped WineUSB children, then specify MI05/MI06 WinUSB discovery as a
separate compatibility layer. Before any later live diagnostic, choose an
interface-4 ownership architecture: an explicit libusb claim/detach can affect
host audio and needs new authorization; a native ALSA/MIDI bridge is a larger
alternative design. Any device-visible read, driver load, claim/detach,
alternate or configuration change, OUT transfer, firmware transition/write,
full Universal Control, Voice FX, or protected-prefix access requires new
explicit authorization and a fresh full preflight. CP24 remains consumed; do
not retry it. Reconnection is not authorization. Pause at 10% battery or lower.

## CP28–CP29 function-scoped WineUSB development and reproduction

CP28 and CP29 completed offline on 2026-08-22. They consumed no live
authorization and did not access a Wine prefix, USB node, device interface,
Universal Control, Voice FX, or firmware image.

The CP27 composite-enumeration repair is now implemented and reproducible.
WineUSB models the one-configuration IO24 as four function children:

    MI_00  {0,1,2}  218-byte partial configuration
    MI_03  {3,4}    133-byte partial configuration
    MI_05  {5}       41-byte partial configuration
    MI_06  {6}       27-byte partial configuration

The base physical device remains, while raw children MI01, MI02, and MI04 are
not emitted. Function membership comes from the active IAD and the legacy UAC1
AudioControl header collection. Multi-configuration devices and composites
without a valid grouping retain the prior raw-interface fallback.

The exact-device contract embeds the already sealed 392-byte physical
configuration and independently checked literal projections. Against CP26 it
exited 1 with 24 intended failures: raw children leaked, descriptor reads were
not widened to the complete physical configuration, the returned descriptors
were unscoped, and MI00 accepted interface 4. Against the candidate it passes
both nine-byte header probes and complete partial reads for all four functions.

Most importantly for the active blocker, MI00 now rejects interface 4 before
pipe mutation. MI03 accepts interfaces 3 and 4 and receives handles `0x202` and
`0x282`. Interface 4 remains the correct CTRL/MIDI transport and was not
redirected to interface 5.

The patch is:

    re/wine-11.15-wineusb-function-scope-v1.patch
    SHA-256 3c44d15b710cc99c253590ace734c28ba5f2fb1f0b7a678dac195ea5184c4a7e

It applies to the sealed CP26 source with fuzz zero. Development, patch-check,
source A, and source B match across all 12,445 regular files. Two empty clean
build roots configured and built separately under identical virtual paths,
one-job/low-priority limits, a 180-second timeout, unshared networking, minimal
devices, empty sysfs, and read-only source/tool mounts.

Development, build A, and build B are byte-identical:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    f355a7d3e228c5376bcf00d5d0b1e971273cdcfdb9a5362ff0ab77a3badd6835  wineusb.sys.so
    88ab927a25c818e308589414c94c06bb41e9b3cba8aa364535e94f958b5b89c0  wineusb.so

Both independent sides pass the function-scope contract, CP26's six retained
hardware-free contracts, the CP27 topology contract, and the topology analyzer
against the sealed passive capture. Full reports are:

    re/wineusb-function-scope-v1/checkpoints/CP28_FUNCTION_SCOPE_DEVELOPMENT.md
    re/wineusb-function-scope-v1/checkpoints/CP29_REPRODUCIBLE_BUILDS.md
    re/wineusb-function-scope-v1/MANIFEST.md

The 45-entry seal is
`re/wineusb-function-scope-v1/checkpoints/CP29_SHA256SUMS`, SHA-256
`2a46d20ca95091f13ac178a0a2a180bf133cbc69986fcb4732cbae2789203346`.

Stop at CP29. The triplet is reproducible but is not staged and the real
harness selector is unchanged. The composite-scope half of the interface-4
blocker is fixed offline; physical ownership is not. CP24 showed interface 4
still owned by `snd-usb-audio`. Before a later live test, choose explicitly
between a disruptive libusb claim/detach architecture and a larger native
ALSA/MIDI bridge. Claim/detach and any live diagnostic require new explicit
authorization and full preflight.

MI05/MI06 driver discovery remains a separate host compatibility gap. It still
does not prove a firmware defect or justify firmware access. Any staging needs
a new hash-pinned selector contract first. Any device-visible read, driver
load, claim/detach, alternate or configuration change, OUT transfer, firmware
transition/write, full Universal Control, Voice FX, or protected-prefix access
requires fresh explicit authorization. CP24 remains consumed; do not retry it.
Reconnection is not authorization. Pause at 10% battery or lower.

## CP30 — MI05/MI06 WinUSB boundary corrected and sealed offline

CP30 completed offline on 2026-08-22. It used only the exact installed
`dspusbdevice.dll`, retained CP24 registry/setup evidence, the CP29 source, and
official upstream source pages. No Wine process, prefix, USB namespace, device,
service, Universal Control process, or firmware artifact was opened.

The former project claim that Wine implements WinUSB over libusb was wrong.
Wine's `wineusb.sys` is the USB bus enumerator exercised by PaeDSPUSB; it is not
a complete generic WinUSB function stack. The exact vendor module imports
fourteen `WinUsb_*` functions and its one IO24 model records MI05 and MI06 as
`WINUSB`, contains `DeviceInterfaceGUID`, and contains a `MSFT100` marker with
vendor code `0xa5`.

The retained CP24 outcome is exact: every MI05/MI06 instance has only USB class
compatible IDs, no `USB\MS_COMP_WINUSB`, no driver, and no service. SetupAPI
examined Wine's `wineusb.inf`, which matches only `root\wineusb`, then reported
no compatible driver for MI05 at line 7878 and MI06 at line 8168.

The pinned Wine source lacks all three required layers:

    OS 1.0 descriptor -> USB\MS_COMP_WINUSB translation   missing
    generic WinUSB function binding/device interface      missing
    vendor module's required WinUsb_* API operations      0/14

All thirteen imported functions other than `WinUsb_Free` are spec stubs;
`WinUsb_Free` is itself an explicit semantic stub. Official Wine master at
release 11.16 commit `8da89f8493b21ebfbe344a54dbef0cde23c7ea59` retains the
same boundary. This means a compatible-ID-only patch would be an inert partial
fix and must not be staged or described as MI05/MI06 support.

The new hardware-free analyzer and contract are:

    tests/io24_winusb_readiness.py
    tests/io24_winusb_readiness_contract.py

The synthetic contract proves the exact three-blocker RED and a structural
GREEN. This is necessary-surface evidence, not behavioral implementation
proof, and the audit always reports `stageable=false`. The analyzer confirms
the real-artifact boundary and deliberately exits 1 under
`--require-structural-ready`. Full evidence is in
`re/io24-winusb-readiness-v1/checkpoints/CP30_WINUSB_READINESS_BOUNDARY.md`.
The legacy `tests/uc_wine_capture.sh uc` mode now fails closed before any
process or filesystem action and requires a future behavioral selector edit.

Presets, effects, and the component model remain valid above this boundary.
What is blocked is new Universal Control synchronization and wire evidence.
MI05 is still only the likely application bulk path; MI06 is the direct DFU
function and likely firmware path. Neither was opened in CP24, and the three
host gaps further narrow firmware rather than implicate it.

Next safe work is offline and test-first: implement Microsoft OS 1.0 discovery
against fake libusb, then a generic WinUSB function binding, then the fourteen
required user APIs; run the retained matrix and two independent clean builds
before any selector. Interface-4 ownership remains separate after that.

Stop at CP30. Do not stage CP29, run `uc_wine_capture.sh uc`, retry CP24, or
touch a device/prefix. Any staging, device-visible read, driver load,
claim/detach, alternate or configuration change, OUT transfer, Universal
Control, Voice FX, firmware transition/write, or protected-prefix access needs
fresh explicit authorization and full preflight. CP24 remains consumed;
reconnection is not authorization. Pause at 10% battery or lower.

## CP31 — Microsoft OS 1.0 discovery implemented and reproduced offline

CP31 completed offline on 2026-08-23. The CP30 seal reverified first. No Wine
process, prefix, USB node, device interface, Universal Control process, Voice
FX process, service, or firmware artifact was opened, and no prior live
authorization was reused.

The first of CP30's three missing WinUSB layers is now GREEN:

    Microsoft OS 1.0 discovery / compatible-ID translation   implemented
    generic WinUSB binding / device-interface lifecycle      missing
    vendor-required WinUsb_* operations                       0/14

The generic WineUSB reader performs bounded descriptor-IN discovery for index
`0xee`, the returned vendor code, extended compatible IDs at `wIndex=4`, and
extended properties at `wIndex=5`. It caps allocations at 4096 bytes, validates
the complete descriptor structure, publishes compatible sections atomically,
defers properties to actually emitted active-config children, carries a valid
`DeviceInterfaceGUID`, and formats `USB\MS_COMP_*` plus optional
`MS_SUBCOMP_*` IDs before the existing class fallbacks. It contains no IO24
VID/PID, vendor-code, interface, ID, or GUID hardcode.

The first contract run against unchanged CP29 was an exact RED: zero descriptor
requests and seven missing MI05/MI06 metadata assertions. Further RED/GREEN
cases blocked an unnecessary request for unknown interface 200 and a partial
metadata leak from a malformed later function section. Eleven discovery
scenarios plus direct PnP-ID tests now pass against clean build A and clean
build B. Both sides also pass every retained hardware-free contract.

The patch and clean artifacts are:

    d63c0b6727c6fa313153738aa0a33bfd5f0cc799e90012d92257eebb0a0ed6d4  re/wine-11.15-wineusb-ms-os-10-v1.patch
    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    13669869e34219947862da6dc46e94fb3a3aaf03902b84cca86cbbee663bff94  wineusb.sys.so
    228cf6b8006714887d6adeb0bc7dff040fba201f84cae1265a292cc115b517c9  wineusb.so

Clean A and B are byte-identical. The patch applies to a sealed CP29 clone with
fuzz zero, and patch-check matches development across 12,447 regular files.
The only new actionable libusb symbol is `libusb_control_transfer`; claim,
detach, alternate-setting, and configuration symbols remain absent.

The fixture's vendor code `0xa5`, interface IDs, and GUIDs are synthetic values
informed by static vendor-module evidence. They are not a physical-device
descriptor response. The new reader would be device-visible if staged, so CP31
is deliberately not stageable while function binding and all user APIs are
missing. The legacy real capture remains fail-closed.

Interface 4 is unchanged: CP29 fixed function leakage, but Linux physical
ownership still needs a separate architecture decision. Preset, effect,
Voice FX, component-model, and prior wire evidence also remain unchanged; CP31
does not create synchronization or effect-wire evidence. Firmware is narrowed,
not implicated: MI06 remains the descriptor-defined DFU function and likely
direct firmware route, but two host layers still precede it.

The full report is
`re/wineusb-ms-os-10-v1/checkpoints/CP31_MS_OS_10_DISCOVERY.md`.

Resume at CP31 with one coherent offline slice: specify generic WinUSB function
binding and device-interface registration/lifecycle, using the parsed GUID,
without changing PaeDSPUSB MI00/MI03. Cover add/remove, failed start, duplicate
GUID, teardown, and discovery-nonsupporting devices before implementing any
`WinUsb_*` transfer API. Do not stage, select, run UC, access a prefix, or touch
the device. CP24 remains consumed; reconnection is not authorization. Pause at
10% battery or lower.

## CP32 — generic WinUSB function binding completed and sealed offline

CP32 completed offline on 2026-08-23. The complete CP31 seal reverified first.
No Wine process, prefix content, USB node, driver/service, Universal Control,
Voice FX, or firmware artifact was opened, and CP24's consumed live
authorization was not reused.

The WinUSB host stack is now two layers out of three:

    Microsoft OS 1.0 discovery / compatible-ID translation   implemented
    generic WinUSB binding / device-interface lifecycle      implemented
    vendor-required WinUsb_* operations                       0/14

The existing WineUSB PDO exposes CP31's validated GUID through a private,
versioned, reference-balanced bus interface. A new generic `winusb.sys` binds
only `USB\MS_COMP_WINUSB`, creates independent per-PDO state, registers the
descriptor-provided device-interface GUID, enables it after successful lower
start, preserves it across normal stop/restart, and makes bounded disable
attempts plus unconditional cleanup during failure/removal paths. Missing,
malformed, unrelated, removed, or invalid-version metadata fails closed before
FDO publication.

The new function driver deliberately has no I/O protocol: create, read, write,
device-control, and internal-device-control are rejected. It has no Unix
library, libusb dependency, URB submission, claim/detach, configuration,
alternate-setting, transfer, or firmware path. The user-mode `dlls/winusb`
tree remains byte-identical to CP31, so MI05/MI06 are still not usable and the
candidate is not stageable.

The current contracts fail against sealed CP31 only because the metadata
interface, generic driver, and INF route are absent. They pass against both
clean CP32 sides, as does the complete CP31/predecessor matrix. The lifecycle
harness was hardened after its reset routine was found to erase assertion
failures; the corrected test drove strict returned-interface validation. A
real Wine link also caught and removed an invalid cross-driver GUID symbol
reference by using module-local constants from a shared initializer.

The patch is:

    re/wine-11.15-winusb-function-binding-v1.patch
    SHA-256 7df4011ea20fa36bf80f4bc0ba409c9dca812b7d76b00f19f1709774eebf75bb

It applies to sealed CP31 with fuzz zero. Development and patch-check match
across 12,453 regular files with no symlinks, `.orig`, or `.rej` files. Both
independent clean builds used identical virtual paths, read-only source/tools,
empty sysfs, minimal devices, private temporary state, one job, low priority,
a 2 GiB cap, a 300-second timeout, and unshared networking.

Clean A and B are byte-identical:

    b16b8d2ab2104dbf98b6a171546258db3dc22c11a4688170710c022e1068f30e  x86_64-windows/wineusb.sys
    28617460085c0a2f8ae4782f3147bcad8a475a5b01daebba72b64380c118808e  wineusb.sys.so
    1edd11b0336a241c1ac8c667fb1d21db3bfac08b0ebdc8f672aa2931785490d9  wineusb.so
    bacee6355cda7eb6bb19a7c8f73d2b8babfc4a22d19b47c31cffc1985f7427eb  x86_64-windows/winusb.sys
    dd1f3f199999546ff64ea7c1daa1306fba0a5958f7c1102df3b49ebfca20be46  winusb.sys.so

The full report and manifest are:

    re/winusb-function-binding-v1/checkpoints/CP32_WINUSB_FUNCTION_BINDING.md
    re/winusb-function-binding-v1/MANIFEST.md

The seal is
`re/winusb-function-binding-v1/checkpoints/CP32_SHA256SUMS`.

Resume at CP32 with one coherent offline, test-first slice: implement the exact
fourteen `WinUsb_*` imports recorded at CP30, including the user/kernel handle
and IOCTL boundary, synchronous and overlapped completion/cancellation, pipe
policy, descriptors, associated interfaces, and alternate settings. Rerun the
complete matrix and two clean builds before designing any selector.

Interface 4 remains separate: CP29's correct MI03 CTRL/MIDI function view is
unchanged, while Linux physical ownership still needs an explicit architecture
choice. Do not stage CP32, run UC or Voice FX, retry CP24, access a prefix, load
a driver, or touch the device. Any staging or live/prefix action requires fresh
explicit authorization and full preflight. CP24 remains consumed; reconnection
is state evidence, not authorization. Pause at 10% battery or lower.
