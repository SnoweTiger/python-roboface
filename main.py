import time
import asyncio
from libs.oled import SSD1306
from libs.robo_face import RoboFace, Mood

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
I2C_ADDR = 0x3C  # common addresses: 0x3C
I2C_BUS = 3  # for LuckFox Pico Pro/Max 3 by default -> /dev/i2c-3


def main() -> None:
    try:
        oled = SSD1306(DISPLAY_WIDTH, DISPLAY_HEIGHT, I2C_BUS, I2C_ADDR)
        robo = RoboFace(oled)

        asyncio.run(robo.animate_smile())

        asyncio.run(robo.animate_angry())

        robo.set_mood(Mood.neutral)
        time.sleep(1)

        robo.set_mood(Mood.shocked)
        time.sleep(1)

        robo.set_mood(Mood.angry)
        time.sleep(1)

        robo.set_mood(Mood.smile)
        time.sleep(1)

        robo.set_mood(Mood.happy)
        time.sleep(1)

        oled.power_off()
    except Exception as e:
        print(f"Exception {e}")


if __name__ == "__main__":
    main()
