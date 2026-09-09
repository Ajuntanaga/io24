#!/usr/bin/env python3
"""
Write-probe: try one native 'set' framing for main/ch1/mute. Sends mute=ON, holds
~3s (watch the io24 output meters drop), then mute=OFF to restore. Strict req/resp.
Usage: probe_write.py <framing:1-6> [route] [holdsecs]
"""
import struct, time, sys
import usb.core, usb.util

VID,PID,IFACE,EP_OUT,EP_IN,FROM_ID=0x194F,0x0422,5,0x01,0x81,104
framing=int(sys.argv[1]) if len(sys.argv)>1 else 1
route=(sys.argv[2] if len(sys.argv)>2 else "main/ch1/mute")
hold=float(sys.argv[3]) if len(sys.argv)>3 else 3.0

def uch(to):
    h=bytearray(b"UC"); h+=struct.pack("<H",256); h+=b"\x00\x00\x00\x00"
    h+=struct.pack("<H",FROM_ID); h+=struct.pack("<H",to); return h
def ucf(d,t): d[4:6]=struct.pack("<H",len(d)-6); d[6:8]=t.encode(); return bytes(d)

def build(fr, route, value):
    rb=route.encode("ascii"); val=struct.pack("<f",value)
    if fr==1: return ucf(bytearray(uch(0x0066))+rb+b"\x00\x00\x00"+val,"PV")      # full UCNET PV, to=0x66
    if fr==2: return rb+b"\x00\x00\x00"+val                                        # PV body, no UC header
    if fr==3: return b"PV"+rb+b"\x00\x00\x00"+val                                  # 'PV' + body
    if fr==4: return rb+b"\x00"+val                                                # route\0 + float
    if fr==5: return ucf(bytearray(uch(0x0000))+rb+b"\x00\x00\x00"+val,"PV")       # full UCNET PV, to=0
    if fr==6: return ucf(bytearray(uch(0x0066))+rb+b"\x00\x00\x00"+val,"PS")       # PS (string-set) variant
    sys.exit("bad framing")

FR_DESC={1:"full UCNET PV (to=0x66)",2:"PV body only (route+000+float)",3:"'PV'+route+000+float",
         4:"route\\0+float",5:"full UCNET PV (to=0)",6:"UCNET PS variant"}

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
        # start channel
        s.dev.ctrl_transfer(0xC1,0,0,IFACE,2); s.dev.ctrl_transfer(0xC1,1,0,IFACE,4); s.dev.ctrl_transfer(0xC1,1,1,IFACE,4)
    def _u(s):
        s.uid=(s.uid+1)&0xff; return s.uid if s.uid else s._u()
    def send(s,payload,tag):
        u=s._u(); w=struct.pack("<H",len(payload)+8)+bytes([1,1,u,0,0,0])+payload
        s.o.write(w,timeout=1500)
        st=None; end=time.monotonic()+0.6
        while time.monotonic()<end:
            try: d=s.i.read(2048,timeout=300)
            except usb.core.USBTimeoutError: break
            except usb.core.USBError: break
            if d and len(d)>=6 and d[4]==u: st=d[5]; break
        print("  TX %-10s uid=%d ack_status=%s bytes=%s"%(tag,u,st," ".join("%02x"%x for x in payload[:40])+(" +%d"%(len(payload)-40) if len(payload)>40 else "")))

def main():
    dv=Dev()
    print("=== framing %d: %s ; route=%s ==="%(framing,FR_DESC[framing],route))
    print(">>> WATCH THE io24 OUTPUT METERS NOW <<<")
    dv.send(build(framing,route,1.0),"MUTE=ON")
    print("   holding muted for %.0fs..."%hold); time.sleep(hold)
    dv.send(build(framing,route,0.0),"MUTE=OFF")
    print("   restored (mute off).")
    usb.util.release_interface(dv.dev,IFACE)

if __name__=="__main__":
    main()
