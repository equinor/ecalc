"""Debug visualization server for the process solver.

Enable by setting SOLVER_DEBUG_PORT=<port> (e.g. 7654) before starting the
worker.  Open http://localhost:<port> in a browser to watch solver events
animate in real time.

``emit()`` sends a UDP datagram to localhost so it works correctly regardless
of how many times this module is imported or in which module instance
``enable()`` was called.

Example::

    SOLVER_DEBUG_PORT=7654 python worker.py
"""

import json
import os
import queue
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

_UDP_OFFSET = 1  # UDP listener port = HTTP port + UDP_OFFSET

_current_phase: str = "idle"
_subscribers: dict[str, queue.Queue] = {}
_lock = threading.Lock()

_emit_sock: socket.socket | None = None
_emit_addr: tuple[str, int] | None = None
_emit_sock_lock = threading.Lock()


def _udp_port() -> int | None:
    v = os.environ.get("SOLVER_DEBUG_PORT")
    return int(v) + _UDP_OFFSET if v else None


def is_enabled() -> bool:
    return os.environ.get("SOLVER_DEBUG_PORT") is not None


def set_phase(phase: str) -> None:
    global _current_phase
    _current_phase = phase
    emit("phase.change", phase=phase)


def current_phase() -> str:
    return _current_phase


def emit(event_type: str, **data: Any) -> None:
    port = _udp_port()
    if port is None:
        return
    global _emit_sock, _emit_addr
    msg = json.dumps({"type": event_type, "ts": time.monotonic(), **data}).encode()
    with _emit_sock_lock:
        if _emit_sock is None:
            _emit_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            _emit_addr = ("127.0.0.1", port)
        try:
            _emit_sock.sendto(msg, _emit_addr)  # type: ignore[arg-type]
        except OSError:
            pass


def enable(http_port: int = 7654) -> None:
    udp_port = http_port + _UDP_OFFSET
    t_udp = threading.Thread(target=_run_udp_listener, args=(udp_port,), daemon=True, name="solver-debug-udp")
    t_http = threading.Thread(target=_run_http_server, args=(http_port,), daemon=True, name="solver-debug-http")
    t_udp.start()
    t_http.start()
    print(f"[solver_debug] http://localhost:{http_port}  (UDP events on :{udp_port})", flush=True)


def _distribute(msg: str) -> None:
    with _lock:
        dead = []
        for cid, q in _subscribers.items():
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(cid)
        for cid in dead:
            del _subscribers[cid]


def _run_udp_listener(port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    # sock.bind(("127.0.0.1", port))
    while True:
        try:
            data, _ = sock.recvfrom(65535)
            msg = data.decode()
            _distribute(msg)
            try:
                ev = json.loads(msg)
                if ev.get("type") == "phase.change":
                    global _current_phase
                    _current_phase = ev.get("phase", _current_phase)
            except (json.JSONDecodeError, AttributeError):
                pass
        except OSError:
            break


def _run_http_server(port: int) -> None:
    html = _HTML.encode()

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # noqa: A002
            pass

        def do_GET(self):  # noqa: N802
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            elif self.path.startswith("/status"):
                with _lock:
                    n = len(_subscribers)
                body = json.dumps({"enabled": True, "subscribers": n, "phase": _current_phase}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            elif self.path.startswith("/events"):
                # Parse ?id= query param for stable per-tab deduplication
                client_id = "default"
                if "?" in self.path:
                    qs = self.path.split("?", 1)[1]
                    for part in qs.split("&"):
                        if part.startswith("id="):
                            client_id = part[3:]
                            break

                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                sub: queue.Queue = queue.Queue(maxsize=2000)
                with _lock:
                    # Kill any existing subscriber with the same client ID immediately
                    old = _subscribers.get(client_id)
                    if old is not None:
                        try:
                            old.put_nowait(None)  # None = sentinel → exit old handler
                        except queue.Full:
                            pass
                    _subscribers[client_id] = sub

                try:
                    while True:
                        try:
                            msg = sub.get(timeout=1)
                            if msg is None:
                                break  # displaced by a new connection with same client ID
                            self.wfile.write(f"data: {msg}\n\n".encode())
                            self.wfile.flush()
                        except queue.Empty:
                            self.wfile.write(b": keepalive\n\n")
                            self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    with _lock:
                        if _subscribers.get(client_id) is sub:
                            del _subscribers[client_id]
            else:
                self.send_response(404)
                self.end_headers()

    ThreadingHTTPServer(("0.0.0.0", port), _Handler).serve_forever()
    # ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>eCalc Solver Debug</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100vh;overflow:hidden;font-family:ui-monospace,"SF Mono",Consolas,monospace;background:#0d1117;color:#e6edf3;font-size:12px}
.grid{display:grid;grid-template-rows:46px 1fr 110px 82px 170px;grid-template-columns:1fr 310px;height:100vh;gap:1px;background:#21262d}
header{grid-column:1/-1;background:#161b22;display:flex;align-items:center;padding:0 16px;gap:14px;border-bottom:1px solid #30363d}
header h1{font-size:14px;font-weight:700;color:#58a6ff;letter-spacing:-0.02em}
#conn{font-size:11px;color:#f85149}
#conn.on{color:#56d364}
#phase-badge{margin-left:auto;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700;background:#21262d;color:#8b949e;border:1px solid #30363d;text-transform:uppercase;letter-spacing:.07em;transition:all .3s}
.panel{background:#161b22;padding:10px 12px;display:flex;flex-direction:column;min-height:0}
.panel-title{font-size:10px;font-weight:700;color:#8b949e;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;flex-shrink:0}
#right-col{display:flex;flex-direction:column;gap:1px;background:#21262d;min-height:0}
#p-compressor{flex:1;min-height:0}
#p-search{height:190px;flex-shrink:0}
#comp-selector{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:4px;flex-shrink:0}
.comp-btn{background:none;border:1px solid #30363d;color:#8b949e;padding:1px 7px;border-radius:3px;cursor:pointer;font-size:10px}
.comp-btn.active{border-color:#58a6ff;color:#58a6ff;background:#1f3a5a}
#pipeline-title{font-size:10px;font-weight:700;color:#8b949e;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;flex-shrink:0}
#pipeline-svg{flex:1;min-height:0;width:100%;display:block}
.stat{flex:1;background:#0d1117;padding:6px 14px;display:flex;flex-direction:column;justify-content:center}
.stat-lbl{font-size:10px;color:#8b949e;text-transform:uppercase;letter-spacing:.05em}
.stat-val{font-size:20px;font-weight:700;color:#e6edf3;margin-top:1px;transition:color .3s}
#log{grid-column:1/-1;background:#0d1117;display:flex;flex-direction:column;overflow:hidden}
#log-hdr{display:flex;align-items:center;padding:3px 12px;background:#161b22;border-bottom:1px solid #30363d;flex-shrink:0;gap:8px}
#log-hdr span{font-size:10px;font-weight:700;color:#8b949e;text-transform:uppercase;letter-spacing:.07em}
#log-hdr button{margin-left:auto;background:none;border:1px solid #30363d;color:#8b949e;padding:2px 9px;border-radius:4px;cursor:pointer;font-size:10px}
#log-hdr button:hover{background:#21262d;color:#e6edf3}
#log-body{flex:1;overflow-y:auto;font-size:11px}
.entry{display:flex;align-items:baseline;gap:7px;padding:1px 12px;line-height:1.6;animation:fi .15s ease}
.entry:hover{background:#161b22}
.ts{color:#484f58;flex-shrink:0;font-size:10px}
.tag{flex-shrink:0;padding:0 5px;border-radius:3px;font-size:10px;font-weight:700}
.kv{color:#8b949e;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
svg{width:100%;height:100%;overflow:visible}
.gl{stroke:#21262d;stroke-width:1}
.al{stroke:#30363d;stroke-width:1}
.at{fill:#484f58;font-size:10px}
.albl{fill:#8b949e;font-size:10px}
.pt{cursor:pointer}
@keyframes fi{from{opacity:0;transform:translateY(-2px)}to{opacity:1;transform:none}}
@keyframes pop{0%{r:0;opacity:0}60%{r:8}100%{opacity:1}}
</style>
</head>
<body>
<div class="grid">
  <header>
    <h1>&#9881; eCalc Solver Debug</h1>
    <div id="conn">&#9679; Disconnected</div>
    <div id="sub-count" style="font-size:11px;color:#8b949e">subs: ?</div>
    <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:#8b949e;margin-left:4px">
      <label for="delay-input">Delay</label>
      <input id="delay-input" type="number" value="1000" min="0" max="5000" step="100"
        style="width:60px;background:#0d1117;border:1px solid #30363d;color:#e6edf3;padding:2px 5px;border-radius:4px;font-size:11px"
        oninput="stepDelay=parseInt(this.value)||0">
      <span>ms</span>
      <button onclick="eventQueue=[]" style="background:none;border:1px solid #30363d;color:#8b949e;padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px">&#x2715; Flush</button>
      <span id="queue-len" style="color:#484f58">q:0</span>
    </div>
    <button onclick="injectTest()" style="background:none;border:1px solid #30363d;color:#8b949e;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:11px">&#9654; Inject test</button>
    <div id="phase-badge">Idle</div>
  </header>

  <div class="panel" id="p-speed">
    <div class="panel-title">Speed &rarr; Outlet Pressure</div>
    <svg id="svg-speed" viewBox="0 0 560 230" preserveAspectRatio="xMidYMid meet"></svg>
  </div>

  <div id="right-col">
    <div class="panel" id="p-compressor">
      <div class="panel-title">Compressor Chart</div>
      <div id="comp-selector"></div>
      <svg id="svg-compressor" viewBox="0 0 290 190" preserveAspectRatio="xMidYMid meet" style="flex:1;min-height:0;width:100%"></svg>
    </div>
    <div class="panel" id="p-search">
      <div class="panel-title">Search Convergence</div>
      <svg id="svg-search" viewBox="0 0 290 155" preserveAspectRatio="xMidYMid meet" style="flex:1;min-height:0;width:100%"></svg>
    </div>
  </div>

  <div id="pipeline">
    <div id="pipeline-title">Process Pipeline</div>
    <svg id="pipeline-svg" viewBox="0 0 800 68" preserveAspectRatio="xMidYMid meet"></svg>
  </div>

  <div id="stats">
    <div class="stat"><div class="stat-lbl">Phase</div><div class="stat-val" id="s-phase">&#8212;</div></div>
    <div class="stat"><div class="stat-lbl">Outlet P (bara)</div><div class="stat-val" id="s-pout">&#8212;</div></div>
    <div class="stat"><div class="stat-lbl">Target P (bara)</div><div class="stat-val" id="s-ptgt">&#8212;</div></div>
    <div class="stat"><div class="stat-lbl">Evaluations</div><div class="stat-val" id="s-iters">0</div></div>
    <div class="stat"><div class="stat-lbl">&#916;P (bara)</div><div class="stat-val" id="s-dp">&#8212;</div></div>
  </div>

  <div id="log">
    <div id="log-hdr"><span>Event Log</span><button onclick="clearLog()">Clear</button></div>
    <div id="log-body"></div>
  </div>
</div>

<script>
const PC = {speed_search:'#58a6ff',anti_surge:'#f78166',pressure_control:'#56d364',feasibility:'#e3b341',root_finding:'#a5d6ff'};
const TC = {'solve.start':'#79c0ff','solve.end':'#56d364','phase.change':'#e3b341','speed.probe':'#58a6ff','binary_search.step':'#a5d6ff','root_finding.probe':'#cae8ff','pressure.probe':'#79c0ff','anti_surge.applied':'#f78166','pressure_control.applied':'#56d364'};
const PL = {speed_search:'Speed Search',anti_surge:'Anti-Surge',pressure_control:'Pressure Control',feasibility:'Feasibility',root_finding:'Root Finding',done:'\\u2713 Solved',failed:'\\u2717 Failed',idle:'Idle'};
const PBG = {speed_search:'#1f3a5a',anti_surge:'#4a2216',pressure_control:'#1a3a27',feasibility:'#3a3214',root_finding:'#0d2a3a',done:'#1a3a27',failed:'#3a1414',idle:'#21262d'};
const PTC = {speed_search:'#58a6ff',anti_surge:'#f78166',pressure_control:'#56d364',feasibility:'#e3b341',root_finding:'#a5d6ff',done:'#56d364',failed:'#f85149',idle:'#8b949e'};

let S = mkState();
function mkState(){return{phase:'idle',tgt:null,bounds:null,evals:[],steps:[],roots:[],sol:null,n:0,units:[],activeUnit:null,unitStats:{},compressorCharts:{},activeCompressorId:null,pipelineOutletPressure:null};}

// Unit type → display label + color
const UNIT_COLORS={
  Compressor:{bg:'#1f3a5a',border:'#58a6ff',label:'Compressor',icon:'C'},
  PressureDropper:{bg:'#3a1f3a',border:'#d2a8ff',label:'P.Drop',icon:'↓'},
  TemperatureSetter:{bg:'#3a2a1a',border:'#e3b341',label:'Temp.',icon:'T'},
  Choke:{bg:'#1a2e3a',border:'#79c0ff',label:'Choke',icon:'⊃'},
  Mixer:{bg:'#1a3a2a',border:'#56d364',label:'Mixer',icon:'M'},
  Splitter:{bg:'#2e2a1a',border:'#f0e68c',label:'Split',icon:'Y'},
};

// Stable per-tab ID — survives refresh, isolated between tabs
let CLIENT_ID = sessionStorage.getItem('sdbg_id');
if (!CLIENT_ID) {
  CLIENT_ID = Math.random().toString(36).slice(2) + Date.now().toString(36);
  sessionStorage.setItem('sdbg_id', CLIENT_ID);
}

let es;
let eventQueue = [];
let stepDelay = 1000;
let stepTimer = null;

function startDraining() {
  if (stepTimer !== null) return;
  function tick() {
    if (eventQueue.length > 0) {
      try { handle(eventQueue.shift()); } catch(x) { console.error(x); }
    }
    stepTimer = setTimeout(tick, stepDelay);
  }
  stepTimer = setTimeout(tick, stepDelay);
}

function connect(){
  if(es){es.close();}
  es=new EventSource(`/events?id=${CLIENT_ID}`);
  es.onopen=()=>{const el=document.getElementById('conn');el.textContent='\\u25cf Connected';el.className='on';};
  es.onerror=()=>{
    const el=document.getElementById('conn');el.textContent='\\u25cf Disconnected';el.className='';
    // EventSource auto-reconnects from CONNECTING state.
    // Only intervene if it has fully closed (e.g. server returned non-SSE response).
    if(es.readyState===EventSource.CLOSED){setTimeout(connect,2000);}
  };
  es.onmessage=e=>{
    try {
      const ev = JSON.parse(e.data);
      if (stepDelay > 0) {
        eventQueue.push(ev);
      } else {
        handle(ev);
      }
    } catch(x) { console.error(x); }
  };
  startDraining();
}

function handle(ev){
  addLog(ev);
  switch(ev.type){
    case 'solve.start':
      S=mkState();S.tgt=ev.target_pressure;S.bounds={min:ev.speed_min,max:ev.speed_max};S.phase='speed_search';
      if(ev.units&&ev.units.length){
        S.units=ev.units;
        for(const u of ev.units){
          if(u.chart){
            S.compressorCharts[u.id]={curves:u.chart.curves,opTrail:[]};
            if(!S.activeCompressorId)S.activeCompressorId=u.id;
          }
        }
        renderCompSelector();
      }
      setPhase('speed_search');
      set('s-ptgt',fmt(ev.target_pressure,2));set('s-iters','0');
      scheduleRender('speed','search','pipeline','compressor');break;

    case 'speed.probe':
      if(ev.pressure!=null){S.evals.push({speed:ev.speed,pressure:ev.pressure,phase:ev.phase||S.phase,result:ev.result||'ok'});}
      S.n++;
      if(ev.pressure!=null){set('s-pout',fmt(ev.pressure,2));updateDp(ev.pressure);}
      set('s-iters',S.n);scheduleRender('speed');break;

    case 'binary_search.step':
      S.steps.push({lower:ev.lower,upper:ev.upper,probe:ev.probe,accepted:ev.accepted,iter:ev.iteration,rel_diff:ev.rel_diff});
      scheduleRender('search');break;

    case 'root_finding.probe':
      if(S.tgt!=null){
        const p=S.tgt+ev.pressure_delta;
        S.evals.push({speed:ev.speed,pressure:p,phase:'root_finding',result:'ok'});
        S.roots.push({speed:ev.speed,delta:ev.pressure_delta,iter:ev.iteration});
        S.n++;set('s-pout',fmt(p,2));updateDp(p);set('s-iters',S.n);scheduleRender('speed');
      }break;

    case 'pressure.probe':
      if(ev.outlet_pressure!=null&&S.evals.length>0){
        const lastSpeed=S.evals[S.evals.length-1].speed;
        S.evals.push({speed:lastSpeed,pressure:ev.outlet_pressure,phase:ev.phase||S.phase,result:'ok'});
        S.n++;set('s-pout',fmt(ev.outlet_pressure,2));updateDp(ev.outlet_pressure);set('s-iters',S.n);
        S.pipelineOutletPressure=ev.outlet_pressure;
        scheduleRender('speed','pipeline');
      }break;

    case 'phase.change':S.phase=ev.phase;setPhase(ev.phase);break;

    case 'unit.enter':
      S.activeUnit=ev.unit_id;
      if(!S.unitStats[ev.unit_id])S.unitStats[ev.unit_id]={calls:0,lastInP:null,lastOutP:null};
      S.unitStats[ev.unit_id].calls++;
      S.unitStats[ev.unit_id].lastInP=ev.inlet_pressure;
      scheduleRender('pipeline');break;

    case 'unit.exit':
      if(S.unitStats[ev.unit_id])S.unitStats[ev.unit_id].lastOutP=ev.outlet_pressure;
      S.activeUnit=null;
      scheduleRender('pipeline');break;

    case 'compressor.op_point':
      if(S.compressorCharts[ev.unit_id]){
        S.compressorCharts[ev.unit_id].opTrail.push({rate:ev.rate,head:ev.head,phase:ev.phase,status:ev.status,speed:ev.speed});
        if(ev.status==='ok')S.activeCompressorId=ev.unit_id;
        scheduleRender('compressor');
      }break;

    case 'solve.end':
      S.sol=ev;S.activeUnit=null;
      if(ev.success){setPhase('done');if(ev.outlet_pressure!=null){set('s-pout',fmt(ev.outlet_pressure,2));updateDp(ev.outlet_pressure);}}
      else setPhase('failed');
      scheduleRender('speed','pipeline');break;
  }
}

function updateDp(p){
  if(S.tgt==null)return;
  const dp=p-S.tgt;
  const el=document.getElementById('s-dp');
  el.textContent=(dp>=0?'+':'')+fmt(dp,3);
  el.style.color=Math.abs(dp)<0.1?'#56d364':Math.abs(dp)<1?'#e3b341':'#f85149';
}

function setPhase(ph){
  S.phase=ph;
  const b=document.getElementById('phase-badge');
  b.textContent=PL[ph]||ph;b.style.background=PBG[ph]||'#21262d';b.style.color=PTC[ph]||'#8b949e';b.style.borderColor=PTC[ph]||'#30363d';
  const sv=document.getElementById('s-phase');sv.textContent=PL[ph]||ph;sv.style.color=PTC[ph]||'#e6edf3';
}
function set(id,v){document.getElementById(id).textContent=v;}
function fmt(v,d){if(v==null||isNaN(v))return'\\u2014';return Number(v).toFixed(d);}

// ── Render scheduling ─────────────────────────────────────────────
// Decouple state updates from DOM work: handle() only touches JS objects,
// scheduleRender() coalesces all pending redraws into one rAF callback.
let renderScheduled = false;
const dirty = {speed:false, search:false, pipeline:false, compressor:false};

function scheduleRender(...charts){
  if(charts.length===0){dirty.speed=dirty.search=dirty.pipeline=dirty.compressor=true;}
  else{for(const c of charts)dirty[c]=true;}
  if(!renderScheduled){
    renderScheduled=true;
    requestAnimationFrame(doRender);
  }
}

function doRender(){
  renderScheduled=false;
  if(dirty.speed){drawSpeed();dirty.speed=false;}
  if(dirty.search){drawSearch();dirty.search=false;}
  if(dirty.pipeline){drawPipeline();dirty.pipeline=false;}
  if(dirty.compressor){drawCompressor();dirty.compressor=false;}
}
function drawSpeed(){
  const svg=document.getElementById('svg-speed');
  const VW=560,VH=230,ml=65,mt=15,mr=22,mb=42;
  const W=VW-ml-mr,H=VH-mt-mb;

  if(S.evals.length===0&&S.tgt==null){
    svg.innerHTML='<text x="280" y="115" text-anchor="middle" fill="#484f58" font-size="12">Waiting for solver\u2026</text>';return;
  }

  const spds=S.evals.map(e=>e.speed);
  const prs=S.evals.map(e=>e.pressure);
  const allX=S.bounds?[S.bounds.min,S.bounds.max,...spds]:spds.length?spds:[0,1];
  const allY=S.tgt!=null?[S.tgt,...prs]:prs.length?prs:[0,1];
  let x0=Math.min(...allX),x1=Math.max(...allX);
  let y0=Math.min(...allY),y1=Math.max(...allY);
  if(x0===x1){x0-=1;x1+=1;}if(y0===y1){y0-=1;y1+=1;}
  const xp=(x1-x0)*.08,yp=(y1-y0)*.10;
  x0-=xp;x1+=xp;y0-=yp;y1+=yp;
  const xs=x=>ml+(x-x0)/(x1-x0)*W;
  const ys=y=>mt+H-(y-y0)/(y1-y0)*H;

  let o='';

  // grid + axes
  for(let i=0;i<=4;i++){
    const y=y0+(y1-y0)*i/4,py=ys(y);
    o+=`<line x1="${ml}" y1="${py}" x2="${ml+W}" y2="${py}" class="gl"/>`;
    o+=`<text x="${ml-5}" y="${py+4}" text-anchor="end" class="at">${fmt(y,1)}</text>`;
  }
  for(let i=0;i<=5;i++){
    const x=x0+(x1-x0)*i/5,px=xs(x);
    o+=`<line x1="${px}" y1="${mt}" x2="${px}" y2="${mt+H}" class="gl"/>`;
    o+=`<text x="${px}" y="${mt+H+14}" text-anchor="middle" class="at">${fmt(x,0)}</text>`;
  }
  o+=`<line x1="${ml}" y1="${mt}" x2="${ml}" y2="${mt+H}" class="al"/>`;
  o+=`<line x1="${ml}" y1="${mt+H}" x2="${ml+W}" y2="${mt+H}" class="al"/>`;
  o+=`<text x="${ml+W/2}" y="${VH-3}" text-anchor="middle" class="albl">Speed</text>`;
  o+=`<text x="10" y="${mt+H/2}" text-anchor="middle" class="albl" transform="rotate(-90 10 ${mt+H/2})">Pressure (bara)</text>`;

  // target pressure line
  if(S.tgt!=null){
    const py=ys(S.tgt);
    o+=`<line x1="${ml}" y1="${py}" x2="${ml+W}" y2="${py}" stroke="#f85149" stroke-width="1.5" stroke-dasharray="5,3" opacity=".9"/>`;
    o+=`<text x="${ml+W+3}" y="${py+4}" class="at" fill="#f85149" font-size="9">target</text>`;
  }

  // connecting lines per phase
  const byPhase={};
  for(const e of S.evals){
    if(!byPhase[e.phase])byPhase[e.phase]=[];
    byPhase[e.phase].push(e);
  }
  for(const [ph,pts] of Object.entries(byPhase)){
    const col=PC[ph]||'#8b949e';
    for(let i=1;i<pts.length;i++){
      const a=pts[i-1],b=pts[i];
      o+=`<line x1="${xs(a.speed)}" y1="${ys(a.pressure)}" x2="${xs(b.speed)}" y2="${ys(b.pressure)}" stroke="${col}" stroke-width="1" opacity=".25"/>`;
    }
  }

  // data points
  for(let i=0;i<S.evals.length;i++){
    const e=S.evals[i];
    const col=PC[e.phase]||'#8b949e';
    const px=xs(e.speed),py=ys(e.pressure);
    const last=i===S.evals.length-1;
    const r=last?6.5:4;
    const op=last?1:0.7;
    if(e.result==='too_high'||e.result==='too_low'){
      const s=r*.7;
      o+=`<line x1="${px-s}" y1="${py-s}" x2="${px+s}" y2="${py+s}" stroke="${col}" stroke-width="2" opacity="${op}"/>`;
      o+=`<line x1="${px+s}" y1="${py-s}" x2="${px-s}" y2="${py+s}" stroke="${col}" stroke-width="2" opacity="${op}"/>`;
    } else {
      o+=`<circle cx="${px}" cy="${py}" r="${r}" fill="${col}" opacity="${op}" class="pt"><title>${e.phase}: speed=${fmt(e.speed,1)} p=${fmt(e.pressure,2)} bara (${e.result})</title></circle>`;
    }
  }

  // solution ring
  if(S.sol&&S.sol.success&&S.sol.speed!=null&&S.sol.outlet_pressure!=null){
    const px=xs(S.sol.speed),py=ys(S.sol.outlet_pressure);
    o+=`<circle cx="${px}" cy="${py}" r="11" fill="none" stroke="#56d364" stroke-width="2.5" opacity=".9"/>`;
    o+=`<circle cx="${px}" cy="${py}" r="4" fill="#56d364"/>`;
  }

  svg.innerHTML=o;
}

// ── Search convergence chart ──────────────────────────────────────
function drawSearch(){
  const svg=document.getElementById('svg-search');
  const VW=295,VH=230,ml=28,mt=15,mr=8,mb=38;
  const W=VW-ml-mr,H=VH-mt-mb;

  if(S.steps.length===0){
    svg.innerHTML='<text x="147" y="115" text-anchor="middle" fill="#484f58" font-size="12">No search steps yet</text>';return;
  }

  const allX=S.steps.flatMap(s=>[s.lower,s.upper,s.probe]);
  let x0=Math.min(...allX),x1=Math.max(...allX);
  if(x0===x1){x0-=1;x1+=1;}
  const xp=(x1-x0)*.04;x0-=xp;x1+=xp;
  const xs=x=>ml+(x-x0)/(x1-x0)*W;

  const vis=S.steps.slice(-14);
  const n=vis.length;
  const rh=H/n;

  let o='';
  o+=`<line x1="${ml}" y1="${mt+H}" x2="${ml+W}" y2="${mt+H}" class="al"/>`;
  for(let i=0;i<=4;i++){
    const x=x0+(x1-x0)*i/4,px=xs(x);
    o+=`<line x1="${px}" y1="${mt}" x2="${px}" y2="${mt+H}" class="gl"/>`;
    o+=`<text x="${px}" y="${mt+H+14}" text-anchor="middle" class="at">${fmt(x,0)}</text>`;
  }
  o+=`<text x="${ml+W/2}" y="${VH-3}" text-anchor="middle" class="albl">Speed</text>`;
  o+=`<text x="${ml-4}" y="${mt-4}" class="at">#</text>`;

  for(let i=0;i<n;i++){
    const s=vis[i];
    const rowY=mt+i*rh;
    const bh=Math.max(rh*.45,4);
    const by=rowY+(rh-bh)/2;
    const px0=xs(s.lower),px1=xs(s.upper),pxm=xs(s.probe);
    const bg=s.accepted?'#1a3060':'#2d1515';
    const bc=s.accepted?'#58a6ff':'#f85149';
    const pc=s.accepted?'#58a6ff':'#f85149';
    o+=`<rect x="${px0}" y="${by}" width="${Math.max(px1-px0,1)}" height="${bh}" fill="${bg}" rx="2"/>`;
    o+=`<rect x="${px0}" y="${by}" width="${Math.max(px1-px0,1)}" height="${bh}" fill="none" stroke="${bc}" stroke-width=".5" rx="2"/>`;
    o+=`<line x1="${pxm}" y1="${by-1}" x2="${pxm}" y2="${by+bh+1}" stroke="${pc}" stroke-width="1.5"/>`;
    const idx=(S.steps.length-n)+i+1;
    o+=`<text x="${ml-3}" y="${by+bh/2+4}" text-anchor="end" class="at">${idx}</text>`;
    if(s.rel_diff!=null){
      const pct=(s.rel_diff*100).toFixed(1);
      o+=`<text x="${ml+W+3}" y="${by+bh/2+4}" class="at" font-size="9">${pct}%</text>`;
    }
  }

  svg.innerHTML=o;
}

// ── Compressor chart ──────────────────────────────────────────────
function renderCompSelector(){
  const sel=document.getElementById('comp-selector');
  const ids=Object.keys(S.compressorCharts);
  if(ids.length<=1){sel.innerHTML='';return;}
  sel.innerHTML=ids.map((id,i)=>`<button class="comp-btn${id===S.activeCompressorId?' active':''}" onclick="S.activeCompressorId='${id}';renderCompSelector();scheduleRender('compressor')">C${i+1}</button>`).join('');
}

function drawCompressor(){
  const svg=document.getElementById('svg-compressor');
  const uid=S.activeCompressorId;
  if(!uid||!S.compressorCharts[uid]){
    svg.innerHTML='<text x="145" y="95" text-anchor="middle" fill="#484f58" font-size="12">Waiting for compressor chart\u2026</text>';return;
  }
  const {curves,opTrail}=S.compressorCharts[uid];
  if(!curves||!curves.length){svg.innerHTML='<text x="145" y="95" text-anchor="middle" fill="#484f58" font-size="11">No chart data</text>';return;}

  const VW=290,VH=190,ml=44,mt=12,mr=18,mb=32;
  const W=VW-ml-mr,H=VH-mt-mb;

  const allR=curves.flatMap(c=>c.rates);
  const allH=curves.flatMap(c=>c.heads);
  const okPts=opTrail.filter(p=>p.rate!=null&&p.head!=null);
  const opR=okPts.map(p=>p.rate),opH=okPts.map(p=>p.head);

  let x0=Math.min(...allR,...(opR.length?opR:[Infinity]));
  let x1=Math.max(...allR,...(opR.length?opR:[-Infinity]));
  let y0=0,y1=Math.max(...allH,...(opH.length?opH:[-Infinity]),1);
  if(x0===x1){x0-=1;x1+=1;}
  const xp=(x1-x0)*.1,yp=y1*.08;
  x0=Math.max(0,x0-xp);x1+=xp;y1+=yp;
  const xs=x=>ml+(x-x0)/(x1-x0)*W;
  const ys=y=>mt+H-(y-y0)/(y1-y0)*H;

  let o='';
  // Grid + axes
  for(let i=0;i<=4;i++){
    const x=x0+(x1-x0)*i/4,px=xs(x);
    o+=`<line x1="${px}" y1="${mt}" x2="${px}" y2="${mt+H}" class="gl"/>`;
    o+=`<text x="${px}" y="${mt+H+13}" text-anchor="middle" class="at">${fmt(x,0)}</text>`;
  }
  for(let i=0;i<=4;i++){
    const y=y0+(y1-y0)*i/4,py=ys(y);
    o+=`<line x1="${ml}" y1="${py}" x2="${ml+W}" y2="${py}" class="gl"/>`;
    o+=`<text x="${ml-3}" y="${py+4}" text-anchor="end" class="at">${fmt(y,0)}</text>`;
  }
  o+=`<line x1="${ml}" y1="${mt}" x2="${ml}" y2="${mt+H}" class="al"/>`;
  o+=`<line x1="${ml}" y1="${mt+H}" x2="${ml+W}" y2="${mt+H}" class="al"/>`;
  o+=`<text x="${ml+W/2}" y="${VH-2}" text-anchor="middle" class="albl">Rate (Am\u00b3/h)</text>`;
  o+=`<text x="9" y="${mt+H/2}" text-anchor="middle" class="albl" transform="rotate(-90 9 ${mt+H/2})">Head (kJ/kg)</text>`;

  // Speed curves (grey, background)
  for(const curve of curves){
    const pts=curve.rates.map((r,j)=>`${xs(r)},${ys(curve.heads[j])}`).join(' ');
    o+=`<polyline points="${pts}" fill="none" stroke="#2c333d" stroke-width="1.5"/>`;
    // Speed label at right end of curve
    const lr=curve.rates[curve.rates.length-1],lh=curve.heads[curve.heads.length-1];
    o+=`<text x="${xs(lr)+3}" y="${ys(lh)+3}" fill="#484f58" font-size="8">${fmt(curve.speed,0)}</text>`;
  }

  // Surge line (min-rate points of each curve)
  if(curves.length>1){
    const sp=curves.map(c=>`${xs(c.rates[0])},${ys(c.heads[0])}`).join(' ');
    o+=`<polyline points="${sp}" fill="none" stroke="#f85149" stroke-width="1.5" stroke-dasharray="4,3" opacity=".75"/>`;
    o+=`<text x="${xs(curves[0].rates[0])-3}" y="${ys(curves[0].heads[0])+3}" text-anchor="end" fill="#f85149" font-size="8">surge</text>`;
  }

  // Stonewall (max-rate points of each curve)
  if(curves.length>1){
    const n=curves.length-1;
    const sp=curves.map(c=>`${xs(c.rates[c.rates.length-1])},${ys(c.heads[c.heads.length-1])}`).join(' ');
    o+=`<polyline points="${sp}" fill="none" stroke="#f0883e" stroke-width="1.5" stroke-dasharray="4,3" opacity=".75"/>`;
    o+=`<text x="${xs(curves[n].rates[curves[n].rates.length-1])+3}" y="${ys(curves[n].heads[curves[n].heads.length-1])+3}" fill="#f0883e" font-size="8">stonewall</text>`;
  }

  // Op trail connecting line
  if(okPts.length>1){
    const tp=okPts.map(p=>`${xs(p.rate)},${ys(p.head)}`).join(' ');
    o+=`<polyline points="${tp}" fill="none" stroke="#484f58" stroke-width="0.5"/>`;
  }

  // Op trail dots (fade older ones)
  const maxShow=80;
  const show=okPts.slice(-maxShow);
  for(let i=0;i<show.length;i++){
    const p=show[i];
    const col=PC[p.phase]||'#8b949e';
    const isLast=i===show.length-1;
    const r=isLast?6:3;
    const op=isLast?1:Math.max(0.15,(i/show.length)*0.6);
    if(p.status==='rate_too_low'){
      o+=`<line x1="${xs(p.rate)-5}" y1="${ys(0)}" x2="${xs(p.rate)-5}" y2="${ys(y1)}" stroke="#f85149" stroke-width="1" stroke-dasharray="3,3" opacity=".4"/>`;
      o+=`<circle cx="${xs(p.rate)}" cy="${mt+H/2}" r="4" fill="none" stroke="#f85149" stroke-width="1.5" opacity=".7"/>`;
    } else if(p.status==='rate_too_high'){
      o+=`<circle cx="${xs(p.rate)}" cy="${mt+H/2}" r="4" fill="none" stroke="#f0883e" stroke-width="1.5" opacity=".7"/>`;
    } else {
      o+=`<circle cx="${xs(p.rate)}" cy="${ys(p.head)}" r="${r}" fill="${col}" opacity="${op}"/>`;
      if(isLast){
        // Glow ring on current operating point
        o+=`<circle cx="${xs(p.rate)}" cy="${ys(p.head)}" r="${r+4}" fill="none" stroke="${col}" stroke-width="1.5" opacity=".5"/>`;
        // Crosshair lines
        o+=`<line x1="${ml}" y1="${ys(p.head)}" x2="${ml+W}" y2="${ys(p.head)}" stroke="${col}" stroke-width="0.5" stroke-dasharray="2,4" opacity=".4"/>`;
        o+=`<line x1="${xs(p.rate)}" y1="${mt}" x2="${xs(p.rate)}" y2="${mt+H}" stroke="${col}" stroke-width="0.5" stroke-dasharray="2,4" opacity=".4"/>`;
        // Label
        o+=`<text x="${xs(p.rate)+9}" y="${ys(p.head)-6}" fill="${col}" font-size="9">${fmt(p.rate,0)} Am\u00b3/h</text>`;
        o+=`<text x="${xs(p.rate)+9}" y="${ys(p.head)+6}" fill="${col}" font-size="9">${fmt(p.head,0)} kJ/kg</text>`;
      }
    }
  }

  svg.innerHTML=o;
}

// ── Pipeline graph ────────────────────────────────────────────────
function drawPipeline(){
  const svg=document.getElementById('pipeline-svg');
  const units=S.units;

  if(!units||units.length===0){
    svg.innerHTML='<text x="400" y="38" text-anchor="middle" fill="#484f58" font-size="12">No pipeline topology received yet \u2014 waiting for solve.start event</text>';
    return;
  }

  const VW=800,VH=68;
  const boxW=Math.min(110, Math.max(60, (VW - 40) / units.length - 28));
  const boxH=44;
  const arrowW=22;
  const totalW=units.length*boxW+(units.length-1)*arrowW;
  const startX=(VW-totalW)/2;
  const boxY=(VH-boxH)/2;

  let o='';

  for(let i=0;i<units.length;i++){
    const u=units[i];
    const cfg=UNIT_COLORS[u.type]||{bg:'#21262d',border:'#8b949e',label:u.type,icon:'?'};
    const x=startX+i*(boxW+arrowW);
    const isActive=S.activeUnit===u.id;
    const stats=S.unitStats[u.id]||{};
    const calls=stats.calls||0;

    // glow ring when active
    if(isActive){
      o+=`<rect x="${x-3}" y="${boxY-3}" width="${boxW+6}" height="${boxH+6}" rx="7" fill="${cfg.border}" opacity=".18"/>`;
    }

    // box
    const borderColor=isActive?cfg.border:(calls>0?cfg.border:'#30363d');
    const bgColor=isActive?cfg.bg:(calls>0?cfg.bg+'88':'#161b22');
    o+=`<rect x="${x}" y="${boxY}" width="${boxW}" height="${boxH}" rx="5" fill="${bgColor}" stroke="${borderColor}" stroke-width="${isActive?2:1}"/>`;

    // icon circle
    const iconR=10;
    const iconX=x+iconR+6;
    const iconY=boxY+boxH/2;
    o+=`<circle cx="${iconX}" cy="${iconY}" r="${iconR}" fill="${isActive?cfg.border:borderColor}" opacity="${calls>0?1:0.4}"/>`;
    o+=`<text x="${iconX}" y="${iconY+4}" text-anchor="middle" fill="#0d1117" font-size="10" font-weight="700">${cfg.icon}</text>`;

    // label
    const labelX=x+iconR*2+12;
    const labelW=boxW-(iconR*2+14);
    o+=`<text x="${labelX}" y="${boxY+16}" fill="${isActive?cfg.border:'#e6edf3'}" font-size="10" font-weight="${isActive?700:400}">${cfg.label}</text>`;

    // call count
    const callsColor=calls>0?(isActive?cfg.border:'#8b949e'):'#484f58';
    o+=`<text x="${labelX}" y="${boxY+28}" fill="${callsColor}" font-size="9">calls: ${calls}</text>`;

    // last outlet pressure
    if(stats.lastOutP!=null){
      o+=`<text x="${labelX}" y="${boxY+40}" fill="${isActive?cfg.border:'#8b949e'}" font-size="9">${fmt(stats.lastOutP,1)} bara</text>`;
    }

    // arrow to next
    if(i<units.length-1){
      const ax=x+boxW;
      const ay=boxY+boxH/2;
      const ax2=ax+arrowW;
      o+=`<line x1="${ax}" y1="${ay}" x2="${ax2-5}" y2="${ay}" stroke="#30363d" stroke-width="1.5"/>`;
      o+=`<polygon points="${ax2-5},${ay-4} ${ax2},${ay} ${ax2-5},${ay+4}" fill="#30363d"/>`;
    }
  }

  // inlet arrow
  if(units.length>0){
    o+=`<line x1="${startX-20}" y1="${VH/2}" x2="${startX-2}" y2="${VH/2}" stroke="#30363d" stroke-width="1.5"/>`;
    o+=`<polygon points="${startX-2},${VH/2-4} ${startX+3},${VH/2} ${startX-2},${VH/2+4}" fill="#30363d"/>`;
    o+=`<text x="${startX-22}" y="${VH/2+4}" text-anchor="end" fill="#484f58" font-size="9">in</text>`;
    // outlet arrow
    const lastX=startX+(units.length-1)*(boxW+arrowW)+boxW;
    o+=`<line x1="${lastX}" y1="${VH/2}" x2="${lastX+18}" y2="${VH/2}" stroke="#30363d" stroke-width="1.5"/>`;
    o+=`<polygon points="${lastX+14},${VH/2-4} ${lastX+20},${VH/2} ${lastX+14},${VH/2+4}" fill="#30363d"/>`;
    o+=`<text x="${lastX+22}" y="${VH/2-3}" fill="#484f58" font-size="9">out</text>`;
    if(S.pipelineOutletPressure!=null){
      const pc=PC[S.phase]||'#8b949e';
      o+=`<text x="${lastX+22}" y="${VH/2+9}" fill="${pc}" font-size="9" font-weight="700">${fmt(S.pipelineOutletPressure,1)} bara</text>`;
    }
  }

  svg.innerHTML=o;
}

// ── Event log ─────────────────────────────────────────────────────
function addLog(ev){
  // Skip high-frequency per-unit events from the log
  if(ev.type==='unit.enter'||ev.type==='unit.exit'||ev.type==='compressor.op_point')return;
  const body=document.getElementById('log-body');
  const el=document.createElement('div');
  el.className='entry';
  const ts=new Date().toLocaleTimeString('en',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const col=TC[ev.type]||'#8b949e';
  const kv=Object.entries(ev).filter(([k])=>!['type','ts'].includes(k)).map(([k,v])=>`${k}=${typeof v==='number'?fmt(v,3):v}`).join('  ');
  el.innerHTML=`<span class="ts">${ts}</span><span class="tag" style="background:${col}22;color:${col}">${ev.type}</span><span class="kv">${kv}</span>`;
  body.appendChild(el);
  while(body.children.length>800)body.removeChild(body.firstChild);
  if(body.scrollTop+body.clientHeight>body.scrollHeight-50)body.scrollTop=body.scrollHeight;
}
function clearLog(){document.getElementById('log-body').innerHTML='';}

connect();
scheduleRender();

// Poll /status every 3s to show subscriber count
setInterval(()=>{
  fetch('/status').then(r=>r.json()).then(d=>{
    document.getElementById('sub-count').textContent=`subs: ${d.subscribers}`;
  }).catch(()=>{});
  document.getElementById('queue-len').textContent=`q:${eventQueue.length}`;
  // Keep connection indicator in sync with actual EventSource state
  const el=document.getElementById('conn');
  if(es&&es.readyState===EventSource.OPEN){el.textContent='\\u25cf Connected';el.className='on';}
  else if(es&&es.readyState===EventSource.CONNECTING){el.textContent='\\u25cb Connecting\u2026';el.className='';}
  else{el.textContent='\\u25cf Disconnected';el.className='';}
}, 1000);

function injectTest(){
  const chart={curves:[
    {speed:8000, rates:[200,350,500,650], heads:[140,130,110,80]},
    {speed:10000,rates:[260,430,620,810], heads:[220,205,175,130]},
    {speed:12000,rates:[310,510,740,960], heads:[315,295,255,190]},
    {speed:14000,rates:[370,600,870,1120],heads:[430,405,350,260]},
  ]};
  const events=[
    {type:'solve.start',target_pressure:120,inlet_rate:45000,speed_min:8000,speed_max:14000,pipeline_id:'test',
     units:[{id:'u1',type:'Compressor',chart},{id:'u2',type:'PressureDropper'},{id:'u3',type:'Compressor',chart},{id:'u4',type:'TemperatureSetter'}]},
    // max speed check — show each unit active with its outlet pressure
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'compressor.op_point',unit_id:'u1',speed:14000,rate:450,head:380,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:92.5},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:92.5},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:90.1},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:90.1},
    {type:'compressor.op_point',unit_id:'u3',speed:14000,rate:450,head:355,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:133.8},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:133.8},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:131.2},
    {type:'speed.probe',speed:14000,pressure:131.2,phase:'speed_search',result:'ok'},
    // min speed check
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'compressor.op_point',unit_id:'u1',speed:8000,rate:450,head:115,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:72.3},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:72.3},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:70.5},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:70.5},
    {type:'compressor.op_point',unit_id:'u3',speed:8000,rate:450,head:107,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:96.8},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:96.8},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:94.5},
    {type:'speed.probe',speed:8000,pressure:94.5,phase:'speed_search',result:'ok'},
    // binary search steps
    {type:'binary_search.step',iteration:0,lower:8000,upper:14000,probe:11000,higher:false,accepted:true,rel_diff:0.273},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'compressor.op_point',unit_id:'u1',speed:11000,rate:450,head:240,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:80.1},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:80.1},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:78.3},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:78.3},
    {type:'compressor.op_point',unit_id:'u3',speed:11000,rate:450,head:224,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:114.2},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:114.2},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:112.1},
    {type:'speed.probe',speed:11000,pressure:112.1,phase:'speed_search',result:'ok'},
    {type:'binary_search.step',iteration:1,lower:11000,upper:14000,probe:12500,higher:false,accepted:true,rel_diff:0.118},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'compressor.op_point',unit_id:'u1',speed:12500,rate:450,head:285,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:86.7},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:86.7},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:84.9},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:84.9},
    {type:'compressor.op_point',unit_id:'u3',speed:12500,rate:450,head:268,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:123.5},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:123.5},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:121.3},
    {type:'speed.probe',speed:12500,pressure:121.3,phase:'speed_search',result:'ok'},
    // root finding
    {type:'root_finding.probe',iteration:0,speed:11750,pressure_delta:-3.6},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'compressor.op_point',unit_id:'u1',speed:11750,rate:450,head:262,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:83.4},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:83.4},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:81.6},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:81.6},
    {type:'compressor.op_point',unit_id:'u3',speed:11750,rate:450,head:248,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:118.7},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:118.7},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:116.4},
    {type:'root_finding.probe',iteration:1,speed:12264,pressure_delta:-0.04},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'compressor.op_point',unit_id:'u1',speed:12264,rate:450,head:277,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:85.9},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:85.9},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:84.1},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:84.1},
    {type:'compressor.op_point',unit_id:'u3',speed:12264,rate:450,head:261,phase:'speed_search',status:'ok'},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:122.1},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:122.1},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:120.0},
    // anti-surge: recirculation iterations — each runs full pipeline
    {type:'phase.change',phase:'anti_surge'},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'compressor.op_point',unit_id:'u1',speed:12264,rate:195,head:302,phase:'anti_surge',status:'rate_too_low',surge_rate:310},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:79.2},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:79.2},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:77.4},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:77.4},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:110.3},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:110.3},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:108.2},
    {type:'pressure.probe',phase:'anti_surge',outlet_pressure:108.2},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'compressor.op_point',unit_id:'u1',speed:12264,rate:253,head:299,phase:'anti_surge',status:'ok'},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:82.0},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:82.0},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:80.2},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:80.2},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:115.8},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:115.8},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:113.7},
    {type:'pressure.probe',phase:'anti_surge',outlet_pressure:113.7},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'compressor.op_point',unit_id:'u1',speed:12264,rate:310,head:296,phase:'anti_surge',status:'ok'},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:85.1},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:85.1},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:83.3},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:83.3},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:121.2},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:121.2},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:119.1},
    {type:'pressure.probe',phase:'anti_surge',outlet_pressure:119.1},
    // pressure control: choke/recirculation iterations
    {type:'phase.change',phase:'pressure_control'},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:85.1},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:85.1},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:83.3},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:83.3},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:124.6},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:124.6},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:122.4},
    {type:'pressure.probe',phase:'pressure_control',outlet_pressure:122.4},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:85.1},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:85.1},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:83.3},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:83.3},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:121.9},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:121.9},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:119.8},
    {type:'pressure.probe',phase:'pressure_control',outlet_pressure:119.8},
    {type:'unit.enter',unit_id:'u1',inlet_pressure:60.0},
    {type:'unit.exit',unit_id:'u1',outlet_pressure:85.1},
    {type:'unit.enter',unit_id:'u2',inlet_pressure:85.1},
    {type:'unit.exit',unit_id:'u2',outlet_pressure:83.3},
    {type:'unit.enter',unit_id:'u3',inlet_pressure:83.3},
    {type:'compressor.op_point',unit_id:'u3',speed:12264,rate:450,head:277,phase:'pressure_control',status:'ok'},
    {type:'unit.exit',unit_id:'u3',outlet_pressure:122.3},
    {type:'unit.enter',unit_id:'u4',inlet_pressure:122.3},
    {type:'unit.exit',unit_id:'u4',outlet_pressure:120.1},
    {type:'pressure.probe',phase:'pressure_control',outlet_pressure:120.1},
    {type:'compressor.op_point',unit_id:'u1',speed:12264,rate:450,head:277,phase:'pressure_control',status:'ok'},
    {type:'solve.end',success:true,speed:12264,outlet_pressure:120.04},
  ];
  for(const ev of events) eventQueue.push(ev);
}
</script>
</body>
</html>"""
