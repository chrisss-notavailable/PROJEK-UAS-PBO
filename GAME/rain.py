"""
rain.py — Efek hujan visual untuk Farming RPG

Desain:
  • Screen-space effect — tidak mengikuti kamera / peta / player.
  • Semua tetes digambar SATU draw call via ShapeElementList (bukan
    150x draw_line terpisah) — ini yang mencegah lag.
  • RainSystem diaktifkan/dimatikan via toggle di main.py (tombol L).
  • 100 partikel — cukup untuk terlihat deras, ringan di GPU.

Warna: biru solid (30, 100, 200) dengan alpha transparan.

Penggunaan di main.py:
    from rain import RainSystem
    self._rain = RainSystem(SCREEN_WIDTH, SCREEN_HEIGHT)

    # on_update
    if self._rain_enabled:
        self._rain.update(delta_time)

    # on_draw — setelah gui_camera.use(), sebelum UI
    if self._rain_enabled:
        self._rain.draw()
"""
from __future__ import annotations
import random
import arcade
import arcade.shape_list as sl

# ── Konstanta ────────────────────────────────────────────────────────────────
_RAIN_COUNT  = 100

_SPEED_Y_MIN = 420.0
_SPEED_Y_MAX = 580.0
_SPEED_X_MIN = 100.0
_SPEED_X_MAX = 150.0

_LEN_MIN     = 8
_LEN_MAX     = 15

# Warna biru — (R, G, B)
_COLOR_R = 30
_COLOR_G = 100
_COLOR_B = 200

_ALPHA_MIN   = 70
_ALPHA_MAX   = 140

# Rasio arah (untuk normalisasi sekali saat init, bukan tiap frame)
import math
_NORM = math.sqrt(_SPEED_X_MAX ** 2 + _SPEED_Y_MAX ** 2)


class _RainDrop:
    __slots__ = ("x", "y", "vx", "vy", "nx", "ny", "length", "alpha")

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.x = float(random.randint(-screen_w // 4, screen_w + screen_w // 4))
        self.y = float(random.randint(0, screen_h + 40))
        self._init_velocity()

    def _init_velocity(self) -> None:
        self.vx     = -random.uniform(_SPEED_X_MIN, _SPEED_X_MAX)
        self.vy     = -random.uniform(_SPEED_Y_MIN, _SPEED_Y_MAX)
        spd         = math.sqrt(self.vx * self.vx + self.vy * self.vy)
        self.nx     = self.vx / spd          # arah X dinormalisasi (konstan)
        self.ny     = self.vy / spd          # arah Y dinormalisasi (konstan)
        self.length = random.randint(_LEN_MIN, _LEN_MAX)
        self.alpha  = random.randint(_ALPHA_MIN, _ALPHA_MAX)

    def respawn(self, screen_w: int, screen_h: int) -> None:
        self.x = float(random.randint(-screen_w // 4, screen_w + screen_w // 4))
        self.y = float(screen_h + random.randint(10, 60))
        self._init_velocity()

    def update(self, dt: float, screen_w: int, screen_h: int) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y < -20 or self.x < -screen_w // 3:
            self.respawn(screen_w, screen_h)


class RainSystem:
    """
    Sistem partikel hujan — semua garis dibatch dalam satu ShapeElementList.

    Interface:
        update(delta_time)
        draw()
    """

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self._sw = screen_w
        self._sh = screen_h
        self._drops: list[_RainDrop] = [
            _RainDrop(screen_w, screen_h) for _ in range(_RAIN_COUNT)
        ]
        self._shape_list: sl.ShapeElementList = sl.ShapeElementList()
        self._dirty = True   # perlu rebuild saat pertama draw

    def update(self, delta_time: float) -> None:
        for drop in self._drops:
            drop.update(delta_time, self._sw, self._sh)
        self._dirty = True

    def _rebuild(self) -> None:
        """Bangun ulang ShapeElementList dari semua tetes saat ini."""
        self._shape_list = sl.ShapeElementList()
        for drop in self._drops:
            x2 = drop.x + drop.nx * drop.length
            y2 = drop.y + drop.ny * drop.length
            shape = sl.create_line(
                drop.x, drop.y,
                x2,     y2,
                (_COLOR_R, _COLOR_G, _COLOR_B, drop.alpha),
                line_width=2,
            )
            self._shape_list.append(shape)
        self._dirty = False

    def draw(self) -> None:
        if self._dirty:
            self._rebuild()
        # Overlay gelap ~20% dari efek malam penuh (alpha 51 ≈ 0.2 × 255)
        arcade.draw_lrbt_rectangle_filled(
            0, self._sw, 0, self._sh,
            (0, 0, 0, 51),
        )
        self._shape_list.draw()