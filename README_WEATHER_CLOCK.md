# Weather Clock project

This project displays a weather clock on a Matrix Orbital VFD module.
It shows:

- current time
- current weather information (temperature, humidity, wind speed, and current
  conditions, such as clouds or rain)
- current indoor temperature and humidity (requires a DHT22 sensor).

Only the 20x4 display is supported.

## The build process

Connect the Matrix Orbital module to the Raspberry Pi Pico 2 W using the
serial TTL connection described in the [main README](README.md#serial-ttl).
The supplied `main.py` uses UART0 at 19200 baud, with GP0 as TX and GP1 as RX.
Use the logic level shifting described in the main README.

The photos in this document come from the Noritake Itron project and show a
Noritake Itron display module. For this version of the project, use a Matrix
Orbital module instead of the Noritake Itron module shown in the photos. All
the build and operating principles are the same; for the Matrix Orbital display
connection and GPIO assignments, follow the instructions here and in the main
README.

For the GPIO assignments in the supplied `main.py`, connect:
- the DHT22 sensor to GP3 + GND pin + 3.3 V pin
- an LED to GP11 (through a resistor) + GND pin
- a push-button to GP2 + GND pin

The following photos show all the parts I used to build this project:

<img src="images/weather_clock/parts_1.jpg" alt="Build parts 1" width="500">

The main parts were:

- VFD module (use a Matrix Orbital module for this version)
- Raspberry Pi Pico 2 W
- DHT22 sensor
- Momentary push button
- Aluminum button cap
- LED
- USB-C port
- Screws (M3, M2.5, M2)
- Standoffs (M3 and M2)
- Rubber feet
- BLS and JST-XH connectors
- Hookup wire
- Prototyping board for the push button
- Prototyping board with a resistor and potentiometer for connecting components

<img src="images/weather_clock/parts_2.jpg" alt="Build parts 2" width="500">

I used a custom-designed acrylic box as the enclosure. I also used 22 AWG wire:

<img src="images/weather_clock/case.jpg" alt="Acrylic enclosure" width="500">

The project might look complex, but what is really needed to make it work is the
connections between the MicroPython board, VFD, LED, and DHT22.

## Python files

The Weather Clock project requires these files:
- `weather_clock.py` - the main file of the project
- `wifi.py` - used for managing the Wi-Fi connection
- `fetchers.py` - used for fetching time and weather data from the Internet
- `settings_handler.py` - the project saves user settings in `settings.txt`
- `large_digits_3_rows.py` - used by the clock on layout 1
- `large_digits_2_rows.py` - used by the clock on layout 2
- `matrix_rain.py` - for showing the Matrix Rain at the start of each hour
- `config.py` - configuration file
- `main.py` - use this file to run the project

The project files above, except `main.py`, are in the `weather_clock/` directory.

You also need the Matrix Orbital driver:
- `matrix_orbital.py`

## How to run it

When using this project, preserve file structures and directories.

Copy `main.py` and `matrix_orbital.py` to the board's root directory, and copy
the `weather_clock/` directory there, preserving its structure.

Use `weather_clock/config.py` as the source when copying to
`weather_clock/config_local.py`. Edit the copy as explained in the
[config file instructions](README.md#config-file).

There is some configuration to do in `main.py` too. If you have
connected a DHT22, a button, or an LED, then you need to provide their pins:

```python
dht_pin = 3
button_pin = 2
led_pin = 11
```

Numbers refer to GPIO numbers, not physical header pin numbers.

If any of these are not connected, then set their values to `None`.

With `main.py` in the board's root directory, the project runs automatically
when the MicroPython board is powered on.

## The DHT22, the LED, and the button

The DHT22 sensor is used for measuring the indoor temperature and humidity.
Without it, that is when its pin is set to `None`, the project will work but the
indoor fields will show `--.-` for temperature and `--` for humidity.

The LED provides decorative lighting inside the acrylic case. Set its pin to
`None` if you are not using it.

The button is used for various functions explained below. When it's not present
(and its pin is set to `None`) some functions are not available.

## Button functions

The functions of the button depend on whether the screen is on (during the day),
dimmed
(during the evening) or off (during the night).

The display is lit during the day, during the evening dim hours, and
while the night-wake function is active.

- Short press:
  - During the day: Changes daytime brightness
  - During dim hours: Nothing
  - During the night: Activates the night-wake function
- Double press (start the second press within 0.5 seconds of releasing the
  first):
  - When the display is lit: Changes LED brightness or turns it on/off
- Long press (hold for at least 1.5 seconds):
  - When the display is lit: Toggles layouts 1 and 2

Night wake turns the display on for 10 seconds. A short press during
a night-wake restarts this timer.

## Settings file

Selected daytime brightness, LED brightness, and layout are saved in the
`settings.txt` file. These settings are loaded at startup.

If you haven't connected a button, you can still choose a fixed daytime
brightness, LED brightness, and layout by editing the `settings.txt` file.

Settings are stored in `settings.txt` in the board’s root directory, alongside
`main.py`.
Use the supplied settings by copying `weather_clock/settings.txt` there.

The settings format is:
```
layout: 1
brightness: 4
led: 4
```

Valid values are:
- 1–2 for layout
- 1–4 for display brightness
- 0–4 for LED brightness (0 means off).

If the file is missing, these defaults are used. Button changes to brightness or
layout create or update the file. A night-wake press alone does not save
settings.

Restart the board after editing it manually.

## Photos of the project

Here are some photos of the completed project:

Layout 1:

<img src="images/weather_clock/layout_1.jpg" alt="Layout 1" width="500">

Layout 2:

<img src="images/weather_clock/layout_2.jpg" alt="Layout 2" width="500">

View from the back:

<img src="images/weather_clock/view_back.jpg" alt="Rear view" width="500">

View from the top:

<img src="images/weather_clock/view_top_1.jpg" alt="Top view 1" width="500">

Another view from the top:

<img src="images/weather_clock/view_top_2.jpg" alt="Top view 2" width="500">

How it looks in the dark:

<img src="images/weather_clock/night_front.jpg" alt="Front, night" width="500">

Rearview in the dark:

<img src="images/weather_clock/night_back.jpg" alt="Rear at night" width="500">

## Final thoughts

The code includes comments explaining its behavior and configuration.

If you have any questions, feel free to ask me.

