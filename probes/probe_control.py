#!/usr/bin/env python3
"""
Non-destructive control-channel probe for the io24 vendor interface (5).

Two safe experiments:
  A) Clear any halt/stall on the bulk endpoints, then retry the UCNET handshake.
     A stalled IN endpoint is a common reason a device never "replies".
  B) Sweep READ-ONLY vendor control-IN requests (GET-style, host<-device) to see
     which the device answers. This maps the control model and narrows what an
     eventual enable-write must look like. No state is changed by IN transfers.

Nothing here writes device state. No bulk enable-writes, no DFU.
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
    um=header(did); um+=struct.pack("<H",0); um=finalize(um,"UM")
    j=json.dumps(SUBSCRIBE,separators=(",",":")); jm=header(did)
    jm+=struct.pack("<I",len(j)); jm+=j.encode(); jm=finalize(jm,"JM")
    return um+jm

def hexd(b):
    b=bytes(b); return " ".join(f"{x:02x}" for x in b)+"  |"+"".join(chr(x) if 32<=x<127 else "." for x in b)+"|"

def drain(ep, seconds, tag):
    frames=[]; end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            d=ep.read(512,timeout=300)
            if d: frames.append(bytes(d)); print(f"    [{tag}] RX {hexd(d)}")
        except usb.core.USBTimeoutError: pass
        except usb.core.USBError as e: print(f"    [{tag}] read err: {e}"); break
    return frames

def main():
    dev=usb.core.find(idVendor=VID,idProduct=PID)
    usb.util.claim_interface(dev,IFACE)
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
    intf=dev.get_active_configuration()[(IFACE,1)]
    ep_in=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_IN)
    ep_out=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_OUT)

    # ---- Experiment A: clear halts, retry handshake ----
    print("=== A: clear endpoint halts, retry handshake ===")
    for ep_addr in (EP_IN, EP_OUT):
        try:
            dev.clear_halt(ep_addr); print(f"  cleared halt on 0x{ep_addr:02x}")
        except usb.core.USBError as e:
            print(f"  clear_halt 0x{ep_addr:02x}: {e}")
    ep_out.write(welcome(0x0066),timeout=1000)
    a_frames=drain(ep_in,2.0,"A")
    print(f"  A frames: {len(a_frames)}")

    # ---- Experiment B: read-only vendor control-IN sweep ----
    print("\n=== B: read-only vendor control-IN sweep (GET-style) ===")
    hits=[]
    # 0xC0 = IN|vendor|device, 0xC1 = IN|vendor|interface
    for bmreq in (0xC0, 0xC1):
        for breq in list(range(0x00,0x12)) + [0x40,0x49,0x55,0x60,0x80,0x81,0x85,0xA0,0xA1,0xB0,0xFE,0xFF]:
            for windex in ((0,) if bmreq==0xC0 else (IFACE,)):
                try:
                    ret=dev.ctrl_transfer(bmreq,breq,0,windex,64,timeout=300)
                    if ret is not None and len(ret)>0:
                        hits.append((bmreq,breq,windex,bytes(ret)))
                        print(f"  HIT rt=0x{bmreq:02x} req=0x{breq:02x} idx={windex} -> {hexd(ret)}")
                except usb.core.USBError:
                    pass  # STALL = unsupported, expected/safe
    print(f"  B hits: {len(hits)}")

    usb.util.release_interface(dev,IFACE)
    print("\n=== SUMMARY ===")
    print(f"A (handshake after halt-clear): {'REPLY!' if a_frames else 'silent'}")
    print(f"B (vendor control-IN reads answered): {len(hits)}")
    if not a_frames and not hits:
        print("Device answers neither bulk UCNET nor any vendor control-IN read.")
        print("The enable is almost certainly a specific control-OUT (state-changing).")

if __name__=="__main__":
    main()
