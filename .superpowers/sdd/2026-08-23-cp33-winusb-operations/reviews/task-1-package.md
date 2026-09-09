# Task 1 review package

- Base label: `task-1-base`.
- Head label: `task-1-head`.
- Base state: `../task-1-base-state.txt` (all Task 1-owned paths absent; CP33 root absent).
- Task brief: `../task-1-brief.md`.
- Implementer report: `../task-1-report.md`.
- Review rubric: `../task-1-review-rubric.md`.
- Full bounded source/test/report/evidence diff: `task-1.diff`.
- Head snapshot manifest: `task-1-head.sha256`.
- Head manifest SHA-256: `d9baed7c96c2bf3269b01dd21e62e445a61abea58bd8c539745a4c72fecd3752`.
- Bounded diff SHA-256: `bb44fe1baf5f0527062b955bdc9e67f4f8f7318b1c1d4032c117c1f7d2ffc315`.

The 1.56 MB `dspusbdevice-winusb-callsite.log` is present in the exact head snapshot and its digest is in the manifest, but it is not inlined in the bounded diff. Review it directly when checking static vendor evidence.

## Fresh controller verification

The controller reran the following after the implementer returned:

```text
SEAL lines=72 ok=72 failed=0
CP33 public RED: prototypes=1/14 definitions=1/14 callable-exports=1/14 failures=3
CP33 function-driver RED: create/device-control/session/select/control absent failures=4
CP33 lower RED: select-interface/control/cancel/function-claims missing; reset backend error is unconditionally reported success; failures=5
CP33 cancel RED: lower/upper cancel absent; abort is all-pipe; removal completes pending IRPs without physical cancel; failures=5
CP33 vendor RED: hash=OK imports=14/14 policy-callsite=0x180084d50 initializer=0x180095e20 callable=1/14 policy-pairs=9 failures=vendor callable count 1/14
STATUSES seal=0 dev_diff=0 patch_diff=0 hash=0
RED user=1 function=1 lower=1 cancel=1 vendor=1
USAGE user=2 function=2 lower=2 cancel=2 vendor=2
```

## Reviewer focus

Determine whether Task 1 really creates the complete test/fake boundary required by the approved design, not merely commands that return the expected numbers. In particular, inspect whether:

- the public DLL contract compiles the actual `dlls/winusb/main.c` with a fake Win32 I/O boundary and tests behavior through exported functions;
- the function-driver contract compiles actual `dlls/winusb.sys/main.c` against a fake WDM/lower-stack boundary and can later exercise create, lifecycle, IOCTL, snapshot, alternate, policy, and same-IRP behavior;
- the lower and cancellation contracts actually execute the linked `unixlib.c`/kernel paths against the fake libusb rather than compiling them unused and scanning source text;
- every named fake counter is externally observable and asserted;
- the declared modes provide a usable focused RED/GREEN contract surface for Tasks 2–13 rather than being accepted but ignored.

Source inspection can supplement behavioral assertions, but a source-string match alone must not substitute for the design's required host behavior contract.

## Global constraints

Review is read-only. Do not run Wine; create/access a Wine prefix; stage/select a build; load a driver; start Universal Control or Voice FX; open a USB node; inspect a sysfs USB path; claim/detach a physical interface; change a physical alternate/configuration; issue a physical transfer; or retry CP24. Do not initialize Git. Do not edit any file.
