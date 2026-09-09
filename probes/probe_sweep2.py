#!/usr/bin/env python3
"""
Clean STRICT-synchronous 'to' sweep (previous sweep was invalid: pipelined -> OUT
jam). For each candidate 'to' deviceId: send UM, read its ack; send JM subscribe,
read its ack AND collect any pushed UCNET state for ~1.5s. Decisive test of
payload==UCNET (some 'to' triggers state) vs native (nothing ever does).
"""
import json, struct, time, sys
import usb.core, usb.util

VID,PID,IFACE,EP_OUT,EP_IN=0x194F,0x0422,5,0x01,0x81
SUB={"id":"Subscribe","clientName":"UC-Surface","clientInternalName":"ucremoteapp",
    "clientType":"CustomAPI","clientDescription":"CustomAPI for Revelator io24",
    "clientIdentifier":"661b1ece-b4d3-44b3-913c-d12964456f0b","clientOptions":"perm users",
    "clientEncoding":23117}
def uch(frm,to):
    h=bytearray(b"UC"); h+=struct.pack("<H",256); h+=b"\x00\x00\x00\x00"; h+=struct.pack("<H",frm); h+=struct.pack("<H",to); return h
def ucf(d,t): d[4:6]=struct.pack("<H",len(d)-6); d[6:8]=t.encode(); return bytes(d)
def UM(frm,to): return ucf(uch(frm,to)+struct.pack("<H",0),"UM")
def JM(frm,to):
    j=json.dumps(SUB,separators=(",",":")); return ucf(uch(frm,to)+struct.pack("<I",len(j))+j.encode(),"JM")

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
        return s.uid if s.uid else s._u()
    def cmd(s,frame,collect=1.2):
        """strict: send one command, read its ack, keep collecting pushes; return non-empty payloads."""
        u=s._u(); w=struct.pack("<H",len(frame)+8)+bytes([1,1,u,0,0,0])+frame
        try: s.o.write(w,timeout=1500)
        except usb.core.USBError:
            try: s.dev.clear_halt(EP_OUT)
            except: pass
            return None,[]
        pushes=[]; end=time.monotonic()+collect; ack=False
        while time.monotonic()<end:
            try: d=s.i.read(2048,timeout=400)
            except usb.core.USBTimeoutError:
                if ack: break   # got our ack and nothing more
                continue
            except usb.core.USBError:
                try: s.dev.clear_halt(EP_IN)
                except: pass
                break
            if not d: continue
            d=bytes(d); payload=d[8:] if len(d)>8 else b""
            if len(d)>4 and d[4]==u and not payload: ack=True    # empty ack for our cmd
            elif payload: pushes.append(d)
        return u,pushes

def main():
    dv=Dev()
    print("PV=",bytes(dv.dev.ctrl_transfer(0xC1,0,0,IFACE,2)).hex())
    hit=None
    tos=[0,1,2,0x64,0x65,0x66,0x67,0x68,0x69,0x6a,0x6b,0x70,0x80,0xff,0x100,0x194f,0x422,0xffff]
    for to in tos:
        dv.cmd(UM(104,to),0.8)
        _,pushes=dv.cmd(JM(104,to),1.4)
        tag="to=0x%04x"%to
        if pushes:
            print("  %s: %d PUSHES <<<"%(tag,len(pushes)))
            for d in pushes[:3]:
                p=d[8:]; t=p[6:8].decode('ascii','replace') if len(p)>=8 and p[:2]==b"UC" else "?"
                print("     UC/%s %s"%(t," ".join("%02x"%x for x in d[:48])))
            hit=tag; break
        else:
            print("  %s: ack only"%tag)
    # also JM-only, strict
    if not hit:
        print("--- JM-only ---")
        for to in (0,0x66,0x6b):
            _,pushes=dv.cmd(JM(104,to),1.4)
            print("  JMonly to=0x%04x: %d pushes"%(to,len(pushes)))
            if pushes: hit="JMonly to=0x%04x"%to; break
    usb.util.release_interface(dv.dev,IFACE)
    print("\nRESULT:", ("STATE from "+hit+" -> payload IS UCNET") if hit else "no state on any 'to' -> payload is NOT plain UCNET (native protocol)")

if __name__=="__main__":
    main()
