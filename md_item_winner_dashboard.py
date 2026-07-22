# -*- coding: utf-8
"""
B7000 아이템위너 모바일 대시보드 + 외부 터널 + 가격 알림.

  python md_item_winner_dashboard.py --tunnel
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from item_winner.dashboard_data import build_status, local_ip
from item_winner.env_util import load_env
from item_winner.notify import dispatch_new_alerts
from item_winner.tunnel import TunnelProcess, read_public_url

PORT_DEFAULT = 8765

PAGE_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#111827">
<title>STIX 아이템위너</title>
<link rel="manifest" href="/manifest.json">
<style>
  :root {
    --bg:#0f172a; --card:#1e293b; --text:#f1f5f9; --muted:#94a3b8;
    --ok:#22c55e; --warn:#f59e0b; --bad:#ef4444; --accent:#38bdf8;
  }
  *{box-sizing:border-box}
  body{margin:0;padding:12px 12px 32px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);line-height:1.45}
  h1{font-size:1.15rem;margin:0 0 4px}
  .sub{color:var(--muted);font-size:0.82rem;margin-bottom:8px;word-break:break-all}
  .pill{display:inline-block;padding:4px 10px;border-radius:999px;font-size:0.75rem;font-weight:600;margin:0 6px 6px 0}
  .pill.ok{background:#14532d;color:#86efac}.pill.bad{background:#450a0a;color:#fca5a5}.pill.neutral{background:#334155;color:#cbd5e1}
  .pill.link{background:#0c4a6e;color:#7dd3fc}
  .card{background:var(--card);border-radius:14px;padding:14px;margin-bottom:10px;border:1px solid #334155}
  .card h2{font-size:0.95rem;margin:0 0 10px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .cell label{display:block;font-size:0.72rem;color:var(--muted)}
  .cell strong{font-size:1.05rem}
  .action{margin-top:10px;padding:8px 10px;border-radius:10px;background:#0b1220;font-size:0.82rem}
  .action.HOLD{border-left:3px solid var(--ok)}.action.LOWER{border-left:3px solid var(--warn)}.action.RAISE{border-left:3px solid var(--accent)}
  .log{font-family:ui-monospace,Menlo,monospace;font-size:0.68rem;white-space:pre-wrap;word-break:break-all;color:#cbd5e1;max-height:220px;overflow:auto}
  .refresh{color:var(--muted);font-size:0.75rem;text-align:center;margin-top:8px}
  .btn{display:inline-block;margin:6px 6px 0 0;padding:8px 12px;border-radius:10px;border:1px solid #475569;background:#334155;color:#fff;font-size:0.82rem;cursor:pointer}
  .alert-item{padding:8px 0;border-bottom:1px solid #334155;font-size:0.82rem}
  .alert-item:last-child{border-bottom:none}
  .toast{position:fixed;left:12px;right:12px;bottom:16px;padding:12px 14px;border-radius:12px;background:#1d4ed8;color:#fff;font-size:0.85rem;box-shadow:0 8px 24px rgba(0,0,0,.4);z-index:99;display:none}
  .applied-yes{color:var(--ok)}.applied-no{color:var(--muted)}
</style>
</head>
<body>
  <h1>STIX B7000 아이템위너</h1>
  <div class="sub" id="meta">로딩 중…</div>
  <div id="links"></div>
  <button class="btn" id="btnNotify" type="button">🔔 알림 켜기</button>
  <div id="health"></div>
  <div class="card" id="alertBox" style="display:none">
    <h2>가격 알림</h2>
    <div id="alerts"></div>
  </div>
  <div id="skus"></div>
  <div class="card"><h2>최근 로그</h2><div class="log" id="log"></div></div>
  <div class="refresh">15초마다 자동 새로고침 · 가격 변경 시 알림</div>
  <div class="toast" id="toast"></div>
<script>
const LS_KEY = "stix_iw_seen_alerts";
let seen = new Set(JSON.parse(localStorage.getItem(LS_KEY) || "[]"));
let notifyOk = Notification.permission === "granted";

function fmt(n){if(n==null)return"-";return Number(n).toLocaleString("ko-KR")+"원";}
function showToast(msg){
  const t=document.getElementById("toast"); t.textContent=msg; t.style.display="block";
  setTimeout(()=>t.style.display="none", 5000);
}
function pushNotify(title, body){
  if(!notifyOk) return;
  try{ new Notification(title,{body,icon:"/icon.svg",tag:title}); }catch(e){}
}
function handleAlerts(alerts){
  if(!alerts||!alerts.length) return;
  const box=document.getElementById("alertBox");
  box.style.display="block";
  document.getElementById("alerts").innerHTML=alerts.map(a=>
    '<div class="alert-item"><strong>'+a.title+'</strong><br>'+a.body+'<br><span style="color:#94a3b8">'+a.ts+'</span></div>'
  ).join("");
  for(const a of alerts){
    if(seen.has(a.id)) continue;
    seen.add(a.id);
    pushNotify(a.title, a.body);
    showToast(a.title+" — "+a.body);
  }
  localStorage.setItem(LS_KEY, JSON.stringify([...seen].slice(-200)));
}
function render(data){
  const h=data.health;
  document.getElementById("meta").textContent=
    "갱신 "+data.generated_at.replace("T"," ")+" · "+h.interval_min+"분 주기 · "+(h.monitor_until==="continuous"?"상시":("종료 "+h.monitor_until.slice(0,10)));
  let links="";
  if(data.public_url) links+='<a class="pill link" href="'+data.public_url+'" target="_blank">외부 URL</a>';
  if(data.local_url) links+='<span class="pill neutral">Wi-Fi '+data.local_url.replace("http://","")+'</span>';
  document.getElementById("links").innerHTML=links;
  document.getElementById("health").innerHTML=
    '<span class="pill '+(h.alive?"ok":"bad")+'">'+(h.alive?"모니터 실행 중":"모니터 응답 없음")+'</span>'+
    (h.days_left!=null?'<span class="pill neutral">D-'+h.days_left+'</span>':'<span class="pill ok">상시</span>');
  document.getElementById("skus").innerHTML=data.skus.map(s=>{
    const hold=s.hold_price?' · 유지가 '+fmt(s.hold_price):'';
    const ap=s.applied===true?'<span class="applied-yes">반영됨</span>':s.applied===false?'<span class="applied-no">미반영</span>':'';
    return '<div class="card"><h2>'+s.label+'</h2><div class="grid">'+
      '<div class="cell"><label>내 가격</label><strong>'+fmt(s.my_price)+'</strong></div>'+
      '<div class="cell"><label>경쟁자</label><strong>'+fmt(s.competitor_price)+'</strong></div>'+
      '<div class="cell"><label>판단</label><strong>'+(s.action||'-')+'</strong></div>'+
      '<div class="cell"><label>권장</label><strong>'+fmt(s.recommended)+'</strong></div></div>'+
      '<div class="action '+(s.action||'')+'">'+(s.reason||'')+hold+' '+ap+'</div></div>';
  }).join("");
  document.getElementById("log").textContent=(data.recent_log||[]).join("\\n");
  handleAlerts(data.alerts);
}
document.getElementById("btnNotify").onclick=async()=>{
  if(!("Notification" in window)){ alert("이 브라우저는 알림을 지원하지 않습니다."); return; }
  const p=await Notification.requestPermission();
  notifyOk=(p==="granted");
  document.getElementById("btnNotify").textContent=notifyOk?"🔔 알림 켜짐":"🔔 알림 켜기";
  if(notifyOk) showToast("가격 변경 알림이 활성화되었습니다.");
};
async function refresh(){
  try{ render(await (await fetch("/api/status")).json()); }
  catch(e){ document.getElementById("meta").textContent="연결 실패"; }
}
if("serviceWorker" in navigator){ navigator.serviceWorker.register("/sw.js").catch(()=>{}); }
refresh(); setInterval(refresh, 15000);
</script>
</body>
</html>"""

MANIFEST = json.dumps(
    {
        "name": "STIX 아이템위너",
        "short_name": "STIX IW",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#111827",
        "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}],
    },
    ensure_ascii=False,
).encode("utf-8")

ICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" rx="20" fill="#111827"/>
<text x="50" y="62" text-anchor="middle" font-size="42" fill="#38bdf8" font-family="sans-serif">S</text>
</svg>"""

SW_JS = b"""
self.addEventListener('install', e => e.waitUntil(self.skipWaiting()));
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        routes = {
            "/": (PAGE_HTML.encode("utf-8"), "text/html; charset=utf-8"),
            "/index.html": (PAGE_HTML.encode("utf-8"), "text/html; charset=utf-8"),
            "/manifest.json": (MANIFEST, "application/json; charset=utf-8"),
            "/icon.svg": (ICON_SVG, "image/svg+xml"),
            "/sw.js": (SW_JS, "application/javascript; charset=utf-8"),
        }
        if path in routes:
            body, ctype = routes[path]
            self._send(200, body, ctype)
            return
        if path == "/api/status":
            dispatch_new_alerts(load_env())
            payload = json.dumps(build_status(), ensure_ascii=False).encode("utf-8")
            self._send(200, payload, "application/json; charset=utf-8")
            return
        self._send(404, b"not found", "text/plain")


def _alert_loop() -> None:
    env = load_env()
    while True:
        try:
            dispatch_new_alerts(env)
        except Exception:
            pass
        time.sleep(60)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=PORT_DEFAULT)
    parser.add_argument("--tunnel", action="store_true", help="Cloudflare quick tunnel (외부 접속)")
    args = parser.parse_args()

    tunnel: TunnelProcess | None = None
    if args.tunnel:
        tunnel = TunnelProcess(args.port)
        threading.Thread(target=tunnel.start, daemon=True).start()

    threading.Thread(target=_alert_loop, daemon=True).start()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    ip = local_ip()
    print("STIX Item Winner Dashboard")
    print(f"  PC:    http://127.0.0.1:{args.port}/")
    print(f"  Wi-Fi: http://{ip}:{args.port}/")
    if args.tunnel:
        print("  Tunnel starting… (public URL in item_winner/public_url.txt)")
        for _ in range(30):
            url = read_public_url()
            if url:
                print(f"  External: {url}")
                break
            time.sleep(1)
    print("Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        if tunnel:
            tunnel.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
