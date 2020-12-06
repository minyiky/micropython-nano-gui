# color_setup.py Customise for your hardware config

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2020 Peter Hinch

# As written, supports:
# ili9341 240x320 displays
# Edit the driver import for other displays.

# Demo of initialisation procedure designed to minimise risk of memory fail
# when instantiating the frame buffer. The aim is to do this as early as
# possible before importing other modules.

# WIRING (TODO).

from machine import Pin, SPI
import gc

# *** Choose your color display driver here ***
# ili9341 specific driver
from divers.ili9XXX.ili9341 import ili9341

# Kept as ssd to maintain compatability
gc.collect()  # Precaution before instantiating framebuf
spi = SPI(2, baudrate=10000000, sck=Pin(18), mosi=Pin(23))
ssd = ili9341(spi, dc=Pin(4), cs=Pin(16), rst=Pin(17))
