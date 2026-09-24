import time

class MatrixOrbital:
    """
    A class for interacting with a Matrix Orbital LCD/VFD display.

    The connection to the display should be done using:
    - UART converted to 5V TTL
    - RS232 serial connection.

    Example usage:
    from machine import UART, Pin
    from matrix_orbital import MatrixOrbital

    bus = UART(0, baudrate=19200, bits=8, parity=None, stop=1, tx=Pin(0), rx=Pin(1))
    mo = MatrixOrbital(bus)

    # Call functions:
    mo.setBrightness(2)

    # Print strings on the display:
    mo.write('test')
    # or
    mo.write(b'test')
    # or
    mo.writeText('test')

    # Print numbers on the display:
    mo.write('3')
    # or
    mo.writeText(3)

    # Execute commands:
    mo.writeCommand(mo.auto_scroll_off)

    # Send bytes to the display:
    mo.write(0x07)
    # or (accepted values are 0-255)
    mo.write(7)
    """

    def __init__(self, bus):
        self.bus = bus

        # Command byte.
        self.command_char = 0xfe

        # Text commands.
        self.auto_line_wrap_on = 0x43  # R
        self.auto_line_wrap_off = 0x44  # R
        self.auto_scroll_on = 0x51  # R
        self.auto_scroll_off = 0x52  # R
        self.set_cursor_position = 0x47  # [column][row]
        self.send_cursor_home = 0x48
        self.turn_on_underline_cursor = 0x4a  # R
        self.turn_off_underline_cursor = 0x4b  # R
        self.turn_on_block_cursor = 0x53  # R
        self.turn_off_block_cursor = 0x54  # R
        self.cursor_left = 0x4c
        self.cursor_right = 0x4d

        # Bar graphs.
        self.init_wide_vertical_bar_graph = 0x76
        self.init_narrow_vertical_bar_graph = 0x73
        self.draw_vertical_bar_graph = 0x3d  # [column][height]
        self.init_horizontal_bar_graph = 0x68
        self.draw_horizontal_bar_graph = 0x7c  # [column][row][dir][length]

        # Custom characters.
        self.define_custom_character = 0x4e  # [slot 0-7][8 bytes]
        self.remember_custom_character = 0xc2  # [slot 0-7][8 bytes]

        # Fan and GPO commands.
        self.general_purpose_output_off = 0x56  # [GPO #]
        self.general_purpose_output_on = 0x57  # [GPO #]
        self.pvm_value = 0xC0  # [fan #][PWM value]
        self.return_fan_rpm = 0xc1  # [fan #]
        self.remember_gpo_pwm_state = 0xc3  # [fan #][PWM value]
        self.set_pwm_base_frequency = 0xc4  # [index]
        self.remember_pwm_base_frequency = 0xc5  # [index]

        # Miscellaneous commands.
        self.remember = 0x93  # [0/1]
        self.clear_display = 0x58
        self.set_brightness = 0x59  # [0x00 to 0x03]
        self.set_brightness_and_save = 0x98  # [0x00 to 0x03]
        self.display_on = 0x42  # [minutes]
        self.display_off = 0x46
        self.load_startup_screen = 0x40  # [40 characters]

        # Init display with these defaults.
        self.clearDisplay()
        self.underlineCursor(False)
        self.blockCursor(False)
        self.autoScroll(False)
        self.setBrightness(4)

    # .-----------------------------------------------------.
    # |                  WRITING COMMANDS                   |
    # '-----------------------------------------------------'

    # TODO: Test this.
    def write(self, data):
        """
        Universal write method for text strings and commands.

        :param data: The data to write - can be text or command bytes.
        """
        if isinstance(data, str):
            self.bus.write(data.encode())

        elif isinstance(data, (list, tuple, bytes, bytearray)):
            for byte in data:
                self.bus.write(byte)

        elif isinstance(data, int):
            self.bus.write(data)

        else:
            raise TypeError('Unsupported data type for write().')

    # TODO: Test this.
    def writeCommand(self, command_bytes):
        """
        Writes a command to the display.

        :param command_bytes: The command bytes write.
        """
        self.write(self.command_char)
        self.write(command_bytes)

    def writeText(self, data):
        """
        Writes text on the display at the cursor position.

        This is used to print non-string values on the display.

        :param data: The text string to write of the display.
        """
        self.bus.write(str(data).encode())

    # TODO: Test this.
    def writeCustomChar(self, slot, char_map, remember = False):
        """
        "Writes a custom character to one of the 8 CGRAM locations.

        After this command, the character can be used on the display.

        :param slot: The slot to write the character to (0-7)
        :param char_map: The character map to write to the slot
        :param remember: True to permanently remember the custom character, False otherwise
        """
        slots = {
            0: 0x00,
            1: 0x01,
            2: 0x02,
            3: 0x03,
            4: 0x04,
            5: 0x05,
            6: 0x06,
            7: 0x07,
        }

        if remember:
            command = [
                self.remember_custom_character,
                slots[slot],
            ]
        else:
            command = [
                self.define_custom_character,
                slots[slot],
            ]

        command.extend(char_map)
        self.writeCommand(command)

    # TODO: Test this,
    def writeNamedChar(self, name):
        """
        Writes a named character on the display at the cursor position.

        This allows writing special characters that can be used as
        built-in icons (e.g., arrows, circles, etc.)

        :param name: The character name. Please refer to getNamedCharacter()
        to see what is available.
        """
        self.write(self.getNamedCharacter(name))

    # .-----------------------------------------------------.
    # |                 NAVIGATION COMMANDS                 |
    # '-----------------------------------------------------'

    # TODO: Test this.
    def setCursor(self, column, row):
        """
        Puts the cursor at the specified column and row.

        Matrix Orbital command: Text - Set cursor position.

        :param column: The column to move the cursor to.
        :param row: The row to move the cursor to.

        """
        self.writeCommand([
            self.set_cursor_position,
            column,
            row,
        ])

    # TODO: Test this.
    def cursorLeft(self, amount = 1):
        """
        Moves the cursor left by the specified number of characters.

        Matrix Orbital command: Text - Cursor left.

        :param amount: By how many characters to move the cursor left.
        """
        for _ in range(amount):
            self.writeCommand(self.cursor_left)

    # TODO: Test this.
    def cursorRight(self, amount = 1):
        """
        Moves the cursor right by the specified number of characters.

        Matrix Orbital command: Text - Cursor right.

        :param amount: By how many characters to move the cursor right.
        """
        for _ in range(amount):
            self.writeCommand(self.cursor_right)

    # TODO: Test this.
    def cursorHome(self):
        """
        Moves the cursor to the home position.

        Matrix Orbital command: Text - Send cursor home.
        """
        self.writeCommand(self.send_cursor_home)

    # .-----------------------------------------------------.
    # |                  GENERAL COMMANDS                   |
    # '-----------------------------------------------------'

    # TODO: Test this.
    def underlineCursor(self, enable):
        """
        Enables or disables the underline cursor.

        Matrix Orbital command: Text - Turn on/off underline cursor.

        :param enable: True to enable the underline cursor, False to disable it.
        """
        if enable:
            self.writeCommand(self.turn_on_underline_cursor)
        else:
            self.writeCommand(self.turn_off_underline_cursor)

    # TODO: Test this.
    def blockCursor(self, enable):
        """
        Enables or disables the blinking block cursor.

        Matrix Orbital command: Text - Turn on/off block cursor.

        :param enable: True to enable the blinking block cursor, False to disable it.
        """
        if enable:
            self.writeCommand(self.turn_on_block_cursor)
        else:
            self.writeCommand(self.turn_off_block_cursor)

    # TODO: Test this.
    def clearDisplay(self):
        """
        Clears the display and moves the cursor to the home position.

        Matrix Orbital command: Miscellaneous - Clear display.
        """
        self.writeCommand(self.clear_display)

    # TODO: Test this.
    def displayOnOff(self, on_off):
        """
        Turns the display on or off.

        Matrix Orbital command: Miscellaneous - Display on/off.

        :param on_off: True to turn the display on, False to turn it off.
        """
        if on_off:
            self.writeCommand([self.display_on, 0x00])
        else:
            self.writeCommand(self.display_off)

    # TODO: Test this.
    def setBrightness(self, brightness, remember = False):
        """
        Sets brightness level (1-4).

        Matrix Orbital command: Miscellaneous - Set brightness.

        :param brightness: 4 for 100%, 3 for 75%, 2 for 50%, and 1 for 25%.
        :param remember: True to remember the brightness level, False to not.
        """
        levels = {
            1: 0x03,
            2: 0x02,
            3: 0x01,
            4: 0x00
        }

        if remember:
            # TODO: Saving brightness command is not working.
            self.writeCommand([
                self.set_brightness_and_save,
                levels[brightness],
            ])
        else:
            self.writeCommand([
                self.set_brightness,
                levels[brightness],
            ])

    # TODO: Test this.
    def autoLineWrap(self, enable):
        """
        Enables or disables automatic line wrapping.

        Matrix Orbital command: Text - Auto line wrap on/off.

        :param enable: True to enable automatic line wrapping,
        False to disable.
        """
        if enable:
            self.writeCommand(self.auto_line_wrap_on)
        else:
            self.writeCommand(self.auto_line_wrap_off)

    # TODO: Test this.
    def autoScroll(self, enable):
        """
        Enables or disables automatic vertical scrolling.

        Matrix Orbital command: Text - Auto scroll on/off.

        When auto-scrolling is on, it causes a shift of the
        entire display's contents up to make room for a new
        line of text when the text reaches the end of the
        last row.

        :param enable: True to enable automatic scrolling,
        False to disable.
        """
        if enable:
            self.writeCommand(self.auto_scroll_on)
        else:
            self.writeCommand(self.auto_scroll_off)

    # .-----------------------------------------------------.
    # |                     BAR GRAPHS                      |
    # '-----------------------------------------------------'

    # TODO: Test this.
    def initWideVerticalBarGraph(self):
        """
        Initializes a wide vertical bar graph.

        Matrix Orbital command: Bar graphs - Initialize wide
        vertical bar graph.
        """
        self.writeCommand(self.init_wide_vertical_bar_graph)

    # TODO: Test this.
    def initNarrowVerticalBarGraph(self):
        """
        Initializes a narrow vertical bar graph.

        Matrix Orbital command: Bar graphs - Initialize narrow
        vertical bar graph.
        """
        self.writeCommand(self.init_narrow_vertical_bar_graph)

    # TODO: Test this.
    def drawVerticalBarGraph(self, column, height):
        """
        Draws a vertical bar graph.

        Matrix Orbital command: Bar graphs - Draw vertical bar graph.

        :param column: The column to draw the bar graph in.
        :param height: The height of the bar graph (0-20).
        """
        self.writeCommand([
            self.draw_vertical_bar_graph,
            column,
            height
        ])

    # TODO: Test this.
    def initHorizontalBarGraph(self):
        """
        Initializes horizontal bar graph.

        Matrix Orbital command: Bar graphs - Initialize horizontal
        bar graph.
        """
        self.writeCommand(self.init_horizontal_bar_graph)

    # TODO: Test this.
    def drawHorizontalBarGraph(self, column, row, direction, length):
        """
        Draws a horizontal bar graph.

        :param column: The column at which to start (0-14).
        :param row: The row in which to draw the bar graph (1-2).
        :param direction: Pass 'left' or 'right'.
        :param length: The length of the bar graph (0-100).
        """
        directions = {
            'left': 0,
            'right': 1,
        }

        self.writeCommand([
            self.draw_horizontal_bar_graph,
            column,
            row,
            directions[direction],
            length
        ])

    # .-----------------------------------------------------.
    # |                     FAN AND GP0                     |
    # '-----------------------------------------------------'

    # TODO: Test this.
    def gpoOnOff(self, gpo, enable):
        """
        Enabled and disables a selected GPO port power.

        :param gpo: The GPO port number (1-6).
        :param enable: Whether to enable or disable the GPO port.
        """
        gpo_ids = {
            1: 0x01,
            2: 0x02,
            3: 0x03,
            4: 0x04,
            5: 0x05,
            6: 0x06,
        }

        if enable:
            self.writeCommand([
                self.general_purpose_output_on,
                gpo_ids[gpo],
            ])
        else:
            self.writeCommand([
                self.general_purpose_output_off,
            ])

    # TODO: Implement these?
    # pvm_value = 0xC0  # [fan #][PWM value]
    # return_fan_rpm = 0xc1  # [fan #]
    # remember_gpo_pwm_state = 0xc3  # [fan #][PWM value]
    # set_pwm_base_frequency = 0xc4  # [index]
    # remember_pwm_base_frequency = 0xc5  # [index]

    # TODO: Test this.
    def remember(self, enable):
        if enable:
            self.writeCommand([
                self.remember,
                0x01,
            ])
        else:
            self.writeCommand([
                self.remember,
                0x00,
            ])

    # TODO: Test this.
    def loadStartupScreen(self, characters):
        """
        Loads a startup screen with the given characters.

        :param characters: A string of 40 characters to display on the startup screen.
        """
        self.write(self.command_char)
        self.write(self.load_startup_screen)

        for char in list(characters):
            self.write(char)
            time.sleep_ms(5)

    # .-----------------------------------------------------.
    # |                  HELPER FUNCTIONS                   |
    # '-----------------------------------------------------'

    def getNamedCharacter(self, name):
        """
        Returns a hex code of the named character.

        Named characters are special ones that can be used to display
        arrows, circles, icon-looking characters, etc.

        :param name: The name of the character.

        :return: A hex code of the named character if found, otherwise 0x3f (?).
        """
        characters = {
            # 00-0f - Custom characters.
            # 10-1f - Blocks, signs and triangles.
            'block_left_1': 0x10,
            'block_left_2': 0x11,
            'block_left_3': 0x12,
            'block_left_4': 0x13,
            'block_full': 0x14,
            'block_right_4': 0x15,
            'block_right_3': 0x16,
            'block_right_2': 0x17,
            'block_right_1': 0x18,
            'note': 0x19,
            'deg_c': 0x1a,
            'deg_f': 0x1b,
            'triangle_down': 0x1c,
            'triangle_right': 0x1d,
            'triangle_left': 0x1e,
            'triangle_up': 0x1f,
            # 20-2f - Standard special characters.
            # 30-3f - Digits and standard special characters.
            # 40-4f - @ and uppercase letters.
            # 50-5f - Uppercase letters and standard special characters.
            # 60-6f - Angled apostrophe-like character and lowercase letters.
            # 70-7f - Lowercase letters, standard special characters and arrows.
            'arrow_right': 0x7e,
            'arrow_left': 0x7f,
            # 80-8f - Accented letters and 4 characters (2 present on keyboard).
            'not_equal': 0x8d,
            'paragraph': 0x8f,
            # 90-9f.
            'circle_fill': 0x94,
            'circle_stroke': 0x95,
            'square_fill': 0x96,
            'square_stroke': 0x97,
            'broken_pipe': 0x98,
            'graph': 0x9a,
            'less_equal': 0x9b,
            'more_equal': 0x9c,
            'return': 0x9d,
            'arrow_up': 0x9e,
            'arrow_down': 0x9f,
            # a0-af.
            'square_bottom': 0xa1,
            'corner_top': 0xa2,
            'corner_bottom': 0xa3,
            'dot': 0xa5,
            'low_i': 0xaa,
            'hook': 0xad,
            'inverted_e': 0xae,
            'fork': 0xaf,
            # b0-bf.
            'high_i': 0xb4,
            'box_open': 0xba,
            # c0-cf.
            # d0-df.
            'triple_line': 0xd0,
            'box_closed': 0xdb,
            'box_open2': 0xdc,
            'slide': 0xdd,
            'shine': 0xde,
            'square_top': 0xdf,
            # e0-ef.
            'square_root': 0xe8,
            'hammer': 0xe9,
            'star': 0xeb,
            'cent': 0xec,
            'branch': 0xed,
            # f0-ff.
            'dash_x': 0xf8,
            'storage': 0xfc,
            'division': 0xfd,
        }

        if name in characters:
            return characters[name]
        else:
            # If no character, then return '?'
            return 0x3f
