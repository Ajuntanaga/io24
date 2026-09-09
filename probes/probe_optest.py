#!/usr/bin/env python3
"""
CAREFUL read-oriented native-opcode mapper for the io24 bulk-command channel.

Sends BARE single-byte payloads (just an opcode, no args -> can't carry a value to
write, minimizing state-change risk), strictly one at a time, and records whether
the device returns DATA (a query/read), an empty ack, or a non-zero status
(rejected). After every opcode it re-reads the protocol-version control register to
confirm the device is still alive/enumerated, and aborts if not.

NO write-shaped payloads (opcode+route+value) are ever sent.
"""
import struct, time, sys
import usb.core, usb.util

VID,PID,IFACE,EP_OUT,EP_IN=0x194F,0x0422,5,0x01,0x81

class Dev:
    def __init__(s):
        s.dev=usb.core.find(idVendor=VID,idProduct=PID)
        if s.dev is None: sys.exit("not found")
        usb.util.claim_interface(s.dev,IFACE)
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
    def alive(s):
        try: return bytes(s.dev.ctrl_transfer(0xC1,0,0,IFACE,2,timeout=800))==b"\x01\x00"
        except usb.core.USBError: return False
    def cmd(s,payload,collect=0.8):
        u=s._u(); w=struct.pack("<H",len(payload)+8)+bytes([1,1,u,0,0,0])+bytes(payload)
        try: s.o.write(w,timeout=1200)
        except usb.core.USBError as e:
            try: s.dev.clear_halt(EP_OUT)
            except: pass
            return ("OUTERR",str(e),[])
        resp=[]; end=time.monotonic()+collect; ack_status=None
        while time.monotonic()<end:
            try: d=s.i.read(2048,timeout=350)
            except usb.core.USBTimeoutError:
                if ack_status is not None: break
                continue
            except usb.core.USBError:
                try: s.dev.clear_halt(EP_IN)
                except: pass
                break
            if not d: continue
            d=bytes(d)
            if len(d)>=6 and d[4]==u:
                ack_status=d[5]
                pl=d[8:] if len(d)>8 else b""
                if pl: resp.append(d)
            elif len(d)>8:
                resp.append(d)  # unsolicited push
        return ("OK",ack_status,resp)

def hexd(b,limit=64):
    b=bytes(b); s=b[:limit]
    return " ".join("%02x"%x for x in s)+(" +%d"%(len(b)-limit) if len(b)>limit else "")

def main():
    dv=Dev()
    if not dv.alive(): sys.exit("device not responding to PV read at start")
    print("device alive (PV=01 00). Probing bare opcodes 0x00-0x1f (1-byte payloads)...\n")
    data_ops=[]; rejected=[]; acked=[]
    for op in range(0x00,0x20):
        status,val,resp=dv.cmd([op])
        alive=dv.alive()
        if status=="OUTERR":
            print("  op 0x%02x: OUT error (%s)"%(op,val));
            if not alive: print("  !! device stopped responding; aborting"); break
            continue
        if resp:
            data_ops.append(op)
            print("  op 0x%02x: *** DATA *** ack_status=%s"%(op,val))
            for d in resp[:2]:
                pl=d[8:]
                print("       resp[%d] total=%d status=%d payload: %s |%s|"%(
                    len(d),struct.unpack('<H',d[0:2])[0],d[5],hexd(d[8:]),
                    "".join(chr(x) if 32<=x<127 else "." for x in d[8:64])))
        elif val is None:
            print("  op 0x%02x: no response (timeout)"%op)
        elif val!=0:
            rejected.append((op,val)); print("  op 0x%02x: ack status=0x%02x (rejected)"%(op,val))
        else:
            acked.append(op)  # empty ack, status 0
        if not alive:
            print("  !! device stopped responding after op 0x%02x; ABORTING"%op); break
    usb.util.release_interface(dv.dev,IFACE)
    print("\n=== SUMMARY ===")
    print("opcodes returning DATA (queries): %s"%[hex(x) for x in data_ops])
    print("opcodes empty-acked (status 0)  : %s"%[hex(x) for x in acked])
    print("opcodes rejected (status!=0)    : %s"%[("0x%02x:st0x%02x"%(o,v)) for o,v in rejected])
    print("device alive at end:", dv.alive() if False else "(released)")

if __name__=="__main__":
    main()
