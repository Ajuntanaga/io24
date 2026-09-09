#!/usr/bin/env python3
"""
THE test: talk to the io24 over USB using the reverse-engineered bulk-command
protocol from dspusbdevice.dll (paesdk::BulkSubdeviceCmd).

Init (faithful to StartBulkPipes):
  - claim iface 5, set alt 1
  - QueryProtocolVersion : ctrl IN bmReqType=0xC1 bReq=0x00 wValue=0 wIndex=5 len=2  -> expect 01 00
  - QueryMaxLength(cmd)  : ctrl IN 0xC1 0x01 wValue=0 wIndex=5 len=4
  - QueryMaxLength(resp) : ctrl IN 0xC1 0x01 wValue=1 wIndex=5 len=4

Bulk command wrapper (8-byte header) around each UCNET frame:
  [0:2] uint16 totalLen = payloadLen + 8   (LE)
  [2]   protocolId  = 0x01
  [3]   messageCode = 0x01 (request) / 0x81 (response)
  [4]   uniqueId    (increment per command, skip 0)
  [5]   messageStatus = 0
  [6:8] reserved = 0
  [8:]  payload = UCNET frame
"""
import json, struct, time, sys
import usb.core, usb.util

VID, PID, IFACE, EP_OUT, EP_IN, FROM_ID = 0x194F, 0x0422, 5, 0x01, 0x81, 104
SUBSCRIBE = {"id":"Subscribe","clientName":"UC-Surface","clientInternalName":"ucremoteapp",
    "clientType":"CustomAPI","clientDescription":"CustomAPI for Revelator io24",
    "clientIdentifier":"661b1ece-b4d3-44b3-913c-d12964456f0b","clientOptions":"perm users",
    "clientEncoding":23117}

# ---- UCNET frame builders (from oddbear MessageWriter) ----
def uc_header(did):
    h=bytearray(b"UC"); h+=struct.pack("<H",256); h+=b"\x00\x00\x00\x00"
    h+=struct.pack("<H",FROM_ID); h+=struct.pack("<H",did); return h
def uc_finalize(d,t): d[4:6]=struct.pack("<H",len(d)-6); d[6:8]=t.encode(); return bytes(d)
def uc_um(did):
    return uc_finalize(uc_header(did)+struct.pack("<H",0),"UM")
def uc_jm(did):
    j=json.dumps(SUBSCRIBE,separators=(",",":"))
    return uc_finalize(uc_header(did)+struct.pack("<I",len(j))+j.encode(),"JM")

# ---- bulk-command wrapper ----
class Cmd:
    def __init__(self): self.uid=0
    def next_uid(self):
        self.uid=(self.uid+1)&0xff
        if self.uid==0: self.uid=1
        return self.uid
    def wrap(self, payload):
        total=len(payload)+8
        hdr=struct.pack("<H",total)+bytes([0x01,0x01,self.next_uid(),0x00])+b"\x00\x00"
        return hdr+payload

def hexd(b,limit=320):
    b=bytes(b); s=b[:limit]
    return "[%d] %s |%s|%s" % (len(b), " ".join("%02x"%x for x in s),
        "".join(chr(x) if 32<=x<127 else "." for x in s),
        (" +%d"%(len(b)-limit)) if len(b)>limit else "")

def parse_resp(b):
    if len(b)<8: return None,"short(%d)"%len(b),b
    total,=struct.unpack("<H",b[0:2])
    pid,mcode,uid,status=b[2],b[3],b[4],b[5]
    payload=b[8:total] if total<=len(b) else b[8:]
    info="total=%d pid=0x%02x mcode=0x%02x uid=%d status=%d"%(total,pid,mcode,uid,status)
    return payload,info,b

def main():
    dev=usb.core.find(idVendor=VID,idProduct=PID)
    if dev is None: sys.exit("io24 not found")
    usb.util.claim_interface(dev,IFACE)
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
    intf=dev.get_active_configuration()[(IFACE,1)]
    ep_in=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_IN)
    ep_out=usb.util.find_descriptor(intf,custom_match=lambda e:e.bEndpointAddress==EP_OUT)

    print("=== init queries ===")
    pv=dev.ctrl_transfer(0xC1,0x00,0,IFACE,2,timeout=1000)
    print("  QueryProtocolVersion -> %s (expect 01 00)"%" ".join("%02x"%x for x in pv))
    mc=dev.ctrl_transfer(0xC1,0x01,0,IFACE,4,timeout=1000)
    mr=dev.ctrl_transfer(0xC1,0x01,1,IFACE,4,timeout=1000)
    print("  MaxCommandLength  -> %s"%" ".join("%02x"%x for x in mc))
    print("  MaxResponseLength -> %s"%" ".join("%02x"%x for x in mr))

    cmd=Cmd()
    def drain(tag, seconds=2.0):
        got=[]; end=time.monotonic()+seconds
        while time.monotonic()<end:
            try:
                d=ep_in.read(2048,timeout=400)
            except usb.core.USBTimeoutError: continue
            except usb.core.USBError as e: print("  [%s] read err %s"%(tag,e)); break
            if d:
                payload,info,raw=parse_resp(bytes(d))
                uc = payload[:2]==b"UC" if payload else False
                print("  [%s] RX %s"%(tag,info))
                print("       raw %s"%hexd(raw))
                if payload:
                    print("       payload %s%s"%(hexd(payload), "   <<< UCNET!" if uc else ""))
                got.append(bytes(d))
        return got

    for did in (0x0066, 0x006b, 0x0000):
        print("\n=== deviceId 0x%04x : wrapped UM+JM subscribe ==="%did)
        for frame,name in ((uc_um(did),"UM"),(uc_jm(did),"JM")):
            wrapped=cmd.wrap(frame)
            print("  TX %s: %s"%(name,hexd(wrapped)))
            try: ep_out.write(wrapped,timeout=1000)
            except usb.core.USBError as e: print("  write err %s"%e)
        frames=drain("did=0x%04x"%did, 2.5)
        if frames:
            print("  *** RESPONSE RECEIVED for did=0x%04x ***"%did); break

    usb.util.release_interface(dev,IFACE)

if __name__=="__main__":
    main()
