"""
main_menu.py — Main Menu State (berjalan di dalam window Arcade yang sama)

Asset: assets/ui/depan/BG_AWAL.png, MENU1.png, MENU2.png, MENU3.png
"""
from __future__ import annotations

import math
import os
import sys

import pygame
import arcade
from PIL import Image as PILImage


# ── RESOLVE PATH ASSET ────────────────────────────────────────────────────────
# Coba beberapa kandidat path, ambil yang pertama berhasil ditemukan.
# Ini menangani semua cara Python dijalankan: dari IDE, terminal, double-click.
def _find_asset_dir() -> str:
    candidates = [
        # 1. Relatif dari lokasi file main_menu.py itu sendiri
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ui", "depan"),
        # 2. Relatif dari CWD saat game dijalankan
        os.path.join(os.getcwd(), "assets", "ui", "depan"),
        # 3. Relatif dari sys.argv[0] (entry point script)
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "assets", "ui", "depan"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    # Tidak ditemukan — kembalikan kandidat pertama dan biarkan error jelas muncul
    return candidates[0]

_ASSET_DIR = _find_asset_dir()
_ASSET_BG   = os.path.join(_ASSET_DIR, "BG_AWAL.png")
_ASSET_M1   = os.path.join(_ASSET_DIR, "MENU1.png")
_ASSET_M2   = os.path.join(_ASSET_DIR, "MENU2.png")
_ASSET_M3   = os.path.join(_ASSET_DIR, "MENU3.png")
_ASSET_NAMA = os.path.join(_ASSET_DIR, "NAMA.png")

# Print segera saat modul di-import


# ── CONVERT PYGAME SURFACE → ARCADE TEXTURE ──────────────────────────────────
def _surf_to_tex(surface: pygame.Surface) -> arcade.Texture:
    raw = pygame.image.tostring(surface, "RGBA", False)
    pil = PILImage.frombytes("RGBA", surface.get_size(), raw)
    return arcade.Texture(pil)


# ── WARNA ─────────────────────────────────────────────────────────────────────
_WHITE     = (255, 255, 255)
_RED_NOTIF = (230,  80,  80)


# ── HELPER ────────────────────────────────────────────────────────────────────
def _ease_out(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ── LOAD ASSET ────────────────────────────────────────────────────────────────
def _load_pg(path: str, size=None, alpha=True) -> pygame.Surface | None:
    try:
        img = pygame.image.load(path)
        # convert_alpha/convert dihapus — butuh video mode aktif, sedangkan
        # asset di-load sebelum Arcade window terbuka. Tidak diperlukan
        # karena rendering lewat Arcade bukan pygame display langsung.
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception as e:
        return None

def _make_hover(img: pygame.Surface | None) -> pygame.Surface | None:
    if img is None:
        return None
    hov = img.copy()
    ov  = pygame.Surface(hov.get_size(), pygame.SRCALPHA)
    ov.fill((255, 255, 255, 60))
    hov.blit(ov, (0, 0))
    return hov


def _remove_black_bg_pil(path: str, threshold: int = 25) -> pygame.Surface | None:
    """
    Load PNG via PIL, hapus background hitam, kembalikan pygame.Surface SRCALPHA.
    Pakai numpy untuk kecepatan (jauh lebih cepat dari pixel-by-pixel).
    """
    try:
        import numpy as np
        pil = PILImage.open(path).convert("RGBA")
        arr = np.array(pil)                     
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        mask = (r.astype(int) < threshold) & \
               (g.astype(int) < threshold) & \
               (b.astype(int) < threshold)
        arr[mask, 3] = 0
        result_pil = PILImage.fromarray(arr, "RGBA")
        raw = result_pil.tobytes()

        if hasattr(pygame.image, "frombytes"):
            surf = pygame.image.frombytes(raw, result_pil.size, "RGBA")
        else:
            surf = pygame.image.fromstring(raw, result_pil.size, "RGBA")
        return surf
    except Exception as e:

        return _load_pg(path)


# ── TOMBOL PNG ────────────────────────────────────────────────────────────────
class _Button:
    def __init__(self, rect, img_normal, img_hover, label: str,
                    slide_delay: float, font: pygame.font.Font):
        self.rect        = pygame.Rect(rect)
        self.img_normal  = img_normal
        self.img_hover   = img_hover
        self.label       = label
        self.slide_delay = slide_delay
        self.font        = font
        self.hovered     = False
        self.hover_t     = 0.0
        self.slide_y     = 80
        self.visible     = False
        self._warned     = False

    def update(self, mouse_pos: tuple, dt: float, entry_t: float) -> None:
        if entry_t >= self.slide_delay:
            progress     = _clamp((entry_t - self.slide_delay) / 0.4, 0.0, 1.0)
            self.slide_y = int((1.0 - _ease_out(progress)) * 80)
            self.visible = True
        r = self.rect.move(0, self.slide_y)
        self.hovered = r.collidepoint(mouse_pos) and self.visible
        target       = 1.0 if self.hovered else 0.0
        self.hover_t += (target - self.hover_t) * 0.15

    def draw(self, surf: pygame.Surface) -> None:
        if not self.visible:
            return
        r   = self.rect.move(0, self.slide_y)
        img = self.img_hover if self.hovered else self.img_normal

        scale = 1.0 + self.hover_t * 0.045
        w = int(r.width  * scale)
        h = int(r.height * scale)
        dx = (w - r.width)  // 2
        dy = (h - r.height) // 2

        if img is not None:
            scaled = pygame.transform.smoothscale(img, (w, h))
            surf.blit(scaled, (r.x - dx, r.y - dy))
        else:
            if not self._warned:
                self._warned = True

    def get_rect(self) -> pygame.Rect:
        return self.rect.move(0, self.slide_y)


# ── NOTIFIKASI ────────────────────────────────────────────────────────────────
class _Notif:
    def __init__(self, font: pygame.font.Font):
        self.font  = font
        self.msg   = ""
        self.alpha = 0
        self.timer = 0.0
        self.state = "idle"

    def show(self, msg: str) -> None:
        self.msg   = msg
        self.alpha = 0
        self.timer = 0.0
        self.state = "fadein"

    def update(self, dt: float) -> None:
        if self.state == "fadein":
            self.alpha = min(255, self.alpha + 20)
            if self.alpha >= 255:
                self.state = "show"
        elif self.state == "show":
            self.timer += dt
            if self.timer >= 2.5:
                self.state = "fadeout"
        elif self.state == "fadeout":
            self.alpha = max(0, self.alpha - 10)
            if self.alpha <= 0:
                self.state = "idle"

    def draw(self, surf: pygame.Surface, w: int, h: int) -> None:
        if self.state == "idle":
            return
        txt = self.font.render(self.msg, True, _RED_NOTIF)
        pad_x, pad_y = 20, 10
        bw = txt.get_width()  + pad_x * 2
        bh = txt.get_height() + pad_y * 2
        bx = w // 2 - bw // 2
        by = h // 2 + 60
        s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(s, (10, 10, 10, self.alpha),  (0, 0, bw, bh), border_radius=8)
        pygame.draw.rect(s, (*_RED_NOTIF, self.alpha), (0, 0, bw, bh), 2, border_radius=8)
        txt.set_alpha(self.alpha)
        s.blit(txt, (pad_x, pad_y))
        surf.blit(s, (bx, by))


# ── FLASH ─────────────────────────────────────────────────────────────────────
class _Flash:
    def __init__(self):
        self.alpha  = 0
        self.active = False

    def trigger(self):
        self.alpha  = 120
        self.active = True

    def update(self):
        if self.active:
            self.alpha -= 10
            if self.alpha <= 0:
                self.alpha  = 0
                self.active = False

    def draw(self, surf: pygame.Surface, w: int, h: int):
        if self.alpha > 0:
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill((255, 255, 255, self.alpha))
            surf.blit(s, (0, 0))


# ══════════════════════════════════════════════════════════════════════════════
# MainMenuState
# ══════════════════════════════════════════════════════════════════════════════
class MainMenuState:

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.screen_width  = screen_width
        self.screen_height = screen_height

        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        try:
            self._font_btn   = pygame.font.SysFont("couriernew", 22, bold=True)
            self._font_notif = pygame.font.SysFont("couriernew", 18, bold=True)
        except Exception:
            self._font_btn   = pygame.font.Font(None, 28)
            self._font_notif = pygame.font.Font(None, 24)

        # ── Debug asset check — hanya sekali saat __init__ ──

        # ── Load asset ──
        self._bg_img = _load_pg(_ASSET_BG, (screen_width, screen_height), alpha=False)
        _img1_raw    = _load_pg(_ASSET_M1)
        _img2_raw    = _load_pg(_ASSET_M2)
        _img3_raw    = _load_pg(_ASSET_M3)

        # NAMA.png memiliki background hitam solid (bukan transparan),
        # jadi gunakan loader khusus yang menghapus pixel hitam → transparan.
        _nama_raw    = _remove_black_bg_pil(_ASSET_NAMA)

        if self._bg_img is None:
            pass
        if _img1_raw is None:
            pass
        if _img2_raw is None:
            pass
        if _img3_raw is None:
            pass
        if _nama_raw is None:
            pass

        # ── Scale NAMA.png agar muat di layar (max 55% lebar layar) ──
        _MAX_NAMA_W = int(screen_width * 0.55)
        if _nama_raw is not None:
            nw, nh = _nama_raw.get_size()
            if nw > _MAX_NAMA_W:
                scale_ratio = _MAX_NAMA_W / nw
                nw = _MAX_NAMA_W
                nh = int(nh * scale_ratio)
                _nama_raw = pygame.transform.smoothscale(_nama_raw, (nw, nh))
            self._nama_img  = _nama_raw
            self._nama_size = (nw, nh)
        else:
            self._nama_img  = None
            self._nama_size = (0, 0)

        # ── Layout tombol vertikal di tengah ──
        def _sz(img):
            return img.get_size() if img is not None else (260, 60)

        sz1 = _sz(_img1_raw)
        sz2 = _sz(_img2_raw)
        sz3 = _sz(_img3_raw)
        szN = self._nama_size

        _GAP      = 16
        _NAMA_GAP = 20   # jarak antara NAMA.png dan tombol PLAY

        # Total tinggi seluruh group (logo + gap + 3 tombol + 2 gap antar tombol)
        _total = szN[1] + _NAMA_GAP + sz1[1] + sz2[1] + sz3[1] + _GAP * 2
        _top   = (screen_height - _total) // 2
        _cx    = screen_width  // 2

        # Posisi NAMA.png — di-center horizontal, di bagian atas group
        self._nama_x = _cx - szN[0] // 2
        self._nama_y = _top

        # Tombol mulai di bawah NAMA.png
        _btn_top = _top + szN[1] + _NAMA_GAP

        rect1 = (_cx - sz1[0] // 2, _btn_top,                               sz1[0], sz1[1])
        rect2 = (_cx - sz2[0] // 2, _btn_top + sz1[1] + _GAP,               sz2[0], sz2[1])
        rect3 = (_cx - sz3[0] // 2, _btn_top + sz1[1] + sz2[1] + _GAP * 2, sz3[0], sz3[1])

        self._buttons = [
            _Button(rect1, _img1_raw, _make_hover(_img1_raw), "PLAY",     0.00, self._font_btn),
            _Button(rect2, _img2_raw, _make_hover(_img2_raw), "NEW GAME", 0.10, self._font_btn),
            _Button(rect3, _img3_raw, _make_hover(_img3_raw), "EXIT",     0.20, self._font_btn),
        ]
        self._btn_actions = ["play", "new_game", "exit"]

        self._notif     = _Notif(self._font_notif)
        self._flash     = _Flash()
        self._entry_t   = 0.0
        self._mouse_pos: tuple = (0, 0)
        self._bg_warned   = False
        self._nama_warned = False

        # ── Animasi slide-in NAMA.png (muncul dari atas) ──
        self._nama_slide_y = -100   # offset awal (di atas posisi normal)
        self._nama_visible = False

        # ── Callbacks ──
        self.on_play_callback     = None
        self.on_new_game_callback = None
        self.on_load_callback     = None   
        self.on_exit_callback     = None

    # ── Public ───────────────────────────────────────────────────────────────

    def show_no_save(self) -> None:
        self._notif.show("No Save Found")

    def on_key_press(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._do_exit()

    def on_mouse_press(self, x: float, y: float) -> None:
        mx, my = int(x), self.screen_height - int(y)
        pos = (mx, my)
        for i, btn in enumerate(self._buttons):
            if btn.get_rect().collidepoint(pos) and btn.visible:
                self._flash.trigger()
                action = self._btn_actions[i]
                if action == "exit":
                    self._do_exit()
                elif action == "play":
                    if self.on_play_callback:
                        self.on_play_callback()
                elif action == "new_game":
                    cb = self.on_new_game_callback or self.on_load_callback
                    if cb:
                        cb()
                return

    def on_mouse_motion(self, x: float, y: float) -> None:
        self._mouse_pos = (int(x), self.screen_height - int(y))

    # ── Internal ─────────────────────────────────────────────────────────────

    def _do_exit(self) -> None:
        if self.on_exit_callback:
            self.on_exit_callback()
        else:
            arcade.exit()

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, delta_time: float) -> None:
        self._entry_t += delta_time

        # ── Animasi slide-in NAMA.png dari atas ──
        progress = _clamp(self._entry_t / 0.45, 0.0, 1.0)
        self._nama_slide_y = int((1.0 - _ease_out(progress)) * -100)
        self._nama_visible = True

        for btn in self._buttons:
            btn.update(self._mouse_pos, delta_time, self._entry_t)
        self._notif.update(delta_time)
        self._flash.update()

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        w = self.screen_width
        h = self.screen_height
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        if self._bg_img is not None:
            surf.blit(self._bg_img, (0, 0))
        else:
            if not self._bg_warned:
                self._bg_warned = True

        for btn in self._buttons:
            btn.draw(surf)

        # ── Gambar NAMA.png (logo judul — bukan tombol, tidak bisa diklik) ──
        if self._nama_visible:
            if self._nama_img is not None:
                draw_y = self._nama_y + self._nama_slide_y
                surf.blit(self._nama_img, (self._nama_x, draw_y))
            else:
                if not self._nama_warned:
                    self._nama_warned = True

        self._notif.draw(surf, w, h)
        self._flash.draw(surf, w, h)

        tex = _surf_to_tex(surf)
        arcade.draw_texture_rect(
            tex,
            arcade.LBWH(0, 0, w, h),
            pixelated=False,
        )
