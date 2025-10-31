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

    def show(self, file_name: str | None = None) -> None:
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
            if file_name is not None:
                self.backend.save_to_file(filename=file_name)

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
        if w == 0:
            return
        elif w < 0:
            x += w
            w = -w

        for i in range(x, x + w):
            self.pixel(i, y, color)

    def vline(self, x: int, y: int, h: int, color: int = 1) -> None:
        if h == 0:
            return
        elif h < 0:
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
        p0: tuple[int, int],
        p1: tuple[int, int],
        p2: tuple[int, int],
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

    def quad_bezier_filled(
        self,
        p0: tuple[int, int],
        p1: tuple[int, int],
        p2: tuple[int, int],
        color: int = 1,
        steps: int = 64,
        steps_current: int = 64,
    ) -> None:
        x0, y0 = p0
        x1, y1 = p1
        x2, y2 = p2

        length_h = x2 + x0

        for i in range(steps_current):
            t = i / steps
            mt = 1.0 - t
            x = int(mt * mt * x0 + 2 * mt * t * x1 + t * t * x2)
            y = int(mt * mt * y0 + 2 * mt * t * y1 + t * t * y2)

            self.hline(x, y, length_h - 2 * x, color)

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
            self.hline(cx - r, cy, 2 * r + 1, color)
            return

        x = r
        y = 0
        d = 1 - r

        while x >= y:
            y_shrunk = int(y * shrink)
            x_shrunk = int(x * shrink)

            self.hline(cx - x, cy + y_shrunk, 2 * x + 1, color)
            self.hline(cx - x, cy - y_shrunk, 2 * x + 1, color)
            self.hline(cx - y, cy + x_shrunk, 2 * y + 1, color)
            self.hline(cx - y, cy - x_shrunk, 2 * y + 1, color)

            y += 1
            if d <= 0:
                d += 2 * y + 1
            else:
                x -= 1
                d += 2 * (y - x) + 1

    def filled_rectangle(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: int = 1,
    ) -> None:
        if height < 0:
            for row in range(abs(height) + 1):
                self.hline(x, y - row, width, color)
        elif height > 0:
            for row in range(height + 1):
                self.hline(x, y + row, width, color)
        else:
            return

    def filled_circle_quarter(
        self,
        cx: int,
        cy: int,
        radius: int,
        quarter: int = 0,  # 0 - all, 1 - 0-90 grad, 2 - 90-180 grad, 3 - 180-270 grad, 4 - 270-0 grad,
        color: int = 1,
    ):
        x = 0
        y = radius
        d = 3 - 2 * radius

        while x <= y:
            if quarter == 1:
                pairs = [(x, -y), (y, -x)]
            elif quarter == 2:
                pairs = [(-x, -y), (-y, -x)]
            elif quarter == 3:
                pairs = [(-y, x), (-x, y)]
            elif quarter == 4:
                pairs = [(x, y), (y, x)]

            else:
                pairs = [
                    (-x, -y),
                    (-y, -x),
                    (x, -y),
                    (y, -x),
                    (-y, x),
                    (-x, y),
                    (x, y),
                    (y, x),
                ]

            for dx, dy in pairs:
                self.hline(cx + dx, cy + dy, -dx, color)

            if d < 0:
                d = d + 4 * x + 6
            else:
                d = d + 4 * (x - y) + 10
                y -= 1
            x += 1

    def filled_rectangle_rounded(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        radius: int,
        color: int = 1,
    ):
        max_r = (width if width < height else height) // 2
        if max_r < radius:
            radius = max_r

        self.filled_rectangle(x, y + radius, width, height - 2 * radius, color)
        self.filled_rectangle(x + radius, y, width - 2 * radius, radius, color)
        self.filled_rectangle(
            x + radius,
            y + height - radius,
            width - 2 * radius,
            radius,
            color,
        )

        self.filled_circle_quarter(
            x + width - radius,
            y + radius,
            radius,
            1,
            color,
        )
        self.filled_circle_quarter(
            x + radius,
            y + radius,
            radius,
            2,
            color,
        )
        self.filled_circle_quarter(
            x + radius,
            y + height - radius,
            radius,
            3,
            color,
        )
        self.filled_circle_quarter(
            x + width - radius,
            y + height - radius,
            radius,
            4,
            color,
        )

    def fill_circle_helper(
        self,
        x: int,
        y: int,
        radius: int,
        side: int,
        dist: int,
        color: int = 1,
    ):
        f = 1 - radius
        df_x = 1
        df_y = -2 * radius
        dx = 0
        dy = radius

        dist += 1

        while dx < dy:
            if f >= 0:
                dy -= 1
                df_y += 2
                f += df_y

            dx += 1
            df_x += 2
            f += df_x

            if dx < (dy + 1):
                if side == 1:
                    self.vline(x + dx, y - dy, dist + 2 * dy, color)
                if side == 2:
                    self.vline(x - dx, y - dy, dist + 2 * dy, color)

    def filled_triangle(
        self,
        x0: int,
        y0: int,
        x2: int,
        y2: int,
        color: int = 1,
    ):
        w = x2 - x0
        h = y2 - y0
        y = y0
        sb = 0

        while y <= y2:
            a = x2
            b = x0 + sb // h
            sb += w

            if a > b:
                a, b = b, a

            self.hline(a, y, b - a + 1, color)
            y += 1
