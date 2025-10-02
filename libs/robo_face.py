import math
import asyncio
from enum import Enum

from libs.oled import SSD1306


class MouthType(Enum):
    neutral = 1
    smile = 2
    negative = 3


class Mood(Enum):
    neutral = 1
    angry = 2
    smile = 3
    happy = 4
    shocked = 5


class RoboFace:
    def __init__(
        self,
        oled: SSD1306,
        border: bool = False,
        color: int = 1,
        duration: int = 5,
    ):
        self.oled = oled
        self.cx = oled.width // 2
        self.cy = oled.height // 2
        self.border = border
        self.color = color
        self.duration = duration

        self.radius = int(min(oled.width, oled.height) * 0.95) // 2

        # Calc eys sizes
        self.eye_offset_x = int(self.radius * 0.45)
        self.eye_offset_y = int(self.radius * 0.35)
        self.eye_radius = self.radius // 6
        self.big_eye_scale = 2.0
        self.small_eye_scale = 0.5
        self.left_eye_scale = None
        self.right_eye_scale = None

        # Calc mouth sizes
        self.smile_width = int(self.radius * 0.8)
        self.smile_height = int(self.radius * 0.2)
        self.mouth_y = self.cy + int(self.radius * 0.35)

        # Calc eyebrow sizes
        self.eyebrow_angle = 0
        self.eyebrow_width = int(self.radius * 0.5)

        # Init face state
        self.wink_left = False
        self.wink_right = False
        self.mouth_type = MouthType.neutral

    def set_mood(self, mood: Mood) -> None:
        self.mood = mood
        match mood:
            case Mood.smile:
                self._set_smile()
            case Mood.angry:
                self._set_angry()
            case Mood.happy:
                self._set_happy()
            case Mood.shocked:
                self._set_shocked()
            case Mood.neutral | _:
                self._set_neutral()
        self._draw_frame()

    def _set_smile(self) -> None:
        self.wink_left = False
        self.wink_right = False
        self.left_eye_scale = None
        self.right_eye_scale = None
        self.eyebrow_angle = 0
        self.mouth_type = MouthType.smile

    def _set_happy(self) -> None:
        self.wink_left = True
        self.wink_right = True
        self.left_eye_scale = None
        self.right_eye_scale = None
        self.eyebrow_angle = 0
        self.mouth_type = MouthType.smile

    def _set_angry(self) -> None:
        self.wink_left = False
        self.wink_right = False
        self.left_eye_scale = None
        self.right_eye_scale = None
        self.eyebrow_angle = math.pi / 8
        self.mouth_type = MouthType.negative

    def _set_shocked(self) -> None:
        self.wink_left = False
        self.wink_right = False
        self.left_eye_scale = None
        self.right_eye_scale = 2
        self.eyebrow_angle = 0
        self.mouth_type = MouthType.neutral

    def _set_neutral(self) -> None:
        self.wink_left = False
        self.wink_right = False
        self.left_eye_scale = None
        self.right_eye_scale = None
        self.eyebrow_angle = 0
        self.mouth_type = MouthType.neutral

    async def animate_smile(self, duration: float = 1.0, fps: int = 30) -> None:
        self._set_smile()
        smile_height = self.smile_height
        frames_n = int(duration * fps)
        self.smile_height = 0
        f = 0

        for _ in range(frames_n):
            tmp_smile = int(smile_height * f / frames_n)

            # Draw only if smile_height changed
            if tmp_smile != self.smile_height:
                self.smile_height = tmp_smile
                self._draw_frame()

            await asyncio.sleep(1 / fps)
            f += 1

    async def animate_angry(self, duration: float = 1.0, fps: int = 30) -> None:
        self._set_angry()
        smile_height = self.smile_height
        eyebrow_width = self.eyebrow_width
        frames_n = int(duration * fps)
        self.smile_height = 0
        # self.eyebrow_width = 0
        f = 0

        for _ in range(frames_n):
            tmp_smile = int(smile_height * f / frames_n)
            tmp_eyebrow = int(eyebrow_width * f / frames_n)

            # Draw only if smile_height changed
            if tmp_smile != self.smile_height or tmp_eyebrow != self.eyebrow_width:
                self.smile_height = tmp_smile
                self.eyebrow_width = tmp_eyebrow
                self._draw_frame()

            await asyncio.sleep(1 / fps)
            f += 1

    def _draw_frame(self) -> None:
        oled = self.oled
        oled.fill(0)

        if self.border:
            self.oled.circle(self.cx, self.cy, self.radius, 1)

        # Left eye
        if self.wink_left:
            oled.hline(
                self.cx - self.eye_offset_x - self.eye_radius,
                self.cy - self.eye_offset_y,
                self.eye_radius * 2,
                self.color,
            )
        else:
            scale = (
                1
                if self.left_eye_scale is None
                else max(0.5, min(2.0, self.left_eye_scale))
            )
            oled.filled_circle(
                self.cx - self.eye_offset_x,
                self.cy - self.eye_offset_y,
                int(self.eye_radius * scale),
                self.color,
            )

        # Right eye
        if self.wink_right:
            oled.hline(
                self.cx + self.eye_offset_x - self.eye_radius,
                self.cy - self.eye_offset_y,
                self.eye_radius * 2,
                self.color,
            )
        else:
            scale = (
                1
                if self.right_eye_scale is None
                else max(0.5, min(2.0, float(self.right_eye_scale)))
            )
            oled.filled_circle(
                self.cx + self.eye_offset_x,
                self.cy - self.eye_offset_y,
                int(self.eye_radius * scale),
                self.color,
            )

        # Eyebrows
        if self.eyebrow_angle != 0.0:
            dx = int(math.cos(self.eyebrow_angle) * self.eyebrow_width)
            dy = int(math.sin(self.eyebrow_angle) * self.eyebrow_width)

            eyebrow_x_l = self.cx - self.eye_offset_x + int(self.radius * 0.3)
            eyebrow_x_r = self.cx + self.eye_offset_x - int(self.radius * 0.3)
            eyebrow_y = (
                self.cy - self.eye_offset_y - self.eye_radius - int(self.radius * 0.1)
            )
            x0 = eyebrow_x_l
            y0 = eyebrow_y
            x1 = eyebrow_x_l - dx
            y1 = eyebrow_y - dy
            oled.line(x0, y0, x1, y1, 1)

            x0 = eyebrow_x_r
            y0 = eyebrow_y
            x1 = eyebrow_x_r + dx
            y1 = eyebrow_y - dy
            oled.line(x0, y0, x1, y1, 1)

        # Mouth
        match self.mouth_type:
            case MouthType.smile:
                print("smile")
                p0 = (self.cx - self.eye_radius * 2, self.mouth_y - self.smile_height)
                p1 = (self.cx, self.mouth_y + self.smile_height)
                p2 = (self.cx + self.eye_radius * 2, self.mouth_y - self.smile_height)
                oled.quad_bezier(p0, p1, p2, offset_y=self.smile_height // 2)

            case MouthType.negative:
                print("negative")
                p0 = (self.cx - self.eye_radius * 2, self.mouth_y + self.smile_height)
                p1 = (self.cx, self.mouth_y - self.smile_height)
                p2 = (self.cx + self.eye_radius * 2, self.mouth_y + self.smile_height)
                oled.quad_bezier(p0, p1, p2, offset_y=-self.smile_height // 2)

            case MouthType.neutral | _:
                print("neutral")
                oled.hline(
                    self.cx - self.smile_width // 2,
                    self.cy + int(self.radius * 0.35),
                    self.smile_width,
                    self.color,
                )

        oled.show()
