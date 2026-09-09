#!/usr/bin/env python3
"""
Synchronous bulk-command driver for the io24 (matches paesdk::ExecuteCommand:
send ONE command, poll the IN pipe for the matching-uniqueId response, then send
the next). Pipelining jams the OUT pipe, so we never have >1 command outstanding.

Flow: UM(welcome) -> JM(subscribe) -> collect the pushed UCNET state -> KA loop.
"""
import json, struct, time, sys
import usb.core, usb.util

VID, PID, IFACE, EP_OUT, EP_IN, FROM_ID = 0x194F, 0x0422, 5, 0x01, 0x81, 104
SUBSCRIBE = {"id":"Subscribe","clientName":"UC-Surface","clientInternalName":"ucremoteapp",
    "clientType":"CustomAPI","clientDescription":"CustomAPI for Revelator io24",
    "clientIdentifier":"661b1ece-b4d3-44b3-913c-d12964456f0b","clientOptions":"perm users",
    "clientEncoding":23117}

def uch(did):
    h=bytearray(b"UC"); h+=struct.pack("<H",256); h+=b"\x00\x00\x00\x00"
    h+=struct.pack("<H",FROM_ID); h+=struct.pack("<H",did); return h
def ucf(d,t): d[4:6]=struct.pack("<H",len(d)-6); d[6:8]=t.encode(); return bytes(d)
def UM(did): return ucf(uch(did)+struct.pack("<H",0),"UM")
def JM(did):
    j=json.dumps(SUBSCRIBE,separators=(",",":"))
    return ucf(uch(did)+struct.pack("<I",len(j))+j.encode(),"JM")
def KA(did): return ucf(uch(did),"KA")

def hexd(b,limit=600):
    b=bytes(b); s=b[:limit]
    return "[%d] %s |%s|%s"%(len(b)," ".join("%02x"%x for x in s),
        "".join(chr(x) if 32<=x<127 else "." for x in s),(" +%d"%(len(b)-limit)) if len(b)>limit else "")

class Dev:
    def __init__(self):
        self.dev=usb.core.find(idVendor=VID,idProduct=PID)
        if self.dev is None: sys.exit("not found")
        usb.util.claim_interface(self.dev,IFACE)
        self.dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
        intf=self.dev.get_active_configuration()[(IFACE,1)]
        self.ep_in=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_IN)
        self.ep_out=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_OUT)
        self.uid=0
        try: self.dev.clear_halt(EP_OUT); self.dev.clear_halt(EP_IN)
        except: pass
    def _uid(self):
        self.uid=(self.uid+1)&0xff
        if self.uid==0: self.uid=1
        return self.uid
    def send(self,frame):
        u=self._uid()
        w=struct.pack("<H",len(frame)+8)+bytes([1,1,u,0,0,0])+frame
        try:
            self.ep_out.write(w,timeout=1500)
        except usb.core.USBError as e:
            print("  OUT err (%s) -> clear_halt"%e)
            try: self.dev.clear_halt(EP_OUT)
            except: pass
            return None
        return u
    def read(self,timeout=800):
        try: d=self.ep_in.read(2048,timeout=timeout)
        except usb.core.USBTimeoutError: return None
        except usb.core.USBError as e:
            print("  IN err (%s) -> clear_halt"%e)
            try: self.dev.clear_halt(EP_IN)
            except: pass
            return None
        return bytes(d) if d else None
    def parse(self,d):
        total,=struct.unpack("<H",d[0:2]); pid,mcode,uid,status=d[2],d[3],d[4],d[5]
        payload=d[8:total] if 8<=total<=len(d) else d[8:]
        return dict(total=total,pid=pid,mcode=mcode,uid=uid,status=status,payload=payload)

def uctype(p): return p[6:8].decode('ascii','replace') if len(p)>=8 and p[:2]==b"UC" else "?"

def main():
    dv=Dev()
    did=0x0066

    def command(frame,name,collect_secs=2.5):
        u=dv.send(frame)
        if u is None: print("TX %s FAILED"%name); return []
        print("TX %-3s uid=%d (%d payload)"%(name,u,len(frame)))
        out=[]; end=time.monotonic()+collect_secs
        while time.monotonic()<end:
            d=dv.read(700)
            if d is None: continue
            r=dv.parse(d); out.append(r)
            p=r["payload"]; t=uctype(p)
            if p and p[:2]==b"UC":
                desc=""
                if t in ("JM","ZM"):
                    try: desc=" :: "+p[16 if t=="JM" else 12:].split(b"\x00")[0].decode("ascii","replace")[:200]
                    except: pass
                print("  RX uid=%d st=%d  UC/%s len=%d%s"%(r["uid"],r["status"],t,len(p),desc))
                if t in ("PS","PV"):
                    try: print("       route=%s"%p[12:].split(b"\x00")[0].decode("ascii","replace"))
                    except: pass
            else:
                print("  RX uid=%d st=%d  (ack total=%d)"%(r["uid"],r["status"],r["total"]))
        return out

    print("=== 1) UM welcome ==="); command(UM(did),"UM",1.5)
    print("=== 2) JM subscribe (collect state) ==="); st=command(JM(did),"JM",4.0)
    print("=== 3) KA keepalive x2 ===")
    for _ in range(2): command(KA(did),"KA",1.5)

    # collect all UC payloads seen
    allp=[r for r in st if r["payload"][:2]==b"UC"]
    types={}
    for r in st:
        p=r["payload"]
        if p[:2]==b"UC":
            t=uctype(p); types[t]=types.get(t,0)+1
    usb.util.release_interface(dv.dev,IFACE)
    print("\n=== SUMMARY ===")
    print("UCNET frames from subscribe: %d  types=%s"%(len(allp),types))
    if allp:
        print("*** UCNET-over-USB duplex confirmed. Dumping first few payloads: ***")
        for r in allp[:6]:
            print(hexd(r["payload"]))

if __name__=="__main__":
    main()
