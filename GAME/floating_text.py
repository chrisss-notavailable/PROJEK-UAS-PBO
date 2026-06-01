"""
floating_text.py — Sistem Floating Text untuk Farming RPG

Reusable: cukup panggil FloatingTextManager.spawn() dari mana saja.
Tidak ada dependency ke sistem lain.

Penggunaan:
    # setup
    from floating_text import FloatingTextManager, FT
    self._ft = FloatingTextManager()

    # spawn (GUI-space, koordinat layar)
    self._ft.spawn("+3 Carrot", x, y, FT.ITEM)
    self._ft.spawn("+150 Gold", x, y, FT.GOLD)
    self._ft.spawn("Game Saved", x, y, FT.SAVE)
    self._ft.spawn("Sleeping...", x, y, FT.SLEEP)
    self._ft.spawn("Inventory Full!", x, y, FT.ERROR)

    # update & draw (GUI camera aktif)
    self._ft.update(delta_time)
    self._ft.draw()
"""
from __future__ import annotations
import arcade

# ── Durasi & animasi ──────────────────────────────────────────────────────────
_LIFETIME    = 1.8    # total durasi teks hidup (detik)
_FADE_IN     = 0.15   # fade-in di awal (detik)
_FADE_OUT    = 0.55   # fade-out di akhir (detik)
_RISE_SPEED  = 28.0   # kecepatan naik (px/s)
_FONT_SIZE   = 13


class FT:
    """Preset warna. Gunakan sebagai argumen `color` di spawn()."""
    GOLD  = (255, 210,  60, 255)   # kuning — Gold / uang
    ITEM  = (255, 255, 255, 255)   # putih  — item harvest
    SAVE  = ( 90, 220, 100, 255)   # hijau  — game saved
    SLEEP = (180, 200, 255, 255)   # biru muda — sleeping
    ERROR = (255,  80,  80, 255)   # merah  — error / gagal


class _FloatingText:
    """Satu instance teks mengambang. Semua state private."""

    __slots__ = ("text", "x", "y", "_color", "_age")

    def __init__(
        self,
        text:  str,
        x:     float,
        y:     float,
        color: tuple,
    ) -> None:
        self.text    = text
        self.x       = x
        self.y       = y
        self._color  = color   # (R, G, B, A) — alpha di sini diabaikan, dihitung dinamis
        self._age    = 0.0

    @property
    def alive(self) -> bool:
        return self._age < _LIFETIME

    def update(self, dt: float) -> None:
        self._age += dt
        self.y    += _RISE_SPEED * dt

    @property
    def alpha(self) -> int:
        """Hitung opacity: fade-in di awal, fade-out di akhir, penuh di tengah."""
        t = self._age

        # Fade-in
        if t < _FADE_IN:
            return int(255 * (t / _FADE_IN))

        # Fade-out
        fade_start = _LIFETIME - _FADE_OUT
        if t > fade_start:
            progress = (t - fade_start) / _FADE_OUT
            return int(255 * max(0.0, 1.0 - progress))

        return 255


class FloatingTextManager:
    """
    Mengelola koleksi _FloatingText.

    Interface publik:
        spawn(text, x, y, color)  — tampilkan teks baru di posisi GUI
        update(delta_time)         — update semua teks aktif
        draw()                     — gambar semua teks (GUI camera harus aktif)
    """

    def __init__(self) -> None:
        self._texts: list[_FloatingText] = []

    def spawn(
        self,
        text:  str,
        x:     float,
        y:     float,
        color: tuple = FT.ITEM,
    ) -> None:
        """
        Munculkan floating text di posisi layar (GUI-space).

        Args:
            text:  teks yang ditampilkan, contoh "+3 Carrot", "+150 Gold"
            x, y:  koordinat layar (GUI camera)
            color: gunakan konstanta FT.GOLD / FT.ITEM / FT.SAVE / FT.SLEEP / FT.ERROR
                    atau tuple (R, G, B, A) custom
        """
        self._texts.append(_FloatingText(text, x, y, color))

    def update(self, delta_time: float) -> None:
        for ft in self._texts:
            ft.update(delta_time)
        # Bersihkan yang sudah mati
        self._texts = [ft for ft in self._texts if ft.alive]

    def draw(self) -> None:
        for ft in self._texts:
            a = ft.alpha
            if a <= 0:
                continue
            r, g, b = ft._color[:3]
            arcade.draw_text(
                ft.text,
                ft.x,
                ft.y,
                color    = (r, g, b, a),
                font_size = _FONT_SIZE,
                bold      = True,
                anchor_x  = "center",
                anchor_y  = "center",
            )
