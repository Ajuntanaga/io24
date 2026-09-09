#!/usr/bin/env python3
"""
Probe the PreSonus Revelator io24 vendor-specific control interface (interface 5).

Phase 1 of reverse-engineering the control protocol: claim the vendor bulk
interface and passively read the IN endpoint while the user physically works the
device (twist encoders, press buttons). If the device pushes unsolicited state,
we capture raw frames here and check for the UCNET magic ("UC\\x00\\x01").

Read-only: we never write to the device in this script, and we never touch
interface 6 (DFU / firmware).
"""
import sys
import time
import usb.core
import usb.util

VID, PID = 0x194F, 0x0422
CONTROL_IFACE = 5
READ_SECONDS = 20


def hexdump(data):
    b = bytes(data)
    hexs = " ".join(f"{x:02x}" for x in b)
    ascii_ = "".join(chr(x) if 32 <= x < 127 else "." for x in b)
    return f"[{len(b):3d}] {hexs}    |{ascii_}|"


def main():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("Device 194f:0422 not found. Is the io24 plugged in?")

    print(f"Found io24 at bus {dev.bus} addr {dev.address}\n")

    # Enumerate interface 5's alt settings + endpoints (diagnostic).
    in_ep = out_ep = None
    chosen_alt = None
    cfg = dev.get_active_configuration()
    for intf in cfg:
        if intf.bInterfaceNumber != CONTROL_IFACE:
            continue
        print(f"interface {intf.bInterfaceNumber} alt {intf.bAlternateSetting} "
              f"class={intf.bInterfaceClass} endpoints={intf.bNumEndpoints}")
        for ep in intf:
            direction = "IN " if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN else "OUT"
            print(f"    ep 0x{ep.bEndpointAddress:02x} {direction} "
                  f"type={usb.util.endpoint_type(ep.bmAttributes)} "
                  f"maxpkt={ep.wMaxPacketSize}")
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                if in_ep is None:
                    in_ep, chosen_alt = ep, intf.bAlternateSetting
            else:
                out_ep = out_ep or ep
    print()

    if in_ep is None:
        sys.exit("No IN endpoint found on interface 5 — unexpected, stop and report this.")

    # Claim interface 5. It has no kernel driver, so no detach needed.
    try:
        usb.util.claim_interface(dev, CONTROL_IFACE)
    except usb.core.USBError as e:
        sys.exit(f"Could not claim interface {CONTROL_IFACE}: {e}\n"
                 "If this is a permission error, the udev rule isn't active yet.")

    if chosen_alt:
        try:
            dev.set_interface_altsetting(interface=CONTROL_IFACE, alternate_setting=chosen_alt)
        except usb.core.USBError:
            pass

    print(f"Claimed interface {CONTROL_IFACE}. Reading ep 0x{in_ep.bEndpointAddress:02x} "
          f"for {READ_SECONDS}s.\n>>> WORK THE DEVICE NOW: twist every knob, press every button. <<<\n")

    deadline = time.monotonic() + READ_SECONDS
    frames = 0
    saw_uc = False
    while time.monotonic() < deadline:
        try:
            data = in_ep.read(in_ep.wMaxPacketSize, timeout=500)
        except usb.core.USBTimeoutError:
            continue
        except usb.core.USBError as e:
            print(f"read error: {e}")
            break
        if not data:
            continue
        frames += 1
        b = bytes(data)
        if b"UC\x00\x01" in b or b.startswith(b"UC"):
            saw_uc = True
        print(hexdump(b))

    usb.util.release_interface(dev, CONTROL_IFACE)
    print(f"\nDone. {frames} frame(s) captured.")
    if saw_uc:
        print("*** UCNET MAGIC 'UC' SEEN — Architecture B confirmed. ***")
    elif frames == 0:
        print("No unsolicited traffic. Device likely needs an init/subscribe frame "
              "before it emits state. Next step: active handshake probe.")
    else:
        print("Got frames but no 'UC' magic yet — inspect the bytes above.")


if __name__ == "__main__":
    main()
