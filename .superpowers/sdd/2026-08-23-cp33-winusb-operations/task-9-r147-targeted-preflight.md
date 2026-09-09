# Task 9 R147 targeted preauthorization review

Timestamp: 2026-08-26

Decision: REQUEST CHANGES.

## Verified integrity

- adjudication manifest SHA-256 `9f5784ffb62c833d88d88722d23165907d4bcd2ec2c26b7c667198e550edce17`
  and all 11 entries verified;
- proposal patch SHA-256
  `8285b45f3c59c0b6442c59df1a943843f8ad45a997fd5e74d2315c20ed753801`
  applied directly to frozen R139 and reconstructed contract
  `45c33598...681a` and fake `bd76d84e...ab15`;
- clean focused and retained candidates exited 0 with zero failures;
- wrong caller handle was caught at exit 1 with 8 failures;
- rejection storage/length/status corruption was caught at exit 1 with 20
  failures; and
- disposable production was restored to `ba3172e...d53051`.

## Important finding

The literal unconditional early-descriptor-release variant required by the
brief is not a valid feature RED.  The poisoned view first breaks the retained
pipe preflight invoked by the lower contract's `main()`.  The outer contract
converts that product assertion failure into harness exit 2 before its focused
group executes; the log has 19 retained failures and no successful fake marker.

The archived exit-1/77 row is a narrower function-scoped variant.  That row is
useful evidence but does not replace the literal unconditional mutation in the
brief.  R147 therefore does not meet its own executable lifetime gate.

No workspace file was edited by the reviewer.
