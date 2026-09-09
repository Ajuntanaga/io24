#!/usr/bin/env python3
"""
Second-pass handshake probe: rule out timing / keepalive / write-failure as the
reason interface 5 stays silent. Verifies bytes actually leave the OUT endpoint,
sustains keepalives, reads for a long window, and tries JM-only as well as UM+JM.
"""
import json, struct, time, threading
import usb.core, usb.util

VID, PID, IFACE, EP_OUT, EP_IN, FROM_ID = 0x194F, 0x0422, 5, 0x01, 0x81, 104
SUBSCRIBE = {"id":"Subscribe","clientName":"UC-Surface","clientInternalName":"ucremoteapp",
    "clientType":"CustomAPI","clientDescription":"CustomAPI for Revelator io24",
    "clientIdentifier":"661b1ece-b4d3-44b3-913c-d12964456f0b","clientOptions":"perm users",
    "clientEncoding":23117}

def header(did):
    h = bytearray(b"UC"); h += struct.pack("<H",256); h += b"\x00\x00\x00\x00"
    h += struct.pack("<H",FROM_ID); h += struct.pack("<H",did); return h
def finalize(d,t): d[4:6]=struct.pack("<H",len(d)-6); d[6:8]=t.encode(); return bytes(d)
def um(did,mp=0):
    d=header(did); d+=struct.pack("<H",mp); return finalize(d,"UM")
def jm(did):
    j=json.dumps(SUBSCRIBE,separators=(",",":")); d=header(did)
    d+=struct.pack("<I",len(j)); d+=j.encode(); return finalize(d,"JM")
def ka(did): return finalize(header(did),"KA")

def hexd(b,limit=200):
    b=bytes(b); s=b[:limit]
    return f"[{len(b):4d}] "+" ".join(f"{x:02x}" for x in s)+"  |"+"".join(chr(x) if 32<=x<127 else "." for x in s)+"|"

def main():
    dev=usb.core.find(idVendor=VID,idProduct=PID)
    usb.util.claim_interface(dev,IFACE)
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
    intf=dev.get_active_configuration()[(IFACE,1)]
    ep_in=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_IN)
    ep_out=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_OUT)

    stop=threading.Event(); got=[]
    def reader():
        while not stop.is_set():
            try:
                d=ep_in.read(512,timeout=300)
                if d:
                    b=bytes(d); got.append(b)
                    print(f"  RX {hexd(b)}")
            except usb.core.USBTimeoutError: pass
            except usb.core.USBError as e:
                print(f"  read err: {e}"); break
    rt=threading.Thread(target=reader,daemon=True); rt.start()

    for did in (0x0066, 0x006b):
        print(f"\n=== deviceId 0x{did:04x} ===")
        n=ep_out.write(um(did),timeout=1000); print(f"  wrote UM: {n} bytes")
        n=ep_out.write(jm(did),timeout=1000); print(f"  wrote JM: {n} bytes")
        # sustain keepalives for 6s
        t_end=time.monotonic()+6
        while time.monotonic()<t_end:
            ep_out.write(ka(did),timeout=1000); time.sleep(0.25)
        print(f"  frames so far: {len(got)}")

    # JM-only, fresh id
    print("\n=== JM-only, id 0x0000 ===")
    print(f"  wrote JM: {ep_out.write(jm(0),timeout=1000)} bytes")
    time.sleep(2)

    stop.set(); rt.join(timeout=1)
    usb.util.release_interface(dev,IFACE)
    print(f"\n=== TOTAL frames received: {len(got)} ===")
    if not got:
        print("Device is fully silent to UCNET on the bulk pipe. Missing a USB-level")
        print("enable/init that the Windows service performs. Ground-truth capture needed.")

if __name__=="__main__":
    main()
