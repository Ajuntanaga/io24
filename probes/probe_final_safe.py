#!/usr/bin/env python3
"""
Final consolidated NON-destructive probe. New hypotheses only:
  a) Catch any device announcement emitted right after (re)selecting alt 1.
  b) Issue the two known GETs, then PASSIVELY read bulk IN (no write) — maybe the
     GET pair is itself the 'start' and the device then streams.
  c) Large-length control-IN reads (wLength=2048) in case a register streams state.
  d) alt 1 -> alt 0 -> alt 1 toggle, then read.
No writes to device state. Reversible. No DFU.
"""
import time
import usb.core, usb.util

VID, PID, IFACE, EP_OUT, EP_IN = 0x194F, 0x0422, 5, 0x01, 0x81
def hexd(b):
    b=bytes(b); return " ".join(f"{x:02x}" for x in b)

def read_bulk(ep_in, seconds, size=512, tag=""):
    frames=[]; end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            d=ep_in.read(size,timeout=300)
            if d: frames.append(bytes(d)); print(f"    [{tag}] RX[{len(d)}] {hexd(d)}")
        except usb.core.USBTimeoutError: pass
        except usb.core.USBError as e: print(f"    [{tag}] err {e}"); break
    return frames

def get_eps(dev):
    intf=dev.get_active_configuration()[(IFACE,1)]
    ep_in=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_IN)
    ep_out=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_OUT)
    return ep_in,ep_out

def main():
    dev=usb.core.find(idVendor=VID,idProduct=PID)
    usb.util.claim_interface(dev,IFACE)

    # (a) select alt 1, immediately read (catch post-config announcement)
    print("=== a: alt1 select, immediate read ===")
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
    ep_in,ep_out=get_eps(dev)
    read_bulk(ep_in,2.0,512,"a")

    # (b) known GETs then passive read (no write)
    print("=== b: GET req0/req1 then passive read (no write) ===")
    for req in (0x00,0x01):
        r=dev.ctrl_transfer(0xC1,req,0,IFACE,256,timeout=400)
        print(f"    GET req=0x{req:02x} -> {hexd(r)}")
    read_bulk(ep_in,3.0,512,"b")

    # (c) large-length control-IN reads
    print("=== c: large control-IN reads (wLength=2048) ===")
    for req in range(0x00,0x10):
        try:
            r=dev.ctrl_transfer(0xC1,req,0,IFACE,2048,timeout=300)
            if r is not None and len(r)>0:
                print(f"    req=0x{req:02x} -> [{len(r)}] {hexd(r)}")
        except usb.core.USBError: pass

    # (d) alt toggle 1->0->1 then read
    print("=== d: alt toggle 1->0->1, read ===")
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=0)
    time.sleep(0.2)
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
    ep_in,ep_out=get_eps(dev)
    read_bulk(ep_in,2.0,512,"d")

    usb.util.release_interface(dev,IFACE)
    print("\n=== done (all four hypotheses) ===")

if __name__=="__main__":
    main()
