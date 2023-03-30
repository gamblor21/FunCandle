# SPDX-FileCopyrightText: 2023 Mark Komus
#
# SPDX-License-Identifier: MIT
import gifio
import displayio
import time
from adafruit_st7789 import ST7789
import board
import busio
import struct
import array
import digitalio
from adafruit_sht4x import SHT4x
import adafruit_dotstar
import asyncio
import pwmio
import random

CNOTE = 523
DNOTE = 587
ENOTE = 659
FNOTE = 698
GNOTE = 784
ANOTE = 880
BFNOTE = 932
C2NOTE = 1046

lights = [(8,10,2), (10,12,3), (7,9,2), (6,8,1), (5,7,0)]

async def FlickerLights(pixels):
    global lights_on

    while True:
        if lights_on is True:
            for p in range(5):
                if random.random() >= 0.999:
                    pixels[p] = lights[random.randint(0,4)]

        await asyncio.sleep(0)

async def PlayTone(freq, duration):
    with pwmio.PWMOut(board.SPEAKER, frequency=freq, variable_frequency=False) as pwm:
        pwm.duty_cycle = 0x8000
        await asyncio.sleep(duration)

async def PlaySong():
    global song_playing
    if song_playing is True:
        return
    song_playing = True

    await PlayTone(CNOTE, 0.3)
    await PlayTone(CNOTE, 0.2)
    await PlayTone(DNOTE, 0.4)
    await PlayTone(CNOTE, 0.4)
    await PlayTone(FNOTE, 0.4)
    await PlayTone(ENOTE, 0.8)

    await PlayTone(CNOTE, 0.3)
    await PlayTone(CNOTE, 0.2)
    await PlayTone(DNOTE, 0.4)
    await PlayTone(CNOTE, 0.4)
    await PlayTone(GNOTE, 0.4)
    await PlayTone(FNOTE, 0.8)

    await PlayTone(CNOTE, 0.3)
    await PlayTone(CNOTE, 0.2)
    await PlayTone(C2NOTE, 0.4)
    await PlayTone(ANOTE, 0.4)
    await PlayTone(FNOTE, 0.4)
    await PlayTone(ENOTE, 0.4)
    await PlayTone(DNOTE, 0.8)

    await PlayTone(BFNOTE, 0.3)
    await PlayTone(BFNOTE, 0.2)
    await PlayTone(ANOTE, 0.4)
    await PlayTone(FNOTE, 0.4)
    await PlayTone(GNOTE, 0.4)
    await PlayTone(FNOTE, 0.8)

    song_playing = False

async def Candle():
    global base_humidity
    global lights_on

    while True:
        frames =  0
        base_humidity = sensor.relative_humidity
        gif = gifio.OnDiskGif("lit.gif")
        gif.next_frame()

        pixels.fill((8,10,2))

        candle_lit = True
        lights_on = True
        while True:
            start = time.monotonic()
            display_bus.send(42, struct.pack(">hh", 0, 239))
            display_bus.send(43, struct.pack(">hh", 80, 319))
            display_bus.send(44, gif.bitmap)

            frames += 1
            if frames > 20:
                base_humidity = sensor.relative_humidity
                print("Base humidity ", base_humidity)
                frames = 0

            if music_button.value is True:
                asyncio.create_task(PlaySong())

            if candle_lit is True and sensor.relative_humidity > base_humidity+1.5:
                print("Candle out ", sensor.relative_humidity)
                candle_lit = False
                gif = gifio.OnDiskGif("out.gif")
                next_delay = gif.next_frame()
                break

            next_delay = gif.next_frame()
            end = time.monotonic()
            await asyncio.sleep(max(0,next_delay-(end-start)))

        lights_on = False
        pixels.fill(0)

        for _ in range(20):
            start = time.monotonic()
            display_bus.send(42, struct.pack(">hh", 0, 239))
            display_bus.send(43, struct.pack(">hh", 80, 319))
            display_bus.send(44, gif.bitmap)

            next_delay = gif.next_frame()
            end = time.monotonic()
            await asyncio.sleep(max(0,next_delay-(end-start)))

        while True:
            if button.value is True:
                break
            await asyncio.sleep(0)

async def main():
    asyncio.create_task(FlickerLights(pixels))
    await Candle()

if __name__=="__main__":
    displayio.release_displays()
    FREQ=60_000_000

    spi = busio.SPI(board.TFT_SCK, board.TFT_MOSI, None)
    spi.try_lock()
    spi.configure(baudrate=FREQ)
    spi.unlock()

    display_bus = displayio.FourWire(
        spi, command=board.TFT_DC, chip_select=board.TFT_CS, reset=board.TFT_RESET,
        baudrate=FREQ
    )

    display = ST7789(display_bus, width=240, height=240, rowstart=80)
    display.root_group = None

    tft_light = digitalio.DigitalInOut(board.TFT_BACKLIGHT)
    tft_light.direction = digitalio.Direction.OUTPUT
    tft_light.value = True

    i2c = board.I2C()
    sensor = SHT4x(i2c)
    base_humidity = sensor.relative_humidity
    print("Base humidity ", base_humidity)

    button = digitalio.DigitalInOut(board.BUTTON_UP)
    button.direction = digitalio.Direction.INPUT

    music_button = digitalio.DigitalInOut(board.BUTTON_SELECT)
    music_button.direction = digitalio.Direction.INPUT
    song_playing = False

    pixels = adafruit_dotstar.DotStar(board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, 5)
    lights_on = True

    display_bus = display.bus

    asyncio.run(main())
