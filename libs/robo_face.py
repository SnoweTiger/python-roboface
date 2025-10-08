import math
import asyncio
from enum import Enum
from typing import Tuple

from libs.oled import SSD1306


class MouthMood(Enum):
    neutral = 1
    smile = 2
    angry = 3


class Mood(Enum):
    neutral = 1
    angry = 2
    smile = 3
    happy = 4
    shocked = 5


class Mouth:
    def __init__(
        self,
        cx: int,  # in pixels
        cy: int,  # in pixels
        height: int,  # in pixels
        width: int,  # in pixels
        enable: bool = True,
        mood: MouthMood = MouthMood.neutral,
    ) -> None:
        self.cx = cx
        self.cy = cy
        self.height = height
        self.width = width
        self.enable = enable
        self.mood = mood

        # calculate points
        self.lx = self.cx - self.width // 2
        self.rx = self.cx + self.width // 2
        self.dy = self.height // 2

    @classmethod
    def from_face_radius(
        cls,
        face_cx: int,
        face_cy: int,
        radius: int,
        scale_offset_y: float = 0.35,
        scale_height: float = 0.4,
        scale_width: float = 0.8,
    ):
        return cls(
            cx=face_cx,
            cy=face_cy + int(radius * scale_offset_y),
            height=int(radius * scale_height),
            width=int(radius * scale_width),
        )

    def set_scale(self, scale: float = 1.0) -> bool:
        """update smile height by scale.Return True if value changed, return False if last height equal current."""
        dy = int(scale * self.height / 2)

        if dy == self.dy:
            return False

        self.dy = dy
        return True

    def get_points(
        self,
        mood: MouthMood | None = None,
    ) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        if mood is not None:
            self.mood = mood

        match self.mood:
            case MouthMood.smile:
                print("smile")
                p0 = (self.lx, self.cy - self.dy)
                p1 = (self.cx, self.cy + self.dy)
                p2 = (self.rx, self.cy - self.dy)

            case MouthMood.angry:
                print("negative")
                p0 = (self.lx, self.cy + self.dy)
                p1 = (self.cx, self.cy - self.dy)
                p2 = (self.rx, self.cy + self.dy)

            case MouthMood.neutral | _:
                print("neutral")
                p0 = (self.lx, self.cy)
                p1 = (self.cx, self.cy)
                p2 = (self.rx, self.cy)

        return (p0, p1, p2)


class Eye:
    def __init__(
        self,
        cx: int,  # in pixels
        cy: int,  # in pixels
        radius: int,  # in pixels
        enable: bool = True,
        get_shocked: bool = True,
    ):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.enable = enable
        self.get_shocked = get_shocked
        self.mood = Mood.neutral
        self.dy = 0
        self.do = 1

    @classmethod
    def from_face_radius(
        cls,
        face_cx: int,
        face_cy: int,
        face_radius: int,
        scale_offset_x: float = 0.45,
        scale_offset_y: float = 0.35,
        scale_radius: float = 0.17,
        right: bool = True,
        enable: bool = True,
        get_shocked: bool = True,
    ):
        k = 1 if right else -1
        return cls(
            cx=face_cx + k * int(face_radius * scale_offset_x),
            cy=face_cy - int(face_radius * scale_offset_y),
            radius=int(face_radius * scale_radius),
            enable=enable,
            get_shocked=get_shocked,
        )

    def set_scale(self, scale: float = 1.0) -> bool:
        """update eye height by scale. Return True if value changed, return False if last height equal current."""
        dy = int(scale * self.radius)

        if dy == self.dy:
            return False

        self.dy = dy
        return True

    def set_open(self, open: float = 1.0) -> bool:
        """update eye height by scale. Return True if value changed, return False if last height equal current."""
        do = open

        if do == self.do:
            return False

        self.do = do
        return True

    def get_points(self, mood: Mood | None = None) -> Tuple[int, int, int, float]:
        if mood is not None:
            self.mood = mood

        match self.mood:
            case Mood.shocked if self.get_shocked:
                radius = self.radius + self.dy
                open_percent = 1
            case Mood.smile:
                radius = self.radius
                open_percent = 1
            case Mood.happy:
                radius = self.radius
                open_percent = self.do
            case Mood.neutral | _:
                radius = self.radius
                open_percent = 1.0

        return self.cx, self.cy, radius, open_percent


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
        self.mood = Mood.neutral

        self.radius = int(min(oled.width, oled.height) * 0.95) // 2

        # Calc eys sizes

        self.eye_l = Eye.from_face_radius(
            face_cx=self.cx,
            face_cy=self.cy,
            face_radius=self.radius,
            right=False,
            get_shocked=False,
        )
        self.eye_r = Eye.from_face_radius(
            face_cx=self.cx,
            face_cy=self.cy,
            face_radius=self.radius,
        )

        self.eye_offset_x = int(self.radius * 0.45)
        self.eye_offset_y = int(self.radius * 0.35)
        self.eye_radius = self.radius // 6

        # Calc mouth sizes
        self.mouth = Mouth.from_face_radius(self.cx, self.cy, self.radius)

        self.smile_width = int(self.radius * 0.8)
        self.smile_height = int(self.radius * 0.2)
        self.mouth_y = self.cy + int(self.radius * 0.35)

        # Calc eyebrow sizes
        self.eyebrow_angle = 0
        self.eyebrow_width = int(self.radius * 0.5)

        # Init face state
        self.wink_left = False
        self.wink_right = False
        self.mouth_type = MouthMood.neutral

    def set_mood(self, mood: Mood) -> None:
        self.mood = mood
        self.mouth.set_scale(1.0)  # set full height for static

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
        self.eyebrow_angle = 0

        self.eye_r.mood = Mood.neutral
        self.eye_l.mood = Mood.neutral
        self.mouth.mood = MouthMood.smile

    def _set_happy(self) -> None:
        self.eyebrow_angle = 0

        self.eye_r.mood = Mood.happy
        self.eye_l.mood = Mood.happy
        self.mouth.mood = MouthMood.smile

        self.eye_r.set_open(0)
        self.eye_l.set_open(0)

    def _set_angry(self) -> None:
        self.eyebrow_angle = math.pi / 8

        self.eye_r.mood = Mood.neutral
        self.eye_l.mood = Mood.neutral
        self.mouth.mood = MouthMood.angry

    def _set_shocked(self) -> None:
        self.eyebrow_angle = 0

        self.eye_r.mood = Mood.shocked
        self.eye_l.mood = Mood.shocked
        self.mouth.mood = MouthMood.neutral

        self.eye_r.set_scale(1)
        self.eye_l.set_scale(1)

    def _set_neutral(self) -> None:
        self.eyebrow_angle = 0

        self.eye_r.mood = Mood.neutral
        self.eye_l.mood = Mood.neutral
        self.mouth.mood = MouthMood.neutral

    async def animate_smile(
        self,
        duration: float = 1.0,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.mood = Mood.smile
        self._set_smile()
        frames_n = int(duration * fps)
        self.smile_height = 0

        for f in range(frames_n):
            # The percentage we show 0-1. For reverse decreases with each frame.
            k = (frames_n - f) / frames_n if reverse else f / frames_n
            updated = self.mouth.set_scale(k)

            # Draw only if smile_height changed
            if updated:
                self._draw_frame()

            await asyncio.sleep(1 / fps)

    async def animate_happy(
        self,
        duration: float = 1.0,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.mood = Mood.happy
        self._set_happy()
        frames_n = int(duration * fps)
        self.smile_height = 0

        for f in range(frames_n):
            # The percentage we show 0-1. For reverse decreases with each frame.
            k = (frames_n - f) / frames_n if reverse else f / frames_n
            updated = self.mouth.set_scale(k)
            updated_eye_r = self.eye_r.set_open(1 - k)
            updated_eye_l = self.eye_l.set_open(1 - k)

            # Draw only if smile_height changed
            if updated or updated_eye_r or updated_eye_l:
                self._draw_frame()

            await asyncio.sleep(1 / fps)

    async def animate_angry(
        self,
        duration: float = 1.0,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.mood = Mood.angry
        self._set_angry()
        eyebrow_width = self.eyebrow_width
        frames_n = int(duration * fps)

        for f in range(frames_n):
            k = (frames_n - f) / frames_n if reverse else f / frames_n
            tmp_eyebrow = int(eyebrow_width * k)
            updated = self.mouth.set_scale(k)

            # Draw only if smile_height changed
            if updated or tmp_eyebrow != self.eyebrow_width:
                self.eyebrow_width = tmp_eyebrow
                self._draw_frame()

            await asyncio.sleep(1 / fps)

    async def animate_shocked(
        self,
        duration: float = 1.0,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.mood = Mood.shocked
        self._set_shocked()
        frames_n = int(duration * fps)

        for f in range(frames_n):
            # The percentage we show 0-1. For reverse decreases with each frame.
            k = (frames_n - f) / frames_n if reverse else f / frames_n
            updated_l = self.eye_l.set_scale(k)
            updated_r = self.eye_r.set_scale(k)

            # Draw only if smile_height changed
            if updated_l or updated_r:
                self._draw_frame()

            await asyncio.sleep(1 / fps)

    async def animate_neutral(self, duration: float = 1.0, fps: int = 30) -> None:
        match self.mood:
            case Mood.smile:
                await self.animate_smile(duration=duration, fps=fps, reverse=True)
            case Mood.angry:
                await self.animate_angry(duration=duration, fps=fps, reverse=True)
            case Mood.shocked:
                await self.animate_shocked(duration=duration, fps=fps, reverse=True)
            case Mood.happy:
                await self.animate_happy(duration=duration, fps=fps, reverse=True)
        self.mood = Mood.neutral
        self._set_neutral()

    def _draw_frame(self, scale: int = 1) -> None:
        oled = self.oled
        oled.fill(0)

        if self.border:
            self.oled.circle(self.cx, self.cy, self.radius, 1)

        # Eye
        eye_l_x, eye_l_y, eye_l_r, eye_l_open = self.eye_l.get_points()
        oled.filled_circle(eye_l_x, eye_l_y, eye_l_r, self.color, eye_l_open)
        eye_r_x, eye_r_y, eye_r_r, eye_r_open = self.eye_r.get_points()
        oled.filled_circle(eye_r_x, eye_r_y, eye_r_r, self.color, eye_r_open)

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
        p0, p1, p2 = self.mouth.get_points()
        oled.quad_bezier(p0, p1, p2)  # offset_y=self.mouth.height // 4)

        oled.show()
