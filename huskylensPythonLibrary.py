# =============================================

#  색맹/색약 보조 색상 인식기

#  HuskyLens (Color Recognition) + Pico

#  IDE: Thonny / MicroPython

#

#  배선:

#    HuskyLens SDA → GP6 (I2C1)

#    HuskyLens SCL → GP7 (I2C1)

#    HuskyLens VCC → VBUS (5V, 40번 핀)

#    HuskyLens GND → GND

# =============================================

 

import time

from machine import I2C, Pin

 

# ── HuskyLens I2C 설정 ──────────────────────

i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=100000)

HL_ADDR = 0x32

 

# ── 색상 ID → 이름 매핑 ─────────────────────

# HuskyLens에서 학습한 순서대로 ID가 붙어요.

# 첫 번째 학습 = 1번, 두 번째 = 2번 ...

# 본인이 학습시킨 색상 순서에 맞게 수정하세요!

COLOR_MAP = {

    1:  "빨간색 (Red)",

    2:  "주황색 (Orange)",

    3:  "노란색 (Yellow)",

    4:  "초록색 (Green)",

    5:  "파란색 (Blue)",

    6:  "보라색 (Violet)",

    7:  "흰색   (White)",

    8:  "검은색 (Black)",

    9:  "회색   (Gray)",

    10: "갈색   (Brown)",

    11: "분홍색 (Pink)",

    12: "하늘색 (Sky Blue)",

}

 

# ── HuskyLens 패킷 유틸 ─────────────────────

def make_packet(cmd, data=None):

    if data is None:

        data = []

    body = [0x55, 0xAA, 0x11, len(data), cmd] + data

    body.append(sum(body) & 0xFF)

    return bytes(body)

 

def read_bytes(n=20):

    try:

        return list(i2c.readfrom(HL_ADDR, n))

    except:

        return []

 

# ── 연결 확인 (handshake) ───────────────────

def handshake():

    try:

        i2c.writeto(HL_ADDR, make_packet(0x2C))

        time.sleep_ms(50)

        r = read_bytes()

        return len(r) >= 2 and r[0] == 0x55 and r[1] == 0xAA

    except:

        return False

 

# ── 인식된 블록 요청 ────────────────────────

def get_blocks():

    blocks = []

    try:

        i2c.writeto(HL_ADDR, make_packet(0x20))

        time.sleep_ms(50)

        r = read_bytes(64)

    except:

        return blocks

 

    idx = 0

    while idx < len(r) - 5:

        if r[idx] == 0x55 and r[idx+1] == 0xAA:

            length = r[idx+3]

            cmd    = r[idx+4]

            # 0x2A = 블록 데이터 응답

            if cmd == 0x2A and length == 10 and idx + 15 <= len(r):

                d = r[idx+5:idx+15]

                color_id = d[8] | (d[9] << 8)

                blocks.append(color_id)

                idx += 15

                continue

        idx += 1

    return blocks

 

# ── 색상 이름 가져오기 ──────────────────────

def get_name(color_id):

    if color_id in COLOR_MAP:

        return COLOR_MAP[color_id]

    return "알 수 없는 색 (ID: " + str(color_id) + ")"

 

# ── 메인 실행 ───────────────────────────────

print("========================================")

print("   색맹/색약 보조 색상 인식기")

print("========================================")

print("HuskyLens 연결 확인 중...")

 

connected = False

for i in range(5):

    if handshake():

        connected = True

        print("연결 성공!")

        break

    print("재시도 " + str(i+1) + "/5...")

    time.sleep_ms(500)

 

if not connected:

    print("연결 실패! 배선을 확인하세요.")

    print("  SDA → GP6,  SCL → GP7")

else:

    print("색상 인식 시작\n")

    prev = []

 

    while True:

        ids = get_blocks()

 

        if ids != prev:

            if not ids:

                print("[---] 인식된 색상 없음")

            else:

                print("[감지] " + str(len(ids)) + "개 색상:")

                for cid in ids:

                    print("  >> " + get_name(cid))

                print("")

            prev = ids

 

        time.sleep_ms(300)
