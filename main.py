# =============================================

#  색맹/색약 보조 색상 인식기 - 웹서버 버전 v3.0

#  HuskyLens (Color Recognition) + Pico W

# =============================================

 

import network

import socket

import time

from machine import I2C, Pin

 

WIFI_SSID = "senWiFi_Free_sky"

WIFI_PASS = "sudo25sky@"

 

i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=100000)

HL_ADDR      = 0x32

MIN_AREA     = 800

STABLE_COUNT = 3

TOP_N        = 3

 

COLOR_MAP = {

    1:  {"name": "빨간색",  "en": "Red",      "hex": "#FF4444", "emoji": "R"},

    2:  {"name": "주황색",  "en": "Orange",   "hex": "#FF8C00", "emoji": "O"},

    3:  {"name": "노란색",  "en": "Yellow",   "hex": "#FFD700", "emoji": "Y"},

    4:  {"name": "초록색",  "en": "Green",    "hex": "#44BB44", "emoji": "G"},

    5:  {"name": "파란색",  "en": "Blue",     "hex": "#4488FF", "emoji": "B"},

    6:  {"name": "보라색",  "en": "Violet",   "hex": "#9966FF", "emoji": "V"},

    7:  {"name": "흰색",    "en": "White",    "hex": "#DDDDDD", "emoji": "W"},

    8:  {"name": "검은색",  "en": "Black",    "hex": "#444444", "emoji": "K"},

    9:  {"name": "회색",    "en": "Gray",     "hex": "#999999", "emoji": "Gr"},

    10: {"name": "갈색",    "en": "Brown",    "hex": "#AA6633", "emoji": "Br"},

    11: {"name": "분홍색",  "en": "Pink",     "hex": "#FF88BB", "emoji": "P"},

    12: {"name": "하늘색",  "en": "Sky Blue", "hex": "#66CCFF", "emoji": "Sk"},

}

 

# 이모지 대신 영문 약자 사용 (JSON 인코딩 안전)

NONE_COLOR = {"name": "없음", "en": "None", "hex": "#CCCCCC", "emoji": "?"}

 

def get_info(cid):

    return COLOR_MAP.get(cid, {"name": "모름", "en": "Unknown",

                                "hex": "#CCCCCC", "emoji": "?"})

 

def make_packet(cmd, data=None):

    if data is None:

        data = []

    body = [0x55, 0xAA, 0x11, len(data), cmd] + data

    body.append(sum(body) & 0xFF)

    return bytes(body)

 

def get_top_colors():

    try:

        i2c.writeto(HL_ADDR, make_packet(0x20))

        time.sleep_ms(50)

        r = list(i2c.readfrom(HL_ADDR, 64))

    except Exception as e:

        print("I2C 오류:", e)

        return []

 

    scores = {}

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

 

    sorted_ids = sorted(scores, key=lambda k: scores[k], reverse=True)

    return sorted_ids[:TOP_N]

 

# ── JSON 빌더 (이모지 없이 안전하게) ──────────

def build_json(stable_ids):

    items = []

    for i in range(TOP_N):

        cid = stable_ids[i] if i < len(stable_ids) else None

        c = get_info(cid) if cid else NONE_COLOR

        items.append(

            '{"name":"' + c["name"] +

            '","en":"'  + c["en"]   +

            '","hex":"' + c["hex"]  +

            '","sym":"' + c["emoji"]+ '"}'

        )

    return '{"top":[' + ','.join(items) + ']}'

 

# ── WiFi 연결 ──────────────────────────────────

wlan = network.WLAN(network.STA_IF)

wlan.active(True)

wlan.connect(WIFI_SSID, WIFI_PASS)

print("와이파이 연결 중...")

for _ in range(30):

    if wlan.isconnected():

        break

    time.sleep(0.5)

 

if not wlan.isconnected():

    print("연결 실패!")

    raise SystemExit

 

ip = wlan.ifconfig()[0]

print("http://" + ip)

 

# ── HTML (str → 전송시 encode) ─────────────────

# 한글은 JS 쪽에서만 처리, Python 문자열로 유지

HTML = """<!DOCTYPE html>

<html lang="ko">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width,initial-scale=1">

<title>Color Detector</title>

<style>

*{margin:0;padding:0;box-sizing:border-box}

 

/* ── 밝은 파스텔 배경 ── */

body{

  font-family:system-ui,sans-serif;

  min-height:100vh;

  background:linear-gradient(135deg,#fff0f5 0%,#f0f4ff 35%,#f0fff4 65%,#fffaf0 100%);

  display:flex;flex-direction:column;

  align-items:center;justify-content:center;

  gap:20px;overflow:hidden;

}

 

/* ── 배경 버블 ── */

.bubble{

  position:fixed;border-radius:50%;opacity:.18;

  animation:rise linear infinite;pointer-events:none;

}

@keyframes rise{

  0%  {transform:translateY(110vh) scale(1)}

  100%{transform:translateY(-20vh) scale(1.2)}

}

 

/* ── 타이틀 ── */

.title{

  font-size:26px;font-weight:900;letter-spacing:2px;

  background:linear-gradient(90deg,#ff6eb4,#ffa94d,#ffe066,#69db7c,#74c0fc,#cc5de8);

  -webkit-background-clip:text;-webkit-text-fill-color:transparent;

  background-clip:text;

  animation:hue 5s linear infinite;

  filter:drop-shadow(0 2px 8px rgba(0,0,0,.10));

}

@keyframes hue{to{filter:hue-rotate(360deg) drop-shadow(0 2px 8px rgba(0,0,0,.10))}}

 

/* ── 메인 카드 ── */

.main-card{

  background:rgba(255,255,255,0.75);

  backdrop-filter:blur(20px);

  border:3px solid var(--col,#ddd);

  border-radius:36px;

  padding:36px 48px 30px;

  text-align:center;width:320px;

  box-shadow:0 8px 40px rgba(0,0,0,.10),

             0 0 0 6px rgba(255,255,255,.6),

             0 0 60px var(--glow,transparent);

  transition:border-color .5s,box-shadow .5s;

  position:relative;z-index:2;

}

.ring-wrap{position:relative;width:160px;margin:0 auto 18px}

.pulse{

  position:absolute;inset:-16px;border-radius:50%;

  border:3px solid var(--col,#ccc);

  animation:pls 2.2s ease-out infinite;opacity:0;

}

.pulse2{animation-delay:.9s}

@keyframes pls{0%{transform:scale(1);opacity:.6}100%{transform:scale(1.55);opacity:0}}

 

.main-circle{

  width:160px;height:160px;border-radius:50%;

  background:var(--col,#ddd);

  display:flex;align-items:center;justify-content:center;

  font-size:38px;font-weight:900;color:#fff;

  text-shadow:0 2px 8px rgba(0,0,0,.3);

  box-shadow:0 0 0 6px rgba(255,255,255,.8),

             0 6px 30px var(--col,#ddd);

  animation:float 3s ease-in-out infinite;

  transition:background .5s,box-shadow .5s;

}

@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}

 

.main-name{

  font-size:36px;font-weight:900;

  color:var(--col,#aaa);

  text-shadow:0 2px 12px var(--col,transparent);

  transition:all .5s;margin-bottom:4px;

}

.main-en{font-size:14px;color:#aaa;margin-bottom:14px}

.hex-badge{

  display:inline-block;padding:8px 24px;

  border-radius:999px;font-size:13px;font-weight:700;

  background:var(--col,#ddd);color:var(--btxt,#fff);

  box-shadow:0 4px 14px var(--col,#ddd);

  transition:all .5s;

}

 

/* ── 서브 카드 ── */

.sub-row{display:flex;gap:14px;position:relative;z-index:2}

.sub-card{

  background:rgba(255,255,255,0.72);

  backdrop-filter:blur(16px);

  border:2px solid var(--sc,#ddd);

  border-radius:24px;padding:16px 18px;

  text-align:center;width:144px;

  box-shadow:0 4px 20px rgba(0,0,0,.08),

             0 0 30px var(--sg,transparent);

  transition:all .5s;

}

.sub-rank{font-size:11px;color:#bbb;letter-spacing:2px;margin-bottom:10px;font-weight:700}

.sub-circle{

  width:62px;height:62px;border-radius:50%;

  background:var(--sc,#ddd);

  display:flex;align-items:center;justify-content:center;

  font-size:18px;font-weight:900;color:#fff;

  text-shadow:0 1px 4px rgba(0,0,0,.3);

  box-shadow:0 0 0 4px rgba(255,255,255,.8),

             0 4px 16px var(--sc,#ddd);

  margin:0 auto 10px;

  animation:float 3.6s ease-in-out infinite;

  transition:background .5s,box-shadow .5s;

}

.sub-name{font-size:15px;font-weight:800;color:#444;margin-bottom:2px}

.sub-en{font-size:11px;color:#aaa;margin-bottom:8px}

.sub-hex{

  font-size:11px;font-weight:700;

  padding:4px 12px;border-radius:999px;

  background:var(--sc,#ddd);color:var(--sbt,#fff);

  transition:all .5s;display:inline-block;

}

 

/* ── 상태 바 ── */

.status-bar{

  font-size:12px;color:#bbb;

  display:flex;align-items:center;gap:6px;

  position:relative;z-index:2;

  background:rgba(255,255,255,.7);

  padding:6px 16px;border-radius:999px;

  box-shadow:0 2px 10px rgba(0,0,0,.06);

}

.dot{

  width:8px;height:8px;border-radius:50%;

  background:#69db7c;

  animation:blink 1.5s ease infinite;

}

@keyframes blink{0%,100%{opacity:1}50%{opacity:.15}}

 

/* ── 대기 중 무지개 테두리 ── */

@keyframes rainbowB{

  0%{border-color:#ff6eb4}20%{border-color:#ffa94d}

  40%{border-color:#ffe066}60%{border-color:#69db7c}

  80%{border-color:#74c0fc}100%{border-color:#ff6eb4}

}

.idle{animation:rainbowB 2.5s linear infinite}

</style>

</head>

<body>

 

<!-- 배경 버블 (JS로 생성) -->

<div class="title" id="titleTxt">&#127752; &#49353;&#49345; &#51064;&#49885;&#44592; &#127752;</div>

 

<div class="main-card idle" id="mainCard" style="--col:#ddd;--glow:transparent">

  <div class="ring-wrap">

    <div class="pulse"  id="ring1" style="border-color:#ddd"></div>

    <div class="pulse pulse2" id="ring2" style="border-color:#ddd"></div>

    <div class="main-circle" id="mainCircle">?</div>

  </div>

  <div class="main-name" id="mainName">&#45824;&#44592; &#51473;...</div>

  <div class="main-en"   id="mainEn">Waiting</div>

  <div class="hex-badge" id="mainBadge">#888888</div>

</div>

 

<div class="sub-row">

  <div class="sub-card" id="sub1" style="--sc:#ddd;--sg:transparent">

    <div class="sub-rank">&#10024; 2&#50948;</div>

    <div class="sub-circle" id="sub1C">?</div>

    <div class="sub-name"   id="sub1N">&#50630;&#51020;</div>

    <div class="sub-en"     id="sub1E">None</div>

    <div class="sub-hex"    id="sub1H">#888</div>

  </div>

  <div class="sub-card" id="sub2" style="--sc:#ddd;--sg:transparent">

    <div class="sub-rank">&#11088; 3&#50948;</div>

    <div class="sub-circle" id="sub2C">?</div>

    <div class="sub-name"   id="sub2N">&#50630;&#51020;</div>

    <div class="sub-en"     id="sub2E">None</div>

    <div class="sub-hex"    id="sub2H">#888</div>

  </div>

</div>

 

<div class="status-bar"><span class="dot"></span>&#49892;&#49884;&#44036; &#44048;&#51648; &#51473;</div>

 

<script>

// ── 배경 버블 생성 ──────────────────────────

const BCOLS=['#ffadad','#ffd6a5','#fdffb6','#caffbf',

             '#9bf6ff','#a0c4ff','#bdb2ff','#ffc6ff'];

for(let i=0;i<18;i++){

  const b=document.createElement('div');

  b.className='bubble';

  const sz=40+Math.random()*120;

  b.style.cssText=[

    'width:'+sz+'px','height:'+sz+'px',

    'left:'+(Math.random()*100)+'vw',

    'bottom:'+(-sz)+'px',

    'background:'+BCOLS[i%BCOLS.length],

    'animation-duration:'+(8+Math.random()*14)+'s',

    'animation-delay:'+(Math.random()*10)+'s'

  ].join(';');

  document.body.appendChild(b);

}

 

// ── 유틸 ─────────────────────────────────────

function txtCol(hex){

  const r=parseInt(hex.slice(1,3),16),

        g=parseInt(hex.slice(3,5),16),

        b=parseInt(hex.slice(5,7),16);

  return(r*299+g*587+b*114)/1000>165?'#333':'#fff';

}

function sv(el,k,v){el.style.setProperty(k,v)}

 

// ── 메인 카드 업데이트 ───────────────────────

function updateMain(d){

  const card=document.getElementById('mainCard');

  card.classList.remove('idle');

  sv(card,'--col',d.hex);

  sv(card,'--glow',d.hex+'66');

  card.style.borderColor=d.hex;

 

  document.getElementById('ring1').style.borderColor=d.hex;

  document.getElementById('ring2').style.borderColor=d.hex;

 

  const circ=document.getElementById('mainCircle');

  circ.style.background=d.hex;

  circ.style.boxShadow='0 0 0 6px rgba(255,255,255,.8),0 6px 30px '+d.hex;

  circ.textContent=d.sym;

 

  const nm=document.getElementById('mainName');

  nm.textContent=d.name; nm.style.color=d.hex;

  nm.style.textShadow='0 2px 12px '+d.hex+'88';

 

  document.getElementById('mainEn').textContent=d.en;

 

  const badge=document.getElementById('mainBadge');

  badge.textContent=d.hex;

  badge.style.background=d.hex;

  badge.style.color=txtCol(d.hex);

  badge.style.boxShadow='0 4px 14px '+d.hex+'99';

}

 

// ── 서브 카드 업데이트 ───────────────────────

function updateSub(n,d){

  const card=document.getElementById('sub'+n);

  const circ=document.getElementById('sub'+n+'C');

  const nm  =document.getElementById('sub'+n+'N');

  const en  =document.getElementById('sub'+n+'E');

  const hx  =document.getElementById('sub'+n+'H');

  sv(card,'--sc',d.hex); sv(card,'--sg',d.hex+'44');

  card.style.borderColor=d.hex+'99';

  circ.style.background=d.hex;

  circ.style.boxShadow='0 0 0 4px rgba(255,255,255,.8),0 4px 16px '+d.hex;

  circ.textContent=d.sym;

  nm.textContent=d.name;

  en.textContent=d.en;

  hx.textContent=d.hex;

  hx.style.background=d.hex;

  hx.style.color=txtCol(d.hex);

}

 

const NONE={name:'없음',en:'None',hex:'#CCCCCC',sym:'?'};

let prevJ='';

 

// ── 폴링 ─────────────────────────────────────

async function poll(){

  try{

    const res=await fetch('/color',{signal:AbortSignal.timeout(1500)});

    if(!res.ok) throw new Error('bad resp');

    const d=await res.json();

    const j=JSON.stringify(d);

    if(j!==prevJ){

      prevJ=j;

      updateMain(d.top[0]||NONE);

      updateSub(1,d.top[1]||NONE);

      updateSub(2,d.top[2]||NONE);

    }

  }catch(e){console.warn('poll err',e)}

  setTimeout(poll,450);

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

print("서버 시작! http://" + ip)

 

stable   = [None] * TOP_N

cand     = [None] * TOP_N

cand_cnt = [0]    * TOP_N

 

while True:

    # HuskyLens 폴링

    top_ids = get_top_colors()

 

    for i in range(TOP_N):

        new_id = top_ids[i] if i < len(top_ids) else None

        if new_id == cand[i]:

            cand_cnt[i] += 1

        else:

            cand[i]     = new_id

            cand_cnt[i] = 1

        if cand_cnt[i] >= STABLE_COUNT:

            stable[i] = cand[i]

 

    # HTTP

    try:

        conn, _ = srv.accept()

        conn.settimeout(1.0)

        try:

            req = conn.recv(512).decode('utf-8', 'ignore')

        except:

            req = ''

 

        if 'GET /color' in req:

            body = build_json(stable).encode('utf-8')

            conn.send(

                b'HTTP/1.1 200 OK\r\n'

                b'Content-Type: application/json; charset=utf-8\r\n'

                b'Access-Control-Allow-Origin: *\r\n'

                b'Connection: close\r\n\r\n' + body

            )

        else:

            body = HTML.encode('utf-8')

            conn.send(

                b'HTTP/1.1 200 OK\r\n'

                b'Content-Type: text/html; charset=utf-8\r\n'

                b'Connection: close\r\n\r\n' + body

            )

        conn.close()

    except:

        pass

 

    time.sleep_ms(50)

# =============================================

#  색맹/색약 보조 색상 인식기 v4.0

#  HuskyLens (Color Recognition) + Pico W

# =============================================

 

import network

import socket

import time

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

    try:

        i2c.writeto(HL_ADDR, make_packet(0x20))

        time.sleep_ms(50)

        r = list(i2c.readfrom(HL_ADDR, 64))

    except Exception as e:

        print("I2C 오류:", e)

        return []

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

    return sorted(scores, key=lambda k: scores[k], reverse=True)[:TOP_N]

 

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

 

# ── 청크 전송 (핵심 수정!) ─────────────────────

def send_all(conn, data: bytes):

    CHUNK = 512

    mv = memoryview(data)

    for i in range(0, len(data), CHUNK):

        try:

            conn.send(mv[i:i+CHUNK])

        except Exception as e:

            print("전송 오류:", e)

            break

        time.sleep_ms(5)

 

# ── HTML 완전히 ASCII/숫자만 사용 ──────────────

# 한글은 전부 &#NNNNN; 엔티티로 변환해서

# encode() 시 크기 증가 없게 처리

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

  background:#ddd;color:#fff;

  transition:all .5s;

}

.sub-row{

  display:flex;gap:12px;

  position:relative;z-index:2;

}

.sub-card{

  background:rgba(255,255,255,0.78);

  border:2px solid #eee;

  border-radius:22px;padding:14px 16px;

  text-align:center;width:138px;

  box-shadow:0 4px 16px rgba(0,0,0,.06);

  transition:all .5s;

}

.sub-rank{font-size:11px;color:#ccc;letter-spacing:1px;margin-bottom:8px;font-weight:700}

.sub-circle{

  width:58px;height:58px;border-radius:50%;

  background:#ddd;

  display:flex;align-items:center;justify-content:center;

  font-size:13px;font-weight:900;color:#fff;

  box-shadow:0 0 0 3px rgba(255,255,255,.9),0 3px 12px #ddd;

  margin:0 auto 8px;

  animation:fl 3.6s ease-in-out infinite;

  transition:background .5s,box-shadow .5s;

}

.sub-name{font-size:14px;font-weight:800;color:#555;margin-bottom:2px}

.sub-en{font-size:11px;color:#bbb;margin-bottom:6px}

.sub-hex{

  font-size:11px;font-weight:700;

  padding:3px 10px;border-radius:999px;

  background:#ddd;color:#fff;

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

.dot{

  width:8px;height:8px;border-radius:50%;

  background:#69db7c;animation:blink 1.5s ease infinite;

}

@keyframes blink{0%,100%{opacity:1}50%{opacity:.1}}

</style>

</head>

<body>

<div class="title">&#127800; Color Detector &#127800;</div>

<div class="main-card" id="MC">

  <div class="ring-wrap">

    <div class="pulse"  id="R1"></div>

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

    <div class="sub-name"   id="S1N">None</div>

    <div class="sub-en"     id="S1E">None</div>

    <div class="sub-hex"    id="S1H">#888</div>

  </div>

  <div class="sub-card" id="S2">

    <div class="sub-rank">&#11088; 3rd</div>

    <div class="sub-circle" id="S2C">?</div>

    <div class="sub-name"   id="S2N">None</div>

    <div class="sub-en"     id="S2E">None</div>

    <div class="sub-hex"    id="S2H">#888</div>

  </div>

</div>

<div class="status-bar">

  <span class="dot"></span>Live Detecting

</div>

<script>

// 버블 배경

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

  mn.textContent=d.name; mn.style.color=d.hex;

  document.getElementById('ME').textContent=d.en;

  const mb=document.getElementById('MB');

  mb.textContent=d.hex; mb.style.background=d.hex; mb.style.color=tc(d.hex);

}

function upSub(n,d){

  const sc=document.getElementById('S'+n+'C');

  const sn=document.getElementById('S'+n+'N');

  const se=document.getElementById('S'+n+'E');

  const sh=document.getElementById('S'+n+'H');

  const sd=document.getElementById('S'+n);

  sd.style.borderColor=d.hex+'99';

  sc.style.background=d.hex;

  sc.style.boxShadow='0 0 0 3px rgba(255,255,255,.9),0 3px 12px '+d.hex+'88';

  sc.textContent=d.sym;

  sn.textContent=d.name;

  se.textContent=d.en;

  sh.textContent=d.hex; sh.style.background=d.hex; sh.style.color=tc(d.hex);

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

 

# ── WiFi ──────────────────────────────────────

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

 

# ── 서버 ──────────────────────────────────────

srv = socket.socket()

srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

srv.bind(('0.0.0.0', 80))

srv.listen(3)

srv.setblocking(False)

print("서버 OK")

 

stable   = [None] * TOP_N

cand     = [None] * TOP_N

cand_cnt = [0]    * TOP_N

 

# HTML은 미리 bytes로 변환 (루프 안에서 encode 반복 방지)

HTML_BYTES = HTML.encode('utf-8')

print("HTML 크기:", len(HTML_BYTES), "bytes")

 

while True:

    # 허스키렌즈 읽기

    top_ids = get_top_colors()

    for i in range(TOP_N):

        nid = top_ids[i] if i < len(top_ids) else None

        if nid == cand[i]:

            cand_cnt[i] += 1

        else:

            cand[i] = nid; cand_cnt[i] = 1

        if cand_cnt[i] >= STABLE_COUNT:

            stable[i] = cand[i]

 

    # HTTP 처리

    try:

        conn, addr = srv.accept()

        conn.settimeout(2.0)

        try:

            req = conn.recv(256).decode('utf-8', 'ignore')

        except:

            req = ''

        print("요청:", req[:40])

 

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

    except Exception as e:

        print("HTTP 오류:", e)

 

    time.sleep_ms(30)
