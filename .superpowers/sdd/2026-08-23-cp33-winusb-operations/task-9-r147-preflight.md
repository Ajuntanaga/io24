# Task 9 R147 combined preauthorization verdict

Timestamp: 2026-08-26

Decision: REQUEST CHANGES.  R147 is rejected and must not be applied.

Both independent reviews verified package integrity, exact patch scope,
candidate reconstruction, and clean focused/retained baselines.  They then
found separate Important executable defects:

1. the function/out-of-scope rejection helper omits the complete fixture and
   deep pipe-table snapshot, allowing a device-handle mutation to pass at exit
   0 with zero failures; and
2. the literal unconditional early-descriptor-release variant fails inside the
   retained preflight and is converted to harness exit 2, while the archived
   exit-1 row is only a narrower function-scoped substitute.

Controller follow-up confirmed that malformed-header and exact null-buffer
RANGE rejection helpers share the partial-state gap.  It also proved that a
changed pipe-table pointer can turn the nominal complete snapshot into a null
dereference and harness exit 2.

R148 must unify complete safe snapshots across every control-rejection helper,
deep-compare a pipe table only when the post-call pointer still equals the
captured pointer, and preserve retained product failures as top-level feature
exit 1 so the literal lifetime variant executes as a real RED.  No live edit is
authorized.
