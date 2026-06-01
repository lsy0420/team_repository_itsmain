import time

from machine import Pin, ADC

import neopixel

 

np = neopixel.NeoPixel(Pin(16), 10)

gas_sensor = ADC(Pin(26))

 

def read_sensor():

    return gas_sensor.read_u16() // 13

 

while True:

    val = read_sensor()

    if val >= 500:

        for i in range(10):

            np[i] = (0, 255, 0)  # 초록

    else:

        for i in range(10):

            np[i] = (255, 0, 0)  # 빨강

    np.write()

    time.sleep(0.05)
