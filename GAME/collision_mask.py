"""
collision_mask.py — Collision Detection via PNG Mask

Encapsulation: CollisionMask menyimpan semua state deteksi tabrakan
(_image, _pixels, dimensi peta) sebagai private attribute. Caller
hanya perlu memanggil is_solid() dan is_player_solid() tanpa
mengetahui detail pixel sampling atau koordinat transformasi.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from PIL import Image

from constants import PIXEL_SCALE, TILE_SIZE, PLAYER_COLLISION_OFFSET_Y

SOLID_COLOR_RGB          = (255, 0, 0)
COLOR_TOLERANCE          = 10
SAMPLE_POINTS            = 8
PLAYER_COLLISION_RADIUS  = 10.0


class CollisionMask:
    """
    Encapsulation: semua data collision (image, pixels, dimensi) dijaga
    private dan diakses hanya melalui is_solid() dan is_player_solid().
    """

    def __init__(self) -> None:
        self._image: Optional[Image.Image] = None
        self._pixels                       = None
        self._png_width:  int   = 0
        self._png_height: int   = 0
        self._map_pixel_width:  float = 0.0
        self._map_pixel_height: float = 0.0
        self._loaded: bool = False
        self._current_map: str = ""

    def load(
        self,
        png_path: str | Path,
        map_pixel_width: float,
        map_pixel_height: float,
        current_map: str = "",
    ) -> None:
        png_path = Path(png_path)
        self._map_pixel_width  = map_pixel_width
        self._map_pixel_height = map_pixel_height
        self._current_map      = current_map
        self._loaded = False
        self._image  = None
        self._pixels = None

        if not png_path.is_file():
            return

        try:
            img = Image.open(png_path).convert("RGB")
            self._image      = img
            self._pixels     = img.load()
            self._png_width  = img.width
            self._png_height = img.height
            self._loaded     = True
        except Exception as exc:
            pass

    def _is_out_of_bounds(self, world_x: float, world_y: float) -> bool:
        return (
            world_x < 0
            or world_x > self._map_pixel_width
            or world_y < 0
            or world_y > self._map_pixel_height
        )

    def _world_to_png(self, world_x: float, world_y: float) -> tuple[int, int]:
        if self._map_pixel_width == 0 or self._map_pixel_height == 0:
            return 0, 0

        norm_x = world_x / self._map_pixel_width
        norm_y = world_y / self._map_pixel_height

        px = int(norm_x * self._png_width)
        py = int((1.0 - norm_y) * self._png_height)

        px = max(0, min(px, self._png_width  - 1))
        py = max(0, min(py, self._png_height - 1))

        return px, py

    def _is_pixel_solid(self, px: int, py: int) -> bool:
        if not self._loaded or self._pixels is None:
            return False
        try:
            r, g, b = self._pixels[px, py]
            return (
                r >= SOLID_COLOR_RGB[0] - COLOR_TOLERANCE
                and g <= SOLID_COLOR_RGB[1] + COLOR_TOLERANCE
                and b <= SOLID_COLOR_RGB[2] + COLOR_TOLERANCE
            )
        except (IndexError, TypeError):
            return False

    def is_solid(self, world_x: float, world_y: float) -> bool:
        if not self._loaded:
            return False

        if self._is_out_of_bounds(world_x, world_y):
            from world_registry import is_transition_corridor
            if is_transition_corridor(world_x, world_y, self._current_map):
                return False
            return True

        px, py = self._world_to_png(world_x, world_y)
        return self._is_pixel_solid(px, py)

    def is_player_solid(
        self,
        center_x: float,
        center_y: float,
        radius: float   = PLAYER_COLLISION_RADIUS,
        num_points: int = SAMPLE_POINTS,
        offset_y: float = PLAYER_COLLISION_OFFSET_Y,
    ) -> bool:
        if not self._loaded:
            return False

        anchor_x = center_x
        anchor_y = center_y + offset_y

        if self.is_solid(anchor_x, anchor_y):
            return True

        angle_step = (2.0 * math.pi) / num_points
        for i in range(num_points):
            angle = i * angle_step
            sx = anchor_x + math.cos(angle) * radius
            sy = anchor_y + math.sin(angle) * radius
            if self.is_solid(sx, sy):
                return True

        return False

    @property
    def loaded(self) -> bool:
        return self._loaded


def get_collision_png_path(tmx_path: str | Path) -> str:
    p = Path(tmx_path)
    png_name = f"Batas_{p.stem}.png"
    return str(p.parent / png_name)
