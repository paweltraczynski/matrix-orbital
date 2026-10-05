import time
from machine import UART, Pin

# Custom libraries.
from matrix_orbital import MatrixOrbital
from vfd_info.vfd_info import VfdInfo

# Allow time for the display to become ready for receiving commands.
time.sleep(2)

# Set GPIO pins.
tx_pin = 0
rx_pin = 1
button_pin = 2
dht_sensor_pin = 3

# Adjust the number of lines and columns that your display has.
lines = 4
cols = 20

# Initialize custom libraries.
ua = UART(0, baudrate = 19200, bits = 8, parity = None, stop = 1, tx = Pin(tx_pin), rx = Pin(rx_pin))

mo = MatrixOrbital(ua)

vfd_info = VfdInfo(mo, lines = lines, cols = cols, dht_pin = dht_sensor_pin, button_pin = button_pin)

# Start the main loop.
vfd_info.keepRunning()
