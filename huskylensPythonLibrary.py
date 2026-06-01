# =============================================

#  색맹/색약 보조 색상 인식기

#  HuskyLens (Color Recognition) + Pico

#  IDE: Thonny / MicroPython

#

#  배선:

#    HuskyLens SDA -> GP6 (I2C1)

#    HuskyLens SCL -> GP7 (I2C1)

#    HuskyLens VCC -> VBUS (5V, 40번 핀)

#    HuskyLens GND -> GND

# =============================================

 

import time

from machine import I2C, Pin

 

# HuskyLens I2C 설정

i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=100000)

HL_ADDR = 0x32

 

# 색상 ID -> 이름 매핑

COLOR_MAP = {

    1:  "빨간색",

    2:  "주황색",

    3:  "노란색",

    4:  "초록색",

    5:  "파란색",

    6:  "보라색",

    7:  "흰색",

    8:  "검은색",

    9:  "회색",

    10: "갈색",

    11: "분홍색",

    12: "하늘색",

}

 

def get_name(color_id):

    if color_id in COLOR_MAP:

        return COLOR_MAP[color_id]

    return "알 수 없는 색"

 

# 패킷 생성

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

 

# 연결 확인

def handshake():

    try:

        i2c.writeto(HL_ADDR, make_packet(0x2C))

        time.sleep_ms(50)

        r = read_bytes(20)

        return len(r) >= 2 and r[0] == 0x55 and r[1] == 0xAA

    except:

        return False

 

# 가장 넓은 블록(w x h 최대)의 ID만 반환

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

            cmd    = r[idx+4]

            if length >= 2 and idx + 5 + length <= len(r):

                d = r[idx+5 : idx+5+length]

                color_id = d[length-2] | (d[length-1] << 8)

                # w, h는 5번째~8번째 바이트

                if length >= 8:

                    w = d[4] | (d[5] << 8)

                    h = d[6] | (d[7] << 8)

                    area = w * h

                else:

                    area = 1   # 크기 정보 없으면 동등 취급

                if 1 <= color_id <= 50 and area > best_area:

                    best_area = area

                    best_id   = color_id

            idx += 5 + length + 1

        else:

            idx += 1

 

    return best_id

 

# 메인

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

else:

    print("색상 인식 시작\n")

    prev_name = ""

 

    while True:

        cid = get_dominant_id()

 

        if cid is None:

            if prev_name != "":

                print("[---] 인식된 색상 없음")

                prev_name = ""

        else:

            name = get_name(cid)

            if name != prev_name:

                print("[감지] " + name)

                prev_name = name

 

        time.sleep_ms(300)# =============================================

#  색맹/색약 보조 색상 인식기

#  HuskyLens (Color Recognition) + Pico

#  IDE: Thonny / MicroPython

#

#  배선:

#    HuskyLens SDA -> GP6 (I2C1)

#    HuskyLens SCL -> GP7 (I2C1)

#    HuskyLens VCC -> VBUS (5V, 40번 핀)

#    HuskyLens GND -> GND

# =============================================

 

import time

from machine import I2C, Pin

 

# HuskyLens I2C 설정

i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=100000)

HL_ADDR = 0x32

 

# 색상 ID -> 이름 매핑

COLOR_MAP = {

    1:  "빨간색",

    2:  "주황색",

    3:  "노란색",

    4:  "초록색",

    5:  "파란색",

    6:  "보라색",

    7:  "흰색",

    8:  "검은색",

    9:  "회색",

    10: "갈색",

    11: "분홍색",

    12: "하늘색",

}

 

def get_name(color_id):

    if color_id in COLOR_MAP:

        return COLOR_MAP[color_id]

    return "알 수 없는 색"

 

# 패킷 생성

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

 

# 연결 확인

def handshake():

    try:

        i2c.writeto(HL_ADDR, make_packet(0x2C))

        time.sleep_ms(50)

        r = read_bytes(20)

        return len(r) >= 2 and r[0] == 0x55 and r[1] == 0xAA

    except:

        return False

 

# 가장 넓은 블록(w x h 최대)의 ID만 반환

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

            cmd    = r[idx+4]

            if length >= 2 and idx + 5 + length <= len(r):

                d = r[idx+5 : idx+5+length]

                color_id = d[length-2] | (d[length-1] << 8)

                # w, h는 5번째~8번째 바이트

                if length >= 8:

                    w = d[4] | (d[5] << 8)

                    h = d[6] | (d[7] << 8)

                    area = w * h

                else:

                    area = 1   # 크기 정보 없으면 동등 취급

                if 1 <= color_id <= 50 and area > best_area:

                    best_area = area

                    best_id   = color_id

            idx += 5 + length + 1

        else:

            idx += 1

 

    return best_id

 

# 메인

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

else:

    print("색상 인식 시작\n")

    prev_name = ""

 

    while True:

        cid = get_dominant_id()

 

        if cid is None:

            if prev_name != "":

                print("[---] 인식된 색상 없음")

                prev_name = ""

        else:

            name = get_name(cid)

            if name != prev_name:

                print("[감지] " + name)

                prev_name = name

 

        time.sleep_ms(300)
