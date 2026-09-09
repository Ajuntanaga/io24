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
