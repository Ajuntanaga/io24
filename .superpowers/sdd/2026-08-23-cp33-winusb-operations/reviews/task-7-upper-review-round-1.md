# CP33 Task 7 upper review round 1

Result: **PASS** for the bounded upper slice. No new material issue was found.
This is not a Task-7 completion claim.

Reviewed hashes:

- `winusb.sys/main.c`: `c577190120f193d51d93aa7fb224b1f63ffafe75314cbd037d61757924af6d6a`
- `winusb.sys/session.c`: `220323174f1b35a334872cad5b332e238df1ce4a146bb728e0c8474850c5abd2`
- `winusb.sys/winusb_private.h`: `9f9ed03b0af32f223f1c77b9f8f8ed0a341f4c61401a60dd9a40be6a5d3b0402`
- `winusb_function_io_contract.c`: `9cae6022cd355b69e01b13db3ed29be27db38b03e42eb2cdc8cff407fc7e8414`

All R91 findings are closed. The unconnected per-interface counter and direct
test mutation are gone; alternate selection requires its dispatch to be the
file's sole outstanding request and revalidates after lower selection. Dispatch
rejects any output length or MDL. The actual upper translation executes exact
and malformed lengths/header/session/reserved fields, output/MDL, unknown
interface/alternate, concurrent request, both allocations, distinct lower NT
and URB failures, post-select state mutation, two generations, a parsed
two-interface target-only replacement, returned default/alternate handles, and
cleanup. MI05 alternate 1 reaches the fake lower boundary as exact bulk
`0x81`/`0x01`, 512-byte metadata.

Focused offline results:

- upper `--alternate`: exit 0
- upper `--lifecycle`: exit 0
- upper `--session`: exit 0
- retained function binding: exit 0
- raw upper `--initialize`: exit 1, LeakSanitizer ptrace refusal only
- `LSAN_OPTIONS=detect_leaks=0` upper `--initialize`: exit 0 with ASan/UBSan,
  alignment instrumentation, and explicit allocation balance retained

No Wine runtime, prefix, USB/sysfs/device, staging, selection, or live action
was used.
