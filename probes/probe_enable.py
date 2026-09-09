#!/usr/bin/env python3
"""
Curated enable-write probe for the io24 vendor control interface (5).

We found two readable vendor registers (rt=0xC1 req0->0x0001, req1->0x0800). The
bulk UCNET pipe is gated behind some control-OUT the Windows service issues. This
tries a SMALL, curated set of reversible control-OUT writes. After each write it:
  - re-reads the two known registers (a changed value => that write did something)
  - attempts the UCNET handshake and reads the bulk IN pipe (UCNET reply => WIN)

All writes are to the vendor CTRL interface, reversible by a USB unplug/replug.
Never touches interface 6 (DFU). Conservative bRequest/wValue/data only.
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
    b=bytes(b); return " ".join(f"{x:02x}" for x in b)

def read_regs(dev):
    out={}
    for req in (0x00,0x01):
        try: out[req]=bytes(dev.ctrl_transfer(0xC1,req,0,IFACE,256,timeout=300))
        except usb.core.USBError: out[req]=None
    return out

def try_handshake(ep_out, ep_in):
    try: ep_out.write(welcome(0x0066),timeout=1000)
    except usb.core.USBError as e: return ("writefail",str(e))
    frames=[]; end=time.monotonic()+1.5
    while time.monotonic()<end:
        try:
            d=ep_in.read(512,timeout=300)
            if d: frames.append(bytes(d))
        except usb.core.USBTimeoutError: pass
        except usb.core.USBError: break
    return ("ok",frames)

def main():
    dev=usb.core.find(idVendor=VID,idProduct=PID)
    usb.util.claim_interface(dev,IFACE)
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
    intf=dev.get_active_configuration()[(IFACE,1)]
    ep_in=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_IN)
    ep_out=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_OUT)

    base=read_regs(dev)
    print(f"baseline regs: req0={hexd(base[0]) if base[0] else None}  req1={hexd(base[1]) if base[1] else None}\n")

    # (bmRequestType, bRequest, wValue, wIndex, data)
    candidates = [
        (0x41,0x00,0x0001,IFACE,b''),
        (0x41,0x00,0x0000,IFACE,b'\x01'),
        (0x41,0x00,0x0001,IFACE,b'\x01'),
        (0x41,0x01,0x0001,IFACE,b''),
        (0x41,0x02,0x0001,IFACE,b''),
        (0x41,0x02,0x0000,IFACE,b''),
        (0x41,0x03,0x0001,IFACE,b''),
        (0x41,0x04,0x0001,IFACE,b''),
        (0x41,0x05,0x0001,IFACE,b''),
        (0x41,0x00,0x0001,IFACE,b'\x01\x00'),
        (0x40,0x00,0x0001,0,b''),
        (0x40,0x01,0x0001,0,b''),
        (0x42,0x00,0x0001,EP_OUT,b''),
        (0x42,0x00,0x0001,EP_IN,b''),
    ]

    win=None
    for (rt,req,wval,widx,data) in candidates:
        tag=f"rt=0x{rt:02x} req=0x{req:02x} wVal=0x{wval:04x} idx=0x{widx:02x} data={data.hex() or '-'}"
        try:
            dev.ctrl_transfer(rt,req,wval,widx,data,timeout=500)
            wr="written"
        except usb.core.USBError as e:
            print(f"  {tag}: STALL/err ({str(e).splitlines()[0]})")
            continue
        regs=read_regs(dev)
        changed=[f"req{r}:{hexd(base[r])}->{hexd(regs[r])}" for r in (0,1)
                 if base[r]!=regs[r] and regs[r] is not None]
        status,res=try_handshake(ep_out,ep_in)
        got = len(res) if status=="ok" else res
        note = f"  REGCHANGE {changed}" if changed else ""
        print(f"  {tag}: {wr}, bulk_frames={got}{note}")
        if status=="ok" and res:
            win=(tag,res);
            print("    *** BULK REPLY AFTER THIS WRITE ***")
            for f in res: print(f"      RX {hexd(f)}")
            break

    usb.util.release_interface(dev,IFACE)
    print("\n=== SUMMARY ===")
    print(f"WIN: {win[0] if win else 'none — no write unlocked the bulk pipe'}")

if __name__=="__main__":
    main()
