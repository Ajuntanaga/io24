# Task 9 R150 allocation-lifetime correction

Timestamp: 2026-09-11T01:20:58-07:00

## Outcome

The R149 lifecycle-oracle rejection is corrected in the working tree. The
change is test-only and touches:

- `tests/wineusb_winusb_urb_contract.c`;
- `tests/wineusb_winusb_urb_fake_libusb.c`; and
- `tests/wineusb_winusb_urb_contract.sh`.

The lower fake now gives each tracked pipe-table allocation a nonzero,
monotonic identity which is deliberately not reset with fixture state. Reject
snapshots validate current liveness and capture that identity before reading
the private table. Post-call comparison requires the same pointer, the same
live allocation identity, and the same bytes.

No Wine process or prefix was opened. The protected `.wine-io24` prefix, USB,
the io24, firmware, driver staging, system state, and the network were not
accessed. Battery was 95 percent.

## TDD evidence

The predecessor R149 lower oracle was compiled with the R150 fake's bounded
same-address allocator and a source-bound release/reallocate/restore mutant.
The allocator returned the identical address and restored identical bytes;
R149 still exited 0 with `failures=0`. This is the missing-oracle RED.

The R150 working-tree contract against that same mutant exited 1 through
exactly one product assertion:

```text
R150_SAME_ADDRESS ... released=<address> allocated=<same-address> bytes_equal=1
FAIL expect_control_reject_snapshot: control_reject_pipe_table_matches(f, snapshot)
CP33 lower executed mode=--control-descriptor completions=1 failures=1
```

A second source-bound mutant released a successfully published alternate-zero
pipe table before the reject snapshot. R150 exited 1 through its explicit
pre-snapshot liveness assertion, without a signal, timeout, invalid read, or
harness exit 2:

```text
FAIL expect_control_reject: FALSE
CP33 lower executed mode=--control-descriptor completions=1 failures=1
```

## Clean verification

The applied bytes exactly match the verified disposable candidate:

```text
5e3d79aab79d7b0b331a5425d2f5a09567aeb8e1f11f623fc470c2f1ea262b45  tests/wineusb_winusb_urb_contract.c
705ee556287fe739459ac44d93ba5b23ca9c3a156be5f423ed2a2f55b9222ef7  tests/wineusb_winusb_urb_fake_libusb.c
6c2b64c2e1a7b328af951f6d33df36739b51683eeb8bfbac98ccaa6dbadea7cf  tests/wineusb_winusb_urb_contract.sh
```

Fresh offline results against the current Task 9 production head:

- lower retained `--red`: exit 0, `completions=3 failures=0`;
- upper `--control-descriptor`: exit 0, `failures=0`;
- actual `wineusb.c` `--control-descriptor`: exit 0, pass;
- public `--control-descriptor`: exit 0, `failures=0`;
- upper retained `--lifecycle`: exit 0, `failures=0`;
- `git diff --check`: pass.

One noncanonical diagnostic run with `WINEDEBUG=-all` crashed inside the
directly compiled retained harness. The canonical command, which does not set
that variable, was immediately run from the same bytes and passed. No product
or test change was made in response.

## Status

The two R149 Important findings are closed locally, and the complete Task 9
control/descriptor boundary is green. The files are modified but uncommitted.
Task 9 still needs its checkpoint seal before Task 10 begins.
