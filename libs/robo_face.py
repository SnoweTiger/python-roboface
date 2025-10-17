import math
import asyncio
from enum import Enum
from dataclasses import dataclass

from libs.oled import SSD1306


class Mood(Enum):
    neutral = 1
    angry = 2
    smile = 3
    happy = 4
    shocked = 5


@dataclass
class EyebrowGeometry:
    x1: int
    y1: int
    x2: int
    y2: int


class SmileMouth:
    def __init__(
        self,
        cx: int,  # in pixels
        cy: int,  # in pixels
        height: int,  # in pixels
        width: int,  # in pixels
        mood: Mood = Mood.neutral,
    ) -> None:
        self._cx = cx
        self._cy = cy
        self._width = width
        self._height = height
        self._mood = mood

        # calculate points
        self._lx = self._cx - self._width // 2
        self._rx = self._cx + self._width // 2
        self._height_current = 0

    @classmethod
    def from_face(
        cls,
        face,
        scale_offset_y: float = 0.35,
        scale_height: float = 0.4,
        scale_width: float = 0.8,
    ):
        return cls(
            cx=face.cx,
            cy=face.cy + int(face.radius * scale_offset_y),
            height=int(face.radius * scale_height),
            width=int(face.radius * scale_width),
        )

    def set(self, mood: Mood | None = None, transition: float = 1.0) -> bool:
        # transition: float = 0.0 -> 1.0, start -> finish
        if mood:
            self.mood = mood

        # set default
        result = False

        match self.mood:
            case Mood.smile | Mood.happy:
                height_current = int(transition * self._height / 2)

                if self._height_current != height_current:
                    self._height_current = height_current
                    self.p0 = (self._lx, self._cy - self._height_current)
                    self.p1 = (self._cx, self._cy + self._height_current)
                    self.p2 = (self._rx, self._cy - self._height_current)
                    result = True

            case Mood.angry:
                height_current = int(transition * self._height / 2)

                if self._height_current != height_current:
                    self._height_current = height_current
                    self.p0 = (self._lx, self._cy + self._height_current)
                    self.p1 = (self._cx, self._cy - self._height_current)
                    self.p2 = (self._rx, self._cy + self._height_current)
                    result = True

            case Mood.neutral | _:
                self.p0 = (self._lx, self._cy)
                self.p1 = (self._cx, self._cy)
                self.p2 = (self._rx, self._cy)
                result = True

        return result

    def draw(self, display: SSD1306) -> None:
        display.quad_bezier(self.p0, self.p1, self.p2)


class SmileEye:
    def __init__(
        self,
        cx: int,  # in pixels
        cy: int,  # in pixels
        radius: int,  # in pixels
        get_shocked: bool = True,
        mood: Mood = Mood.neutral,
        has_eye_lid: bool = False,
    ):
        self._cx = cx
        self._cy = cy
        self._radius = radius
        self._mood = mood
        self._get_shocked = get_shocked
        self._has_eye_lid = has_eye_lid
        self._radius_current = self._radius
        self._ellipsis = 1.0
        self._eyelid_height = 0

    @classmethod
    def from_face(
        cls,
        face,
        scale_offset_x: float = 0.45,
        scale_offset_y: float = 0.35,
        scale_radius: float = 0.17,
        right: bool = True,
        get_shocked: bool = True,
        has_eye_lid: bool = False,
    ):
        k = 1 if right else -1
        return cls(
            cx=face.cx + k * int(face.radius * scale_offset_x),
            cy=face.cy - int(face.radius * scale_offset_y),
            radius=int(face.radius * scale_radius),
            get_shocked=get_shocked,
            has_eye_lid=has_eye_lid,
        )

    def set(self, mood: Mood | None = None, transition: float = 1.0) -> bool:
        # transition: float = 0.0 -> 1.0, start -> finish
        if mood:
            self.mood = mood

        # set default
        result = False
        self._eyelid_height = 0
        self._ellipsis = 1.0
        self._radius_current = self._radius

        match self.mood:
            case Mood.shocked if self._get_shocked:
                new_radius = self._radius + int(transition * self._radius)

                if self._radius_current == new_radius:
                    result = False
                else:
                    self._radius_current = new_radius
                    result = True

            case Mood.happy:
                if self._has_eye_lid:
                    # eyelids
                    eyelid_height = math.ceil(transition * self._radius_current)
                    if self._eyelid_height == eyelid_height:
                        result = False
                    else:
                        self._eyelid_height = eyelid_height
                        result = True
                else:
                    # ellipsis
                    if self._ellipsis == 1 - transition:
                        result = False
                    else:
                        self._ellipsis = 1 - transition
                        result = True

            case Mood.neutral | Mood.smile | _:
                # default
                pass

        return result

    def draw(self, display: SSD1306) -> None:
        # draw eye
        display.filled_circle(
            self._cx,
            self._cy,
            self._radius_current,
            1,
            self._ellipsis,
        )

        # draw eyelid
        if self._eyelid_height != 0:
            eyelid_bot_width = self._radius_current * 2 + 1
            display.filled_rectangle(
                self._cx - self._radius_current,
                self._cy - self._radius_current,
                eyelid_bot_width,
                self._eyelid_height,
                0,
            )
            display.filled_rectangle(
                self._cx - self._radius_current,
                self._cy + self._radius_current,
                eyelid_bot_width,
                self._eyelid_height * -1,
                0,
            )


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

    def draw(self, display: SSD1306) -> None:
        match self.mood:
            case Mood.angry:
                k = 1 if self.right else -1
                eyebrow = EyebrowGeometry(
                    self.x,
                    self.y,
                    self.x + self.dx * k,
                    self.y - self.dy,
                )
            case _:
                eyebrow = None

        if eyebrow:
            display.line(eyebrow.x1, eyebrow.y1, eyebrow.x2, eyebrow.y2, 1)


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
        self.eye_l = SmileEye.from_face(face=self, right=False, get_shocked=False)
        self.eye_r = SmileEye.from_face(face=self, has_eye_lid=True)

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

        # Mouth
        self.mouth = SmileMouth.from_face(face=self)

    def set_mood(self, mood: Mood) -> None:
        self.mood = mood

        self.eyebrow_r.mood = self.mood
        self.eyebrow_l.mood = self.mood

        self.eyebrow_r.set_scale(1)
        self.eyebrow_l.set_scale(1)

        self.mouth.set(self.mood, 1.0)
        self.eye_l.set(self.mood, 1.0)
        self.eye_r.set(self.mood, 1.0)

        self._draw_frame()

    async def _animate(
        self,
        duration: float | None = None,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        duration = duration if duration else self.animation_duration
        frames_n = int(duration * fps)

        for f in range(frames_n):
            # The percentage we show 0-1. For reverse decreases with each frame.
            k = (frames_n - f) / frames_n if reverse else f / frames_n

            updated_mouth = False if not self.mouth else self.mouth.set(self.mood, k)
            updated_eye_left = False if not self.eye_l else self.eye_l.set(self.mood, k)
            updated_eye_right = (
                False if not self.eye_r else self.eye_r.set(self.mood, k)
            )
            updated_eyebrow_left = (
                False if not self.eyebrow_l else self.eyebrow_l.set_scale(k)
            )
            updated_eyebrow_right = (
                False if not self.eyebrow_r else self.eyebrow_r.set_scale(k)
            )

            # Draw only if smile_height changed
            if (
                updated_mouth
                or updated_eye_left
                or updated_eye_right
                or updated_eyebrow_left
                or updated_eyebrow_right
            ):
                self._draw_frame()

            await asyncio.sleep(1 / fps)

    async def animate_smile(
        self,
        duration: float | None = None,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.set_mood(Mood.smile)
        await self._animate(duration, fps, reverse)

    async def animate_happy(
        self,
        duration: float | None = None,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.set_mood(Mood.happy)
        await self._animate(duration, fps, reverse)

    async def animate_angry(
        self,
        duration: float | None = None,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.set_mood(Mood.angry)
        await self._animate(duration, fps, reverse)

    async def animate_shocked(
        self,
        duration: float | None = None,
        fps: int = 30,
        reverse: bool = False,
    ) -> None:
        self.set_mood(Mood.shocked)
        await self._animate(duration, fps, reverse)

    async def animate_neutral(
        self,
        duration: float | None = None,
        fps: int = 30,
    ) -> None:
        # duration = duration if duration else self.animation_duration
        match self.mood:
            case Mood.smile:
                await self.animate_smile(duration=duration, fps=fps, reverse=True)
            case Mood.angry:
                await self.animate_angry(duration=duration, fps=fps, reverse=True)
            case Mood.shocked:
                await self.animate_shocked(duration=duration, fps=fps, reverse=True)
            case Mood.happy:
                await self.animate_happy(duration=duration, fps=fps, reverse=True)

        self.set_mood(Mood.happy)

    def _draw_frame(self) -> None:
        self.oled.fill(0)
        if self.border:
            self.oled.circle(self.cx, self.cy, self.radius, 1)

        # Eye
        if self.eye_l:
            self.eye_l.draw(self.oled)
        if self.eye_r:
            self.eye_r.draw(self.oled)

        # Eyebrows
        if self.eyebrow_l:
            self.eyebrow_l.draw(self.oled)
        if self.eyebrow_r:
            self.eyebrow_r.draw(self.oled)

        # Mouth
        if self.mouth:
            self.mouth.draw(self.oled)

        self.oled.show()
