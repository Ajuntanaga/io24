# Task 9 R143 isolated implementer report

## Scope and candidate

All implementation and replay work occurred in disposable
`/tmp/io24-r143-proposal.e1l6Za`. The live workspace, production, test files,
wrappers, support files, snapshots, and hardware paths were not edited.

The candidate starts from frozen R139 test head, applies the sealed R142
three-scope patch only in the disposable tree, then changes exactly these two
candidate test paths:

| Path | frozen live/base SHA-256 | R143 candidate SHA-256 |
| --- | --- | --- |
| `tests/wineusb_winusb_urb_contract.c` | `7dfe09e4dbc0d3463a2c407791c91771326f0c0037d33dd804e64c82ee0b0afa` | `048243af556bd5e68176ca211d74825506f6297f7ed5c85c71e5712e7a3b4f32` |
| `tests/wineusb_winusb_urb_fake_libusb.c` | `c48fbe4c51e53089257c7892a30f8476873fcbfa863b7a9b6e3232189a652acb` | `e1087e04a025d4456b7996a0077e491295096d2ca066b86be71a4ae378a0cb9c` |

R143 retains R142's three-scope matrix and preservation snapshots. It sets
`USBD_STATUS_NOT_ACCESSED` immediately before each exact production call and
retains the `USBD_STATUS_SUCCESS` postcondition. The fake and contract have
the same ABI-shaped `api_calls` tail field. The fake-local
`IO24_FAKE_API_CALL()` increment is the first operation in every exported
`libusb_*` fake entry, so R142's complete count snapshot observes even
side-effect-free boundary queries.

The copied production baseline was
`source/dlls/wineusb.sys/unixlib.c` SHA-256
`ba3172e6547a13311182ce57a128f8e42b46afa1ac83163837404960f57063c1`.

## Baseline and restored final replay

Both commands ran against the disposable candidate, copied production, the
existing offline function-binding build root, and the existing local libusb
headers:

```sh
tests/wineusb_winusb_urb_contract.sh source \
  '/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.io24-build/winusb-function-binding-v1/build-a' \
  '/home/ajuntanaga/Development/Experiments/PreSonus Revelator | UniCont/.io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0' \
  --control-descriptor
```

| Replay | Exit | Result |
| --- | ---: | --- |
| candidate baseline | 0 | `CP33 lower executed mode=--control-descriptor completions=1 failures=0` |
| final replay after all restores | 0 | `CP33 lower executed mode=--control-descriptor completions=1 failures=0` |

## Executable production-mutant replay

Each counted row compiled successfully, executed production through the fake
libusb boundary (`WineUSB pipe-observe fake-libusb behavior: pass`), exited
feature status 1, and reported contract failures. After every run, the copied
production file was restored from `unixlib.c.r143-base`; its SHA-256 matched
the baseline value above after every restore and before the final replay.

| # | Mutant | Exit | Failures |
| ---: | --- | ---: | ---: |
| 1 | R139 broad/suppress predicate | 1 | 24 |
| 2 | function-membership exact suppression plus direction widening | 1 | 20 |
| 3 | allocate/free before function-scope rejection | 1 | 18 |
| 4 | coherent non-function exact tail corruption | 1 | 1 |
| 5 | exact suppression only for coherent non-function metadata | 1 | 10 |
| 6 | synchronous `libusb_control_transfer()` then correct local exact response | 1 | 6 |
| 7 | first-49-byte caller corruption after generic function/in-scope direction miss | 1 | 1 |
| 8 | function-membership recipient widening | 1 | 10 |
| 9 | omit exact local `header->Status = USBD_STATUS_SUCCESS` | 1 | 3 |
| 10 | exact-path `libusb_get_device_descriptor(libusb_get_device(handle), &probe)` | 1 | 3 |
| 11 | same device/descriptor probe before function-scope rejection | 1 | 6 |

One non-evidence harness attempt occurred before row 1: the first broad
predicate draft bypassed the existing predicate helper, causing `-Werror`
unused-function compilation failure and harness exit 2. It was discarded,
the helper-preserving mutant was compiled and rerun as row 1, and only that
rerun is counted above. There were no other exit-2 attempts.

## Complete fake-boundary audit

`nm -D --defined-only fake-audit.so` reported these 32 externally defined
symbols beginning exactly `libusb_`; source audit confirmed that each begins
with `IO24_FAKE_API_CALL()`:

```text
libusb_alloc_transfer
libusb_bulk_transfer
libusb_cancel_transfer
libusb_claim_interface
libusb_clear_halt
libusb_close
libusb_control_transfer
libusb_detach_kernel_driver
libusb_exit
libusb_free_config_descriptor
libusb_free_interface_association_descriptors
libusb_free_transfer
libusb_get_active_config_descriptor
libusb_get_active_interface_association_descriptors
libusb_get_bus_number
libusb_get_device
libusb_get_device_descriptor
libusb_get_device_speed
libusb_get_port_number
libusb_handle_events
libusb_hotplug_deregister_callback
libusb_hotplug_register_callback
libusb_init
libusb_interrupt_event_handler
libusb_interrupt_transfer
libusb_open
libusb_release_interface
libusb_set_auto_detach_kernel_driver
libusb_set_configuration
libusb_set_interface_alt_setting
libusb_strerror
libusb_submit_transfer
```

The audit found 32 exported `libusb_*` symbols and 32 call-site witness
increments (the raw source count of 33 includes the macro definition itself).
No `io24_fake_*` helper or libusb header inline/macro was instrumented.

## Self-review and concerns

- The status sentinel kills the omitted-success-status mutation, and the full
  struct snapshot now catches the exact-path and scope-rejection descriptor
  probes without relying on source scanning as feature evidence.
- The ABI-shaped fake count definitions are byte-layout identical in the two
  candidate files; the candidate compiles under the strict harness and both
  clean replays pass.
- Concern for handoff: the archival path labelled R138 production has a
  different `unixlib.c` SHA-256 (`ff9bea...`) than the active copied production
  lineage used by the sealed R142 replay (`ba3172...`). This report used the
  active copied lineage because it is the one that executes the frozen R139/R142
  contract cleanly. Reconcile that archival identity before any authorization
  to apply a proposal; no live file was changed here.
- No Wine/prefix, USB/device/sysfs, network, firmware, preset/effect, or live
  hardware action was invoked.
