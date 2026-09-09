#!/usr/bin/env python3
"""
READ-ONLY physical-feedback capture. Properly starts the control channel (alt 1 +
the two vendor queries), then just LISTENS on the bulk IN pipe while the user
physically works the io24 (twist encoders, press buttons, move faders). If the
device pushes native notifications for physical control changes, we capture the
native command format directly off the device — no writes, no guessing.

Nothing is written to the device except the two read-only control queries.
"""
import struct, time, sys
import usb.core, usb.util

VID,PID,IFACE,EP_OUT,EP_IN=0x194F,0x0422,5,0x01,0x81
LISTEN_SECONDS=25

def hexd(b,limit=96):
    b=bytes(b); s=b[:limit]
    return "%s%s"%(" ".join("%02x"%x for x in s)," +%d"%(len(b)-limit) if len(b)>limit else "")
def ascii_(b,limit=96):
    return "".join(chr(x) if 32<=x<127 else "." for x in bytes(b)[:limit])

def main():
    dev=usb.core.find(idVendor=VID,idProduct=PID)
    if dev is None: sys.exit("io24 not found — is it plugged in?")
    usb.util.claim_interface(dev,IFACE)
    dev.set_interface_altsetting(interface=IFACE,alternate_setting=1)
    i=dev.get_active_configuration()[(IFACE,1)]
    ep_in=usb.util.find_descriptor(i,custom_match=lambda e:e.bEndpointAddress==EP_IN)
    try: dev.clear_halt(EP_IN)
    except: pass
    # proper channel start (read-only control queries)
    pv=bytes(dev.ctrl_transfer(0xC1,0,0,IFACE,2,timeout=800))
    dev.ctrl_transfer(0xC1,1,0,IFACE,4,timeout=800)
    dev.ctrl_transfer(0xC1,1,1,IFACE,4,timeout=800)
    print("channel started (PV=%s)."%pv.hex())
    print(">>> WORK THE DEVICE NOW for ~%ds: twist EVERY encoder back and forth,"%LISTEN_SECONDS)
    print(">>> press mute/preset/monitor buttons, move the headphone & main knobs. <<<\n")
    n=0; end=time.monotonic()+LISTEN_SECONDS
    while time.monotonic()<end:
        try: d=ep_in.read(2048,timeout=400)
        except usb.core.USBTimeoutError: continue
        except usb.core.USBError as e: print("read err",e); break
        if d:
            n+=1; b=bytes(d)
            # unwrap the 8-byte bulk-command header if present
            payload=b[8:] if len(b)>8 else b""
            print("RX[%d] %s |%s|"%(len(b),hexd(b),ascii_(b)))
            if payload:
                print("     payload[%d]: %s |%s|"%(len(payload),hexd(payload),ascii_(payload)))
    usb.util.release_interface(dev,IFACE)
    print("\n=== %d frame(s) captured ==="%n)
    if n==0:
        print("Device pushes nothing for physical changes without an explicit 'subscribe'")
        print("command -> read-only path is out; next is write-shaped probing or a capture.")
    else:
        print("*** DEVICE PUSHED NATIVE FRAMES — this is the native format. Analyze above. ***")

if __name__=="__main__":
    main()
