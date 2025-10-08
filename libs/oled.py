from dataclasses import dataclass

from libs.i2c import TkSimulator, check_connection


@dataclass(frozen=True)
class Display_cmd:
    CHARGE_PUMP = 0x8D
    COM_SCAN_DEC = 0xC8
    DISPLAY_ALL_ON_RESUME = 0xA4
    DISPLAY_OFF = 0xAE
    DISPLAY_ON = 0xAF
    MEMORY_MODE = 0x20
    NORMAL_DISPLAY = 0xA6
    SEG_REMAP_MIRROR = 0xA1
    SEG_REMAP_NORMAL = 0xA0
    SET_COM_PINS = 0xDA
    SET_CONTRAST = 0x81
    SET_DISPLAY_CLOCK_DIV = 0xD5
    SET_DISPLAY_OFFSET = 0xD3
    SET_MULTIPLEX = 0xA8
    SET_PRECHARGE = 0xD9
    SET_SCROLL_OFF = 0x2E
    SET_START_LINE = 0x40
    SET_VCOM_DETECT = 0xDB


class SSD1306:
    INIT_CMD = (
        Display_cmd.DISPLAY_OFF,
        Display_cmd.SET_DISPLAY_CLOCK_DIV,
        0x80,  # Set display clock divide ratio/oscillator frequency
        Display_cmd.SET_MULTIPLEX,
        0x3F,  # Set multiplex ratio (1 to 64)
        Display_cmd.SET_DISPLAY_OFFSET,
        0x00,  # Set display offset
        Display_cmd.SET_START_LINE,  # Set display start line
        Display_cmd.CHARGE_PUMP,
        0x14,  # Charge pump setting (0x14 для включения)
        Display_cmd.MEMORY_MODE,
        0x00,  # Horizontal addressing mode
        Display_cmd.SEG_REMAP_MIRROR,  # Segment re-map (0 - нормально, 1 - зеркально)
        Display_cmd.COM_SCAN_DEC,  # COM output scan direction (0 - нормально, 1 - зеркально)
        Display_cmd.SET_COM_PINS,
        0x12,  # COM pins hardware configuration
        Display_cmd.SET_CONTRAST,
        0xCF,  # Set contrast control
        Display_cmd.SET_PRECHARGE,
        0xF1,  # Set pre-charge period
        Display_cmd.SET_VCOM_DETECT,
        0x40,  # Set VCOMH deselect level
        Display_cmd.DISPLAY_ALL_ON_RESUME,  # Set entire display ON/OFF
        Display_cmd.NORMAL_DISPLAY,  # Set normal/inverse display
        Display_cmd.SET_SCROLL_OFF,  # Deactivate scroll
        Display_cmd.DISPLAY_ON,  # Display ON
    )

    def __init__(
        self,
        width: int = 128,
        height: int = 64,
        bus: int = 1,
        address: int = 0x3C,
    ):
        self.width = width
        self.height = height
        self.pages = self.height // 8
        self.buffer = bytearray(self.width * self.pages)
        self.backend = check_connection(bus, address)
        self.backend.init(width, height)
        self._init_display()

    def _write_cmd(self, cmd: int) -> None:
        self.backend.write_cmd(cmd)

    def _write_data(self, buf: bytes) -> None:
        self.backend.write_data(buf)

    def _init_display(self) -> None:
        # Initialization sequence based on SSD1306 datasheet
        for cmd in self.INIT_CMD:
            self._write_cmd(cmd)
        self.fill(0)
        self.show()

    def power_off(self) -> None:
        self._write_cmd(0xAE)

    def power_on(self) -> None:
        self._write_cmd(0xAF)

    def contrast(self, contrast: int) -> None:
        contrast = max(0, min(255, int(contrast)))
        self._write_cmd(0x81)
        self._write_cmd(contrast)

    def invert(self, invert: bool) -> None:
        self._write_cmd(0xA7 if invert else 0xA6)

    def show(self) -> None:
        # Set the full window and push buffer
        self._write_cmd(0x21)  # COLUMN_ADDR
        self._write_cmd(0)
        self._write_cmd(self.width - 1)
        self._write_cmd(0x22)  # PAGE_ADDR
        self._write_cmd(0)
        self._write_cmd(self.pages - 1)

        # Send buffer in chunks to avoid large writes
        chunk = 64
        for i in range(0, len(self.buffer), chunk):
            self._write_data(self.buffer[i : i + chunk])

        # Also flush to simulator if used
        if isinstance(self.backend, TkSimulator):
            self.backend.flush(self.buffer, self.width, self.height)

    def fill(self, color: int) -> None:
        fill_byte = 0xFF if color else 0x00
        for i in range(len(self.buffer)):
            self.buffer[i] = fill_byte

    def pixel(self, x: int, y: int, color: int = 1) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        page = y >> 3
        index = x + page * self.width
        bit = 1 << (y & 0x07)
        if color:
            self.buffer[index] |= bit
        else:
            self.buffer[index] &= ~bit

    def hline(self, x: int, y: int, w: int, color: int = 1) -> None:
        if w < 0:
            x += w
            w = -w
        for i in range(x, x + w):
            self.pixel(i, y, color)

    def vline(self, x: int, y: int, h: int, color: int = 1) -> None:
        if h < 0:
            y += h
            h = -h
        for j in range(y, y + h):
            self.pixel(x, j, color)

    def line(self, x0: int, y0: int, x1: int, y1: int, color: int = 1) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def quad_bezier(
        self,
        p0,
        p1,
        p2,
        color: int = 1,
        steps: int = 64,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        x0, y0 = p0
        x1, y1 = p1
        x2, y2 = p2
        for i in range(steps + 1):
            t = i / steps
            mt = 1.0 - t
            x = int(mt * mt * x0 + 2 * mt * t * x1 + t * t * x2 + offset_x)
            y = int(mt * mt * y0 + 2 * mt * t * y1 + t * t * y2 + offset_y)
            self.pixel(x, y, color)

    def circle(self, cx: int, cy: int, r: int, color: int = 1) -> None:
        x = r
        y = 0
        d = 1 - r
        while x >= y:
            self.pixel(cx + x, cy + y, color)
            self.pixel(cx + y, cy + x, color)
            self.pixel(cx - y, cy + x, color)
            self.pixel(cx - x, cy + y, color)
            self.pixel(cx - x, cy - y, color)
            self.pixel(cx - y, cy - x, color)
            self.pixel(cx + y, cy - x, color)
            self.pixel(cx + x, cy - y, color)
            y += 1
            if d <= 0:
                d += 2 * y + 1
            else:
                x -= 1
                d += 2 * (y - x) + 1

    def filled_circle(
        self,
        cx: int,
        cy: int,
        r: int,
        color: int = 1,
        shrink: float = 1.0,
    ) -> None:
        # shrink: 1 (full circle), 0 (horizontal line), in-between: ellipse squashed vertically
        if shrink == 0.0:
            # Draw only a horizontal line of length 2r+1
            self.hline(cx - r, cy, 2 * r + 1, color)
            return

        x = r
        y = 0
        d = 1 - r

        while x >= y:
            # Calculate vertical shrink
            y_shrunk = int(y * shrink)
            x_shrunk = int(x * shrink)

            # Draw vertical lines, but shrink their height
            self.vline(cx + x, cy - y_shrunk, 2 * y_shrunk + 1, color)
            self.vline(cx - x, cy - y_shrunk, 2 * y_shrunk + 1, color)
            self.vline(cx + y, cy - x_shrunk, 2 * x_shrunk + 1, color)
            self.vline(cx - y, cy - x_shrunk, 2 * x_shrunk + 1, color)
            y += 1

            if d <= 0:
                d += 2 * y + 1
            else:
                x -= 1
                d += 2 * (y - x) + 1
