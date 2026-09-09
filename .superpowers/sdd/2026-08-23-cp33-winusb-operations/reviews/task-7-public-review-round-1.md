# CP33 Task 7 public review round 1

Result: **PASS** for the bounded public slice. This is not a Task-7 completion
claim; upper/lower integration and combined review remain gated.

Reviewed hashes:

- DLL `main.c`: `7443e37451478fd3102d4d3381342fb3fe54c8ce8fd9f63967ee903a6367a1bb`
- DLL `winusb_private.h`: `5b9df910e1e1bac6587048e2af337197e8e3933c1ad9582ca699e62991fc0bfe`
- DLL `Makefile.in`: `aed7eb71709f9aabf126030c1f8f6b3bfd2cc0be84530fc52ad68c20e1083a0e`
- DLL `io.c`: `211dfebb91d009c858101730781d452b9c51d05f66ebe52486a70993bf720e28`
- user contract: `b5e7ff7db6d0d2962fee1555b59cacd89b002a96190732e1266bd27c0278dfc6`
- user wrapper: `781989250735120f7f4eb60d347c13d18541be652d6c07f97ec98ecfc87f6a4b`

The four R90-frozen hashes are unchanged. `io.c` locally bounds the immutable
snapshot size, total, offsets, record-array extents, and selected alternate
range before pointer arithmetic. It acquires one opaque handle, builds a
zeroed exact request from retained root/session/interface state, submits once,
and releases on success and all failures. No opaque-token cast or test seam is
present, and the wrapper compiles and links all DLL production units.

The three-interface contract issues both associated handles and observes exact
private indices 1 and 2. Immediate failure, pending completion failure, and
wait failure preserve exact errors and prove one submit, final root RELEASE,
event closure, and heap balance. An isolated temporary mutation swapping the
two associated indices exits feature 1 with two executed failures; workspace
production remained unchanged and the overlay was removed.

Focused offline results:

- public `--alternate`: exit 0
- public `--handles`: exit 0
- public `--initialize`: exit 0
- isolated associated-index swap: exit 1 with two failures

One optional non-blocking lens remains: the alternate group does not separately
force `CreateEventW()` failure. Shared submission code and initialization cover
related event behavior; this is not an R90 blocker.
