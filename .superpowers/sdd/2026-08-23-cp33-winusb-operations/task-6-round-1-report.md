# CP33 Task 6 round-1 report

Status: implementation and focused offline contracts complete; Task 6 remains
open for controller review.  No ledger state, seal, snapshot, wrapper, Wine
runtime, physical device, USB path, or external service was touched.

## Round-1 correction

- Each file has a passive `session_mutex` covering initialize/release and the
  initialize output copy.  The reentrant same-file release witness proves that
  release runs only after commit, publication, and copy-out.
- The device has a passive `finalization_mutex`.  Initialize performs exactly
  one retained-token rollback recovery before its next SELECT.  A failed
  COMMIT followed by a failed ROLLBACK retains the token plus upper snapshot
  and interface allocation on the device; neither is freed early.
- File state is published only after a successful lower COMMIT.  A null token
  remains the successful legacy non-function SELECT path and is not finalized.
- STOP holds the finalization mutex over lower forwarding and its visible state
  transition.  SURPRISE removal serializes state/files removal.  REMOVE marks
  removal under that mutex, releases it before waiting for CLOSE/file drain,
  then reacquires it for its one final recovery attempt, lower removal, and
  synchronous-child-destruction terminal ownership clear.
- The fake WDM boundary now supplies passive mutex operations and has an exact
  expected file layout.  The lower fake distinguishes forwarded PnP from a
  transaction URB and accepts device-scoped terminal rollback after close.

The finalization transport contract is intentionally limited: a failed
finalization submission is treated as not consuming its token.  Lost lower
acknowledgement after consumption needs a future idempotent lower query or
compensation protocol and is not claimed here.

## Test-first and focused results

The current expanded upper test against the frozen round-1 tree could not be
compiled without an overlay because that minimal snapshot omits its `include/`
tree and `msos_id.h`; its direct wrapper therefore exits `2` before executing.
The prior recorded expanded RED is the genuine source-level feature RED (exit
`1`, 16 assertions) required by the task.  This round did not misclassify the
incomplete snapshot as feature evidence.

Commands executed in this round:

```text
LSAN_OPTIONS=detect_leaks=0 tests/winusb_function_io_contract.sh \
  .io24-build/winusb-api-v1/dev-source --initialize
exit 0

tests/wineusb_winusb_urb_contract.sh .io24-build/winusb-api-v1/dev-source \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0 --claims
exit 0

tests/wineusb_function_scope_contract.sh .io24-build/winusb-api-v1/dev-source \
  .io24-build/winusb-function-binding-v1/build-a \
  .io24-build/winusb-function-binding-v1/build-a/dlls/wineusb.sys/wineusb.so \
  .io24-build/wineusb-observe-v2/tools/usr/include/libusb-1.0
exit 0

tests/wineusb_winusb_busif_contract.sh .io24-build/winusb-api-v1/dev-source
exit 0
```

The raw sanitizer wrapper exits `1` only because LeakSanitizer refuses this
ptrace environment (`LeakSanitizer does not work under ptrace`).  The accepted
assertion run above disables only leak detection and retains ASan, UBSan, and
alignment instrumentation.  It is not a raw-leak-check pass.

## Round-1 changed-path SHA-256

`tests/wineusb_winusb_urb_contract.c` is included below as coverage closure:
the existing lower production implementation already passed; the contract
change closes the nonempty rollback/prior-commit witness gap.

```text
d32da2798aa8b41f271cbcf95a77feded021c5df7de6030d3224ad4b7a30c7a4  dlls/winusb.sys/main.c
ea06f9486ef6dbb18162a8bb8bcc8537ba30b35ccb8ddac9ee47ee5dd460fe88  dlls/winusb.sys/session.c
3f70be253ae14c406cfa843f2d3424d8834f08b08c7e4f57ccb191fdfc6a9cad  dlls/winusb.sys/winusb_private.h
473e7d4b0cddf5b02c7bf4d17a4316d036e0f01622f1e6d03dbe13d49c390c2a  tests/wineusb_winusb_urb_contract.c
81beeed81d73bd46551c09271532f406fdf17b200f75ee6ad27559f6d5ac9a5b  tests/winusb_function_binding_contract.c
83b0505873cfb132627a567b260119d83713d99241dc2cdf320a66f6acbd82c4  tests/winusb_function_io_contract.c
```

No completion claim is made for the ledger or a seal.
