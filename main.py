import time
from libs.oled import SSD1306


DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
I2C_ADDR = 0x3C  # common addresses: 0x3C
I2C_BUS = 3  # for LuckFox Pico Pro/Max 3 by default -> /dev/i2c-3


def main() -> None:
    oled = SSD1306(DISPLAY_WIDTH, DISPLAY_HEIGHT, I2C_BUS, I2C_ADDR)

    try:
        oled.fill(0)
        oled.circle(oled.width // 2, oled.height // 2, oled.height // 2, 1)
        oled.show()
        time.sleep(0.8)

        oled.power_off()
    except Exception as e:
        print(f"Exception {e}")


if __name__ == "__main__":
    main()
