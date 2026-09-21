#!/usr/bin/env python3
"""
io24web — a browser mixer for the PreSonus Revelator io24.

This is the Linux stand-in for Universal Control's window. It serves a single
self-contained page (no CDN, no build step, no toolkit) and drives the device
through the same `io24d.Device` used by the daemon, so USB access stays
serialised behind one lock.

    io24web.py [--port 8424] [--bind 127.0.0.1] [--wait]

Then open http://127.0.0.1:8424/

Only ONE process can hold the control interface at a time, so run either this or
io24d / ucnet_shim — not both. Binding defaults to loopback: the page has no
authentication and can change your monitoring, so do not expose it to a network
you do not trust.
"""
import json
import math
import os
import socketserver
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from io24d import Device, SETTERS, wait_for_device

# JaSt meter slots (see PROTOCOL.md §6 and io24_meters.py)
SLOTS = {"in1": 4, "in2": 6, "mainL": 12, "mainR": 13,
         "mixaL": 14, "mixaR": 15, "mixbL": 16, "mixbR": 17}
DEVICE = None


def db(x):
    return -99.0 if x is None or x <= 1e-12 else 20.0 * math.log10(x)


def read_meters():
    """One JaSt read -> every meter, plus the chain's gain reduction.

    Deliberately a single small read: the state blob carries all of them, so
    polling 8 meters costs exactly as much as polling one.
    """
    with DEVICE.lock:
        rsp = DEVICE.dev.read_state(0x100)
        f = DEVICE.dev.floats(rsp) if rsp else None
        red = {}
        for blk in ("gate", "comp", "lim "):
            try:
                r = DEVICE.dev.read_reduction(blk, 1)
                red[blk.strip()] = db(r[0]) if r else 0.0
            except Exception:
                red[blk.strip()] = 0.0
    if not f:
        return {"ok": False}
    return {"ok": True,
            "meters": {k: round(db(f[s]), 2) for k, s in SLOTS.items()},
            "reduction": {k: round(v, 2) for k, v in red.items()}}


# --------------------------------------------------------------------------
# API. Everything the page can do goes through here; nothing else is exposed.
# --------------------------------------------------------------------------
def api(path, body):
    d = DEVICE.dev
    if path == "/api/state":
        st = DEVICE.status()
        out = {"ok": st is not None, "state": st}
        out.update(read_meters())
        return out

    if path == "/api/meters":
        return read_meters()

    if path == "/api/set":                       # the plain 'Appl' parameters
        DEVICE.apply(body["param"], int(body.get("channel", 1)),
                     body.get("value"), body)
        return {"ok": True}

    if path == "/api/eq":
        ch = int(body["channel"])
        with DEVICE.lock:
            if body.get("shape") == "flat":
                d.eq_off(ch)
            else:
                d.set_eq_band(ch, int(body["band"]), body.get("shape", "peaking"),
                              float(body.get("freq", 1000)),
                              float(body.get("gain", 0)),
                              float(body.get("q", 0.7)))
        return {"ok": True}

    if path == "/api/mix":
        with DEVICE.lock:
            if body.get("off"):
                d.mix_off(body["source"], bus=body.get("bus", "main"))
            else:
                d.set_mix_db(body["source"], float(body["db"]),
                             bus=body.get("bus", "main"))
        return {"ok": True}

    if path == "/api/dsp":
        ch = int(body["channel"]); kind = body["kind"]; on = bool(body.get("on"))
        with DEVICE.lock:
            if kind == "gate":
                if on:
                    d.set_gate(ch, on=True,
                               threshold_db=float(body.get("threshold", -40)),
                               range_db=float(body.get("range", -60)))
                else:
                    d.gate_off(ch)
            elif kind == "comp":
                if on:
                    d.set_compressor(ch, model=int(body.get("model", 0)), on=True,
                                     threshold_db=float(body.get("threshold", -24)),
                                     ratio=float(body.get("ratio", 3)),
                                     attack_s=float(body.get("attack", 0.01)),
                                     release_s=float(body.get("release", 0.15)),
                                     gain_db=float(body.get("makeup", 0)),
                                     softknee=bool(body.get("softknee", True)),
                                     automode=False, keyfilter_hz=0.0,
                                     keylisten=False)
                else:
                    d.compressor_off(ch)
            elif kind == "limiter":
                d.set_limiter(ch, on, float(body.get("threshold", -28)))
            elif kind == "hpfreq":
                d.set_highpass_freq(ch, float(body.get("freq", 24)))
            else:
                return {"ok": False, "error": "unknown dsp %r" % kind}
        return {"ok": True}

    if path == "/api/preset":
        p = body.get("path") or os.path.expanduser("~/io24-preset.json")
        if body.get("action") == "save":
            snap = DEVICE.save_preset(p)
            return {"ok": True, "scope": "host-file", "path": p,
                    "live": len(snap["live"]),
                    "settings": len(snap["calls"])}
        n_live, n_calls = DEVICE.load_preset(p)
        return {"ok": True, "scope": "host-file", "path": p,
                "live": n_live, "settings": n_calls}

    return {"ok": False, "error": "unknown endpoint %r" % path}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass                                   # a meter poll every 70 ms; no spam

    def _reply(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            b = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        if self.path.startswith("/api/"):
            try:
                self._reply(api(self.path, {}))
            except Exception as e:
                self._reply({"ok": False, "error": "%s: %s" % (type(e).__name__, e)}, 500)
            return
        self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._reply({"ok": False, "error": "bad json: %s" % e}, 400)
        try:
            self._reply(api(self.path, body))
        except Exception as e:
            self._reply({"ok": False, "error": "%s: %s" % (type(e).__name__, e)}, 500)


PAGE = r"""<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>io24</title>
<style>
:root{--bg:#faf9f7;--panel:#fff;--line:#e3e1db;--ink:#14140f;--dim:#6c6a63;
      --accent:#1d9e75;--warn:#ba7517;--hot:#d03b3b;--track:#eceae4}
@media(prefers-color-scheme:dark){:root{--bg:#141413;--panel:#1c1c1a;--line:#302f2c;
      --ink:#f2f1ec;--dim:#9b9992;--track:#282725}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font:14px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;
       align-items:baseline;gap:14px;position:sticky;top:0;background:var(--bg);z-index:5}
h1{font-size:16px;font-weight:500;margin:0}
#conn{font-size:12px;color:var(--dim)}
main{padding:18px 20px 40px;display:grid;gap:18px;
     grid-template-columns:repeat(auto-fit,minmax(330px,1fr));max-width:1500px}
section{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
h2{font-size:13px;font-weight:500;margin:0 0 14px;color:var(--dim);
   text-transform:uppercase;letter-spacing:.06em}
.row{display:flex;align-items:center;gap:10px;margin:9px 0}
.row label{width:88px;flex:none;color:var(--dim);font-size:13px}
.row output{width:66px;flex:none;text-align:right;font-variant-numeric:tabular-nums;font-size:13px}
input[type=range]{flex:1;accent-color:var(--accent);height:20px}
button{font:inherit;padding:5px 11px;border:1px solid var(--line);border-radius:7px;
       background:transparent;color:var(--ink);cursor:pointer}
button:hover{background:var(--track)}
button.on{background:var(--accent);border-color:var(--accent);color:#fff}
button.danger.on{background:var(--hot);border-color:var(--hot)}
select{font:inherit;padding:4px 7px;border:1px solid var(--line);border-radius:7px;
       background:var(--panel);color:var(--ink)}
.meter{height:9px;background:var(--track);border-radius:5px;overflow:hidden;flex:1}
.meter i{display:block;height:100%;width:0;background:var(--accent);
         transition:width .05s linear}
.meter i.warn{background:var(--warn)} .meter i.hot{background:var(--hot)}
.mrow{display:flex;align-items:center;gap:9px;margin:7px 0}
.mrow span{width:56px;flex:none;color:var(--dim);font-size:12px}
.mrow em{width:62px;flex:none;text-align:right;font-style:normal;font-size:12px;
         color:var(--dim);font-variant-numeric:tabular-nums}
canvas{width:100%;height:150px;display:block;border:1px solid var(--line);
       border-radius:8px;background:var(--bg)}
.bands{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}
.bands button{padding:4px 0;font-size:12px}
.tiny{font-size:12px;color:var(--dim)}
.btns{display:flex;gap:7px;flex-wrap:wrap;margin-top:6px}
</style>

<header><h1>Revelator io24</h1><span id="conn">connecting…</span></header>
<main>
  <section><h2>Meters</h2><div id="meters"></div>
    <div class="tiny" id="red" style="margin-top:10px"></div></section>
  <section><h2>Channel 1</h2><div id="ch1"></div></section>
  <section><h2>Channel 2</h2><div id="ch2"></div></section>
  <section><h2>Monitoring</h2><div id="master"></div></section>
  <section style="grid-column:1/-1"><h2>Equaliser — channel <select id="eqch">
      <option value="1">1</option><option value="2">2</option></select></h2>
    <canvas id="eqc" width="1200" height="300"></canvas>
    <div class="bands" id="eqbands"></div>
    <div id="eqctl" style="margin-top:12px"></div>
    <div class="btns"><button onclick="eqFlat()">Flatten all bands</button></div></section>
  <section><h2>Dynamics — channel 1</h2><div id="dyn"></div></section>
  <section><h2>Presets</h2>
    <div class="row"><label>File</label>
      <input id="ppath" style="flex:1;font:inherit;padding:5px 8px;border:1px solid var(--line);
             border-radius:7px;background:var(--panel);color:var(--ink)"></div>
    <div class="btns"><button onclick="preset('save')">Save</button>
      <button onclick="preset('load')">Load</button></div>
    <div class="tiny" id="pmsg" style="margin-top:8px"></div>
    <p class="tiny">A preset holds the readable parameters plus the DSP settings this
      driver has written. The device cannot report its DSP back, so anything set by
      other software is not captured.</p></section>
</main>

<script>
const $=s=>document.querySelector(s);
async function post(p,b){const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify(b)});return r.json()}
async function get(p){const r=await fetch(p);return r.json()}

function row(label,html){return `<div class="row"><label>${label}</label>${html}</div>`}
function slider(id,min,max,step,val,unit){
  return `<input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${val}">
          <output id="${id}o">${(+val).toFixed(unit==='dB'?1:2)}${unit?' '+unit:''}</output>`}

/* ---------- channel strips ---------- */
function strip(ch){
  return row('Gain',slider('g'+ch,0,60,0.5,0,'dB'))
    + `<div class="btns">
        <button id="p${ch}">48V</button><button id="m${ch}" class="danger">Mute</button>
        <button id="h${ch}">Low cut</button></div>`
    + row('Cut freq',slider('hf'+ch,24,1000,1,24,'Hz'))
    + row('FX send',slider('fx'+ch,0,1,0.01,0,''));
}
function wireStrip(ch){
  bind('g'+ch,'dB',v=>post('/api/set',{param:'gain',channel:ch,value:v}));
  bind('hf'+ch,'Hz',v=>post('/api/dsp',{kind:'hpfreq',channel:ch,freq:v}));
  bind('fx'+ch,'',v=>post('/api/set',{param:'fxmix',channel:ch,value:v}));
  toggle('p'+ch,v=>post('/api/set',{param:'phantom',channel:ch,value:v}));
  toggle('m'+ch,v=>post('/api/set',{param:'mute',channel:ch,value:v}));
  toggle('h'+ch,v=>post('/api/set',{param:'hpf',channel:ch,value:v}));
}
function bind(id,unit,fn){const e=$('#'+id),o=$('#'+id+'o');let t=null;
  e.oninput=()=>{o.textContent=(+e.value).toFixed(unit==='dB'?1:(unit==='Hz'?0:2))+(unit?' '+unit:'');
    clearTimeout(t);t=setTimeout(()=>fn(+e.value),60)}}
function toggle(id,fn){const e=$('#'+id);e.onclick=()=>{e.classList.toggle('on');
    fn(e.classList.contains('on'))}}

$('#ch1').innerHTML=strip(1); $('#ch2').innerHTML=strip(2);
$('#master').innerHTML=row('Headphone',slider('hp',0,1,0.01,0.5,''))
  + row('Main',slider('mv',0,1,0.01,0.5,''))
  + row('Blend',slider('bl',-1,1,0.02,0,''))
  + `<div class="btns"><button id="hpm" class="danger">Headphone mute</button>
     <button id="lnk">Stereo link</button></div>`;
wireStrip(1); wireStrip(2);
bind('hp','',v=>post('/api/set',{param:'hpvol',value:v}));
bind('mv','',v=>post('/api/set',{param:'mainvol',value:v}));
bind('bl','',v=>post('/api/set',{param:'blend',value:v}));
toggle('hpm',v=>post('/api/set',{param:'hpmute',value:v}));
toggle('lnk',v=>post('/api/set',{param:'link',value:v}));

/* ---------- dynamics ---------- */
$('#dyn').innerHTML=`<div class="btns"><button id="gt">Gate</button>
   <button id="cp">Compressor</button><button id="lm">Limiter</button></div>`
  + row('Gate thr',slider('gth',-80,0,1,-40,'dB'))
  + row('Comp thr',slider('cth',-60,0,1,-24,'dB'))
  + row('Ratio',slider('crat',1,20,0.5,3,':1'))
  + row('Makeup',slider('cmk',0,20,0.5,0,'dB'))
  + row('Lim thr',slider('lth',-40,0,1,-28,'dB'));
const dyn={gate:false,comp:false,lim:false};
function pushGate(){post('/api/dsp',{kind:'gate',channel:1,on:dyn.gate,
  threshold:+$('#gth').value,range:-60})}
function pushComp(){post('/api/dsp',{kind:'comp',channel:1,on:dyn.comp,
  threshold:+$('#cth').value,ratio:+$('#crat').value,makeup:+$('#cmk').value})}
function pushLim(){post('/api/dsp',{kind:'limiter',channel:1,on:dyn.lim,
  threshold:+$('#lth').value})}
$('#gt').onclick=e=>{dyn.gate=!dyn.gate;e.target.classList.toggle('on');pushGate()};
$('#cp').onclick=e=>{dyn.comp=!dyn.comp;e.target.classList.toggle('on');pushComp()};
$('#lm').onclick=e=>{dyn.lim=!dyn.lim;e.target.classList.toggle('on');pushLim()};
bind('gth','dB',()=>dyn.gate&&pushGate());
bind('cth','dB',()=>dyn.comp&&pushComp());
bind('crat',':1',()=>dyn.comp&&pushComp());
bind('cmk','dB',()=>dyn.comp&&pushComp());
bind('lth','dB',()=>dyn.lim&&pushLim());

/* ---------- EQ: four bands, live response curve ---------- */
const SHAPES=['off','peaking','lowshelf','highshelf','hp','lp'];
const bands=[0,1,2,3].map(i=>({shape:'off',freq:[120,600,2500,8000][i],gain:0,q:0.7}));
let cur=0;
$('#eqbands').innerHTML=bands.map((b,i)=>
  `<button id="b${i}" onclick="pick(${i})">${['Low','Low mid','High mid','High'][i]}</button>`).join('');
$('#eqctl').innerHTML=row('Shape',`<select id="esh">${SHAPES.map(s=>
    `<option value="${s}">${s}</option>`).join('')}</select>`)
  + row('Frequency',slider('efr',20,18000,1,120,'Hz'))
  + row('Gain',slider('egn',-15,15,0.5,0,'dB'))
  + row('Q',slider('eq',0.1,10,0.1,0.7,''));
function pick(i){cur=i;[0,1,2,3].forEach(k=>$('#b'+k).classList.toggle('on',k===i));
  const b=bands[i];$('#esh').value=b.shape;
  setS('efr',b.freq,'Hz');setS('egn',b.gain,'dB');setS('eq',b.q,'');draw()}
function setS(id,v,u){$('#'+id).value=v;
  $('#'+id+'o').textContent=(+v).toFixed(u==='dB'?1:(u==='Hz'?0:2))+(u?' '+u:'')}
function pushEQ(){const b=bands[cur];
  post('/api/eq',{channel:+$('#eqch').value,band:cur,shape:b.shape,
    freq:b.freq,gain:b.gain,q:b.q});draw()}
$('#esh').onchange=e=>{bands[cur].shape=e.target.value;pushEQ()};
['efr','egn','eq'].forEach((id,k)=>{const key=['freq','gain','q'][k];
  bind(id,['Hz','dB',''][k],v=>{bands[cur][key]=v;pushEQ()})});
function eqFlat(){bands.forEach(b=>b.shape='off');
  post('/api/eq',{channel:+$('#eqch').value,shape:'flat'});pick(cur)}

/* RBJ response, matching the driver's designers, for display only */
function coeffs(b,fs){const A=Math.pow(10,b.gain/40),w=2*Math.PI*b.freq/fs,
  cw=Math.cos(w),sw=Math.sin(w),al=sw/(2*b.q);
  let b0,b1,b2,a0,a1,a2;
  switch(b.shape){
   case 'peaking':b0=1+al*A;b1=-2*cw;b2=1-al*A;a0=1+al/A;a1=-2*cw;a2=1-al/A;break;
   case 'lowshelf':{const be=Math.sqrt(A)/b.q*sw;
     b0=A*((A+1)-(A-1)*cw+be);b1=2*A*((A-1)-(A+1)*cw);b2=A*((A+1)-(A-1)*cw-be);
     a0=(A+1)+(A-1)*cw+be;a1=-2*((A-1)+(A+1)*cw);a2=(A+1)+(A-1)*cw-be;break}
   case 'highshelf':{const be=Math.sqrt(A)/b.q*sw;
     b0=A*((A+1)+(A-1)*cw+be);b1=-2*A*((A-1)+(A+1)*cw);b2=A*((A+1)+(A-1)*cw-be);
     a0=(A+1)-(A-1)*cw+be;a1=2*((A-1)-(A+1)*cw);a2=(A+1)-(A-1)*cw-be;break}
   case 'hp':b0=(1+cw)/2;b1=-(1+cw);b2=(1+cw)/2;a0=1+al;a1=-2*cw;a2=1-al;break;
   case 'lp':b0=(1-cw)/2;b1=1-cw;b2=(1-cw)/2;a0=1+al;a1=-2*cw;a2=1-al;break;
   default:return null}
  return [b0/a0,b1/a0,b2/a0,a1/a0,a2/a0]}
function draw(){const c=$('#eqc'),g=c.getContext('2d'),W=c.width,H=c.height,fs=48000;
  const css=getComputedStyle(document.documentElement);
  g.clearRect(0,0,W,H);
  g.strokeStyle=css.getPropertyValue('--line');g.lineWidth=1;g.font='11px sans-serif';
  g.fillStyle=css.getPropertyValue('--dim');
  [-12,-6,0,6,12].forEach(d=>{const y=H/2-d/18*(H/2);g.globalAlpha=d?0.5:1;
    g.beginPath();g.moveTo(0,y);g.lineTo(W,y);g.stroke();g.globalAlpha=1;
    g.fillText(d+' dB',4,y-3)});
  [100,1000,10000].forEach(f=>{const x=(Math.log10(f/20)/Math.log10(24000/20))*W;
    g.globalAlpha=0.5;g.beginPath();g.moveTo(x,0);g.lineTo(x,H);g.stroke();g.globalAlpha=1;
    g.fillText(f>=1000?(f/1000)+'k':f,x+3,H-5)});
  g.strokeStyle=css.getPropertyValue('--accent');g.lineWidth=2;g.beginPath();
  for(let px=0;px<=W;px++){
    const f=20*Math.pow(24000/20,px/W),w=2*Math.PI*f/fs;
    let re=1,im=0;
    bands.forEach(b=>{const c2=coeffs(b,fs);if(!c2)return;
      const[nb0,nb1,nb2,na1,na2]=c2;
      const cw1=Math.cos(-w),sw1=Math.sin(-w),cw2=Math.cos(-2*w),sw2=Math.sin(-2*w);
      const nr=nb0+nb1*cw1+nb2*cw2, ni=nb1*sw1+nb2*sw2;
      const dr=1+na1*cw1+na2*cw2,  di=na1*sw1+na2*sw2;
      const dd=dr*dr+di*di;
      const hr=(nr*dr+ni*di)/dd, hi=(ni*dr-nr*di)/dd;
      const orr=re*hr-im*hi; im=re*hi+im*hr; re=orr});
    const mag=20*Math.log10(Math.max(Math.hypot(re,im),1e-6));
    const y=H/2-mag/18*(H/2);
    px?g.lineTo(px,y):g.moveTo(px,y)}
  g.stroke()}

/* ---------- meters ---------- */
const MET=[['in1','Input 1'],['in2','Input 2'],['mainL','Main L'],['mainR','Main R'],
           ['mixaL','Mix A L'],['mixaR','Mix A R'],['mixbL','Mix B L'],['mixbR','Mix B R']];
$('#meters').innerHTML=MET.map(([k,n])=>
  `<div class="mrow"><span>${n}</span><div class="meter"><i id="mt${k}"></i></div>
   <em id="mv${k}">−∞</em></div>`).join('');
function paint(m){for(const[k,]of MET){const v=m[k];const e=$('#mt'+k);
  const pc=Math.max(0,Math.min(100,(v+60)/60*100));
  e.style.width=pc+'%';e.className=v>-1?'hot':(v>-9?'warn':'');
  $('#mv'+k).textContent=v<=-98?'−∞':v.toFixed(1)}}

/* ---------- presets ---------- */
async function preset(a){const r=await post('/api/preset',{action:a,path:$('#ppath').value});
  $('#pmsg').textContent=r.ok?`${a==='save'?'Saved':'Loaded'} ${r.path} — ${r.live} live values, ${r.settings} DSP settings`
    :('failed: '+r.error)}

/* ---------- polling ---------- */
let fails=0;
async function tick(){
  try{const r=await get('/api/meters');
    if(r.ok){paint(r.meters);
      $('#red').textContent='Gain reduction — gate '+r.reduction.gate.toFixed(1)
        +' dB, comp '+r.reduction.comp.toFixed(1)+' dB, limiter '+r.reduction.lim.toFixed(1)+' dB';
      $('#conn').textContent='connected';fails=0}
  }catch(e){if(++fails>3)$('#conn').textContent='disconnected'}
  setTimeout(tick,70)}
async function initial(){const r=await get('/api/state');
  if(!r.ok||!r.state)return;const s=r.state;
  setS('g1',s.input1Gain,'dB');setS('g2',s.input2Gain,'dB');
  setS('hp',s.hpVolume,'');setS('mv',s.mainVolume,'');setS('bl',s.monitorMix,'');
  $('#p1').classList.toggle('on',s.input1PhantomPower);
  $('#p2').classList.toggle('on',s.input2PhantomPower);
  $('#ppath').value=(navigator.platform.startsWith('Win')?'':'')+'io24-preset.json'}
pick(0); initial(); tick();
</script>
"""


def main():
    argv = sys.argv[1:]
    if argv and argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8424
    bind = argv[argv.index("--bind") + 1] if "--bind" in argv else "127.0.0.1"

    global DEVICE
    DEVICE = wait_for_device(0.5, timeout=None if "--wait" in argv else 0.0)
    srv = ThreadingHTTPServer((bind, port), Handler)
    srv.daemon_threads = True
    print("io24web on http://%s:%d/   (Ctrl-C to stop)" % (bind, port), flush=True)
    if bind not in ("127.0.0.1", "localhost", "::1"):
        print("  NOTE: bound beyond loopback and there is no authentication.",
              flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        DEVICE.close()
        print("io24web stopped")


if __name__ == "__main__":
    main()
