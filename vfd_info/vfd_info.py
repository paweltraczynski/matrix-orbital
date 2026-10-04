import time
import network
import requests
from machine import Pin, RTC
import dht

# Dots on the start are required for RPi Pico/MicroPython boards.
from .vfd_info_digits import VfdInfoDigits

# Import vfd_info_config_local.py if user has created it.
try:
    from . import vfd_info_config_local as config
# Otherwise import vfd_info_config.py (assuming the user has customized it).
except ImportError:
    from . import vfd_info_config as config

class VfdInfo:
    """
    Displays a local time clock, local weather, and indoor temperature.

    :param mo: The Matrix Orbital class.
    :param lines: The number of lines on the display.
    :param cols: The number of columns on the display.
    :param dht_pin: The number of the DHT22 sensor pin.
      Leave blank if you have not connected the sensor.
    :param button_pin: The number of the button pin.
      Leave blank if you have not connected the button.
    """

    def __init__(self, mo, lines, cols, dht_pin = None, button_pin = None):
        # Display details.
        self.mo = mo
        self.lines = lines
        self.cols = cols

        # Large digits.
        self.digits = VfdInfoDigits(self.mo)

        # DHT22 sensor.
        if dht_pin is not None:
            self.sensor = dht.DHT22(Pin(dht_pin))
        else:
            self.sensor = None

        # Button for changing the brightness.
        if button_pin is not None:
            self.button = Pin(button_pin, Pin.IN, Pin.PULL_UP)
        else:
            self.button = None

        # RTC used by the clock feature.
        self.rtc = RTC()

        # Wi-Fi.
        self.wlan = network.WLAN(network.STA_IF)
        self.ssid = config.wifi_ssid
        self.password = config.wifi_password
        self.wifi_last_attempt = None
        self.wifi_retry_interval = 10 * 1000

        # Time settings.
        self.timeapi_api_key = config.time_api_key
        self.timezone = config.time_timezone

        # Time fetching.
        # Stores the last date synchronization time in ms.
        self.date_last_fetch =  None
        self.date_last_attempt = None
        # 6-hour interval converted to milliseconds.
        self.date_fetch_interval = 6 * 60 * 60 * 1000

        # Weather settings.
        self.weather_api_key = config.weather_api_key
        self.weather_city = config.weather_city
        self.weather_unit = config.weather_unit

        # Weather fetching.
        # Stores the last weather synchronization time in ms.
        self.weather_last_fetch =  None
        self.weather_last_attempt = None
        # 10-minutes interval converted to milliseconds.
        self.weather_fetch_interval = 10 * 60 * 1000

        # Fetched weather.
        self.weather = {
            'temperature': 0,
            'humidity': 0,
            'conditions': '',
            'success': False,
        }

        # Failed API requests are retried after one minute.
        self.api_retry_interval = 60 * 1000
        self.api_timeout = 10

        # Track last displayed values.
        # This is used to prevent writing to the VFD data did not change.
        self.displayed_time = None
        self.displayed_temperature = None
        self.displayed_humidity = None
        self.displayed_conditions = None
        self.displayed_indoor_temperature = None
        self.displayed_indoor_humidity = None

        # Track the last time when values were displayed.
        # This is used to prevent calling print methods more
        # often than necessary.
        self.last_time = None
        self.last_weather = None
        self.last_indoor = None

        # Track brightness.
        # Current brightness status (on, dimed, off).
        self.brightness_status = 'on'
        # Last user set brightness.
        self.brightness_set = 4
        # Brightness changing button last pressed time.
        self.brightness_button = None

        # Track download icon.
        self.download_icon_start = True
        self.download_icon_shown = False
        self.download_icon_time = 0

    def connectWifi(self):
        """
        Connects to the Wi-Fi network, retries if the SSID is unavailable.
        """
        current_ticks = time.ticks_ms()

        # Do not retry connecting more often than the configured interval.
        if (
            self.wifi_last_attempt is not None and
            time.ticks_diff(current_ticks, self.wifi_last_attempt)
            < self.wifi_retry_interval
        ):
            return False

        self.wifi_last_attempt = current_ticks
        self.wlan.active(True)

        # Indicate no Wi-Fi connection by settings the connection icon.
        self.mo.setCursor(0, 4)
        self.mo.write(self.mo.getNamedCharacter('not_equal'))

        # Initiate a Wi-Fi connection.
        try:
            self.wlan.connect(self.ssid, self.password)
        except OSError:
            return False

        # Give this attempt up to 10 seconds.
        for _ in range(10):
            if self.wlan.isconnected():
                break
            time.sleep(1)

        # Because up to 10 seconds might have passed, update the last attempt.
        self.wifi_last_attempt = time.ticks_ms()

        # If the connection failed, then try to disconnect before retrying.
        if not self.wlan.isconnected():
            try:
                self.wlan.disconnect()
            except OSError:
                pass

            print('Wi-Fi unavailable; retrying...')
            return False

        # At this point, the connection has been established.
        self.mo.setCursor(0, 4)
        self.mo.write(self.mo.getNamedCharacter('graph'))

        print('Established Wi-Fi connection.')
        return True

    def urlEncode(self, value):
        """
        Encodes a string to be used in a URL.

        :param value: The string to encode.

        :return: The encoded string.
        """
        encoded = []

        for byte in str(value).encode('utf-8'):
            is_unreserved = (
                ord('A') <= byte <= ord('Z') or
                ord('a') <= byte <= ord('z') or
                ord('0') <= byte <= ord('9') or
                byte in (ord('-'), ord('.'), ord('_'), ord('~'))
            )

            if is_unreserved:
                encoded.append(chr(byte))
            else:
                encoded.append('%{:02X}'.format(byte))

        return ''.join(encoded)

    def urlGetJson(self, url, params = None):
        """
        Gets JSON from a URL.

        :param url: The URL to get JSON from.
        :param params: The parameters to include in the URL.

        :return: The JSON data or False if the request failed.
        """
        if params:
           url = url.rstrip('?') + '?'

           for key, value in params.items():
               url += key + '=' + self.urlEncode(value) + '&'

           url = url.rstrip('&')

        response = None
        try:
            response = requests.get(url, timeout = self.api_timeout)

            if response.status_code == 200:
                # TODO: Shouldn't it close before returning?
                return response.json()
            else:
                return False
        finally:
            if response is not None:
                response.close()

        return False

    def checkHourInRange(self, hour, start, end):
        """
        Checks if the given hour is in the given range.

        :param hour: The hours to check, e.g., 3 or 22.
        :param start: The start hour of the range.
        :param end: The end hour of the range.

        :return: True if the hour is in the range, False otherwise.
        """
        if start == end:
            return False

        if start < end:
            return start <= hour < end

        return hour >= start or hour < end

    def changeBrightness(self):
        """
        Continuously changes the brightness by 1 brightness level.
        """
        # Each time the brightness gets decreased by 1.
        brightness = self.brightness_set - 1

        # After reaching the minimum brightness, reset to maximum.
        if brightness < 1:
            brightness = 4

        self.brightness_set = brightness

        if self.brightness_status == 'on':
            self.mo.setBrightness(brightness)

    def fetchDateTime(self):
        """
        Fetches the current date from the https://gateway.timeapi.world/ API.
        """
        print('Fetching date and time from the Internet.')

        # The timeapi.world gateway endpoint url.
        url = f'https://gateway.timeapi.world/timezone/{self.timezone}'

        headers = {
            'x-rapidapi-key': self.timeapi_api_key,
            'x-rapidapi-host': 'world-time-api3.p.rapidapi.com',
            'Content-Type': 'application/json'
        }

        self.date_last_attempt = time.ticks_ms()
        response = None

        try:
            # Send the GET request with the required headers.
            response = requests.get(url, headers = headers, timeout = self.api_timeout)

            if response.status_code == 200:
                data = response.json()
                datetime = data['datetime']

                # Parse the ISO 8601 datetime response string.
                year = int(datetime[0:4])
                month = int(datetime[5:7])
                day = int(datetime[8:10])
                hour = int(datetime[11:13])
                minute = int(datetime[14:16])
                second = int(datetime[17:19])

                # The API uses 0 for Sunday to 6 for Saturday.
                # RTC expects 0 for Monday to 6 for Sunday.
                api_dow = data['day_of_week']
                rtc_dow = 6 if api_dow == 0 else api_dow - 1

                # Set the system time.
                self.rtc.datetime(
                    (year, month, day, rtc_dow, hour, minute, second, 0)
                )

                # Save the timestamp of the successful synchronization.
                self.date_last_fetch = time.ticks_ms()

                # Set a flag that will toggle the download icon.
                self.download_icon_start = True

                response.close()
                print('Synchronized date and time.')
                return True

            else:
                response.close()
                print('Failed to synchronize date and time.')
                return False

        except Exception as e:
            if hasattr(response, 'close'):
                response.close()
            print('Date and time synchronization error:', e)
            return False

    def getDateTime(self):
        """
        Gets the current date and time from the hardware RTC.
        """
        # TODO: time.ticks_ms() and time.ticks_diff() CPython compatible.
        current_ticks = time.ticks_ms()

        # Fetch date and time from the internet if they weren't fetched yet,
        # or if they were fetched more than 6 hours ago.
        if (
            (self.date_last_fetch is None) or
            (time.ticks_diff(current_ticks, self.date_last_fetch)
             >= self.date_fetch_interval)
        ) and (
            (self.date_last_attempt is None) or
            (time.ticks_diff(current_ticks, self.date_last_attempt)
             >= self.api_retry_interval)
        ):
            self.fetchDateTime()

        # Read the current time directly from the hardware RTC.
        hardware_time = self.rtc.datetime()

        # Return the dictionary with the current date and time parts.
        if self.date_last_fetch is not None:
            return {
                'year': str(hardware_time[0]),
                # Fill with leading zeros.
                'month': '{:0>2}'.format(hardware_time[1]),
                'day': '{:0>2}'.format(hardware_time[2]),
                'hour': '{:0>2}'.format(hardware_time[4]),
                'minute': '{:0>2}'.format(hardware_time[5]),
                'second': '{:0>2}'.format(hardware_time[6]),
                'timestamp': time.time(),
                'hour_int': hardware_time[4],
                'minute_int': hardware_time[5],
            }
        else:
            return {
                'year': 0,
                'month': '00',
                'day': '00',
                'hour': '00',
                'minute': '00',
                'second': '00',
                'timestamp': '00',
                'hour_int': 0,
                'minute_int': 0,
            }

    def printDateTime(self):
        """
        Prints the current time on the display.
        """
        current_ticks = time.ticks_ms()

        # Don't print time more often than every 0.2 seconds.
        if self.last_time is not None and time.ticks_diff(current_ticks, self.last_time) < 200:
            return

        self.last_time = current_ticks

        # Get date and time.
        date = self.getDateTime()

        # Print the time if it is set.
        if date['year'] != 0:
            time_formatted = '{hour}:{minute}:{second}'.format(
                hour = date['hour'],
                minute = date['minute'],
                second = date['second']
            )

            # Do so only if it has changed since the last print.
            if self.displayed_time != time_formatted:
                hour = str(date['hour'])
                minute = str(date['minute'])

                self.digits.largeDigit(hour[0], 10)
                self.digits.largeDigit(hour[1], 13)
                self.digits.largeDigit(minute[0], 16)
                self.digits.largeDigit(minute[1], 19)
                self.mo.setCursor(18, 4)
                self.mo.write(":{0}".format(date['second']))

                self.displayed_time = time_formatted

                # Blinking colon between hours and minutes.
                if date['timestamp'] % 2 == 0:
                    self.digits.largeDigit('colon', 15)
                else:
                    self.digits.largeDigit('erase_colon', 15)

        # If time is not set, then print dashes and static colon.
        else:
            if self.displayed_time != '-':
                self.digits.largeDigit('dash', 10)
                self.digits.largeDigit('dash', 13)
                self.digits.largeDigit('dash', 16)
                self.digits.largeDigit('dash', 19)
                self.mo.setCursor(18, 4)
                self.mo.write(':--')

                self.displayed_time = '-'

                # Static colon when time is not known.
                self.digits.largeDigit('colon', 15)

    def fetchWeather(self):
        """
        Fetches the weather data for from the OpenWeatherMap API.
        """
        print('Fetching weather data from the OpenWeatherMap.')

        # The open weather API endpoint url.
        weather_url = 'https://api.openweathermap.org/data/2.5/weather'

        params = {
            'q': self.weather_city,
            'appid': self.weather_api_key,
            'units': self.weather_unit,
        }

        temperature = 0
        humidity = 0
        conditions = ''
        success = False

        self.weather_last_attempt = time.ticks_ms()

        try:
            weather = self.urlGetJson(weather_url, params)

            # Weather API deta structure.
            # timezone => 7200
            # sys => Dict {
            #   type => 2
            #   sunrise => 1787888431
            #   country => 'PL'
            #   id => 2032856
            #   sunset => 1787938467
            # }
            # base => 'stations'
            # main => Dict {
            #   pressure => 1016
            #   feels_like => 23.67
            #   temp_max => 25.86
            #   temp => 24.18
            #   temp_min => 23.13
            #   humidity => 39
            #   sea_level => 1016
            #   grnd_level => 1005
            # }
            # visibility => 10000
            # id => 756135
            # clouds => Dict {
            #   all => 89
            # }
            # coord => Dict {
            #   lon => 21.0118
            #   lat => 52.2298
            # }
            # name => 'Warsaw'
            # cod => 200
            # weather => [
            #   0 => Dict {
            #     id => 804
            #     icon => '04d'
            #     main => 'Clouds'
            #     description => 'overcast clouds'
            #   }
            # ]
            # dt => 1787930328
            # wind => Dict {
            #   speed => 5.14
            #   deg => 130
            # }

            if weather and isinstance(weather, dict):
                temperature = round(weather['main']['temp'], 1)
                humidity = round(weather['main']['humidity'])
                conditions = weather['weather'][0]['main']
                success = True

                # Save the timestamp of the successful synchronization.
                self.weather_last_fetch = time.ticks_ms()

                # Set a flag that will toggle the download icon.
                self.download_icon_start = True

                print('Fetched weather data from OpenWeatherMap.')

            else:
                print('Failed to fetch weather data from OpenWeatherMap.')

        except Exception as e:
            print('Weather synchronization error:', e)

        self.weather = {
            'temperature': temperature,
            'humidity': humidity,
            'conditions': conditions,
            'success': success,
        }

    def getWeather(self):
        """
        Gets the last fetched weather data and refetches if needed.
        """
        current_ticks = time.ticks_ms()

        # Fetch weather from the internet if it wasn't fetched yet,
        # or if it was fetched more than 10 minutes ago.
        if (
            (self.weather_last_fetch is None) or
            (time.ticks_diff(current_ticks, self.weather_last_fetch)
             >= self.weather_fetch_interval)
        ) and (
            (self.weather_last_attempt is None) or
            (time.ticks_diff(current_ticks, self.weather_last_attempt)
             >= self.api_retry_interval)
        ):
            self.fetchWeather()

        # Return the weather data.
        return self.weather

    def printWeather(self):
        current_ticks = time.ticks_ms()

        # Don't print weather more often than 30 seconds.
        if self.last_weather is not None and time.ticks_diff(current_ticks, self.last_weather) < 30 * 1000:
            return

        self.last_weather = current_ticks

        # Get weather data.
        weather = self.getWeather()

        # Print weather if it was fetched.
        if weather['success']:
            temperature = weather['temperature']
            humidity = weather['humidity']
            conditions = weather['conditions']

            # Temperature should always include 1 fraction digit
            # occupying 5 characters because it can, for example, be '-15.5'.
            temperature = '{:>5.1f}'.format(temperature)

            # Humidity should be rounded and always in range of 0-99,
            # and also always 2 characters. It should never be more
            # than 99% because of available space.
            if humidity > 99:
                humidity = 99
            humidity = '{:>2}'.format(humidity)

            # Print temperature.
            if self.displayed_temperature != temperature:
                self.mo.setCursor(3, 3)
                self.mo.write(temperature)
                self.displayed_temperature = temperature

            # Print humidity.
            if self.displayed_humidity != humidity:
                self.mo.setCursor(14, 4)
                self.mo.write(humidity)
                self.displayed_humidity = humidity

            # Print icon for indicating weather conditions.
            if self.displayed_conditions != conditions:
                self.mo.setCursor(3, 4)
                self.displayed_conditions = conditions

                # Clouds.
                if conditions == 'Clouds':
                    self.mo.writeNamedChar('circle_fill')
                # Rain.
                elif conditions == 'Rain' or conditions == 'Thunderstorm':
                    self.mo.write(0xd9)
                # Snow.
                elif conditions == 'Snow':
                    self.mo.write('*')
                # Sunny.
                else:
                    self.mo.writeNamedChar('circle_stroke')

        # Clear weather when the fetching has failed.
        else:
            # Print temperature.
            self.mo.setCursor(3, 3)
            self.mo.write(' --.-')
            self.displayed_temperature = ' --.-'

            # Print humidity.
            self.mo.setCursor(14, 4)
            self.mo.write('--')
            self.displayed_humidity = '--'

            # Print icon for indicating weather conditions.
            self.mo.setCursor(3, 4)
            self.mo.write('-')
            self.displayed_conditions = '-'

    def printIndoorTemp(self):
        """
        Prints the indoor temperature and humidity.

        This function relies on the presence of the DHT22 sensor.
        """
        current_ticks = time.ticks_ms()

        # Don't print indoor temperature more often than every 30 seconds.
        if self.last_indoor is not None and time.ticks_diff(current_ticks, self.last_indoor) < 30 * 1000:
            return

        self.last_indoor = current_ticks

        if self.sensor:
            try:
                self.sensor.measure()
                temperature = round(self.sensor.temperature(), 1)
                humidity = round(self.sensor.humidity())

            # If the DHT22 sensor cannot be read, then return.
            # Most probably the sensor is not connected.
            except Exception as e:
                print(f"Error reading DHT22 sensor data: {e}")
                return

            # Indoor temperature should always include 1 fraction digit
            # occupying 4 characters because it can, for example, be '23.5'.
            temperature = '{:>4.1f}'.format(temperature)

            # Humidity should never be more than 99% because of available space.
            if humidity > 99:
                humidity = 99
            humidity = '{:>2}'.format(humidity)

            self.mo.setCursor(4, 1)
            self.mo.write(temperature)
            self.mo.setCursor(10, 4)
            self.mo.write(humidity)

    def screenInit(self):
        """
        Initializes large digits and prints data placeholders.
        """
        self.mo.clearDisplay()
        self.digits.largeDigitsInit()

        # Temperatures placeholders.
        self.mo.write('In --.-')
        self.mo.writeNamedChar('deg_c')
        self.mo.setCursor(0, 2)
        self.mo.write('Out')
        self.mo.setCursor(4, 3)
        self.mo.write('--.-')
        self.mo.writeNamedChar('deg_c')

        # Status icons initial.
        self.mo.setCursor(0, 4)
        self.mo.writeNamedChar('not_equal')
        self.mo.setCursor(3, 4)
        self.mo.write('-')

        # Humidity placeholder
        self.mo.setCursor(10, 4)
        self.mo.write('--% --%')

        # Clock placeholder.
        self.digits.largeDigit('dash', 10)
        self.digits.largeDigit('dash', 13)
        self.digits.largeDigit('colon', 15)
        self.digits.largeDigit('dash', 16)
        self.digits.largeDigit('dash', 19)
        self.mo.setCursor(18, 4)
        self.mo.write(':--')

    def keepRunning(self):
        """
        The main loop that keeps the info display running.
        """
        self.screenInit()
        self.connectWifi()

        while True:
            ticks_ms = time.ticks_ms()

            # Update displayed time (fetches new every 6 hours).
            self.printDateTime()

            # Update displayed weather (fetches new every 10 minutes).
            self.printWeather()

            # Update indoor temperature and humidity.
            self.printIndoorTemp()

            # Update download icon.
            if self.download_icon_start and not self.download_icon_shown:
                # Show icon if not shown but flagged to start appearing.
                self.mo.setCursor(5, 4)
                self.mo.writeNamedChar('arrow_right')
                self.download_icon_shown = True
                self.download_icon_time = ticks_ms

            elif self.download_icon_shown and time.ticks_diff(ticks_ms, self.download_icon_time) >= (1000 * 60):
                # Hide icon if shown and 60 seconds have passed.
                self.mo.setCursor(5, 4)
                self.mo.write(' ')
                self.download_icon_shown = False
                self.download_icon_start = False

            # Handle brightness button.
            if self.button is not None:
                if self.button.value() == 0:
                    if self.brightness_button is None:
                        self.brightness_button = ticks_ms
                else:
                    if self.brightness_button is not None:
                        if time.ticks_diff(ticks_ms, self.brightness_button) >= 100:
                            self.changeBrightness()
                            self.brightness_button = None

            # Update night/day brightness.
            date = self.getDateTime()
            if date['year'] != 0:
                hour = date['hour_int']

                off_hours = self.checkHourInRange(
                    hour,
                    config.display_off_start_hour,
                    config.display_off_end_hour
                )

                dim_hours = self.checkHourInRange(
                    hour,
                    config.display_dim_start_hour,
                    config.display_dim_end_hour
                )

                # Off hours.
                if off_hours:
                    if self.brightness_status != 'off':
                        self.mo.displayOnOff(0)
                        self.brightness_status = 'off'

                # Dim hours.
                elif dim_hours:
                    if self.brightness_status != 'dim':
                        self.mo.displayOnOff(1)
                        self.mo.setBrightness(1)
                        self.brightness_status = 'dim'

                # On hours.
                elif self.brightness_status != 'on':
                    self.mo.displayOnOff(1)
                    self.mo.setBrightness(self.brightness_set)
                    self.brightness_status = 'on'

            # Reconnect Wi-Fi if needed.
            if not self.wlan.isconnected():
                self.connectWifi()

            # Wait.
            time.sleep(0.1)

