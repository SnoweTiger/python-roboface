import time
from libs.oled import SSD1306
from libs.robo_face import RoboFace, Mood, Style

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
I2C_ADDR = 0x3C  # common addresses: 0x3C
I2C_BUS = 3  # for LuckFox Pico Pro/Max 3 by default -> /dev/i2c-3


def main() -> None:
    try:
        oled = SSD1306(DISPLAY_WIDTH, DISPLAY_HEIGHT)

        for style in Style:
            robo = RoboFace(oled, style=style)
            robo.file_prefix = style.name

            for mood in Mood:
                robo.set_mood(mood)
            time.sleep(0.1)

        oled.power_off()
    except Exception as e:
        print(f"Exception {e}")


if __name__ == "__main__":
    main()
