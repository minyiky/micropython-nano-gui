# color_setup.py Customise for your hardware config

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2020 Peter Hinch

# As written, supports:
# Adafruit 1.5" 128*128 OLED display: https://www.adafruit.com/product/1431
# Adafruit 1.27" 128*96 display https://www.adafruit.com/product/1673
# Edit the driver import for other displays.

# Demo of initialisation procedure designed to minimise risk of memory fail
# when instantiating the frame buffer. The aim is to do this as early as
# possible before importing other modules.

# WIRING (Adafruit pin nos and names).

from machine import Pin, SPI
import gc

# *** Choose your color display driver here ***
# Driver supporting non-STM platforms

# STM specific driver
from drivers.ili9XXX.ili9341 import Display

gc.collect()  # Precaution before instantiating framebuf
spi = SPI(2, baudrate=40000000, sck=Pin(18), mosi=Pin(23))

# Name ssd kept to maintain compatability with examples
ssd = Display(spi, dc=Pin(4), cs=Pin(16), rst=Pin(17))
