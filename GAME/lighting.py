"""
lighting.py — Night Lighting System

Encapsulation: NightLighting menyembunyikan pygame Surface, buffer
half-resolution, dan cache texture di balik satu method publik draw().
Caller tidak perlu tahu detail BLEND_RGBA_MULT, PIL, atau ukuran buffer.

Teknik (half-resolution eraser pipeline):
  1. Shadow buffer diisi overlay gelap (navy, alpha proporsional night_alpha)
  2. Per lampu: eraser surface di-blit dengan BLEND_RGBA_MULT
     → pixel overlay di area lampu menjadi transparan (area terang)
  3. Hasil di-upload ke arcade.Texture dan di-scale 2x ke layar penuh
  4. Warm core circles digambar pure arcade di pusat tiap lampu

Optimasi: shadow texture di-cache dan hanya di-rebuild saat state berubah
(night_alpha, posisi lampu, atau kamera bergerak > 0.5px).
Shadow buffer dibuat setengah resolusi (640×360) → 4× lebih cepat,
blur alami pada gradient.
"""
from __future__ import annotations
import math
import pygame
import arcade
from PIL import Image as PILImage

from constants import SCREEN_WIDTH, SCREEN_HEIGHT

NIGHT_OVERLAY_COLOR = (16, 24, 60, 130)
LAMP_RADIUS         = 150
SHADOW_SCALE        = 2

_LAMP_R_SMALL = LAMP_RADIUS // SHADOW_SCALE


class NightLighting:
    """
    Encapsulation: shadow buffer pygame, eraser surface, dan cache texture
    sepenuhnya private. Satu-satunya interface publik adalah draw().

    Inheritance peluang: jika kelak ada tipe pencahayaan lain (misalnya
    IndoorLighting atau DynamicLighting), NightLighting dapat dijadikan
    subclass dari AbstractLighting dengan method draw() sebagai kontrak.
    """

    def __init__(self) -> None:
        self._sw = SCREEN_WIDTH  // SHADOW_SCALE
        self._sh = SCREEN_HEIGHT // SHADOW_SCALE

        self._shadow_surf = pygame.Surface((self._sw, self._sh), pygame.SRCALPHA)
        self._glow_surf: pygame.Surface = self._make_glow_surf(_LAMP_R_SMALL)

        self._cached_tex:   arcade.Texture | None = None
        self._cache_alpha:  float = -1.0
        self._cache_lamps:  list  = []
        self._cache_cam:    tuple = (-999999.0, -999999.0)

    @staticmethod
    def _make_glow_surf(radius: int) -> pygame.Surface:
        """
        Encapsulation: precompute gradient eraser surface untuk BLEND_RGBA_MULT.

        alpha=0 di pusat → shadow transparan (area terang).
        alpha=255 di tepi → shadow tidak berubah (tetap gelap).
        Falloff kuadratik menghasilkan transisi yang natural.
        """
        size = 2 * radius + 1
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = radius

        for y in range(size):
            for x in range(size):
                dx, dy = x - cx, y - cy
                dist   = math.sqrt(dx * dx + dy * dy)
                if dist >= radius:
                    a = 255
                else:
                    t = dist / radius
                    a = int((t ** 2.0) * 255)
                surf.set_at((x, y), (255, 255, 255, a))

        return surf

    def _needs_rebuild(
        self,
        night_alpha: float,
        lamps: list,
        cam_x: float,
        cam_y: float,
    ) -> bool:
        if self._cached_tex is None:
            return True
        if abs(night_alpha - self._cache_alpha) > 0.005:
            return True
        if lamps != self._cache_lamps:
            return True
        cx, cy = self._cache_cam
        if abs(cam_x - cx) > 0.5 or abs(cam_y - cy) > 0.5:
            return True
        return False

    def _rebuild(
        self,
        night_alpha: float,
        lamps: list,
        cam_x: float,
        cam_y: float,
    ) -> None:
        shadow = self._shadow_surf
        sw, sh = self._sw, self._sh

        r, g, b, base_a = NIGHT_OVERLAY_COLOR
        fill_alpha = int(base_a * night_alpha)
        shadow.fill((r, g, b, fill_alpha))

        half_w = sw / 2
        half_h = sh / 2
        R = _LAMP_R_SMALL

        for (wx, wy) in lamps:
            sx = (wx - cam_x) / SHADOW_SCALE + half_w
            sy = sh - ((wy - cam_y) / SHADOW_SCALE + half_h)

            blit_x = int(sx) - R
            blit_y = int(sy) - R
            shadow.blit(
                self._glow_surf, (blit_x, blit_y),
                special_flags=pygame.BLEND_RGBA_MULT,
            )

        raw = pygame.image.tostring(shadow, "RGBA", False)
        pil = PILImage.frombytes("RGBA", (sw, sh), raw)
        self._cached_tex  = arcade.Texture(pil)
        self._cache_alpha = night_alpha
        self._cache_lamps = list(lamps)
        self._cache_cam   = (cam_x, cam_y)

    def draw(
        self,
        night_alpha: float,
        lamp_world_positions: list[tuple[float, float]],
        cam_x: float,
        cam_y: float,
        screen_w: int,
        screen_h: int,
    ) -> None:
        """
        Gambar night lighting ke layar.

        Dipanggil dari on_draw() setelah semua tile & sprite digambar,
        sebelum gui_camera.use(). night_alpha 0.0 = siang, 1.0 = malam penuh.
        """
        if night_alpha <= 0.001:
            return

        lamps = lamp_world_positions

        if self._needs_rebuild(night_alpha, lamps, cam_x, cam_y):
            self._rebuild(night_alpha, lamps, cam_x, cam_y)

        arcade.draw_texture_rect(
            self._cached_tex,
            arcade.XYWH(cam_x, cam_y, screen_w, screen_h),
            pixelated=True,
        )

        a    = night_alpha
        WARM = [
            (52, int(18 * a), (255, 185,  50)),
            (30, int(45 * a), (255, 210, 100)),
            (15, int(85 * a), (255, 235, 160)),
        ]
        for (wx, wy) in lamps:
            for (r_w, alpha_w, col) in WARM:
                arcade.draw_circle_filled(wx, wy, r_w, (*col, alpha_w))
