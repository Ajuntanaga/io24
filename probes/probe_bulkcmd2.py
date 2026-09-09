#!/usr/bin/env python3
"""
Follow-up: we confirmed the bulk-command framing (device acks with mcode=0x81).
Now drive a full subscribe and collect the device's UCNET state stream.

Sends wrapped UM + JM(subscribe), then continuously reads the bulk IN pipe,
unwrapping each 8-byte bulk-command header and printing the UCNET payload.
A wrapped KA (keepalive) is sent every ~1s to keep the session alive.
"""
import json, struct, time, sys
import usb.core, usb.util

VID, PID, IFACE, EP_OUT, EP_IN, FROM_ID = 0x194F, 0x0422, 5, 0x01, 0x81, 104
SUBSCRIBE = {"id":"Subscribe","clientName":"UC-Surface","clientInternalName":"ucremoteapp",
    "clientType":"CustomAPI","clientDescription":"CustomAPI for Revelator io24",
    "clientIdentifier":"661b1ece-b4d3-44b3-913c-d12964456f0b","clientOptions":"perm users",
    "clientEncoding":23117}

def uc_header(did):
    h=bytearray(b"UC"); h+=struct.pack("<H",256); h+=b"\x00\x00\x00\x00"
    h+=struct.pack("<H",FROM_ID); h+=struct.pack("<H",did); return h
def uc_finalize(d,t): d[4:6]=struct.pack("<H",len(d)-6); d[6:8]=t.encode(); return bytes(d)
def uc_um(did): return uc_finalize(uc_header(did)+struct.pack("<H",0),"UM")
def uc_jm(did):
    j=json.dumps(SUBSCRIBE,separators=(",",":"))
    return uc_finalize(uc_header(did)+struct.pack("<I",len(j))+j.encode(),"JM")
def uc_ka(did): return uc_finalize(uc_header(did),"KA")

class Cmd:
    def __init__(self): self.uid=0
    def _n(self):
        self.uid=(self.uid+1)&0xff
        if self.uid==0: self.uid=1
        return self.uid
    def wrap(self,p):
        return struct.pack("<H",len(p)+8)+bytes([1,1,self._n(),0,0,0])+p

def hexd(b,limit=400):
    b=bytes(b); s=b[:limit]
    return "[%d] %s |%s|%s"%(len(b)," ".join("%02x"%x for x in s),
        "".join(chr(x) if 32<=x<127 else "." for x in s),(" +%d"%(len(b)-limit)) if len(b)>limit else "")

def uctype(p):
    return p[6:8].decode('ascii','replace') if len(p)>=8 and p[:2]==b"UC" else "?"

def main():
    dev=usb.core.find(idVendor=VID,idProduct=PID)
    if dev is None: sys.exit("not found")
    usb.util.claim_interface(dev,IFACE)
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
    intf=dev.get_active_configuration()[(IFACE,1)]
    ep_in=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_IN)
    ep_out=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_OUT)

    did=0x0066
    cmd=Cmd()
    def send(frame,name):
        w=cmd.wrap(frame); ep_out.write(w,timeout=1000)
        print("TX %-3s uid=%d (%d payload bytes)"%(name,cmd.uid,len(frame)))
    def read_one(timeout=500):
        try: d=ep_in.read(2048,timeout=timeout)
        except usb.core.USBTimeoutError: return None
        except usb.core.USBError as e: print("read err",e); return None
        return bytes(d) if d else None

    print("=== subscribe ===")
    send(uc_um(did),"UM"); send(uc_jm(did),"JM")

    print("=== reading state stream (8s, KA every 1s) ===")
    end=time.monotonic()+8.0; last_ka=time.monotonic()
    uc_count=0; total_payload=0; ids_seen=set()
    while time.monotonic()<end:
        d=read_one(400)
        if d is not None:
            total,=struct.unpack("<H",d[0:2]) if len(d)>=2 else (0,)
            pid=d[2] if len(d)>2 else 0; mcode=d[3] if len(d)>3 else 0
            uid=d[4] if len(d)>4 else 0; status=d[5] if len(d)>5 else 0
            payload=d[8:] if len(d)>8 else b""
            t=uctype(payload)
            if payload and payload[:2]==b"UC":
                uc_count+=1; total_payload+=len(payload)
                # try to surface JSON id if JM
                extra=""
                if t=="JM":
                    try:
                        js=payload[16:].split(b"\x00")[0].decode("ascii","replace")
                        extra=" json="+js[:120]
                    except: pass
                print("RX mcode=0x%02x uid=%d status=%d UCtype=%s len=%d%s"%(mcode,uid,status,t,len(payload),extra))
                ids_seen.add(t)
            else:
                print("RX mcode=0x%02x uid=%d status=%d (empty/ack, total=%d)"%(mcode,uid,status,total))
        if time.monotonic()-last_ka>1.0:
            send(uc_ka(did),"KA"); last_ka=time.monotonic()

    usb.util.release_interface(dev,IFACE)
    print("\n=== SUMMARY ===")
    print("UCNET payload frames: %d, total %d bytes, UC message types seen: %s"%(uc_count,total_payload,sorted(ids_seen)))
    if uc_count>0:
        print("*** FULL DUPLEX UCNET-OVER-USB WORKING. oddbear protocol now drives the io24 on Linux. ***")

if __name__=="__main__":
    main()
