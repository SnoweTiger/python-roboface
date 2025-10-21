import math
import asyncio
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod

from libs.oled import SSD1306


class Mood(Enum):
    neutral = 1
    angry = 2
    smile = 3
    happy = 4
    shocked = 5


class Style(Enum):
    smile = 1
    robo_round = 2


@dataclass
class EyebrowGeometry:
    x1: int
    y1: int
    x2: int
    y2: int


# Abstract classes for styles
class Face(ABC):
    oled: SSD1306
    cx: int
    cy: int
    mood: Mood
    radius: int

    @abstractmethod
    def set_mood(self, mood: Mood) -> None:
        pass


class Mouth(ABC):
    @abstractmethod
    def __init__(self, cx: int, cy: int, height: int, width: int):
        pass

    @abstractmethod
    def set(self, mood: Mood | None = None, transition: float = 1.0) -> bool:
        pass

    @abstractmethod
    def draw(self, display: SSD1306) -> None:
        pass


class Eye(ABC):
    @abstractmethod
    def __init__(self, cx: int, cy: int, radius: int):
        pass

    @abstractmethod
    def set(self, mood: Mood | None = None, transition: float = 1.0) -> bool:
        pass

    @abstractmethod
    def draw(self, display: SSD1306) -> None:
        pass


class Eyebrow(ABC):
    @abstractmethod
    def __init__(self, cx: int, cy: int, height: int, width: int) -> None:
        pass

    @abstractmethod
    def set(self, mood: Mood | None = None, transition: float = 1.0) -> bool:
        pass

    @abstractmethod
    def draw(self, display: SSD1306) -> None:
        pass


# Smile style
class SmileMouth(Mouth):
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
        face: Face,
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

    def _set_points_from_height(self, height_current: int) -> bool:
        if self._height_current == height_current:
            return False

        self._height_current = height_current
        self.p0 = (self._lx, self._cy - self._height_current)
        self.p1 = (self._cx, self._cy + self._height_current)
        self.p2 = (self._rx, self._cy - self._height_current)
        return True

    def set(self, mood: Mood | None = None, transition: float = 1.0) -> bool:
        # transition: float = 0.0 -> 1.0, start -> finish
        if mood:
            self.mood = mood

        # set default
        result = False

        match self.mood:
            case Mood.smile | Mood.happy:
                height_current = int(transition * self._height / 2)
                result = self._set_points_from_height(height_current)

            case Mood.angry:
                height_current = int(transition * self._height / 2) * -1
                result = self._set_points_from_height(height_current)

            case Mood.neutral | _:
                self.p0 = (self._lx, self._cy)
                self.p1 = (self._cx, self._cy)
                self.p2 = (self._rx, self._cy)
                result = True

        return result

    def draw(self, display: SSD1306) -> None:
        display.quad_bezier(self.p0, self.p1, self.p2)


class SmileEye(Eye):
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
        face: Face,
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


class SmileEyebrow(Eyebrow):
    def __init__(
        self,
        cx: int,  # in pixels
        cy: int,  # in pixels
        length: int,  # in pixels
        is_right: bool = False,
    ):
        self._cx = cx
        self._cy = cy
        self._length = length
        self._is_right = is_right
        self._mood = Mood.neutral
        self._geom: EyebrowGeometry | None = None

        # Calc
        self._direction = 1 if self._is_right else -1
        self._x = self._cx - self._direction * self._length // 2
        self._y = self._cy
        self._angle = math.pi / 6
        self._dx = self._dy = 0

    @classmethod
    def from_face(
        cls,
        face: Face,
        scale_offset_x: float = 0.40,
        scale_offset_y: float = 0.55,
        scale_length: float = 0.5,
        is_right: bool = False,
    ):
        k = 1 if is_right else -1
        return cls(
            cx=face.cx + k * int(face.radius * scale_offset_x),
            cy=face.cy - int(face.radius * scale_offset_y),
            length=int(face.radius * scale_length),
            is_right=is_right,
        )

    def set(self, mood: Mood | None = None, transition: float = 1.0) -> bool:
        # transition: float = 0.0 -> 1.0, start -> finish
        if mood:
            self.mood = mood

        # set default
        result = False
        self._geom = None

        match self.mood:
            case Mood.angry:
                dx = int(math.cos(self._angle) * self._length * transition)
                dy = int(math.sin(self._angle) * self._length * transition)

                if self._dx != dx or self._dy != dy:
                    self._dx = dx
                    self._dy = dy

                    self._geom = EyebrowGeometry(
                        self._x,
                        self._y,
                        self._x + self._dx * self._direction,
                        self._y - self._dy,
                    )
                    result = True

        return result

    def draw(self, display: SSD1306) -> None:
        if self._geom:
            display.line(self._geom.x1, self._geom.y1, self._geom.x2, self._geom.y2, 1)


# RoboRound style
class RoboMouth(Mouth):
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
        self._curve_steps: int = 64
        self._curve_steps_current: int = self._curve_steps // 2
        self._filled: float = 1.0

        # calculate points
        self._lx = self._cx - self._width // 2
        self._rx = self._cx + self._width // 2
        self.p0 = (self._lx, self._cy)
        self.p2 = (self._rx, self._cy)

    @classmethod
    def from_face(
        cls,
        face: Face,
        scale_offset_y: float = 0.35,
        scale_height: float = 0.25,
        scale_width: float = 0.9,
    ):
        return cls(
            cx=face.cx,
            cy=face.cy + int(face.radius * scale_offset_y),
            height=int(face.radius * scale_height),
            width=int(face.radius * scale_width),
        )

    def _set_points_from_height(self, height: int, transition: float) -> bool:
        current = int(self._curve_steps * transition / 2)
        self.p1 = (self._cx, self._cy + 2 * height)

        if self._curve_steps_current == current:
            return False

        self._curve_steps_current = current
        return True

    def set(self, mood: Mood | None = None, transition: float = 1.0) -> bool:
        # transition: float = 0.0 -> 1.0, start -> finish
        if mood:
            self._mood = mood

        # set default
        result = False

        match self._mood:
            case Mood.smile | Mood.happy:
                result = self._set_points_from_height(self._height, transition)

            case Mood.angry:
                result = self._set_points_from_height(self._height * -1, transition)

            case Mood.neutral | _:
                self.p0 = (self._lx, self._cy)
                self.p1 = (self._cx, self._cy)
                self.p2 = (self._rx, self._cy)
                result = True

        return result

    def draw(self, display: SSD1306) -> None:
        if self.p0[1] == self.p1[1]:
            display.quad_bezier(self.p0, self.p1, self.p2)
            return

        display.quad_bezier_filled(
            self.p0,
            self.p1,
            self.p2,
            steps=self._curve_steps,
            steps_current=self._curve_steps_current,
        )


class RoboRoundEye(Eye):
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
        face: Face,
        scale_offset_x: float = 0.45,
        scale_offset_y: float = 0.35,
        scale_radius: float = 0.25,
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


class RoboFace(Face):
    def __init__(
        self,
        oled: SSD1306,
        border: bool = False,
        color: int = 1,
        animation_duration: float = 1,
        style: Style = Style.smile,
    ):
        self.oled = oled
        self.cx = oled.width // 2
        self.cy = oled.height // 2
        self.border = border
        self.color = color
        self.animation_duration = animation_duration
        self.mood = Mood.neutral
        self.radius = int(min(oled.width, oled.height) * 0.95) // 2

        # style
        match style:
            case Style.robo_round:
                self.eye_l = RoboRoundEye.from_face(
                    face=self,
                    right=False,
                    get_shocked=False,
                )
                self.eye_r = RoboRoundEye.from_face(face=self, has_eye_lid=True)
                self.mouth = RoboMouth.from_face(face=self)

            case Style.smile | _:
                self.eye_l = SmileEye.from_face(
                    face=self,
                    right=False,
                    get_shocked=False,
                )
                self.eye_r = SmileEye.from_face(face=self, has_eye_lid=True)
                self.eyebrow_l = SmileEyebrow.from_face(face=self)
                self.eyebrow_r = SmileEyebrow.from_face(face=self, is_right=True)
                self.mouth = SmileMouth.from_face(face=self)

    def set_mood(self, mood: Mood) -> None:
        self.mood = mood

        if hasattr(self, "mouth"):
            self.mouth.set(self.mood, 1.0)
        if hasattr(self, "eye_l"):
            self.eye_l.set(self.mood, 1.0)
        if hasattr(self, "eye_r"):
            self.eye_r.set(self.mood, 1.0)
        if hasattr(self, "eyebrow_r"):
            self.eyebrow_r.set(self.mood, 1.0)
        if hasattr(self, "eyebrow_l"):
            self.eyebrow_l.set(self.mood, 1.0)

        self._draw_frame()

    async def _animate(self, duration: float, fps: int, reverse: bool = False) -> None:
        frames_n = int(duration * fps)

        for f in range(frames_n):
            # The percentage we show 0-1. For reverse decreases with each frame.
            k = (frames_n - f) / frames_n if reverse else f / frames_n

            updated_mouth = (
                False if not hasattr(self, "mouth") else self.mouth.set(self.mood, k)
            )
            updated_eye_left = (
                False if not hasattr(self, "eye_l") else self.eye_l.set(self.mood, k)
            )
            updated_eye_right = (
                False if not hasattr(self, "eye_r") else self.eye_r.set(self.mood, k)
            )
            updated_eyebrow_left = (
                False
                if not hasattr(self, "eyebrow_l")
                else self.eyebrow_l.set(self.mood, k)
            )
            updated_eyebrow_right = (
                False
                if not hasattr(self, "eyebrow_r")
                else self.eyebrow_r.set(self.mood, k)
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

    async def set_mood_animated(
        self,
        mood: Mood,
        duration: float | None = None,
        fps: int = 30,
    ) -> None:
        duration = duration if duration else self.animation_duration

        if mood == Mood.neutral:
            await self._animate(duration, fps, True)
            self.set_mood(mood)

        self.set_mood(mood)
        await self._animate(duration, fps)

    def _draw_frame(self) -> None:
        self.oled.fill(0)
        if self.border:
            self.oled.circle(self.cx, self.cy, self.radius, 1)

        # Eye
        if hasattr(self, "eye_l"):
            self.eye_l.draw(self.oled)
        if hasattr(self, "eye_r"):
            self.eye_r.draw(self.oled)

        # Eyebrows
        if hasattr(self, "eyebrow_l"):
            self.eyebrow_l.draw(self.oled)
        if hasattr(self, "eyebrow_r"):
            self.eyebrow_r.draw(self.oled)

        # Mouth
        if hasattr(self, "mouth"):
            self.mouth.draw(self.oled)

        self.oled.show()
