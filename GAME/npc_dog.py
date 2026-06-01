"""
npc_dog.py
==========
NPC Anjing dengan random-walk behavior.
Hanya muncul di map Latar_Depan.

Inheritance: DogNPC mewarisi arcade.Sprite
Encapsulation: state mesin (_state, _facing, _walk_*) dijaga private

Frame layout: 4 cols × 4 rows, masing-masing 64×64 px.
  Row 0 = DIR_DOWN
  Row 1 = DIR_LEFT
  Row 2 = DIR_RIGHT
  Row 3 = DIR_UP
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image as PILImage

import arcade

from constants import (
    PLAYER_MOVEMENT_SPEED,
    PIXEL_SCALE,
    ASSETS_DIR,
    SCALED_TILE_SIZE,
)
from collision_mask import (
    CollisionMask,
    PLAYER_COLLISION_RADIUS,
    SAMPLE_POINTS,
    PLAYER_COLLISION_OFFSET_Y,
)

NPC_SPEED: float = PLAYER_MOVEMENT_SPEED * 0.9

_FRAME_W    = 64
_FRAME_H    = 64
_FRAME_COLS = 4
_NPC_SCALE  = 1.5

_IDLE_SEQ  = [0, 1, 2, 3, 2, 1]
_WALK_SEQ  = [0, 1, 2, 3]
_ANIM_SPEED = 6

_DOG_ASSETS  = ASSETS_DIR / "npc" / "dog"
_IDLE_SHEET  = _DOG_ASSETS / "Root_Idle.png"
_WALK_SHEET  = _DOG_ASSETS / "Root_Walk.png"

_ST_IDLE = "idle"
_ST_WALK = "walk"

_MAX_SPAWN_TRIES = 400
_MAP_MARGIN      = SCALED_TILE_SIZE * 3

_SPAWN_RADIUS_MIN = SCALED_TILE_SIZE * 3
_SPAWN_RADIUS_MAX = SCALED_TILE_SIZE * 8


# ---------------------------------------------------------------------------
# Module-level texture cache
# Encapsulation: cache disimpan di level modul, tidak bocor ke luar kelas
# ---------------------------------------------------------------------------

_TEX_CACHE: dict[str, arcade.Texture] = {}


def _load_row(sheet_path: Path, row: int) -> list[arcade.Texture]:
    """
    Load satu baris frame dari sprite sheet.

    Encapsulation: cache _TEX_CACHE dijaga di level modul agar
    re-spawn tidak membuat duplikat texture.
    """
    textures: list[arcade.Texture] = []
    sheet_key  = str(sheet_path)
    sheet_img  = None

    for col in range(_FRAME_COLS):
        cache_key = f"{sheet_key}|r{row}|c{col}"

        if cache_key not in _TEX_CACHE:
            if sheet_img is None:
                sheet_img = PILImage.open(sheet_path).convert("RGBA")
            x0 = col * _FRAME_W
            y0 = row * _FRAME_H
            cropped = sheet_img.crop((x0, y0, x0 + _FRAME_W, y0 + _FRAME_H))
            _TEX_CACHE[cache_key] = arcade.Texture(cropped)

        textures.append(_TEX_CACHE[cache_key])

    return textures


# ===========================================================================
# DogNPC
# Inheritance: mewarisi arcade.Sprite (sama dengan Player)
# Encapsulation: state machine (idle/walk), arah, dan timer dijaga private
# ===========================================================================

class DogNPC(arcade.Sprite):
    """
    Inheritance: DogNPC mewarisi arcade.Sprite, konsisten dengan Player.
    Encapsulation: state machine _state, _facing, _walk_remain
                   hanya diubah melalui _enter_idle() / _enter_walk().
    """

    DIR_DOWN  = 0
    DIR_UP    = 1
    DIR_LEFT  = 2
    DIR_RIGHT = 3

    _DIRECTIONS = (DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT)

    _DIR_ROW = {
        DIR_DOWN:  0,
        DIR_LEFT:  1,
        DIR_RIGHT: 2,
        DIR_UP:    3,
    }

    def __init__(self) -> None:
        super().__init__()

        self.scale = _NPC_SCALE

        self._facing: int = self.DIR_DOWN
        self._state:  str = _ST_IDLE

        self._anim_counter = 0
        self._anim_frame   = 0

        self._idle_timer:  float = 0.0
        self._idle_target: float = 0.0

        self._walk_remain: float = 0.0
        self._walk_dx:     float = 0.0
        self._walk_dy:     float = 0.0

        self._idle_tex: dict[int, list[arcade.Texture]] = {}
        self._walk_tex: dict[int, list[arcade.Texture]] = {}

        self._load_textures()
        self._apply_texture()
        self._enter_idle()

    def _load_textures(self) -> None:
        fallback = [arcade.make_soft_circle_texture(32, arcade.color.BROWN)]

        for direction, row in self._DIR_ROW.items():
            try:
                self._idle_tex[direction] = _load_row(_IDLE_SHEET, row)
            except Exception as e:
                self._idle_tex[direction] = fallback

            try:
                self._walk_tex[direction] = _load_row(_WALK_SHEET, row)
            except Exception as e:
                self._walk_tex[direction] = self._idle_tex[direction]

    def _enter_idle(self) -> None:
        self._state        = _ST_IDLE
        self._idle_timer   = 0.0
        self._idle_target  = random.uniform(2.0, 5.0)
        self._anim_counter = 0
        self._anim_frame   = 0

    def _enter_walk(self) -> None:
        direction    = random.choice(self._DIRECTIONS)
        self._facing = direction

        tiles = random.randint(1, 4)
        self._walk_remain = tiles * SCALED_TILE_SIZE

        if direction == self.DIR_DOWN:
            self._walk_dx, self._walk_dy = 0.0, -NPC_SPEED
        elif direction == self.DIR_UP:
            self._walk_dx, self._walk_dy = 0.0,  NPC_SPEED
        elif direction == self.DIR_LEFT:
            self._walk_dx, self._walk_dy = -NPC_SPEED, 0.0
        else:
            self._walk_dx, self._walk_dy =  NPC_SPEED, 0.0

        self._state        = _ST_WALK
        self._anim_counter = 0
        self._anim_frame   = 0

    def _apply_texture(self) -> None:
        if self._state == _ST_IDLE:
            frames = self._idle_tex.get(self._facing, [])
            seq    = _IDLE_SEQ
        else:
            frames = self._walk_tex.get(self._facing, [])
            seq    = _WALK_SEQ

        if not frames:
            return

        idx = self._anim_frame % len(seq)
        self.texture = frames[seq[idx] % len(frames)]

    def _try_move(self, collision_mask: CollisionMask) -> bool:
        new_x = self.center_x + self._walk_dx
        new_y = self.center_y + self._walk_dy

        if not collision_mask.is_player_solid(
            new_x, new_y,
            radius     = PLAYER_COLLISION_RADIUS,
            num_points = SAMPLE_POINTS,
            offset_y   = PLAYER_COLLISION_OFFSET_Y,
        ):
            self.center_x = new_x
            self.center_y = new_y
            return True
        return False

    def update_npc(
        self,
        delta_time:     float,
        collision_mask: CollisionMask,
        map_w:          float,
        map_h:          float,
    ) -> None:

        self._anim_counter += 1
        if self._anim_counter >= _ANIM_SPEED:
            self._anim_counter = 0
            self._anim_frame  += 1

        self._apply_texture()

        if self._state == _ST_IDLE:
            self._idle_timer += delta_time
            if self._idle_timer >= self._idle_target:
                self._enter_walk()
            return

        next_x = self.center_x + self._walk_dx
        next_y = self.center_y + self._walk_dy

        if (
            next_x < _MAP_MARGIN
            or next_x > map_w - _MAP_MARGIN
            or next_y < _MAP_MARGIN
            or next_y > map_h - _MAP_MARGIN
        ):
            self._enter_idle()
            return

        if not self._try_move(collision_mask):
            self._enter_idle()
            return

        dist = math.hypot(self._walk_dx, self._walk_dy)
        self._walk_remain -= dist
        if self._walk_remain <= 0:
            self._enter_idle()


# ---------------------------------------------------------------------------
# Fungsi spawn
# ---------------------------------------------------------------------------

def spawn_dog(
    collision_mask: CollisionMask,
    map_w:          float,
    map_h:          float,
    near_x:         float | None = None,
    near_y:         float | None = None,
) -> "DogNPC | None":
    """
    Spawn anjing di posisi valid.
    Return None jika tidak ada posisi valid ditemukan.
    """
    dog = DogNPC()

    pivot_x = near_x if near_x is not None else map_w / 2
    pivot_y = near_y if near_y is not None else map_h / 2

    _SPAWN_CHECK_RADIUS = PLAYER_COLLISION_RADIUS * 1.5

    def _valid(x: float, y: float) -> bool:
        if x < _MAP_MARGIN or x > map_w - _MAP_MARGIN:
            return False
        if y < _MAP_MARGIN or y > map_h - _MAP_MARGIN:
            return False
        return not collision_mask.is_player_solid(
            x, y,
            radius     = _SPAWN_CHECK_RADIUS,
            num_points = SAMPLE_POINTS,
            offset_y   = PLAYER_COLLISION_OFFSET_Y,
        )

    for _ in range(_MAX_SPAWN_TRIES):
        angle = random.uniform(0.0, 2.0 * math.pi)
        dist  = random.uniform(_SPAWN_RADIUS_MIN, _SPAWN_RADIUS_MAX)
        x = pivot_x + math.cos(angle) * dist
        y = pivot_y + math.sin(angle) * dist

        x = max(_MAP_MARGIN, min(x, map_w - _MAP_MARGIN))
        y = max(_MAP_MARGIN, min(y, map_h - _MAP_MARGIN))

        if _valid(x, y):
            dog.center_x = x
            dog.center_y = y
            return dog

    for _ in range(_MAX_SPAWN_TRIES):
        x = random.uniform(_MAP_MARGIN, map_w - _MAP_MARGIN)
        y = random.uniform(_MAP_MARGIN, map_h - _MAP_MARGIN)

        if _valid(x, y):
            dog.center_x = x
            dog.center_y = y
            return dog

    return None
