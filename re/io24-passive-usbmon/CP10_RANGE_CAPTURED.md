# CP10 — exact io24 Clock Source RANGE response captured passively

On 2026-08-21 a newly authorized, control-URB-only usbmon window captured the
owned io24's normal snd-usb-audio enumeration during a user-controlled
reconnect. The device returned two byte-identical, status-zero, 50-byte
responses to `a1 02 00 01 00 05 32 00`.

The response is pinned in `clock-source-5-range-v1.hex`. It declares four
discrete subranges: 44.1, 48, 88.2, and 96 kHz, each encoded as
minimum=maximum with resolution zero. Two preceding 2-byte requests returned
`04 00`, independently confirming the subrange count.

The capture contained 316 control-URB events with zero kernel drops. The
project extractor and an independent tcpdump hex inspection agree on the
request tuples, successful completions, exact response bytes, and duplicate
count. The pcap SHA-256 is:

    194a4b2619e0bddcdeef2108b0969cf13c029b3d2516309123c6567437b2922d

Postflight restored usbmon to absent, left the expected serial at sysfs 3-1
with interfaces 0 through 4 on snd-usb-audio and 5 through 6 unclaimed, left
no capture/Wine/UC process, and did not change the protected prefix.

This checkpoint authorizes no further live operation. Continue offline only:
contract an exact-tuple captured response and fail closed for all other class
requests, select-interface operations, writes, and broader behavior.
