from abc import ABC, abstractmethod
import os


class Display(ABC):
    @abstractmethod
    def init(self, width: int, height: int) -> None:
        pass

    @abstractmethod
    def write_cmd(self, cmd: int) -> None:
        pass

    @abstractmethod
    def write_data(self, data: bytes) -> None:
        pass

    @abstractmethod
    def flush(self, buffer: bytes, width: int, height: int) -> None:
        pass


class LinuxI2CDisplay(Display):
    """I2C backend using /dev/i2c-* and ioctl (no external libs). Works on Linux only (e.g., LuckFox Pico, Raspberry Pi)."""

    I2C_SLAVE = 0x0703

    def __init__(self, bus: int, address: int):
        import fcntl  # import library on Linux

        self._fcntl = fcntl
        self.bus = bus
        self.address = address

    def init(self, width: int, height: int) -> None:
        path = f"/dev/i2c-{self.bus}"
        self.fd = os.open(path, os.O_RDWR)
        self._fcntl.ioctl(self.fd, self.I2C_SLAVE, self.address)

    def write_cmd(self, cmd: int) -> None:
        os.write(self.fd, bytes((0x00, cmd)))

    def write_data(self, data: bytes) -> None:
        os.write(self.fd, b"\x40" + data)

    def flush(self, buffer: bytes, width: int, height: int) -> None:
        pass


class TkSimulator(Display):
    """Simple Tkinter window that simulates the OLED pixels."""

    def __init__(self, scale: int = 4):
        self.scale = scale
        self._tk = None
        self._canvas = None
        self.width = 0
        self.height = 0

    def init(self, width: int, height: int) -> None:
        import tkinter as tk

        self.width = width
        self.height = height
        self._tk = tk.Tk()
        self._tk.title("OLED SIM")
        self._canvas = tk.Canvas(
            self._tk, width=width * self.scale, height=height * self.scale, bg="black"
        )
        self._canvas.pack()
        # Update once to show window
        self._tk.update_idletasks()
        self._tk.update()

    def write_cmd(self, cmd: int) -> None:  # not used by simulator
        pass

    def write_data(self, data: bytes) -> None:  # not used by simulator
        pass

    def flush(self, buffer: bytes, width: int, height: int) -> None:
        # Draw white rectangles for set pixels
        self._canvas.delete("all")
        pages = height // 8
        for page in range(pages):
            for x in range(width):
                byte_val = buffer[x + page * width]
                if byte_val == 0:
                    continue
                for bit in range(8):
                    if byte_val & (1 << bit):
                        y = page * 8 + bit
                        sx = x * self.scale
                        sy = y * self.scale
                        self._canvas.create_rectangle(
                            sx,
                            sy,
                            sx + self.scale,
                            sy + self.scale,
                            outline="",
                            fill="white",
                        )
        self._tk.update_idletasks()
        self._tk.update()


def check_connection(i2c_bus: int, i2c_addr: int) -> Display:
    # Prefer Linux I2C if available
    if os.path.exists(f"/dev/i2c-{i2c_bus}"):  # os.name == "posix" and
        return LinuxI2CDisplay(i2c_bus, i2c_addr)
    # Otherwise use simulator (works on Windows/macOS too)
    return TkSimulator(scale=4)
