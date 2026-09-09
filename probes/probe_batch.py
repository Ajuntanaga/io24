#!/usr/bin/env python3
"""
Batched write-probe for the native 'set' format, with a binary-search protocol.
Enumerates framing x value-encoding combos for a route (default main/ch1/mute) and
sends a chosen subset as mute-ON (value=1) or mute-OFF (value=0). If the tone mutes
after an ON batch, the working combo is in that subset -> narrow by halves.

Usage: probe_batch.py on|off [startIdx endIdx] [route]
"""
import struct, time, sys
import usb.core, usb.util

VID,PID,IFACE,EP_OUT,EP_IN,FROM_ID=0x194F,0x0422,5,0x01,0x81,104

# value encodings: (name, on_bytes, off_bytes)
VALS=[("f32",struct.pack("<f",1.0),struct.pack("<f",0.0)),
      ("i32",struct.pack("<i",1),struct.pack("<i",0)),
      ("i8", b"\x01",b"\x00"),
      ("i16",struct.pack("<h",1),struct.pack("<h",0))]
# framing shapes: fn(route_bytes, value_bytes) -> payload
FRAMES=[("s1_r000v", lambda rb,vb: rb+b"\x00\x00\x00"+vb),
        ("s2_r0v",   lambda rb,vb: rb+b"\x00"+vb),
        ("s3_PVr000v",lambda rb,vb: b"PV"+rb+b"\x00\x00\x00"+vb),
        ("s4_rv",    lambda rb,vb: rb+vb),
        ("s5_0r0v",  lambda rb,vb: b"\x00"+rb+b"\x00"+vb),
        ("s6_r0000v",lambda rb,vb: rb+b"\x00\x00\x00\x00"+vb)]

def combos(route):
    rb=route.encode("ascii"); out=[]
    for fi,(fn,ff) in enumerate(FRAMES):
        for vi,(vn,onb,offb) in enumerate(VALS):
            out.append(("%s/%s"%(fn,vn), ff(rb,onb), ff(rb,offb)))
    return out

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
        s.dev.ctrl_transfer(0xC1,0,0,IFACE,2); s.dev.ctrl_transfer(0xC1,1,0,IFACE,4); s.dev.ctrl_transfer(0xC1,1,1,IFACE,4)
    def _u(s):
        s.uid=(s.uid+1)&0xff; return s.uid if s.uid else s._u()
    def send(s,payload):
        u=s._u(); w=struct.pack("<H",len(payload)+8)+bytes([1,1,u,0,0,0])+payload
        try: s.o.write(w,timeout=1200)
        except usb.core.USBError:
            try: s.dev.clear_halt(EP_OUT)
            except: pass
            return
        end=time.monotonic()+0.25
        while time.monotonic()<end:
            try: s.i.read(2048,timeout=150)
            except usb.core.USBTimeoutError: break
            except usb.core.USBError: break

def main():
    mode=sys.argv[1] if len(sys.argv)>1 else "on"
    route="main/ch1/mute"; s_i=0; e_i=None
    args=sys.argv[2:]
    if args and args[0].lstrip("-").isdigit():
        s_i=int(args[0]); e_i=int(args[1]); args=args[2:]
    if args: route=args[0]
    cb=combos(route)
    if e_i is None: e_i=len(cb)-1
    dv=Dev()
    print("route=%s  mode=%s  combos[%d..%d] of %d"%(route,mode,s_i,e_i,len(cb)))
    for idx in range(s_i,e_i+1):
        name,onb,offb=cb[idx]
        dv.send(onb if mode=="on" else offb)
        print("  [%2d] %-14s %s"%(idx,name,"ON" if mode=="on" else "OFF"))
    usb.util.release_interface(dv.dev,IFACE)
    print("done. (if mode=on and tone muted -> working combo is in this index range)")

if __name__=="__main__":
    main()
