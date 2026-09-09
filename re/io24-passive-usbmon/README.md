# io24 passive usbmon evidence

This directory receives bounded, control-URB-only usbmon captures made while
the user physically reconnects the owned PreSonus Revelator IO 24. The capture
wrapper does not open the io24 device node, detach or claim an interface, write
USB or sysfs state, or start Universal Control.

Each run has a unique directory and records its preflight, kernel USB events,
tcpdump filter, pcap, postflight, module restoration, and SHA-256 manifest.
Do not start a capture or reconnect the device without explicit authorization.
