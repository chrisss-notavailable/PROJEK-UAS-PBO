"""
player.py – Kelas Player

Inheritance: Player mewarisi arcade.Sprite
Encapsulation: state animasi, facing, dan flag activity dijaga private;
               diakses via property dan method publik.
"""
from __future__ import annotations

import math
from pathlib import Path
import arcade

from constants import (
    PLAYER_MOVEMENT_SPEED,
    PLAYER_COLLISION_OFFSET_Y,
    TILE_SIZE,
    ASSETS_DIR,
)

_PLAYER_ASSETS    = ASSETS_DIR / "player"
_IDLE_DIR         = _PLAYER_ASSETS / "idle"
_WALK_DIR         = _PLAYER_ASSETS / "walk"
_CASTING_DIR      = ASSETS_DIR / "Casting"
_WAITING_DIR      = ASSETS_DIR / "Waiting"
_WATERING_DIR     = ASSETS_DIR / "Watering"
_PLAYER_SCALE     = 2.0
_ANIM_SPEED_FRAMES = 4


# ===========================================================================
# Player
# Inheritance: mewarisi arcade.Sprite untuk integrasi engine
# Encapsulation: _frames_*, _anim_*, _prev_is_moving dijaga private
# ===========================================================================

class Player(arcade.Sprite):
    """
    Inheritance: mewarisi arcade.Sprite sehingga dapat dimasukkan
    ke SpriteList, mendukung collision detection, dan rendering arcade.

    Encapsulation: state animasi diakses hanya melalui update() dan
    get_*_frames(); posisi collider diakses via property.
    """

    DIR_DOWN  = 0
    DIR_UP    = 1
    DIR_LEFT  = 2
    DIR_RIGHT = 3

    def __init__(self, spritesheet_path: str | None = None) -> None:
        super().__init__()

        self.scale = _PLAYER_SCALE

        self.facing    = self.DIR_DOWN
        self.is_moving = False
        self._anim_frame   = 0
        self._anim_counter = 0
        self._prev_is_moving = False

        self.change_x = 0.0
        self.change_y = 0.0

        self.fishing  = False
        self.watering = False

        self._frames_idle:  list[arcade.Texture] = []
        self._frames_kanan: list[arcade.Texture] = []
        self._frames_kiri:  list[arcade.Texture] = []

        self._frames_casting_r: list[arcade.Texture] = []
        self._frames_casting_l: list[arcade.Texture] = []
        self._frames_waiting_r: list[arcade.Texture] = []
        self._frames_waiting_l: list[arcade.Texture] = []

        self._frames_watering: list[arcade.Texture] = []

        self._load_textures()
        self._load_fishing_textures()
        self._load_watering_textures()
        self.texture = self._frames_idle[0]

    def _load_single(self, path: Path) -> arcade.Texture:
        return arcade.load_texture(str(path))

    def _load_textures(self) -> None:
        try:
            for i in range(1, 10):
                self._frames_idle.append(self._load_single(_IDLE_DIR / f"idle{i}.gif"))
            for i in range(1, 9):
                self._frames_kanan.append(self._load_single(_WALK_DIR / f"kanan{i}.gif"))
            for i in range(1, 9):
                self._frames_kiri.append(self._load_single(_WALK_DIR / f"kiri{i}.gif"))
        except Exception as e:
            self._make_fallback_textures()

    def _load_fishing_textures(self) -> None:
        try:
            for i in range(15):
                name = f"frame_{i:02d}_delay-0.07s.gif"
                tex = arcade.load_texture(str(_CASTING_DIR / name))
                flp = tex.flip_left_right()
                self._frames_casting_r.append(tex)
                self._frames_casting_l.append(flp)
            for i in range(9):
                name = f"frame_{i}_delay-0.07s.gif"
                tex = arcade.load_texture(str(_WAITING_DIR / name))
                flp = tex.flip_left_right()
                self._frames_waiting_r.append(tex)
                self._frames_waiting_l.append(flp)
        except Exception as e:
            pass

    def _load_watering_textures(self) -> None:
        try:
            for i in range(5):
                name = f"frame_{i}_delay-0.07s.gif"
                tex = arcade.load_texture(str(_WATERING_DIR / name))
                self._frames_watering.append(tex)
        except Exception as e:
            pass

    def _make_fallback_textures(self) -> None:
        size = TILE_SIZE
        self._frames_idle  = [arcade.make_soft_circle_texture(size, arcade.color.BLUE_VIOLET,   outer_alpha=255)]
        self._frames_kanan = [arcade.make_soft_circle_texture(size, arcade.color.MEDIUM_PURPLE,  outer_alpha=255)]
        self._frames_kiri  = [arcade.make_soft_circle_texture(size, arcade.color.DARK_VIOLET,    outer_alpha=255)]

    def _current_frames(self) -> list[arcade.Texture]:
        if not self.is_moving:
            return self._frames_idle
        if self.facing == self.DIR_RIGHT:
            return self._frames_kanan
        if self.facing == self.DIR_LEFT:
            return self._frames_kiri
        return self._frames_idle

    @property
    def collision_center_x(self) -> float:
        return self.center_x

    @property
    def collision_center_y(self) -> float:
        return self.center_y + PLAYER_COLLISION_OFFSET_Y

    def move_with_collision(self, collision_mask) -> None:
        from collision_mask import PLAYER_COLLISION_RADIUS, SAMPLE_POINTS

        dx = self.change_x
        dy = self.change_y

        if dx == 0.0 and dy == 0.0:
            return

        new_cx = self.center_x + dx
        new_cy = self.center_y + dy

        if not collision_mask.is_player_solid(
            new_cx, new_cy,
            radius     = PLAYER_COLLISION_RADIUS,
            num_points = SAMPLE_POINTS,
            offset_y   = PLAYER_COLLISION_OFFSET_Y,
        ):
            self.center_x = new_cx
            self.center_y = new_cy
            return

        if dx != 0.0:
            test_x = self.center_x + dx
            if not collision_mask.is_player_solid(
                test_x, self.center_y,
                radius     = PLAYER_COLLISION_RADIUS,
                num_points = SAMPLE_POINTS,
                offset_y   = PLAYER_COLLISION_OFFSET_Y,
            ):
                self.center_x = test_x
                return

        if dy != 0.0:
            test_y = self.center_y + dy
            if not collision_mask.is_player_solid(
                self.center_x, test_y,
                radius     = PLAYER_COLLISION_RADIUS,
                num_points = SAMPLE_POINTS,
                offset_y   = PLAYER_COLLISION_OFFSET_Y,
            ):
                self.center_y = test_y
                return

    def update(self) -> None:
        if self.fishing or self.watering:
            self.change_x = 0.0
            self.change_y = 0.0
            return

        if self.change_x != 0 or self.change_y != 0:
            self.is_moving = True
            if abs(self.change_x) >= abs(self.change_y):
                self.facing = self.DIR_RIGHT if self.change_x > 0 else self.DIR_LEFT
            else:
                self.facing = self.DIR_UP if self.change_y > 0 else self.DIR_DOWN
        else:
            self.is_moving = False

        state_switched = self.is_moving != self._prev_is_moving
        if state_switched:
            self._anim_frame   = 0
            self._anim_counter = 0

        self._prev_is_moving = self.is_moving

        frames = self._current_frames()

        self._anim_counter += 1
        if self._anim_counter >= _ANIM_SPEED_FRAMES:
            self._anim_counter = 0
            self._anim_frame   = (self._anim_frame + 1) % len(frames)

        self.texture = frames[self._anim_frame % len(frames)]

    def get_fishing_frames(self, casting: bool, facing_left: bool) -> list[arcade.Texture]:
        """
        Return daftar frame animasi memancing yang sesuai.

        Parameters
        ----------
        casting     : True = sedang casting/reverse, False = waiting
        facing_left : True = player menghadap kiri
        """
        if casting:
            return self._frames_casting_l if facing_left else self._frames_casting_r
        return self._frames_waiting_l if facing_left else self._frames_waiting_r

    def get_watering_frames(self) -> list[arcade.Texture]:
        """Return daftar frame animasi watering player."""
        return self._frames_watering

    def process_keys(self, keys_pressed: set[int]) -> None:
        if self.fishing or self.watering:
            self.change_x = 0.0
            self.change_y = 0.0
            return

        dx = 0.0
        dy = 0.0

        if arcade.key.W in keys_pressed or arcade.key.UP in keys_pressed:
            dy += PLAYER_MOVEMENT_SPEED
        if arcade.key.S in keys_pressed or arcade.key.DOWN in keys_pressed:
            dy -= PLAYER_MOVEMENT_SPEED
        if arcade.key.A in keys_pressed or arcade.key.LEFT in keys_pressed:
            dx -= PLAYER_MOVEMENT_SPEED
        if arcade.key.D in keys_pressed or arcade.key.RIGHT in keys_pressed:
            dx += PLAYER_MOVEMENT_SPEED

        if dx != 0 and dy != 0:
            factor = 1.0 / math.sqrt(2)
            dx *= factor
            dy *= factor

        self.change_x = dx
        self.change_y = dy
