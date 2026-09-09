#!/usr/bin/env python3
"""
Deeper READ-ONLY map of the io24 vendor control interface (5).
Still non-destructive: only IN (GET) control transfers + a bulk read attempt.

1) Issue the two known-good GETs, then try the UCNET handshake (did GETs arm it?).
2) Full safe read map: rt in {0xC0 device, 0xC1 interface}, bRequest 0x00..0x1F,
   wValue in {0,1}, wLength 256 — log every response so we can read the control model.
"""
import json, struct, time
import usb.core, usb.util

VID, PID, IFACE, EP_OUT, EP_IN, FROM_ID = 0x194F, 0x0422, 5, 0x01, 0x81, 104
SUBSCRIBE = {"id":"Subscribe","clientName":"UC-Surface","clientInternalName":"ucremoteapp",
    "clientType":"CustomAPI","clientDescription":"CustomAPI for Revelator io24",
    "clientIdentifier":"661b1ece-b4d3-44b3-913c-d12964456f0b","clientOptions":"perm users",
    "clientEncoding":23117}
def header(did):
    h=bytearray(b"UC"); h+=struct.pack("<H",256); h+=b"\x00\x00\x00\x00"
    h+=struct.pack("<H",FROM_ID); h+=struct.pack("<H",did); return h
def finalize(d,t): d[4:6]=struct.pack("<H",len(d)-6); d[6:8]=t.encode(); return bytes(d)
def welcome(did):
    um=finalize(header(did)+struct.pack("<H",0),"UM")
    j=json.dumps(SUBSCRIBE,separators=(",",":"))
    jm=finalize(header(did)+struct.pack("<I",len(j))+j.encode(),"JM"); return um+jm
def hexd(b):
    b=bytes(b); return " ".join(f"{x:02x}" for x in b)+"  |"+"".join(chr(x) if 32<=x<127 else "." for x in b)+"|"

def main():
    dev=usb.core.find(idVendor=VID,idProduct=PID)
    usb.util.claim_interface(dev,IFACE)
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
    intf=dev.get_active_configuration()[(IFACE,1)]
    ep_in=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_IN)
    ep_out=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_OUT)

    print("=== 1: known GETs, then handshake ===")
    for req in (0x00,0x01):
        r=dev.ctrl_transfer(0xC1,req,0,IFACE,256,timeout=400)
        print(f"  GET req=0x{req:02x} -> {hexd(r)}")
    ep_out.write(welcome(0x0066),timeout=1000)
    frames=[]; end=time.monotonic()+2.0
    while time.monotonic()<end:
        try:
            d=ep_in.read(512,timeout=300)
            if d: frames.append(bytes(d)); print(f"  RX {hexd(d)}")
        except usb.core.USBTimeoutError: pass
        except usb.core.USBError as e: print(f"  read err {e}"); break
    print(f"  handshake-after-GET frames: {len(frames)}")

    print("\n=== 2: full read-only map ===")
    for bmreq,label in ((0xC0,"dev"),(0xC1,"if")):
        for wval in (0,1):
            for breq in range(0x00,0x20):
                widx = 0 if bmreq==0xC0 else IFACE
                try:
                    r=dev.ctrl_transfer(bmreq,breq,wval,widx,256,timeout=250)
                    if r is not None and len(r)>0:
                        print(f"  rt=0x{bmreq:02x}({label}) req=0x{breq:02x} wVal={wval} -> [{len(r)}] {hexd(r)}")
                except usb.core.USBError:
                    pass
    usb.util.release_interface(dev,IFACE)

if __name__=="__main__":
    main()
