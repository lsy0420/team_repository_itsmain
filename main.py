# =============================================

#  색맹/색약 보조 색상 인식기 - WEB SERVER

#  HuskyLens (Color Recognition) + Pico W

#  IDE: Thonny / MicroPython

#

#  배선:

#    HuskyLens SDA -> GP6 (I2C1)

#    HuskyLens SCL -> GP7 (I2C1)

#    HuskyLens VCC -> VBUS (5V, 40번 핀)

#    HuskyLens GND -> GND

#

#  사용법:

#    1. WIFI_SSID, WIFI_PASSWORD 를 본인 것으로 수정

#    2. Pico W에 업로드 후 실행

#    3. 시리얼 모니터에 뜨는 IP 주소를 브라우저에 입력

# =============================================

 

import time

import network

import socket

import json

from machine import I2C, Pin

 

# ── Wi-Fi 설정 (여기만 수정!) ──────────────────

WIFI_SSID     = "senWiFi_Free_sky"

WIFI_PASSWORD = "sudo25sky@"

# ──────────────────────────────────────────────

 

i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=100000)

HL_ADDR = 0x32

 

COLOR_MAP = {

    1:  ("빨간색",   "#FF3B30"),

    2:  ("주황색",   "#FF9500"),

    3:  ("노란색",   "#FFCC00"),

    4:  ("초록색",   "#34C759"),

    5:  ("파란색",   "#007AFF"),

    6:  ("보라색",   "#AF52DE"),

    7:  ("흰색",     "#F2F2F7"),

    8:  ("검은색",   "#1C1C1E"),

    9:  ("회색",     "#8E8E93"),

    10: ("갈색",     "#A2845E"),

    11: ("분홍색",   "#FF2D55"),

    12: ("하늘색",   "#5AC8FA"),

}

 

MIN_AREA     = 2000

STABLE_COUNT = 3

 

# ── 상태 변수 ──────────────────────────────────

state = {

    "name":  "대기 중...",

    "color": "#888888",

    "id":    0,

    "count": 0,

}

prev_name     = ""

candidate     = None

candidate_cnt = 0

 

 

# ── HuskyLens 함수들 ───────────────────────────

def get_name_color(color_id):

    if color_id in COLOR_MAP:

        return COLOR_MAP[color_id]

    return ("알 수 없는 색", "#888888")

 

def make_packet(cmd, data=None):

    if data is None:

        data = []

    body = [0x55, 0xAA, 0x11, len(data), cmd] + data

    body.append(sum(body) & 0xFF)

    return bytes(body)

 

def read_bytes(n=64):

    try:

        return list(i2c.readfrom(HL_ADDR, n))

    except:

        return []

 

def handshake():

    try:

        i2c.writeto(HL_ADDR, make_packet(0x2C))

        time.sleep_ms(50)

        r = read_bytes(20)

        return len(r) >= 2 and r[0] == 0x55 and r[1] == 0xAA

    except:

        return False

 

def get_dominant_id():

    try:

        i2c.writeto(HL_ADDR, make_packet(0x20))

        time.sleep_ms(50)

        r = read_bytes(64)

    except:

        return None

 

    best_id   = None

    best_area = 0

    idx = 0

    while idx < len(r) - 5:

        if r[idx] == 0x55 and r[idx+1] == 0xAA:

            length = r[idx+3]

            if length >= 8 and idx + 5 + length <= len(r):

                d = r[idx+5 : idx+5+length]

                w        = d[4] | (d[5] << 8)

                h        = d[6] | (d[7] << 8)

                color_id = d[length-2] | (d[length-1] << 8)

                area     = w * h

                if area < MIN_AREA:

                    idx += 5 + length + 1

                    continue

                if 1 <= color_id <= 50 and area > best_area:

                    best_area = area

                    best_id   = color_id

            idx += 5 + length + 1

        else:

            idx += 1

    return best_id

 

 

# ── Wi-Fi 연결 ─────────────────────────────────

def connect_wifi():

    wlan = network.WLAN(network.STA_IF)

    wlan.active(True)

    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    print("Wi-Fi 연결 중", end="")

    for _ in range(20):

        if wlan.isconnected():

            print()

            print("Wi-Fi 연결 성공!")

            print("IP 주소:", wlan.ifconfig()[0])

            return wlan.ifconfig()[0]

        print(".", end="")

        time.sleep(1)

    print()

    print("Wi-Fi 연결 실패!")

    return None

 

 

# ── HTML 페이지 ────────────────────────────────

HTML = """\

HTTP/1.1 200 OK\r

Content-Type: text/html; charset=utf-8\r

Connection: close\r

\r

<!DOCTYPE html>

<html lang="ko">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>색상 인식기</title>

<style>

  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');

  * { margin:0; padding:0; box-sizing:border-box; }

  body {

    font-family: 'Noto Sans KR', sans-serif;

    background: #0f0f1a;

    min-height: 100vh;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

    overflow: hidden;

  }

  .bg-blobs {

    position: fixed; inset: 0; z-index: 0; pointer-events: none;

  }

  .blob {

    position: absolute;

    border-radius: 50%;

    filter: blur(80px);

    opacity: 0.18;

    animation: float 8s ease-in-out infinite;

  }

  .blob1 { width:400px; height:400px; background:#FF3B30; top:-100px; left:-100px; animation-delay:0s; }

  .blob2 { width:300px; height:300px; background:#007AFF; bottom:-80px; right:-80px; animation-delay:-3s; }

  .blob3 { width:250px; height:250px; background:#AF52DE; top:40%; left:60%; animation-delay:-5s; }

  @keyframes float {

    0%,100% { transform: translateY(0) scale(1); }

    50%      { transform: translateY(-30px) scale(1.05); }

  }

 

  .card {

    position: relative; z-index: 1;

    background: rgba(255,255,255,0.06);

    border: 1px solid rgba(255,255,255,0.12);

    border-radius: 32px;

    padding: 48px 40px 40px;

    width: 340px;

    text-align: center;

    backdrop-filter: blur(20px);

  }

  h1 {

    font-size: 15px;

    font-weight: 700;

    color: rgba(255,255,255,0.5);

    letter-spacing: 0.15em;

    text-transform: uppercase;

    margin-bottom: 36px;

  }

 

  .orb-wrap {

    position: relative;

    width: 200px; height: 200px;

    margin: 0 auto 32px;

  }

  .orb-ring {

    position: absolute; inset: -12px;

    border-radius: 50%;

    border: 2px solid transparent;

    animation: spin 3s linear infinite;

  }

  .orb-ring::before {

    content: '';

    position: absolute; inset: -2px;

    border-radius: 50%;

    background: conic-gradient(from 0deg, transparent 70%, var(--c, #888) 100%);

    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);

    -webkit-mask-composite: xor;

    mask-composite: exclude;

    padding: 2px;

  }

  @keyframes spin { to { transform: rotate(360deg); } }

 

  .orb {

    width: 200px; height: 200px;

    border-radius: 50%;

    background: var(--c, #888888);

    transition: background 0.6s ease;

    display: flex; align-items: center; justify-content: center;

    font-size: 72px;

    box-shadow:

      0 0 40px color-mix(in srgb, var(--c, #888) 50%, transparent),

      0 0 80px color-mix(in srgb, var(--c, #888) 25%, transparent);

    animation: pulse 2s ease-in-out infinite;

  }

  @keyframes pulse {

    0%,100% { transform: scale(1); box-shadow: 0 0 40px color-mix(in srgb, var(--c,#888) 50%, transparent), 0 0 80px color-mix(in srgb, var(--c,#888) 25%, transparent); }

    50%      { transform: scale(1.04); box-shadow: 0 0 60px color-mix(in srgb, var(--c,#888) 70%, transparent), 0 0 120px color-mix(in srgb, var(--c,#888) 35%, transparent); }

  }

 

  .color-name {

    font-size: 36px;

    font-weight: 900;

    color: #ffffff;

    letter-spacing: -0.02em;

    margin-bottom: 8px;

    transition: color 0.5s;

    min-height: 48px;

  }

  .color-hex {

    font-size: 14px;

    color: rgba(255,255,255,0.4);

    letter-spacing: 0.1em;

    margin-bottom: 28px;

    font-family: monospace;

  }

 

  .status-bar {

    display: flex; align-items: center; justify-content: center; gap: 8px;

    background: rgba(255,255,255,0.06);

    border-radius: 100px;

    padding: 10px 20px;

    font-size: 13px;

    color: rgba(255,255,255,0.5);

  }

  .dot {

    width: 8px; height: 8px;

    border-radius: 50%;

    background: #34C759;

    animation: blink 1.4s ease-in-out infinite;

  }

  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }

 

  /* 팡팡 파티클 */

  .particles { position: fixed; inset: 0; pointer-events: none; z-index: 99; }

  .particle {

    position: absolute;

    border-radius: 50%;

    animation: burst 0.8s ease-out forwards;

  }

  @keyframes burst {

    0%   { transform: translate(0,0) scale(1); opacity: 1; }

    100% { transform: translate(var(--tx), var(--ty)) scale(0); opacity: 0; }

  }

</style>

</head>

<body>

<div class="bg-blobs">

  <div class="blob blob1"></div>

  <div class="blob blob2"></div>

  <div class="blob blob3"></div>

</div>

 

<div class="particles" id="particles"></div>

 

<div class="card">

  <h1>&#127752; 색상 인식기</h1>

  <div class="orb-wrap">

    <div class="orb-ring" id="ring" style="--c:#888888"></div>

    <div class="orb" id="orb" style="--c:#888888">&#128065;</div>

  </div>

  <div class="color-name" id="name">대기 중...</div>

  <div class="color-hex" id="hex">#888888</div>

  <div class="status-bar">

    <div class="dot"></div>

    <span>실시간 감지 중</span>

  </div>

</div>

 

<script>

const EMOJI = {

  "빨간색":"&#128308;","주황색":"&#128992;","노란색":"&#128993;",

  "초록색":"&#128994;","파란색":"&#128309;","보라색":"&#128995;",

  "흰색":"&#9898;","검은색":"&#9899;","회색":"&#128444;",

  "갈색":"&#129321;","분홍색":"&#10084;","하늘색":"&#128307;",

  "대기 중...":"&#128065;","알 수 없는 색":"&#10067;"

};

 

let lastColor = "";

 

function burst(hex) {

  const p = document.getElementById("particles");

  for (let i = 0; i < 24; i++) {

    const el = document.createElement("div");

    el.className = "particle";

    const size = 8 + Math.random() * 14;

    const angle = Math.random() * 360;

    const dist = 80 + Math.random() * 180;

    const tx = Math.cos(angle * Math.PI/180) * dist;

    const ty = Math.sin(angle * Math.PI/180) * dist;

    el.style.cssText = [

      "width:"+size+"px","height:"+size+"px",

      "background:"+hex,

      "left:50%","top:50%",

      "--tx:"+tx+"px","--ty:"+ty+"px",

      "animation-delay:"+(Math.random()*0.2)+"s"

    ].join(";");

    p.appendChild(el);

    setTimeout(() => el.remove(), 1000);

  }

}

 

function blobUpdate(hex) {

  document.querySelector(".blob1").style.background = hex;

}

 

async function poll() {

  try {

    const r = await fetch("/data");

    const d = await r.json();

    const orb  = document.getElementById("orb");

    const ring = document.getElementById("ring");

    const nm   = document.getElementById("name");

    const hx   = document.getElementById("hex");

 

    if (d.name !== lastColor) {

      lastColor = d.name;

      orb.style.setProperty("--c", d.color);

      ring.style.setProperty("--c", d.color);

      orb.innerHTML = EMOJI[d.name] || "&#10067;";

      nm.textContent = d.name;

      hx.textContent = d.color.toUpperCase();

      burst(d.color);

      blobUpdate(d.color);

    }

  } catch(e) {}

  setTimeout(poll, 400);

}

poll();

</script>

</body>

</html>

"""

 

JSON_HEADER = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n"

 

 

# ── 웹 서버 ────────────────────────────────────

def handle_request(conn):

    try:

        req = conn.recv(512).decode("utf-8", "ignore")

    except:

        conn.close()

        return

 

    if "GET /data" in req:

        body = json.dumps({

            "name":  state["name"],

            "color": state["color"],

            "id":    state["id"],

        })

        conn.send(JSON_HEADER + body)

    else:

        conn.send(HTML)

    conn.close()

 

 

# ── 메인 ───────────────────────────────────────

print("========================================")

print("   색맹/색약 보조 색상 인식기 (웹 서버)")

print("========================================")

 

print("HuskyLens 연결 확인 중...")

hl_ok = False

for i in range(5):

    if handshake():

        hl_ok = True

        print("HuskyLens 연결 성공!")

        break

    print("재시도 " + str(i+1) + "/5...")

    time.sleep_ms(500)

 

if not hl_ok:

    print("HuskyLens 연결 실패! 배선을 확인하세요.")

 

ip = connect_wifi()

if ip is None:

    print("Wi-Fi 없이는 웹 서버를 시작할 수 없어요.")

    raise SystemExit

 

addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]

srv  = socket.socket()

srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

srv.bind(addr)

srv.listen(2)

srv.setblocking(False)

 

print("\n브라우저에서 http://" + ip + " 접속!")

print("색상 감지 시작\n")

 

prev_name     = ""

candidate     = None

candidate_cnt = 0

 

while True:

    # ── HuskyLens 읽기 ──

    if hl_ok:

        cid = get_dominant_id()

        if cid is None:

            name, color = "대기 중...", "#888888"

        else:

            name, color = get_name_color(cid)

    else:

        name, color, cid = "HuskyLens 없음", "#888888", 0

 

    # 안정화 필터

    if name == candidate:

        candidate_cnt += 1

    else:

        candidate     = name

        candidate_cnt = 1

 

    if candidate_cnt >= STABLE_COUNT and candidate != prev_name:

        state["name"]  = candidate

        state["color"] = color

        state["id"]    = cid if cid else 0

        prev_name = candidate

        print("[감지]", candidate, color)

 

    # ── 웹 요청 처리 ──

    try:

        conn, _ = srv.accept()

        conn.setblocking(True)

        handle_request(conn)

    except OSError:

        pass

 

    time.sleep_ms(200)
