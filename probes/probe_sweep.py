#!/usr/bin/env python3
"""
The device acks our wrapped UCNET subscribe but pushes no state -> the UCNET
subscribe is being accepted at transport level but ignored at session level,
most likely a wrong 'to' (server/device) id. Sweep candidate ids (and a
from/to-swapped variant) and watch for any non-empty pushed UCNET payload.
"""
import json, struct, time, sys
import usb.core, usb.util

VID,PID,IFACE,EP_OUT,EP_IN = 0x194F,0x0422,5,0x01,0x81
SUB = {"id":"Subscribe","clientName":"UC-Surface","clientInternalName":"ucremoteapp",
    "clientType":"CustomAPI","clientDescription":"CustomAPI for Revelator io24",
    "clientIdentifier":"661b1ece-b4d3-44b3-913c-d12964456f0b","clientOptions":"perm users",
    "clientEncoding":23117}

def uch(frm,to):
    h=bytearray(b"UC"); h+=struct.pack("<H",256); h+=b"\x00\x00\x00\x00"
    h+=struct.pack("<H",frm); h+=struct.pack("<H",to); return h
def ucf(d,t): d[4:6]=struct.pack("<H",len(d)-6); d[6:8]=t.encode(); return bytes(d)
def UM(frm,to): return ucf(uch(frm,to)+struct.pack("<H",0),"UM")
def JM(frm,to):
    j=json.dumps(SUB,separators=(",",":")); return ucf(uch(frm,to)+struct.pack("<I",len(j))+j.encode(),"JM")

def hexd(b,limit=500):
    b=bytes(b); s=b[:limit]
    return "[%d] %s |%s|"%(len(b)," ".join("%02x"%x for x in s),"".join(chr(x) if 32<=x<127 else "." for x in s))

class Dev:
    def __init__(s):
        s.dev=usb.core.find(idVendor=VID,idProduct=PID); usb.util.claim_interface(s.dev,IFACE)
        s.dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
        i=s.dev.get_active_configuration()[(IFACE,1)]
        s.i=usb.util.find_descriptor(i,custom_match=lambda e:e.bEndpointAddress==EP_IN)
        s.o=usb.util.find_descriptor(i,custom_match=lambda e:e.bEndpointAddress==EP_OUT)
        s.uid=0
        try: s.dev.clear_halt(EP_OUT); s.dev.clear_halt(EP_IN)
        except: pass
    def _u(s):
        s.uid=(s.uid+1)&0xff
        if s.uid==0: s.uid=1
        return s.uid
    def send(s,f):
        w=struct.pack("<H",len(f)+8)+bytes([1,1,s._u(),0,0,0])+f
        try: s.o.write(w,timeout=1500); return True
        except usb.core.USBError as e:
            print("   OUT err %s"%e)
            try: s.dev.clear_halt(EP_OUT)
            except: pass
            return False
    def read(s,to=600):
        try: d=s.i.read(2048,timeout=to)
        except usb.core.USBTimeoutError: return None
        except usb.core.USBError as e:
            try: s.dev.clear_halt(EP_IN)
            except: pass
            return None
        return bytes(d) if d else None

def payload(d): return d[8:] if len(d)>8 else b""

def main():
    dv=Dev()
    print("init: PV=%s"%bytes(dv.dev.ctrl_transfer(0xC1,0,0,IFACE,2)).hex())
    hit=None
    # (from,to) candidates. oddbear: from=104(0x68), to=deviceId.
    tos=[0x0000,0x0001,0x0066,0x0067,0x0068,0x0069,0x006a,0x006b,0x0064,0x0065,0x00ff,0x0100,0xffff]
    def trial(frm,to,label,send_um=True):
        nonlocal hit
        if send_um: dv.send(UM(frm,to))
        dv.send(JM(frm,to))
        end=time.monotonic()+1.6; nonempty=[]
        while time.monotonic()<end:
            d=dv.read(400)
            if d is None: continue
            p=payload(d)
            if p:  # non-empty push
                t=p[6:8].decode('ascii','replace') if len(p)>=8 and p[:2]==b"UC" else "?"
                print("   >>> %s: NON-EMPTY push UC/%s  %s"%(label,t,hexd(d)))
                nonempty.append(d)
        if nonempty and hit is None: hit=label
        print("   %s: %d non-empty pushes"%(label,len(nonempty)))

    print("\n=== sweep to (from=104) ===")
    for to in tos:
        trial(104,to,"from=104 to=0x%04x"%to)
        if hit: break
    if not hit:
        print("\n=== swapped from/to (from=deviceId to=104) ===")
        for frm in (0x0066,0x006b,0x0068,0x0000):
            trial(frm,104,"from=0x%04x to=104"%frm)
            if hit: break
    if not hit:
        print("\n=== JM-only (no UM), from=104 ===")
        for to in (0x0066,0x006b,0x0000):
            trial(104,to,"JMonly to=0x%04x"%to,send_um=False)
            if hit: break

    usb.util.release_interface(dv.dev,IFACE)
    print("\n=== RESULT: %s ==="%(("state push from "+hit) if hit else "no push on any candidate"))

if __name__=="__main__":
    main()
