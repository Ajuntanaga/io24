# CP34 zero-selector final receiver construction - progress

Timestamp: 2026-09-05T23:50:44-07:00
Status: locally verified offline correction; independent review remains open;
no live authority or physical-device conclusion follows

## Result

The exact stored-record wrapper constructs
`SetP | 0 | 0 | nested Stat`. Firmware selector `0x3cf20/0x3ce98` therefore
receives `{0,0}` on this route and returns device global `0x20216660`
unchanged.

Lazy initializer `0x3d4f0` loads that global and calls derived constructor
`0x5e014` at `0x3d52a`. Constructor order is decisive:

1. `0x5e018 -> 0x5d990` invokes the base constructor. It temporarily installs
   primary vtable `0x6008d3a8`; raw slot `+0x38` at `0x6d3e0` targets the
   four-byte success/no-op `0x3ccb4`.
2. The derived constructor resumes, loads exact table header `0x6012cb38` from
   literal raw `0x5e08c`, forms header plus eight at `0x5e02a`, and stores
   final primary vtable `0x6012cb40` to `[global+0]` at `0x5e036`.
3. Final raw slot zero `0x10cb40` targets dispatcher `0x420bc`; final raw slot
   `+0x38` `0x10cb78` targets structured-state method `0x531e0`.
4. Only after construction, initializer `0x3d4f0` loads callback `0x41580` and
   registers it through direct call `0x3d536 -> 0x5fc04`. That callback
   restores base tables during teardown; its writes are not final live state.

The exact final-vtable address occurs zero times literally because the code
forms it as `0x6012cb38 + 8`. The source-bound header literal occurs exactly
once. Literal-pointer absence therefore cannot invalidate the constructor
binding.

Dispatcher `0x420bc` captures the selected final object in `r5`; both calls
`0x42266` and `0x42280` load its final `+0x38` slot and reach `0x531e0`.

Result:
`ZERO_SELECTOR_STAT_ROUTE_SOURCE_BOUND_FINAL_DERIVED_SLOT_0X38_0X531E0`.

## Retraction and restored dependent results

The sealed run
`runs/20260905T212623-0700-zero-selector-recall-vtable-correction/` remains
unchanged, but its no-op route conclusion is retracted. It mistook transient
base-constructor and registered-teardown writes for the state left by the
derived constructor. Direct checkpoint reconciliation now reports ten expected
stale shared-file rows and seven verifying immutable/task-local predecessor
rows. That stale manifest must not restore current shared files.

The following source-bound results are restored and strengthened by final
constructor provenance:

- `STAT_DISPATCHER_FIRST_VTABLE_HANDOFF_SOURCE_BOUND_TOP_LEVEL_R1_UNRESOLVED`;
- `STAT_STREAM_CURSOR_ZERO_SOURCE_BOUND_FIRST_WORD_FROM_ACCUMULATION_BUFFER`;
- `DIRECT_STAT_HANDOFF_ENABLES_SELECTOR_GATE_IF_REACHED_COMPONENT_SELECTION_UNRESOLVED`;
- `PAIRED_STAT_HANDOFF_ENTRY_GATES_SOURCE_BOUND_COMPONENT_SELECTION_UNRESOLVED`;
- `STORED_STAT_RECALL_SOURCE_BOUND_BYTE_PRESERVING_NO_PREFIX_INSERTION`;
- `FIRMWARE_STAT_INGRESS_RECALL_SOURCE_BOUND_LOGICAL_BYTE_ZERO_UNCHANGED_NO_PREFIX_INSERTION`.

Link/slot route reports again bind their `+0x38` calls to `0x531e0`. This does
not prove runtime helper completion, a data-dependent selected index, a
physical write, device-resident persistence, Voice FX activation, or audibility.

## Scope disposition

The run directory name preserves the initial `{Appl,0}` question. Static
reconciliation showed that the host's outer `{Appl,0}` envelope is not passed
literally to this firmware selector; the stored-recall query is `{0,0}`. No
separate nonzero selector receiver is required to resolve this route.

## TDD and verification

- Intended focused RED: the final-derived-vtable contract failed against the
  provisional base/no-op report.
- Intended dependent RED: stored recall failed against its provisional no-op
  report; ingress/storage then rejected the stale predecessor status.
- Zero-selector analyzer: 2/2 passed.
- Stored-recall analyzer: 2/2 passed.
- Ingress/storage analyzer: 2/2 passed.
- Route-sensitive consolidated contracts: 7/7 passed in 16.63 seconds.
- Complete firmware-static module: 47/47 passed in 18.756 seconds.
- All four affected modules: 53/53 passed in 19.406 seconds.
- Python compilation of all eight affected analyzer/contract files: PASS.
- Complete hardware-free suite: 235 passed, one expected skip, and 47 subtests
  in 158.89 seconds, exit 0.

The environment printed its recurring `Failed to create stream fd` diagnostic;
the focused and full commands all exited successfully.

## Boundary and continuation

Boundary:
`0X531E0_RUNTIME_COMPLETION_SELECTED_COMPONENT_AND_PHYSICAL_OUTCOMES_REMAIN_UNRESOLVED`.

The pinned UC 4.7.2 host serializer source remains unavailable in bounded local
roots. Reacquisition needs separate network authority. Any physical preset
round trip, effect operation, audio observation, or device access requires its
own exact live authorization.

## Safety

The pinned firmware application was recovered from the installed package in
memory only. No image was emitted. No USB/device, interface claim/detach,
transfer, ALSA, preset/effect, Wine, protected-prefix, network, reset, DFU,
install, staging, flash, or REAPER action occurred. Device connection was not
treated as authority.
