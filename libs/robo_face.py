import math
import asyncio
from enum import Enum
from typing import Tuple
from dataclasses import dataclass

from libs.oled import SSD1306


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
        mood: Mood = Mood.neutral,
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
        mood: Mood | None = None,
    ) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        if mood is not None:
            self.mood = mood

        match self.mood:
            case Mood.smile | Mood.happy:
                print("smile|happy")
                p0 = (self.lx, self.cy - self.dy)
                p1 = (self.cx, self.cy + self.dy)
                p2 = (self.rx, self.cy - self.dy)

            case Mood.angry:
                print("negative")
                p0 = (self.lx, self.cy + self.dy)
                p1 = (self.cx, self.cy - self.dy)
                p2 = (self.rx, self.cy + self.dy)

            case Mood.neutral | _:
                print("neutral")
                p0 = (self.lx, self.cy)
                p1 = (self.cx, self.cy)
                p2 = (self.rx, self.cy)

        return (p0, p1, p2)


@dataclass
class EyeGeometry:
    x: int
    y: int
    radius: int


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

    def get_points(self, mood: Mood | None = None) -> Tuple[EyeGeometry, float]:
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

        return EyeGeometry(self.cx, self.cy, radius), open_percent


class Eyebrow:
    def __init__(
        self,
        x: int,  # in pixels
        y: int,  # in pixels
        length: int,  # in pixels
        angle: float,
        enable: bool = True,
        right: bool = True,
    ):
        self.x = x
        self.y = y
        self.length = length
        self.angle = angle
        self.enable = enable
        self.right = right
        self.mood = Mood.neutral
        self.dx = int(math.cos(self.angle) * self.length)
        self.dy = int(math.sin(self.angle) * self.length)

    @classmethod
    def from_face_radius(
        cls,
        face_cx: int,
        face_cy: int,
        face_radius: int,
        scale_offset_x: float = 0.40,
        scale_offset_y: float = 0.55,
        scale_length: float = 0.6,
        angle: float = math.pi / 6,
        right: bool = True,
        enable: bool = True,
    ):
        k = 1 if right else -1
        length = int(face_radius * scale_length)
        return cls(
            x=face_cx + k * (int(face_radius * scale_offset_x - length / 2)),
            y=face_cy - int(face_radius * scale_offset_y),
            length=length,
            angle=angle,
            enable=enable,
            right=right,
        )

    def set_scale(self, scale: float = 0) -> bool:
        dx = int(math.cos(self.angle) * self.length * scale)
        dy = int(math.sin(self.angle) * self.length * scale)

        if dx == self.dx and dy == self.dy:
            return False

        self.dx = dx
        self.dy = dy
        return True

    def get_points(self, mood: Mood | None = None) -> Tuple | None:
        if mood:
            self.mood = mood

        match self.mood:
            case Mood.angry:
                k = 1 if self.right else -1
                # dx = int(math.cos(self.angle) * self.length)
                # dy = int(math.sin(self.angle) * self.length)
                result = (self.x, self.y, self.x + self.dx * k, self.y - self.dy)
            case _:
                result = None
        return result


class RoboFace:
    def __init__(
        self,
        oled: SSD1306,
        border: bool = False,
        color: int = 1,
        animation_duration: float = 1,
    ):
        self.oled = oled
        self.cx = oled.width // 2
        self.cy = oled.height // 2
        self.border = border
        self.color = color
        self.animation_duration = animation_duration
        self.mood = Mood.neutral
        self.radius = int(min(oled.width, oled.height) * 0.95) // 2

        # Eye
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

        # Eyebrow
        self.eyebrow_l = Eyebrow.from_face_radius(
            face_cx=self.cx,
            face_cy=self.cy,
            face_radius=self.radius,
            right=False,
        )
        self.eyebrow_r = Eyebrow.from_face_radius(
            face_cx=self.cx,
            face_cy=self.cy,
            face_radius=self.radius,
        )

        # mouth
        self.mouth = Mouth.from_face_radius(self.cx, self.cy, self.radius)

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

        self.eyebrow_r.mood = self.mood
        self.eyebrow_l.mood = self.mood
        self.eye_r.mood = self.mood
        self.eye_l.mood = self.mood
        self.mouth.mood = self.mood

    def _set_happy(self) -> None:
        self.eyebrow_angle = 0

        self.eyebrow_r.mood = self.mood
        self.eyebrow_l.mood = self.mood
        self.eye_r.mood = self.mood
        self.eye_l.mood = self.mood
        self.mouth.mood = self.mood

        self.eye_r.set_open(0)
        self.eye_l.set_open(0)

    def _set_angry(self) -> None:
        self.eyebrow_angle = math.pi / 8

        self.eyebrow_r.mood = self.mood
        self.eyebrow_l.mood = self.mood
        self.eye_r.mood = self.mood
        self.eye_l.mood = self.mood
        self.mouth.mood = self.mood

        self.eyebrow_r.set_scale(1)
        self.eyebrow_l.set_scale(1)

    def _set_shocked(self) -> None:
        self.eyebrow_angle = 0

        self.eyebrow_r.mood = self.mood
        self.eyebrow_l.mood = self.mood
        self.eye_r.mood = self.mood
        self.eye_l.mood = self.mood
        self.mouth.mood = self.mood

        self.eye_r.set_scale(1)
        self.eye_l.set_scale(1)

    def _set_neutral(self) -> None:
        self.eyebrow_angle = 0

        self.eyebrow_r.mood = self.mood
        self.eyebrow_l.mood = self.mood
        self.eye_r.mood = self.mood
        self.eye_l.mood = self.mood
        self.mouth.mood = self.mood

    async def animate_smile(
        self,
        duration: float | None = None,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.mood = Mood.smile
        self._set_smile()
        duration = duration if duration else self.animation_duration
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
        duration: float | None = None,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.mood = Mood.happy
        self._set_happy()
        duration = duration if duration else self.animation_duration
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
        duration: float | None = None,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.mood = Mood.angry
        self._set_angry()
        duration = duration if duration else self.animation_duration
        frames_n = int(duration * fps)

        for f in range(frames_n):
            k = (frames_n - f) / frames_n if reverse else f / frames_n
            updated_m = self.mouth.set_scale(k)
            updated_e_l = self.eyebrow_l.set_scale(k)
            updated_e_r = self.eyebrow_r.set_scale(k)

            # Draw only if smile_height changed
            if updated_m or updated_e_l or updated_e_r:
                self._draw_frame()

            await asyncio.sleep(1 / fps)

    async def animate_shocked(
        self,
        duration: float | None = None,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.mood = Mood.shocked
        self._set_shocked()
        duration = duration if duration else self.animation_duration
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

    async def animate_neutral(
        self,
        duration: float | None = None,
        fps: int = 30,
    ) -> None:
        duration = duration if duration else self.animation_duration
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

    def _draw_frame(self) -> None:
        self.oled.fill(0)
        if self.border:
            self.oled.circle(self.cx, self.cy, self.radius, 1)

        # Eye
        eye_l, eye_l_open = self.eye_l.get_points()
        self.oled.filled_circle(eye_l.x, eye_l.y, eye_l.radius, self.color, eye_l_open)
        eye_r, eye_r_open = self.eye_r.get_points()
        self.oled.filled_circle(eye_r.x, eye_r.y, eye_r.radius, self.color, eye_r_open)

        # Eyebrows
        eyebrow_l = self.eyebrow_l.get_points()
        if eyebrow_l:
            x10, y10, x11, y11 = eyebrow_l
            self.oled.line(x10, y10, x11, y11, 1)

        eyebrow_r = self.eyebrow_r.get_points()
        if eyebrow_r:
            x0, y0, x1, y1 = eyebrow_r
            self.oled.line(x0, y0, x1, y1, 1)

        # Mouth
        p0, p1, p2 = self.mouth.get_points()
        self.oled.quad_bezier(p0, p1, p2)  # offset_y=self.mouth.height // 4)

        self.oled.show()
