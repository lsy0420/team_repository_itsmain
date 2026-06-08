import network
import socket
import time
import errno
from machine import I2C, Pin

WIFI_SSID = "senWiFi_Free_sky"
WIFI_PASS  = "sudo25sky@"

i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=100000)
HL_ADDR      = 0x32
MIN_AREA     = 800
STABLE_COUNT = 3
TOP_N        = 3

COLOR_MAP = {
    1:  {"name": "빨간색", "en": "Red",      "hex": "#FF4444", "sym": "RED"},
    2:  {"name": "주황색", "en": "Orange",   "hex": "#FF8C00", "sym": "ORA"},
    3:  {"name": "노란색", "en": "Yellow",   "hex": "#FFD700", "sym": "YEL"},
    4:  {"name": "초록색", "en": "Green",    "hex": "#44BB44", "sym": "GRN"},
    5:  {"name": "파란색", "en": "Blue",     "hex": "#4488FF", "sym": "BLU"},
    6:  {"name": "보라색", "en": "Violet",   "hex": "#9966FF", "sym": "VIO"},
    7:  {"name": "흰색",   "en": "White",    "hex": "#CCCCCC", "sym": "WHT"},
    8:  {"name": "검은색", "en": "Black",    "hex": "#555555", "sym": "BLK"},
    9:  {"name": "회색",   "en": "Gray",     "hex": "#999999", "sym": "GRY"},
    10: {"name": "갈색",   "en": "Brown",    "hex": "#AA6633", "sym": "BRN"},
    11: {"name": "분홍색", "en": "Pink",     "hex": "#FF88BB", "sym": "PNK"},
    12: {"name": "하늘색", "en": "Sky Blue", "hex": "#66CCFF", "sym": "SKY"},
}
NONE_C = {"name": "없음", "en": "None", "hex": "#CCCCCC", "sym": "?"}

def get_info(cid):
    return COLOR_MAP.get(cid, {"name": "모름", "en": "Unknown",
                                "hex": "#CCCCCC", "sym": "?"})

def make_packet(cmd, data=None):
    if data is None:
        data = []
    body = [0x55, 0xAA, 0x11, len(data), cmd] + data
    body.append(sum(body) & 0xFF)
    return bytes(body)

def get_top_colors():
    # 최대 3번 재시도
    for attempt in range(3):
        try:
            i2c.writeto(HL_ADDR, make_packet(0x20))
            time.sleep_ms(80)
            r = list(i2c.readfrom(HL_ADDR, 64))
            scores = {}
            idx = 0
            while idx < len(r) - 5:
                if r[idx] == 0x55 and r[idx+1] == 0xAA:
                    length = r[idx+3]
                    if length >= 8 and idx + 5 + length <= len(r):
                        d    = r[idx+5: idx+5+length]
                        w    = d[4] | (d[5] << 8)
                        h    = d[6] | (d[7] << 8)
                        cid  = d[length-2] | (d[length-1] << 8)
                        area = w * h
                        if area >= MIN_AREA and 1 <= cid <= 50:
                            scores[cid] = scores.get(cid, 0) + area
                    idx += 5 + length + 1
                else:
                    idx += 1
            # 성공하면 바로 반환
            return sorted(scores, key=lambda k: scores[k], reverse=True)[:TOP_N]
        except Exception as e:
            time.sleep_ms(50)
    return []

def build_json(stable_ids):
    items = []
    for i in range(TOP_N):
        cid = stable_ids[i] if i < len(stable_ids) else None
        c   = get_info(cid) if cid else NONE_C
        items.append(
            '{"name":"' + c["name"] +
            '","en":"'  + c["en"]   +
            '","hex":"' + c["hex"]  +
            '","sym":"' + c["sym"]  + '"}'
        )
    return '{"top":[' + ','.join(items) + ']}'

def send_all(conn, data: bytes):
    CHUNK = 512
    mv = memoryview(data)
    for i in range(0, len(data), CHUNK):
        try:
            conn.send(mv[i:i+CHUNK])
        except:
            break
        time.sleep_ms(5)

HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Color Detector</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:system-ui,sans-serif;
  min-height:100vh;
  background:linear-gradient(135deg,#fff0f9,#f0f4ff,#f0fff8,#fffbf0);
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  gap:18px;overflow:hidden;
}
.bubble{
  position:fixed;border-radius:50%;pointer-events:none;
  animation:rise linear infinite;
}
@keyframes rise{
  0%{transform:translateY(110vh);opacity:.25}
  100%{transform:translateY(-20vh);opacity:0}
}
.title{
  font-size:24px;font-weight:900;letter-spacing:2px;
  color:#ff6eb4;
  animation:hue 5s linear infinite;
  position:relative;z-index:2;
}
@keyframes hue{to{filter:hue-rotate(360deg)}}
.main-card{
  background:rgba(255,255,255,0.80);
  border:3px solid #ddd;
  border-radius:34px;padding:32px 44px 26px;
  text-align:center;width:300px;
  box-shadow:0 8px 32px rgba(0,0,0,.08);
  transition:border-color .5s,box-shadow .5s;
  position:relative;z-index:2;
}
.ring-wrap{position:relative;width:150px;margin:0 auto 16px}
.pulse{
  position:absolute;inset:-14px;border-radius:50%;
  border:3px solid #ddd;
  animation:pls 2.2s ease-out infinite;opacity:0;
}
.pulse2{animation-delay:.9s}
@keyframes pls{0%{transform:scale(1);opacity:.6}100%{transform:scale(1.5);opacity:0}}
.main-circle{
  width:150px;height:150px;border-radius:50%;
  background:#ddd;
  display:flex;align-items:center;justify-content:center;
  font-size:22px;font-weight:900;color:#fff;
  letter-spacing:1px;
  box-shadow:0 0 0 5px rgba(255,255,255,.9),0 6px 24px #ddd;
  animation:fl 3s ease-in-out infinite;
  transition:background .5s,box-shadow .5s;
}
@keyframes fl{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
.main-name{
  font-size:32px;font-weight:900;color:#bbb;
  transition:all .5s;margin-bottom:4px;
}
.main-en{font-size:13px;color:#bbb;margin-bottom:12px}
.hex-badge{
  display:inline-block;padding:7px 22px;
  border-radius:999px;font-size:13px;font-weight:700;
  background:#ddd;color:#fff;transition:all .5s;
}
.sub-row{display:flex;gap:12px;position:relative;z-index:2}
.sub-card{
  background:rgba(255,255,255,0.78);
  border:2px solid #eee;border-radius:22px;
  padding:14px 16px;text-align:center;width:138px;
  box-shadow:0 4px 16px rgba(0,0,0,.06);transition:all .5s;
}
.sub-rank{font-size:11px;color:#ccc;letter-spacing:1px;margin-bottom:8px;font-weight:700}
.sub-circle{
  width:58px;height:58px;border-radius:50%;background:#ddd;
  display:flex;align-items:center;justify-content:center;
  font-size:13px;font-weight:900;color:#fff;
  box-shadow:0 0 0 3px rgba(255,255,255,.9),0 3px 12px #ddd;
  margin:0 auto 8px;animation:fl 3.6s ease-in-out infinite;
  transition:background .5s,box-shadow .5s;
}
.sub-name{font-size:14px;font-weight:800;color:#555;margin-bottom:2px}
.sub-en{font-size:11px;color:#bbb;margin-bottom:6px}
.sub-hex{
  font-size:11px;font-weight:700;padding:3px 10px;
  border-radius:999px;background:#ddd;color:#fff;
  transition:all .5s;display:inline-block;
}
.status-bar{
  font-size:12px;color:#bbb;
  display:flex;align-items:center;gap:6px;
  background:rgba(255,255,255,.8);
  padding:6px 16px;border-radius:999px;
  box-shadow:0 2px 10px rgba(0,0,0,.05);
  position:relative;z-index:2;
}
.dot{width:8px;height:8px;border-radius:50%;background:#69db7c;animation:blink 1.5s ease infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.1}}
</style>
</head>
<body>
<div class="title">&#127800; Color Detector &#127800;</div>
<div class="main-card" id="MC">
  <div class="ring-wrap">
    <div class="pulse" id="R1"></div>
    <div class="pulse pulse2" id="R2"></div>
    <div class="main-circle" id="CC">?</div>
  </div>
  <div class="main-name" id="MN">Waiting...</div>
  <div class="main-en"   id="ME">Waiting</div>
  <div class="hex-badge" id="MB">#888</div>
</div>
<div class="sub-row">
  <div class="sub-card" id="S1">
    <div class="sub-rank">&#10024; 2nd</div>
    <div class="sub-circle" id="S1C">?</div>
    <div class="sub-name" id="S1N">None</div>
    <div class="sub-en"   id="S1E">None</div>
    <div class="sub-hex"  id="S1H">#888</div>
  </div>
  <div class="sub-card" id="S2">
    <div class="sub-rank">&#11088; 3rd</div>
    <div class="sub-circle" id="S2C">?</div>
    <div class="sub-name" id="S2N">None</div>
    <div class="sub-en"   id="S2E">None</div>
    <div class="sub-hex"  id="S2H">#888</div>
  </div>
</div>
<div class="status-bar"><span class="dot"></span>Live Detecting</div>
<script>
const BC=['#ffadad','#ffd6a5','#fdffb6','#caffbf','#9bf6ff','#a0c4ff','#bdb2ff','#ffc6ff'];
for(let i=0;i<14;i++){
  const b=document.createElement('div');
  b.className='bubble';
  const sz=30+Math.random()*100;
  b.style.cssText='width:'+sz+'px;height:'+sz+'px;left:'+(Math.random()*100)+'vw;bottom:'+(-sz)+'px;background:'+BC[i%BC.length]+';opacity:.22;animation-duration:'+(10+Math.random()*12)+'s;animation-delay:'+(Math.random()*8)+'s';
  document.body.appendChild(b);
}
function tc(h){
  const r=parseInt(h.slice(1,3),16),g=parseInt(h.slice(3,5),16),b=parseInt(h.slice(5,7),16);
  return(r*299+g*587+b*114)/1000>160?'#444':'#fff';
}
function upMain(d){
  const mc=document.getElementById('MC');
  mc.style.borderColor=d.hex;
  mc.style.boxShadow='0 8px 32px '+d.hex+'44';
  document.getElementById('R1').style.borderColor=d.hex;
  document.getElementById('R2').style.borderColor=d.hex;
  const cc=document.getElementById('CC');
  cc.style.background=d.hex;
  cc.style.boxShadow='0 0 0 5px rgba(255,255,255,.9),0 6px 24px '+d.hex+'88';
  cc.textContent=d.sym;
  const mn=document.getElementById('MN');
  mn.textContent=d.name;mn.style.color=d.hex;
  document.getElementById('ME').textContent=d.en;
  const mb=document.getElementById('MB');
  mb.textContent=d.hex;mb.style.background=d.hex;mb.style.color=tc(d.hex);
}
function upSub(n,d){
  const sd=document.getElementById('S'+n);
  const sc=document.getElementById('S'+n+'C');
  const sn=document.getElementById('S'+n+'N');
  const se=document.getElementById('S'+n+'E');
  const sh=document.getElementById('S'+n+'H');
  sd.style.borderColor=d.hex+'99';
  sc.style.background=d.hex;
  sc.style.boxShadow='0 0 0 3px rgba(255,255,255,.9),0 3px 12px '+d.hex+'88';
  sc.textContent=d.sym;
  sn.textContent=d.name;
  se.textContent=d.en;
  sh.textContent=d.hex;sh.style.background=d.hex;sh.style.color=tc(d.hex);
}
const NL={name:'None',en:'None',hex:'#CCCCCC',sym:'?'};
let pj='';
async function poll(){
  try{
    const r=await fetch('/color',{signal:AbortSignal.timeout(2000)});
    if(!r.ok)throw new Error(r.status);
    const d=await r.json();
    const j=JSON.stringify(d);
    if(j!==pj){pj=j;upMain(d.top[0]||NL);upSub(1,d.top[1]||NL);upSub(2,d.top[2]||NL);}
  }catch(e){console.warn(e);}
  setTimeout(poll,450);
}
poll();
</script>
</body>
</html>"""

# ── WiFi ───────────────────────────────────────
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)
print("WiFi 연결 중...")
for _ in range(30):
    if wlan.isconnected(): break
    time.sleep(0.5)
if not wlan.isconnected():
    print("WiFi 실패!")
    raise SystemExit
ip = wlan.ifconfig()[0]
print("http://" + ip)

HTML_BYTES = HTML.encode('utf-8')
print("HTML 크기:", len(HTML_BYTES), "bytes")

# ── 서버 non-blocking으로 변경! ───────────────
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('0.0.0.0', 80))
srv.listen(3)
srv.setblocking(False)  # ← non-blocking 으로 변경!
print("서버 OK - http://" + ip)

stable   = [None] * TOP_N
cand     = [None] * TOP_N
cand_cnt = [0]    * TOP_N

while True:
    # ── HuskyLens 읽기 (매 루프마다) ─────────
    top_ids = get_top_colors()
    for i in range(TOP_N):
        nid = top_ids[i] if i < len(top_ids) else None
        if nid == cand[i]:
            cand_cnt[i] += 1
        else:
            cand[i] = nid
            cand_cnt[i] = 1
        if cand_cnt[i] >= STABLE_COUNT:
            stable[i] = cand[i]

    # ── HTTP 처리 ─────────────────────────────
    try:
        conn, addr = srv.accept()
        conn.settimeout(2.0)
        try:
            req = conn.recv(256).decode('utf-8', 'ignore')
        except:
            req = ''

        if 'GET /color' in req:
            body = build_json(stable).encode('utf-8')
            hdr = (
                'HTTP/1.1 200 OK\r\n'
                'Content-Type: application/json; charset=utf-8\r\n'
                'Content-Length: ' + str(len(body)) + '\r\n'
                'Connection: close\r\n\r\n'
            ).encode()
            send_all(conn, hdr + body)
        else:
            hdr = (
                'HTTP/1.1 200 OK\r\n'
                'Content-Type: text/html; charset=utf-8\r\n'
                'Content-Length: ' + str(len(HTML_BYTES)) + '\r\n'
                'Connection: close\r\n\r\n'
            ).encode()
            send_all(conn, hdr + HTML_BYTES)
        conn.close()

    except OSError as e:
        if e.args[0] != errno.EAGAIN:
            print("소켓 오류:", e)
    except Exception as e:
        print("일반 오류:", e)

    time.sleep_ms(20)  # ← 20ms로 줄여서 I2C 더 자주 읽기
