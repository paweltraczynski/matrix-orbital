"""
This main script is intended to be used with MicroPython for launching
the weather display project, which was written for MicroPython.
"""
import time
from machine import UART, Pin

# Import Matrix Orbital for interacting with the display.
from matrix_orbital import MatrixOrbital

# Import Weather Clock project.
from weather_clock.weather_clock import WeatherClock

# Allow time for the display to become ready for receiving commands.
time.sleep(2)

# Set GPIO pins.
tx_pin = 0
rx_pin = 1
dht_pin = 3
button_pin = 2
led_pin = 11

# Adjust the number of lines and columns that your display has.
lines = 4
cols = 20

# Initialize Matrix Orbital for interacting with the display module.
ua = UART(
    0,
    baudrate = 19200,
    bits = 8,
    parity = None,
    stop = 1,
    tx = Pin(tx_pin),
    rx = Pin(rx_pin)
)

mo = MatrixOrbital(ua)

# Weather and clock project that displays weather and time.
weather_clock = WeatherClock(
    vfd = mo,
    lines = lines,
    cols = cols,
    dht_pin = dht_pin,
    button_pin = button_pin,
    led_pin = led_pin
)

# Start the main loop.
weather_clock.keepRunning()
