# CP5 — class-interface-IN contract is RED

Reached at `2026-08-19T20:49:15-07:00`. This is the first durable pause point
after CP4. No implementation exists at this checkpoint.

## Scope

The contract permits only the exact request observed at CP4:

```text
URB function       CLASS_INTERFACE (0x1b)
transfer flags     IN | SHORT_TRANSFER_OK (0x3)
reserved bits      0
request            0x02
value              0x0100
index              0x0500
receive capacity   256
setup bytes        a1 02 00 01 00 05 00 01
```

It requires asynchronous submission and completion, short-response copying,
bounded receive semantics, cleanup after immediate submit error, cancellation
and STALL completion, and exact rejection of OUT, unknown flags/fields/lengths,
undersized headers, and missing buffers. `URB_FUNCTION_SELECT_INTERFACE`
must retain its observation-only `STATUS_NOT_IMPLEMENTED` path.

## Device-free fixture

The test builds a fake library with libusb's real ABI and SONAME, then loads
the exact WineUSB Unix library and invokes its exported
`unix_usb_submit_urb` entry. The fake provides no enumeration or device access;
submission and completion are controlled entirely by the test. The final run
was inside Bubblewrap with user/PID/network/IPC/UTS/cgroup namespaces, all
capabilities dropped, a private `/dev`, empty `/sys`, `/run`, `/home`, and
`/tmp`, and the project mounted read-only.

Test inputs:

```text
c6f872ac7c8257b654e620355b17b92434211f56fc84da20729e5b19bd693a08  tests/wineusb_class_interface_in_contract.c
f70f767da5d1d3475e44694eeec73d6a9290fce72c333f8f856706d2642067bd  tests/wineusb_class_interface_in_fake_libusb.c
f7ee696aae656f413051b6d4f8ac17ab2df9943eee8e2776402e964c5cb19392  tests/wineusb_class_interface_in_contract.sh
```

## RED result

Against observation v2, the real Unix backend logged `Unhandled function
0x1b`, returned `STATUS_NOT_IMPLEMENTED`, and made zero fake-libusb
submissions. All positive, completion, cleanup, bounds, and explicit rejection
expectations therefore failed: 37 checks, exit status 1. This is the expected
RED baseline, not a test-infrastructure failure.

Baseline artifacts:

```text
e5d4d22ec48ac4321627b30fb014133193d7d77bff3f296e867c1cafe7e07520  wineusb.sys.so
03a4c63ec669bf4f05789dfffd42c55e10d9e0ef990a1cc0622c1a0ab7812826  wineusb.so
```

Exact output is in
`.io24-build/wineusb-class-interface-in-v1/logs/contract-red.log`.

## Safety state and next pause

The io24 device count was zero, no Wine/UC/Xvfb/io24 process ran, and the
protected prefix retained inode 3427833 and timestamp
`2026-08-12 00:31:35.825186221 -0700`.

Checkpoint CP6 may begin by implementing only this contract against a fresh
copy of the pinned Wine 11.15 source layered with USB-DI v1 and observation v2.
Any broader class request, class OUT path, select-interface semantics, device
visibility, or regression in the existing contracts is a hard pause.
