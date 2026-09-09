# UC 4.7.2 Standard high-shelf recovery scope

Status: `STATIC_SOURCE_BOUND`

This run answers one question: which exact coefficient algorithm Universal
Control 4.7.2 uses when the Standard high-band `eqtype4` UI value selects its
high shelf.  Its only executable authority is the retained
`dspusbdevice.dll` with size `4,979,672` and SHA-256
`de685e89c88b191b9709145056aa37d58a76f141a53a9c1533dff917f611fd28`.
The retained factory extraction is independently gated at size `47,158` and
SHA-256
`89b0572dd760b77831d012e2db0568b4f4eeb158985a4ca86126be28e934c73d`.

The analyzer parses the PE as data, rejects either wrong identity, and
disassembles only 18 named hash-pinned instruction intervals.  It binds the
Standard descriptor, enum mapper, full and incremental selector dispatches,
constants, precision transitions, operation order, output conversion, and one
retained Bright Vocal factory tuple.  Vendor code is never loaded or run.

No device, USB, audio, Host launch, Wine/prefix access, firmware action,
network, install, user-cache access, or Obsidian operation is in scope.  This
run proves static UC source semantics and exact host-produced bytes; it does
not prove device acceptance, audibility, storage, recall, or standalone
persistence.
