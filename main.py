# =============================================

#  색맹/색약 보조 색상 인식기 - 웹서버 버전

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

from machine import I2C, Pin

 

WIFI_SSID = "여기에_와이파이_이름"

WIFI_PASS = "여기에_와이파이_비밀번호"

 

i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=100000)

HL_ADDR = 0x32

MIN_AREA = 2000

STABLE_COUNT = 3

 

COLOR_MAP = {

    1:  {"name": "빨간색",  "en": "Red",      "hex": "#FF4444"},

    2:  {"name": "주황색",  "en": "Orange",   "hex": "#FF8C00"},

    3:  {"name": "노란색",  "en": "Yellow",   "hex": "#FFD700"},

    4:  {"name": "초록색",  "en": "Green",    "hex": "#44BB44"},

    5:  {"name": "파란색",  "en": "Blue",     "hex": "#4488FF"},

    6:  {"name": "보라색",  "en": "Violet",   "hex": "#9966FF"},

    7:  {"name": "흰색",    "en": "White",    "hex": "#EEEEEE"},

    8:  {"name": "검은색",  "en": "Black",    "hex": "#333333"},

    9:  {"name": "회색",    "en": "Gray",     "hex": "#999999"},

    10: {"name": "갈색",    "en": "Brown",    "hex": "#AA6633"},

    11: {"name": "분홍색",  "en": "Pink",     "hex": "#FF88BB"},

    12: {"name": "하늘색",  "en": "Sky Blue", "hex": "#66CCFF"},

}

 

def get_info(cid):

    return COLOR_MAP.get(cid, {"name": "알 수 없음", "en": "Unknown", "hex": "#CCCCCC"})

 

def make_packet(cmd, data=None):

    if data is None:

        data = []

    body = [0x55, 0xAA, 0x11, len(data), cmd] + data

    body.append(sum(body) & 0xFF)

    return bytes(body)

 

def get_dominant_id():

    try:

        i2c.writeto(HL_ADDR, make_packet(0x20))

        time.sleep_ms(50)

        r = list(i2c.readfrom(HL_ADDR, 64))

    except:

        return None

 

    best_id = None

    best_area = 0

    idx = 0

    while idx < len(r) - 5:

        if r[idx] == 0x55 and r[idx+1] == 0xAA:

            length = r[idx+3]

            if length >= 8 and idx + 5 + length <= len(r):

                d = r[idx+5: idx+5+length]

                w = d[4] | (d[5] << 8)

                h = d[6] | (d[7] << 8)

                cid = d[length-2] | (d[length-1] << 8)

                area = w * h

                if area >= MIN_AREA and 1 <= cid <= 50 and area > best_area:

                    best_area = area

                    best_id = cid

            idx += 5 + length + 1

        else:

            idx += 1

    return best_id

 

# 와이파이 연결

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

print("브라우저에서 http://" + ip + " 접속!")

 

# HTML 페이지

HTML = """<!DOCTYPE html>

<html lang="ko">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width,initial-scale=1">

<title>색상 인식기</title>

<style>

*{margin:0;padding:0;box-sizing:border-box}

body{font-family:'Apple SD Gothic Neo',sans-serif;background:#0d0d1a;min-height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden}

canvas{position:fixed;top:0;left:0;pointer-events:none}

.card{position:relative;z-index:2;background:rgba(255,255,255,0.06);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.12);border-radius:36px;padding:44px 52px;text-align:center;width:320px}

.top{font-size:13px;color:rgba(255,255,255,0.4);letter-spacing:2px;margin-bottom:28px}

.circle-wrap{position:relative;width:160px;margin:0 auto 24px}

.ring{position:absolute;inset:-14px;border-radius:50%;border:3px solid;opacity:0;animation:ring 2s ease-out infinite}

@keyframes ring{0%{transform:scale(1);opacity:.5}100%{transform:scale(1.4);opacity:0}}

.circle{width:160px;height:160px;border-radius:50%;transition:background .6s ease;display:flex;align-items:center;justify-content:center;font-size:48px}

.name{font-size:42px;font-weight:900;color:white;margin-bottom:4px;transition:color .6s}

.en{font-size:16px;color:rgba(255,255,255,.35);margin-bottom:20px}

.badge{display:inline-block;padding:8px 22px;border-radius:999px;font-size:13px;font-weight:700;letter-spacing:1px;transition:all .6s}

.dot{width:8px;height:8px;border-radius:50%;background:#44ff88;display:inline-block;margin-right:6px;animation:blink 1.5s ease infinite}

@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}

.status{margin-top:22px;font-size:12px;color:rgba(255,255,255,.35)}

</style>

</head>

<body>

<canvas id="c"></canvas>

<div class="card">

  <div class="top"> 색상 인식기</div>

  <div class="circle-wrap">

    <div class="ring" id="ring"></div>

    <div class="circle" id="circle"></div>

  </div>

  <div class="name" id="name">대기 중...</div>

  <div class="en" id="en">Waiting</div>

  <div class="badge" id="badge" style="background:rgba(255,255,255,.08);color:rgba(255,255,255,.4)">#888888</div>

  <div class="status"><span class="dot"></span>실시간 감지 중</div>

</div>

<script>

const canvas=document.getElementById('c');

const ctx=canvas.getContext('2d');

canvas.width=window.innerWidth;canvas.height=window.innerHeight;

const particles=[];

const cols=['#FF4444','#FF8C00','#FFD700','#44BB44','#4488FF','#9966FF','#FF88BB','#66CCFF'];

for(let i=0;i<60;i++){

  particles.push({x:Math.random()*canvas.width,y:Math.random()*canvas.height,r:2+Math.random()*4,

  c:cols[Math.floor(Math.random()*cols.length)],vx:(Math.random()-.5)*.4,vy:(Math.random()-.5)*.4,a:Math.random()});

}

function drawParticles(){

  ctx.clearRect(0,0,canvas.width,canvas.height);

  particles.forEach(p=>{

    p.x+=p.vx;p.y+=p.vy;p.a+=0.01;

    if(p.x<0)p.x=canvas.width;if(p.x>canvas.width)p.x=0;

    if(p.y<0)p.y=canvas.height;if(p.y>canvas.height)p.y=0;

    ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);

    ctx.fillStyle=p.c;ctx.globalAlpha=0.15+0.1*Math.sin(p.a);ctx.fill();

  });

  ctx.globalAlpha=1;

  requestAnimationFrame(drawParticles);

}

drawParticles();

 

function textColor(hex){

  const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);

  return(r*299+g*587+b*114)/1000>150?'#222':'#fff';

}

 

let prev='';

async function poll(){

  try{

    const res=await fetch('/color',{signal:AbortSignal.timeout(1000)});

    const d=await res.json();

    if(d.hex!==prev){

      prev=d.hex;

      document.getElementById('circle').style.background=d.hex;

      document.getElementById('ring').style.borderColor=d.hex;

      document.getElementById('name').textContent=d.name;

      document.getElementById('name').style.color=d.hex==='#EEEEEE'?'#aaa':d.hex;

      document.getElementById('en').textContent=d.en;

      const b=document.getElementById('badge');

      b.style.background=d.hex;b.style.color=textColor(d.hex);b.textContent=d.hex;

    }

  }catch(e){}

  setTimeout(poll,400);

}

poll();

</script>

</body>

</html>"""

 

# 소켓 서버

s = socket.socket()

s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.bind(('0.0.0.0', 80))

s.listen(5)

s.setblocking(False)

print("서버 시작!")

 

current = {"name": "대기 중...", "en": "Waiting", "hex": "#888888"}

candidate = None

candidate_cnt = 0

 

while True:

    # HuskyLens 폴링

    cid = get_dominant_id()

    if cid == candidate:

        candidate_cnt += 1

    else:

        candidate = cid

        candidate_cnt = 1

    if candidate_cnt >= STABLE_COUNT:

        if candidate is None:

            current = {"name": "없음", "en": "None", "hex": "#888888"}

        else:

            current = get_info(candidate)

 

    # HTTP 요청 처리

    try:

        conn, _ = s.accept()

        conn.settimeout(1.0)

        try:

            req = conn.recv(512).decode('utf-8', 'ignore')

        except:

            req = ''

 

        if 'GET /color' in req:

            body = '{"name":"' + current["name"] + '","en":"' + current["en"] + '","hex":"' + current["hex"] + '"}'

            conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n' + body.encode())

        else:

            conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n' + HTML.encode())

        conn.close()

    except:

        pass

 

    time.sleep_ms(50)
