#!/usr/bin/env python3
"""Frozen, hardware-free PE/source WinUSB vendor-profile contract."""
import argparse, hashlib, pathlib, re, subprocess, sys
EXPECTED_IMPORTS = (
    "WinUsb_AbortPipe", "WinUsb_ControlTransfer", "WinUsb_Free",
    "WinUsb_GetAssociatedInterface", "WinUsb_GetDescriptor",
    "WinUsb_GetOverlappedResult", "WinUsb_GetPipePolicy", "WinUsb_Initialize",
    "WinUsb_QueryDeviceInformation", "WinUsb_ReadPipe", "WinUsb_ResetPipe",
    "WinUsb_SetCurrentAlternateSetting", "WinUsb_SetPipePolicy", "WinUsb_WritePipe",
)
EXPECTED_POLICY_SEQUENCE = {"all": ((3, 0), (9, 0)), "out": ((1, 0),), "in": ((2, 0), (4, 0), (5, 0), (6, 0), (7, 1)), "get": ((8, 4),)}
EXPECTED_HASH = "567892d75c7243b3cc30487f7431933e593f3c288ea6add84c21d4e8678f877b"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--wine-source",required=True); ap.add_argument("--vendor-dll",required=True); ns=ap.parse_args()
    root=pathlib.Path(ns.wine_source); dll=pathlib.Path(ns.vendor_dll)
    required=[root/"include/winusb.h",root/"dlls/winusb/main.c",root/"dlls/winusb/winusb.spec",dll]
    try:
        if any(not p.is_file() for p in required): print("HARNESS: missing vendor contract input",file=sys.stderr); return 2
        source_paths=[root/"dlls/winusb/main.c"]
        optional_io=root/"dlls/winusb/io.c"
        if optional_io.is_file(): source_paths.append(optional_io)
        sources="\n".join(p.read_text(errors="replace") for p in source_paths)
        digest=hashlib.sha256(dll.read_bytes()).hexdigest()
        pe=subprocess.run(["objdump","-p",str(dll)],check=True,text=True,capture_output=True).stdout
        policy_site=subprocess.run(["objdump","-d","-M","intel","--start-address=0x180084d50","--stop-address=0x180084dc0",str(dll)],check=True,text=True,capture_output=True).stdout
        initializer_site=subprocess.run(["objdump","-d","-M","intel","--start-address=0x180095e20","--stop-address=0x180095f80",str(dll)],check=True,text=True,capture_output=True).stdout
        public=subprocess.run([str(pathlib.Path(__file__).with_name("winusb_user_api_contract.sh")),str(root),"--vendor"],text=True,capture_output=True)
    except (OSError,subprocess.CalledProcessError) as error:
        print(f"HARNESS: vendor static/executable tool failure: {error}",file=sys.stderr); return 2
    if public.returncode not in (0,1):
        print(public.stdout,end=""); print(public.stderr,end="",file=sys.stderr)
        print(f"HARNESS: public vendor sequence exited {public.returncode}",file=sys.stderr); return 2
    found=tuple(sorted(set(re.findall(r"WinUsb_[A-Za-z]+",pe))))
    callable_count=sum(bool(re.search(r"\b"+re.escape(name)+r"\s*\(",sources)) for name in EXPECTED_IMPORTS)
    failures=[]
    if digest!=EXPECTED_HASH: failures.append("vendor hash")
    if found!=tuple(sorted(EXPECTED_IMPORTS)): failures.append("exact fourteen imports")
    if "180084d50" not in policy_site: failures.append("policy get callsite")
    if "180095e20" not in initializer_site: failures.append("initializer callsite")
    if callable_count!=14: failures.append(f"vendor callable count {callable_count}/14")
    if public.returncode: failures.append("synthetic fourteen-operation sequence")
    if sum(len(v) for v in EXPECTED_POLICY_SEQUENCE.values())!=9: failures.append("policy fixture")
    print(public.stdout,end="")
    print(f"CP33 vendor RED: hash={'OK' if digest==EXPECTED_HASH else 'BAD'} imports={len(found)}/14 policy-callsite=0x180084d50 initializer=0x180095e20 static-definitions={callable_count}/14 synthetic-sequence={'RED' if public.returncode else 'PASS'} policy-pairs=9 failures={'; '.join(failures) or 'none'}")
    return 1 if failures else 0
if __name__=="__main__": raise SystemExit(main())
