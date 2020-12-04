"""ILI9341 LCD/Touch module."""
from time import sleep
from math import cos, sin, pi, radians
from sys import implementation
import ustruct
import utime
import gc
import framebuf

@micropython.viper
def color4to565(c:int) -> int:
    clup = [    0,30720,  992,31712,
               15,30735, 1007,25388,
            52825,63488, 2016,65504,
               31,63519, 2047,65535]
    return int(clup[c])

@micropython.viper
def _lcopy(dest, source, length:int):
    n = 0
    for x in range(length):
        c = source[x]
#         r, g, b = color4to24(int(c) >> 4)
#         color = int(color565(r, g, b))
        color = color4to565(int(c) >> 4)
        dest[n] = int(color) >> 8  # Blue green
        n += 1
        dest[n] = int(color) & 0xff   # Red
        n += 1
#         r, g, b = color4to24(int(c) & 15)
#         color = int(color565(r, g, b))
        color = color4to565(int(c) & 15)
        dest[n] = int(color) >> 8  # Blue green
        n += 1
        dest[n] = int(color) & 0xff   # Red
        n += 1

class Display(framebuf.FrameBuffer):
    """Serial interface for 16-bit color (5-6-5 RGB) IL9341 display.
    Note:  All coordinates are zero based.
    """

    # Command constants from ILI9341 datasheet
    NOP = bytearray([0x00])  # No-op
    SWRESET = bytearray([0x01])  # Software reset
    RDDID = bytearray([0x04])  # Read display ID info
    RDDST = bytearray([0x09])  # Read display status
    SLPIN = bytearray([0x10])  # Enter sleep mode
    SLPOUT = bytearray([0x11])  # Exit sleep mode
    PTLON = bytearray([0x12])  # Partial mode on
    NORON = bytearray([0x13])  # Normal display mode on
    RDMODE = bytearray([0x0A])  # Read display power mode
    RDMADCTL = bytearray([0x0B])  # Read display MADCTL
    RDPIXFMT = bytearray([0x0C])  # Read display pixel format
    RDIMGFMT = bytearray([0x0D])  # Read display image format
    RDSELFDIAG = bytearray([0x0F])  # Read display self-diagnostic
    INVOFF = bytearray([0x20])  # Display inversion off
    INVON = bytearray([0x21])  # Display inversion on
    GAMMASET = bytearray([0x26])  # Gamma set
    DISPLAY_OFF = bytearray([0x28])  # Display off
    DISPLAY_ON = bytearray([0x29])  # Display on
    SET_COLUMN = bytearray([0x2A])  # Column address set
    SET_PAGE = bytearray([0x2B])  # Page address set
    WRITE_RAM = bytearray([0x2C])  # Memory write
    READ_RAM = bytearray([0x2E])  # Memory read
    PTLAR = bytearray([0x30])  # Partial area
    VSCRDEF = bytearray([0x33])  # Vertical scrolling definition
    MADCTL = bytearray([0x36])  # Memory access control
    VSCRSADD = bytearray([0x37])  # Vertical scrolling start address
    PIXFMT = bytearray([0x3A])  # COLMOD: Pixel format set
    FRMCTR1 = bytearray([0xB1])  # Frame rate control (In normal mode/full colors])
    FRMCTR2 = bytearray([0xB2])  # Frame rate control (In idle mode/8 colors])
    FRMCTR3 = bytearray([0xB3])  # Frame rate control (In partial mode/full colors])
    INVCTR = bytearray([0xB4])  # Display inversion control
    DFUNCTR = bytearray([0xB6])  # Display function control
    PWCTR1 = bytearray([0xC0])  # Power control 1
    PWCTR2 = bytearray([0xC1])  # Power control 2
    PWCTRA = bytearray([0xCB])  # Power control A
    PWCTRB = bytearray([0xCF])  # Power control B
    VMCTR1 = bytearray([0xC5])  # VCOM control 1
    VMCTR2 = bytearray([0xC7])  # VCOM control 2
    RDID1 = bytearray([0xDA])  # Read ID 1
    RDID2 = bytearray([0xDB])  # Read ID 2
    RDID3 = bytearray([0xDC])  # Read ID 3
    RDID4 = bytearray([0xDD])  # Read ID 4
    GMCTRP1 = bytearray([0xE0])  # Positive gamma correction
    GMCTRN1 = bytearray([0xE1])  # Negative gamma correction
    DTCA = bytearray([0xE8])  # Driver timing control A
    DTCB = bytearray([0xEA])  # Driver timing control B
    POSC = bytearray([0xED])  # Power on sequence control
    ENABLE3G = bytearray([0xF2])  # Enable 3 gamma control
    PUMPRC = bytearray([0xF7])  # Pump ratio control

    ROTATE = {
        0: 0x88,
        90: 0xE8,
        180: 0x48,
        270: 0x28
    }

    ##@timed_function
    def __init__(self, spi, cs, dc, rst,
                 width=240, height=320, rotation=0):
        """Initialize OLED.
        Args:
            spi (Class Spi):  SPI interface for OLED
            cs (Class Pin):  Chip select pin
            dc (Class Pin):  Data/Command pin
            rst (Class Pin):  Reset pin
            width (Optional int): Screen width (default 240)
            height (Optional int): Screen height (default 320)
            rotation (Optional int): Rotation must be 0 default, 90. 180 or 270
        """
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.width = width
        self.height = height
        self.mode = framebuf.GS4_HMSB
        self.lines = 1
        gc.collect()
        self.buffer = bytearray(self.height * self.width // 2)
        self._mvb = memoryview(self.buffer)
        super().__init__(self.buffer, self.width, self.height, self.mode)
        self._linebuf = bytearray(self.width*self.lines*2)
        
        if rotation not in self.ROTATE.keys():
            raise RuntimeError('Rotation must be 0, 90, 180 or 270.')
        else:
            self.rotation = self.ROTATE[rotation]

        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        self.rst.init(self.rst.OUT, value=1)
        self.reset = self.reset_mpy
        self.write_cmd = self.write_cmd_mpy
        self.write_data = self.write_data_mpy
        self.reset()
        # Send initialization commands
        self.write_cmd(self.SWRESET)  # Software reset
        sleep(.1)
        self.write_cmd(self.PWCTRB, 0x00, 0xC1, 0x30)  # Pwr ctrl B
        self.write_cmd(self.POSC, 0x64, 0x03, 0x12, 0x81)  # Pwr on seq. ctrl
        self.write_cmd(self.DTCA, 0x85, 0x00, 0x78)  # Driver timing ctrl A
        self.write_cmd(self.PWCTRA, 0x39, 0x2C, 0x00, 0x34, 0x02)  # Pwr ctrl A
        self.write_cmd(self.PUMPRC, 0x20)  # Pump ratio control
        self.write_cmd(self.DTCB, 0x00, 0x00)  # Driver timing ctrl B
        self.write_cmd(self.PWCTR1, 0x23)  # Pwr ctrl 1
        self.write_cmd(self.PWCTR2, 0x10)  # Pwr ctrl 2
        self.write_cmd(self.VMCTR1, 0x3E, 0x28)  # VCOM ctrl 1
        self.write_cmd(self.VMCTR2, 0x86)  # VCOM ctrl 2
        self.write_cmd(self.MADCTL, self.rotation)  # Memory access ctrl
        self.write_cmd(self.VSCRSADD, 0x00)  # Vertical scrolling start address
        self.write_cmd(self.PIXFMT, 0x55)  # COLMOD: Pixel format
        self.write_cmd(self.FRMCTR1, 0x00, 0x18)  # Frame rate ctrl
        self.write_cmd(self.DFUNCTR, 0x08, 0x82, 0x27)
        self.write_cmd(self.ENABLE3G, 0x00)  # Enable 3 gamma ctrl
        self.write_cmd(self.GAMMASET, 0x01)  # Gamma curve selected
        self.write_cmd(self.GMCTRP1, 0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08, 0x4E,
                       0xF1, 0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00)
        self.write_cmd(self.GMCTRN1, 0x00, 0x0E, 0x14, 0x03, 0x11, 0x07, 0x31,
                       0xC1, 0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F)
        self.write_cmd(self.SLPOUT)  # Exit sleep
        sleep(.1)
        self.write_cmd(self.DISPLAY_ON)  # Display on
        sleep(.1)

        self.show()

    def reset_mpy(self):
        """Perform reset: Low=initialization, High=normal operation.
        Notes: MicroPython implemntation
        """
        self.rst(0)
        sleep(.05)
        self.rst(1)
        sleep(.05)

    def write_cmd(self, command, *args):
        """Write command to OLED (MicroPython).
        Args:
            command (byte): ILI9341 command code.
            *args (optional bytes): Data to transmit.
        """
        self.dc(0)
        self.cs(0)
        self.spi.write(command)
        self.cs(1)
        # Handle any passed data
        if len(args) > 0:
            self.write_data(bytearray(args))

    def write_data(self, data):
        """Write data to OLED (MicroPython).
        Args:
            data (bytes): Data to transmit.
        """
        self.dc(1)
        self.cs(0)
        self.spi.write(data)
        self.cs(1)

    def show(self):  # Blocks 38.6ms on Pyboard D at stock frequency
        wd = self.width // 2
        ht = self.height
        lb = self._linebuf
        buf = self._mvb
        self.write_cmd(self.SET_COLUMN, *ustruct.pack(">HH", 0, wd*2))
        self.write_cmd(self.SET_PAGE, *ustruct.pack(">HH", 0, ht))
        self.write_cmd(self.WRITE_RAM)
        self.dc(1)
        self.cs(0)
        for start in range(0, wd*ht, wd*self.lines):  # For each line
            _lcopy(lb, buf[start :], wd*self.lines)  # Copy and map colors (68us)
            self.spi.write(lb)
        self.cs(1)
