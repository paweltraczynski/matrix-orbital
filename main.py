import time
from machine import UART, Pin

# Custom libraries.
from matrix_orbital import MatrixOrbital
from vfd_info.vfd_info import VfdInfo

# Allow time for the display to become ready for receiving commands.
time.sleep(2)

# Initialize custom libraries.
ua = UART(0, baudrate = 19200, bits = 8, parity = None, stop = 1, tx = Pin(0), rx = Pin(1))
mo = MatrixOrbital(ua)
vfd_info = VfdInfo(mo, lines = 4, cols = 20, dht_pin = 3, button_pin = 2)

# Start the main loop.
vfd_info.keepRunning()
