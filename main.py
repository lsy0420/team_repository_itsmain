# =============================================

#  색맹/색약 보조 색상 인식기 - 웹서버 버전 v2.0

#  HuskyLens (Color Recognition) + Pico W

#

#  배선:

#    HuskyLens SDA -> GP6 (I2C1)

#    HuskyLens SCL -> GP7 (I2C1)

#    HuskyLens VCC -> VBUS (5V, 40번 핀)

#    HuskyLens GND -> GND

# =============================================

 

import network

import socket

import time

import json

from machine import I2C, Pin

 

# ── WiFi 설정 (별도 분리 권장) ──────────────────

WIFI_SSID = "senWiFi_Free_sky"

WIFI_PASS = "sudo25sky@"

 

# ── HuskyLens 설정 ───────────────────────────

i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=100000)

HL_ADDR   = 0x32

MIN_AREA  = 800      # 너무 작은 블록 무시

STABLE_COUNT = 3     # 안정화 프레임 수

TOP_N     = 3        # 상위 몇 개 색상 추적

 

# ── 색상 테이블 ──────────────────────────────

COLOR_MAP = {

    1:  {"name": "빨간색",  "en": "Red",      "hex": "#FF4444", "emoji": ""},

    2:  {"name": "주황색",  "en": "Orange",   "hex": "#FF8C00", "emoji": ""},

    3:  {"name": "노란색",  "en": "Yellow",   "hex": "#FFD700", "emoji": ""},

    4:  {"name": "초록색",  "en": "Green",    "hex": "#44BB44", "emoji": ""},

    5:  {"name": "파란색",  "en": "Blue",     "hex": "#4488FF", "emoji": ""},

    6:  {"name": "보라색",  "en": "Violet",   "hex": "#9966FF", "emoji": ""},

    7:  {"name": "흰색",    "en": "White",    "hex": "#EEEEEE", "emoji": ""},

    8:  {"name": "검은색",  "en": "Black",    "hex": "#444444", "emoji": ""},

    9:  {"name": "회색",    "en": "Gray",     "hex": "#999999", "emoji": "🩶"},

    10: {"name": "갈색",    "en": "Brown",    "hex": "#AA6633", "emoji": ""},

    11: {"name": "분홍색",  "en": "Pink",     "hex": "#FF88BB", "emoji": ""},

    12: {"name": "하늘색",  "en": "Sky Blue", "hex": "#66CCFF", "emoji": "🩵"},

}

 

DEFAULT_COLOR = {"name": "없음", "en": "None", "hex": "#888888", "emoji": ""}

 

def get_info(cid):

    return COLOR_MAP.get(cid, {"name": "알 수 없음", "en": "Unknown",

                                "hex": "#CCCCCC", "emoji": ""})

 

# ── HuskyLens 패킷 ────────────────────────────

def make_packet(cmd, data=None):

    if data is None:

        data = []

    body = [0x55, 0xAA, 0x11, len(data), cmd] + data

    body.append(sum(body) & 0xFF)

    return bytes(body)

 

# ── 상위 N개 색상 ID 반환 ──────────────────────

def get_top_colors():

    """카메라에서 면적 기준 상위 TOP_N 색상 ID 목록 반환"""

    try:

        i2c.writeto(HL_ADDR, make_packet(0x20))

        time.sleep_ms(50)

        r = list(i2c.readfrom(HL_ADDR, 64))

    except Exception as e:

        print("I2C 오류:", e)

        return []

 

    scores = {}   # {cid: 총 면적}

    idx = 0

    while idx < len(r) - 5:

        if r[idx] == 0x55 and r[idx+1] == 0xAA:

            length = r[idx+3]

            if length >= 8 and idx + 5 + length <= len(r):

                d = r[idx+5: idx+5+length]

                w   = d[4] | (d[5] << 8)

                h   = d[6] | (d[7] << 8)

                cid = d[length-2] | (d[length-1] << 8)

                area = w * h

                if area >= MIN_AREA and 1 <= cid <= 50:

                    scores[cid] = scores.get(cid, 0) + area

            idx += 5 + length + 1

        else:

            idx += 1

 

    # 면적 내림차순 정렬 → 상위 TOP_N

    sorted_ids = sorted(scores, key=lambda k: scores[k], reverse=True)

    return sorted_ids[:TOP_N]

 

# ── WiFi 연결 ─────────────────────────────────

wlan = network.WLAN(network.STA_IF)

wlan.active(True)

wlan.connect(WIFI_SSID, WIFI_PASS)

print("와이파이 연결 중...")

for _ in range(30):

    if wlan.isconnected():

        break

    time.sleep(0.5)

 

if not wlan.isconnected():

    print("와이파이 연결 실패!")

    raise SystemExit

 

ip = wlan.ifconfig()[0]

print("IP: " + ip)

print("접속 주소   http://" + ip)

 

# ── HTML (한 번만 메모리에 올림) ──────────────

HTML = b"""<!DOCTYPE html>

<html lang="ko">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width,initial-scale=1">

<title>\xec\x83\x89\xec\x83\x81 \xec\x9d\xb8\xec\x8b\x9d\xea\xb8\xb0 \xf0\x9f\x8c\x88</title>

<style>

@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;900&display=swap');

*{margin:0;padding:0;box-sizing:border-box}

body{font-family:'Nunito',sans-serif;background:#0d0d1a;min-height:100vh;

     display:flex;flex-direction:column;align-items:center;justify-content:center;

     overflow:hidden;gap:24px}

 

/* ─── 배경 파티클 캔버스 ─── */

#bgCanvas{position:fixed;top:0;left:0;pointer-events:none;z-index:0}

 

/* ─── 타이틀 ─── */

.title{position:relative;z-index:2;font-size:22px;font-weight:900;

       color:white;letter-spacing:3px;text-align:center;

       text-shadow:0 0 20px rgba(255,255,255,.3)}

.title span{background:linear-gradient(90deg,#ff6ec7,#ffe66d,#6ef0ff,#a8ff78);

            -webkit-background-clip:text;-webkit-text-fill-color:transparent;

            background-clip:text;animation:hueShift 4s linear infinite}

@keyframes hueShift{0%{filter:hue-rotate(0deg)}100%{filter:hue-rotate(360deg)}}

 

/* ─── 카드 레이아웃 ─── */

.scene{position:relative;z-index:2;display:flex;flex-direction:column;

       align-items:center;gap:20px}

 

/* ─── 메인 카드 ─── */

.main-card{

  background:rgba(255,255,255,0.07);

  backdrop-filter:blur(24px);

  border:2px solid rgba(255,255,255,0.15);

  border-radius:40px;

  padding:40px 52px 36px;

  text-align:center;

  width:340px;

  position:relative;

  overflow:hidden;

  transition:border-color .6s;

}

.main-card::before{

  content:'';position:absolute;inset:0;

  background:radial-gradient(circle at 50% 0%,var(--glow,transparent) 0%,transparent 70%);

  opacity:.25;pointer-events:none;transition:background .6s;

}

 

/* 빛나는 링 */

.ring-wrap{position:relative;width:170px;margin:0 auto 20px}

.pulse{position:absolute;inset:-18px;border-radius:50%;

       border:3px solid var(--color,#888);

       animation:pulseAnim 2.2s ease-out infinite;opacity:0}

.pulse2{animation-delay:.8s}

@keyframes pulseAnim{0%{transform:scale(1);opacity:.55}100%{transform:scale(1.5);opacity:0}}

 

/* 메인 원 */

.main-circle{

  width:170px;height:170px;border-radius:50%;

  background:var(--color,#888);

  display:flex;align-items:center;justify-content:center;

  font-size:60px;

  transition:background .6s,box-shadow .6s;

  box-shadow:0 0 40px var(--color,#888),0 0 80px var(--color,#88888855);

  animation:float 3s ease-in-out infinite;

}

@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}

 

.main-name{font-size:38px;font-weight:900;color:white;

           text-shadow:0 0 20px var(--color,#888);transition:all .6s;margin-bottom:2px}

.main-en{font-size:15px;color:rgba(255,255,255,.35);margin-bottom:16px}

.hex-badge{

  display:inline-block;padding:8px 26px;border-radius:999px;

  font-size:13px;font-weight:700;letter-spacing:1px;

  background:var(--color,#888);

  color:var(--badge-text,#fff);

  box-shadow:0 4px 16px var(--color,#88888888);

  transition:all .6s;

}

 

/* ─── 서브 카드 2개 ─── */

.sub-row{display:flex;gap:14px}

.sub-card{

  background:rgba(255,255,255,0.06);

  backdrop-filter:blur(16px);

  border:1.5px solid rgba(255,255,255,0.1);

  border-radius:26px;

  padding:18px 22px;

  text-align:center;

  width:148px;

  transition:border-color .5s;

  position:relative;overflow:hidden;

}

.sub-card::before{

  content:'';position:absolute;inset:0;

  background:radial-gradient(circle at 50% 0%,var(--sc,transparent) 0%,transparent 70%);

  opacity:.2;pointer-events:none;transition:background .5s;

}

.sub-rank{font-size:11px;color:rgba(255,255,255,.35);letter-spacing:2px;margin-bottom:10px}

.sub-circle{

  width:64px;height:64px;border-radius:50%;

  background:var(--sc,#888);margin:0 auto 10px;

  display:flex;align-items:center;justify-content:center;font-size:26px;

  box-shadow:0 0 16px var(--sc,#888);

  transition:background .5s,box-shadow .5s;

  animation:float 3.4s ease-in-out infinite;

}

.sub-name{font-size:15px;font-weight:700;color:white;margin-bottom:2px}

.sub-en{font-size:11px;color:rgba(255,255,255,.3);margin-bottom:8px}

.sub-hex{font-size:11px;font-weight:700;

         padding:4px 12px;border-radius:999px;

         background:var(--sc,#888);color:var(--sb-text,#fff);

         transition:all .5s}

 

/* ─── 상태 바 ─── */

.status-bar{

  position:relative;z-index:2;

  display:flex;align-items:center;gap:8px;

  font-size:12px;color:rgba(255,255,255,.3);

}

.dot{width:8px;height:8px;border-radius:50%;

     background:#44ff88;animation:blink 1.5s ease infinite}

@keyframes blink{0%,100%{opacity:1}50%{opacity:.15}}

 

/* ─── 무지개 테두리 애니메이션 ─── */

@keyframes rainbowBorder{

  0%{border-color:#ff6ec7}25%{border-color:#ffe66d}

  50%{border-color:#6ef0ff}75%{border-color:#a8ff78}100%{border-color:#ff6ec7}

}

.idle-border{animation:rainbowBorder 3s linear infinite}

</style>

</head>

<body>

<canvas id="bgCanvas"></canvas>

 

<div class="title"><span> 색상 인식기 </span></div>

 

<div class="scene">

  <!-- 메인 카드 -->

  <div class="main-card idle-border" id="mainCard" style="--color:#888;--glow:#888">

    <div class="ring-wrap">

      <div class="pulse"  id="ring1"></div>

      <div class="pulse pulse2" id="ring2"></div>

      <div class="main-circle" id="mainCircle"></div>

    </div>

    <div class="main-name" id="mainName">대기 중...</div>

    <div class="main-en"   id="mainEn">Waiting</div>

    <div class="hex-badge" id="mainBadge">#888888</div>

  </div>

 

  <!-- 서브 카드 2개 -->

  <div class="sub-row">

    <div class="sub-card" id="sub1" style="--sc:#888">

      <div class="sub-rank"> 2위</div>

      <div class="sub-circle" id="sub1Circle"></div>

      <div class="sub-name"  id="sub1Name">없음</div>

      <div class="sub-en"    id="sub1En">None</div>

      <div class="sub-hex"   id="sub1Hex">#888888</div>

    </div>

    <div class="sub-card" id="sub2" style="--sc:#888">

      <div class="sub-rank"> 3위</div>

      <div class="sub-circle" id="sub2Circle"></div>

      <div class="sub-name"  id="sub2Name">없음</div>

      <div class="sub-en"    id="sub2En">None</div>

      <div class="sub-hex"   id="sub2Hex">#888888</div>

    </div>

  </div>

</div>

 

<div class="status-bar"><span class="dot"></span>실시간 감지 중</div>

 

<script>

// ── 배경 파티클 ──────────────────────────────

const canvas = document.getElementById('bgCanvas');

const ctx    = canvas.getContext('2d');

function resize(){canvas.width=innerWidth;canvas.height=innerHeight}

resize(); window.addEventListener('resize',resize);

 

const COLS=['#FF4444','#FF8C00','#FFD700','#44BB44','#4488FF',

            '#9966FF','#FF88BB','#66CCFF','#ffffff'];

const pts=[];

for(let i=0;i<80;i++){

  pts.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight,

    r:1.5+Math.random()*3.5,c:COLS[i%COLS.length],

    vx:(Math.random()-.5)*.5,vy:(Math.random()-.5)*.5,a:Math.random()*Math.PI*2});

}

(function loop(){

  ctx.clearRect(0,0,canvas.width,canvas.height);

  pts.forEach(p=>{

    p.x+=p.vx; p.y+=p.vy; p.a+=.018;

    if(p.x<0)p.x=canvas.width; if(p.x>canvas.width)p.x=0;

    if(p.y<0)p.y=canvas.height;if(p.y>canvas.height)p.y=0;

    ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);

    ctx.fillStyle=p.c;

    ctx.globalAlpha=.12+.1*Math.sin(p.a);

    ctx.fill();

  });

  ctx.globalAlpha=1;

  requestAnimationFrame(loop);

})();

 

// ── 유틸 ─────────────────────────────────────

function textColor(hex){

  const r=parseInt(hex.slice(1,3),16),

        g=parseInt(hex.slice(3,5),16),

        b=parseInt(hex.slice(5,7),16);

  return(r*299+g*587+b*114)/1000>150?'#222':'#fff';

}

function setVar(el,k,v){el.style.setProperty(k,v)}

 

// ── 메인 업데이트 ─────────────────────────────

function updateMain(d){

  const card=document.getElementById('mainCard');

  setVar(card,'--color',d.hex); setVar(card,'--glow',d.hex);

  card.style.borderColor=d.hex;

  card.classList.remove('idle-border');

 

  document.getElementById('ring1').style.borderColor=d.hex;

  document.getElementById('ring2').style.borderColor=d.hex;

 

  const circ=document.getElementById('mainCircle');

  circ.style.background=d.hex;

  circ.textContent=d.emoji;

 

  document.getElementById('mainName').textContent=d.name;

  document.getElementById('mainName').style.textShadow='0 0 20px '+d.hex;

  document.getElementById('mainEn').textContent=d.en;

 

  const badge=document.getElementById('mainBadge');

  badge.textContent=d.hex;

  badge.style.background=d.hex;

  badge.style.color=textColor(d.hex);

  badge.style.boxShadow='0 4px 16px '+d.hex+'99';

}

 

function updateSub(idx,d){

  const card =document.getElementById('sub'+idx);

  const circ =document.getElementById('sub'+idx+'Circle');

  const name =document.getElementById('sub'+idx+'Name');

  const en   =document.getElementById('sub'+idx+'En');

  const hex  =document.getElementById('sub'+idx+'Hex');

  setVar(card,'--sc',d.hex);

  card.style.borderColor=d.hex+'88';

  circ.style.background=d.hex;

  circ.textContent=d.emoji;

  name.textContent=d.name;

  en.textContent=d.en;

  hex.textContent=d.hex;

  hex.style.background=d.hex;

  hex.style.color=textColor(d.hex);

}

 

const NONE={name:'없음',en:'None',hex:'#555555',emoji:''};

 

// ── 폴링 ─────────────────────────────────────

let prevJson='';

async function poll(){

  try{

    const res=await fetch('/color',{signal:AbortSignal.timeout(1200)});

    const d=await res.json();

    const j=JSON.stringify(d);

    if(j!==prevJson){

      prevJson=j;

      updateMain(d.top[0]||NONE);

      updateSub(1, d.top[1]||NONE);

      updateSub(2, d.top[2]||NONE);

    }

  }catch(e){}

  setTimeout(poll,400);

}

poll();

</script>

</body>

</html>"""

 

# ── 소켓 서버 ─────────────────────────────────

srv = socket.socket()

srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

srv.bind(('0.0.0.0', 80))

srv.listen(5)

srv.setblocking(False)

print("서버 시작!  http://" + ip)

 

# ── 상태 관리 ─────────────────────────────────

# 각 슬롯별 안정화 카운터

stable   = [None] * TOP_N   # 확정된 top 색상 ID

cand     = [None] * TOP_N   # 후보 ID

cand_cnt = [0]    * TOP_N   # 연속 카운트

 

def build_response(stable_ids):

    top_list = []

    for cid in stable_ids:

        if cid is None:

            top_list.append({"name":"없음","en":"None","hex":"#555555","emoji":""})

        else:

            info = get_info(cid)

            top_list.append({

                "name":  info["name"],

                "en":    info["en"],

                "hex":   info["hex"],

                "emoji": info["emoji"],

            })

    # TOP_N 길이 보장

    while len(top_list) < TOP_N:

        top_list.append({"name":"없음","en":"None","hex":"#555555","emoji":""})

    return '{"top":[' + ','.join(

        '{"name":"'+c["name"]+'","en":"'+c["en"]+'","hex":"'+c["hex"]+'","emoji":"'+c["emoji"]+'"}'

        for c in top_list

    ) + ']}'

 

# ── 메인 루프 ─────────────────────────────────

while True:

    # HuskyLens 폴링

    top_ids = get_top_colors()   # 최대 TOP_N 개

 

    # 슬롯별 안정화

    for i in range(TOP_N):

        new_id = top_ids[i] if i < len(top_ids) else None

        if new_id == cand[i]:

            cand_cnt[i] += 1

        else:

            cand[i]     = new_id

            cand_cnt[i] = 1

        if cand_cnt[i] >= STABLE_COUNT:

            stable[i] = cand[i]

 

    # HTTP 처리

    try:

        conn, _ = srv.accept()

        conn.settimeout(1.0)

        try:

            req = conn.recv(512).decode('utf-8', 'ignore')

        except:

            req = ''

 

        if 'GET /color' in req:

            body = build_response(stable).encode()

            conn.send(

                b'HTTP/1.1 200 OK\r\n'

                b'Content-Type: application/json\r\n'

                b'Access-Control-Allow-Origin: *\r\n'

                b'Connection: close\r\n\r\n' + body

            )

        else:

            conn.send(

                b'HTTP/1.1 200 OK\r\n'

                b'Content-Type: text/html; charset=utf-8\r\n'

                b'Connection: close\r\n\r\n' + HTML

            )

        conn.close()

    except:

        pass

 

    time.sleep_ms(50)
