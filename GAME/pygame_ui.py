"""
pygame_ui.py — Sistem UI Berbasis Pygame

Hierarki Inheritance:
  AbstractSlotContainer (ABC)
    ├── InventoryUI   – grid inventory 5×12 dengan scroll
    └── HotbarUI      – bar 5 slot di bawah layar

  AbstractPopup (ABC)
    ├── SellConfirmUI – popup konfirmasi jual
    └── ShopUI        – popup toko benih

Polymorphism: InventoryUI dan HotbarUI dipanggil seragam via
try_stack() dan try_place_empty() dari GameWindow._auto_fill_item(),
tanpa membedakan jenis container-nya.

Encapsulation: _items, _slot_items, _selected dijaga private;
diakses hanya melalui method publik dan property.
"""
from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod

import pygame
import arcade
from PIL import Image as PILImage


pygame.init()
pygame.font.init()


def surface_to_arcade_texture(surface: pygame.Surface) -> arcade.Texture:
    raw = pygame.image.tostring(surface, "RGBA", False)
    pil = PILImage.frombytes("RGBA", surface.get_size(), raw)
    return arcade.Texture(pil)


# ===========================================================================
# FIndicator
# Encapsulation: tekstur dan sprite dijaga internal
# ===========================================================================

class FIndicator:
    """
    Encapsulation: tekstur, sprite, dan timer animasi pulse dijaga private.
    """

    _PULSE_SPEED: float = 0.08
    _PULSE_AMP  : float = 0.08

    def __init__(self, image_path: str) -> None:
        raw_surface = pygame.image.load(image_path)
        self.texture: arcade.Texture = surface_to_arcade_texture(raw_surface)
        self._sprite = arcade.Sprite()
        self._sprite.texture = self.texture
        self._list = arcade.SpriteList()
        self._list.append(self._sprite)
        self._time: float = 0.0

    @property
    def _scale(self) -> float:
        return 1.0 + abs(math.sin(self._time)) * self._PULSE_AMP

    def draw(self, screen_x: float, screen_y: float) -> None:
        self._time += self._PULSE_SPEED
        self._sprite.center_x = screen_x
        self._sprite.center_y = screen_y
        self._sprite.scale    = self._scale
        self._list.draw(pixelated=True)


# ===========================================================================
# HUD
# ===========================================================================

_HUD_BG_COLOR    : tuple[int, ...] = (0, 0, 0, 110)
_HUD_BORDER_COLOR: tuple[int, ...] = (255, 255, 255, 50)
_HUD_TEXT_COLOR  : tuple[int, ...] = (255, 255, 255, 255)
_HUD_BG_W  : int = 340
_HUD_BG_H  : int = 26
_HUD_PAD_X : int = 6
_HUD_PAD_Y : int = 5


class HUD:
    """
    Encapsulation: tekstur background dan teks dikonstruksi sekali di __init__,
    tidak dibuat ulang setiap frame.
    """

    def __init__(self) -> None:
        surf = pygame.Surface((_HUD_BG_W, _HUD_BG_H), pygame.SRCALPHA)
        surf.fill(_HUD_BG_COLOR)
        pygame.draw.rect(surf, _HUD_BORDER_COLOR, surf.get_rect(), width=1)
        self._bg_texture: arcade.Texture = surface_to_arcade_texture(surf)
        self._text_obj = arcade.Text("", 0, 0, _HUD_TEXT_COLOR, font_size=13)

    def draw(self, text: str, x: float, y: float) -> None:
        arcade.draw_texture_rect(
            self._bg_texture,
            arcade.LBWH(x, y, self._bg_texture.width, self._bg_texture.height),
        )
        self._text_obj.x    = x + _HUD_PAD_X
        self._text_obj.y    = y + _HUD_PAD_Y
        self._text_obj.text = text
        self._text_obj.draw()


# ===========================================================================
# ClockPanel
# Encapsulation: panel texture, font, dan text objects dikonstruksi sekali.
# Semua koordinat dihitung relatif terhadap margin kiri-atas layar.
# ===========================================================================

_CLOCK_PANEL_PATH   : str   = "assets/ui/clock/PANEL.png"
_CLOCK_SUN_PATH     : str   = "assets/ui/clock/SUN.png"
_CLOCK_MOON_PATH    : str   = "assets/ui/clock/MOON.png"
_CLOCK_ICON_SIZE    : int   = 36          # ukuran render icon (px) — 31 * 1.15 ≈ 36
_CLOCK_ICON_GAP     : int   = 7           # jarak icon ke tepi kiri panel (px)
_CLOCK_FONT_PATH    : str   = "assets/fonts/monogram-extended.ttf"
_CLOCK_MARGIN_X     : int   = 20          # px dari tepi kiri layar
_CLOCK_MARGIN_Y     : int   = 20          # px dari tepi atas layar
_CLOCK_PANEL_W      : int   = 150         # lebar render panel di layar (px)
_CLOCK_PANEL_H      : int   = 50          # tinggi render panel di layar (px)
_CLOCK_SIZE_COMBINED: int   = 12          # font size untuk "Wed, 00:00" (satu baris) — 10 * 1.15 ≈ 12
_CLOCK_COLOR_TEXT   : tuple = (60, 30, 5, 255)     # coklat tua — kontras di atas panel emas
_CLOCK_COLOR_SHADOW : tuple = (255, 240, 200, 120)  # highlight terang tipis


def _load_panel_texture(path: str, target_w: int, target_h: int) -> arcade.Texture:
    """
    Load PANEL.png, crop border hitam, buat transparan, scale ke target size.

    PANEL.png adalah RGB (bukan RGBA) — background hitamnya bukan alpha.
    Pipeline:
      1. Buka sebagai RGB via PIL
      2. Deteksi bounding box konten non-hitam
      3. Crop ke bounding box (hilangkan border hitam)
      4. Konversi ke RGBA — pixel hampir hitam (brightness<12) → alpha=0
      5. Scale ke target_w × target_h via LANCZOS
      6. Kembalikan sebagai arcade.Texture

    Ini dilakukan sekali di __init__, tidak per frame.
    """
    import numpy as np

    pil_img = PILImage.open(path).convert("RGB")
    arr     = np.array(pil_img)
    w, h    = pil_img.size


    brightness = arr[:, :, 0].astype(int) + arr[:, :, 1].astype(int) + arr[:, :, 2].astype(int)
    mask       = brightness > 20
    rows       = np.any(mask, axis=1)
    cols       = np.any(mask, axis=0)
    rmin, rmax = int(np.where(rows)[0][0]),  int(np.where(rows)[0][-1])
    cmin, cmax = int(np.where(cols)[0][0]),  int(np.where(cols)[0][-1])


    arr_crop = arr[rmin:rmax + 1, cmin:cmax + 1]

    arr_rgba        = np.zeros((*arr_crop.shape[:2], 4), dtype=np.uint8)
    arr_rgba[:, :, :3] = arr_crop
    bri_crop        = arr_crop[:, :, 0].astype(int) + arr_crop[:, :, 1].astype(int) + arr_crop[:, :, 2].astype(int)
    arr_rgba[:, :, 3]  = np.where(bri_crop < 12, 0, 255).astype(np.uint8)

    pil_rgba = PILImage.fromarray(arr_rgba, "RGBA")

    pil_scaled = pil_rgba.resize((target_w, target_h), PILImage.NEAREST)

    return arcade.Texture(pil_scaled)


class ClockPanel:
    """
    Clock Panel UI — panel kiri atas dengan jam game berjalan otomatis.

    Encapsulation:
      - _panel_tex        : arcade.Texture dari PANEL.png (load sekali)
      - _text_clock       : arcade.Text untuk "Wed, 00:00" (satu baris)
      - _game_hour        : jam game saat ini (0-23)
      - _game_minute      : menit game saat ini (0-59)
      - _game_day         : indeks hari saat ini (0=Sun..6=Sat)
      - _time_accumulator : akumulasi delta_time untuk tick menit
      - _tex_sun          : arcade.Texture dari SUN.png (load sekali)
      - _tex_moon         : arcade.Texture dari MOON.png (load sekali)
      - _icon_sprite      : arcade.Sprite untuk render icon aktif

    Skala waktu:
      1 detik nyata = 1 menit game
      60 detik nyata = 1 jam game
      24 menit nyata = 1 hari game (reset ke 00:00, hari +1)

    Update: panggil update(delta_time) tiap frame dari game loop.
    Render: panggil draw(screen_h) — string waktu dihitung internal.

    PANEL.png: 1536x1024 RGB, crop border hitam, scale ke 150x50px.
    """

    _START_HOUR  : int            = 7       # jam awal game
    _START_MINUTE: int            = 0       # menit awal game
    _START_DAY   : int            = 3       # 0=Sun 1=Mon 2=Tue 3=Wed 4=Thu 5=Fri 6=Sat
    _DAY_NAMES   : tuple[str,...] = ("Sun.", "Mon.", "Tue.", "Wed.", "Thu.", "Fri.", "Sat.")

    def __init__(self) -> None:
        try:
            self._panel_tex: arcade.Texture | None = _load_panel_texture(
                _CLOCK_PANEL_PATH, _CLOCK_PANEL_W, _CLOCK_PANEL_H,
            )
        except Exception as exc:
            self._panel_tex = None

        def _load_icon(path: str, size: int) -> arcade.Texture | None:
            try:
                pil_img = PILImage.open(path).convert("RGBA")
                pil_img = pil_img.resize((size, size), PILImage.NEAREST)
                tex = arcade.Texture(pil_img)
                return tex
            except Exception as exc:
                return None

        self._tex_sun  : arcade.Texture | None = _load_icon(_CLOCK_SUN_PATH,  _CLOCK_ICON_SIZE)
        self._tex_moon : arcade.Texture | None = _load_icon(_CLOCK_MOON_PATH, _CLOCK_ICON_SIZE)

        self._icon_sprite = arcade.Sprite()
        self._icon_list   = arcade.SpriteList()
        self._icon_list.append(self._icon_sprite)

        # Satu baris: "Wed, 00:00"
        # Warna gelap agar kontras di atas permukaan panel yang terang/emas
        common = dict(
            x=0, y=0,
            font_name=_CLOCK_FONT_PATH,
            anchor_x="center",
            anchor_y="center",
        )
        self._text_clock = arcade.Text("Wed, 00:00", color=_CLOCK_COLOR_TEXT,   font_size=_CLOCK_SIZE_COMBINED, **common)
        self._hi_clock   = arcade.Text("Wed, 00:00", color=_CLOCK_COLOR_SHADOW, font_size=_CLOCK_SIZE_COMBINED, **common)

        self._game_hour        : int   = self._START_HOUR
        self._game_minute      : int   = self._START_MINUTE
        self._game_day         : int   = self._START_DAY
        self._time_accumulator : float = 0.0


    # ── Public properties ────────────────────────────────────────────────

    @property
    def game_hour(self) -> int:
        return self._game_hour

    @property
    def game_minute(self) -> int:
        return self._game_minute

    @property
    def game_day(self) -> int:
        return self._game_day

    @property
    def time_str(self) -> str:
        """Format jam:menit untuk display, contoh: '06:05'"""
        return f"{self._game_hour:02d}:{self._game_minute:02d}"

    @property
    def day_str(self) -> str:
        """Nama hari pendek, contoh: 'Wed.'"""
        return self._DAY_NAMES[self._game_day]

    # ── Update (dipanggil tiap frame) ────────────────────────────────────

    def update(self, delta_time: float) -> None:
        """
        Maju waktu game berdasarkan delta_time.

        Skala: 1 detik nyata = 1 menit game.
        Dipanggil dari on_update() atau game loop utama.
        Tidak menggunakan sleep — aman untuk FPS berapa pun.
        """
        self._time_accumulator += delta_time
        while self._time_accumulator >= 1.0:
            self._time_accumulator -= 1.0
            self._game_minute += 1
            if self._game_minute >= 60:
                self._game_minute = 0
                self._game_hour += 1
                if self._game_hour >= 24:
                    self._game_hour = 0
                    self._game_day  = (self._game_day + 1) % 7

    # ── Draw ─────────────────────────────────────────────────────────────

    def draw(
        self,
        screen_h: float,
    ) -> None:
        """
        Render panel + text ke layar.

        Dipanggil dari _draw_hud() setelah gui_camera.use().
        Waktu diambil dari state internal (_game_hour, _game_minute).
        Koordinat Arcade: Y=0 di bawah layar.
        """
        day_str  = self.day_str
        time_str = self.time_str
        pw = _CLOCK_PANEL_W
        ph = _CLOCK_PANEL_H

        panel_left   = float(_CLOCK_MARGIN_X)
        panel_bottom = screen_h - _CLOCK_MARGIN_Y - ph

        if self._panel_tex is not None:
            arcade.draw_texture_rect(
                self._panel_tex,
                arcade.LBWH(panel_left, panel_bottom, pw, ph),
            )

        # ── 2. Draw icon SUN / MOON di kiri panel ────────────────────────
        # Icon center X = panel_left - icon_gap - icon_size/2
        # Icon center Y = panel_center_y (sejajar tengah panel)
        is_night = self._game_hour >= 19 or self._game_hour < 7
        icon_tex = self._tex_moon if is_night else self._tex_sun
        if icon_tex is not None:
            icon_cx = panel_left - _CLOCK_ICON_GAP - _CLOCK_ICON_SIZE / 2.0 + 55
            icon_cy = panel_bottom + ph / 2.0 + 2
            self._icon_sprite.texture  = icon_tex
            self._icon_sprite.center_x = icon_cx
            self._icon_sprite.center_y = icon_cy
            self._icon_sprite.width    = _CLOCK_ICON_SIZE
            self._icon_sprite.height   = _CLOCK_ICON_SIZE
            self._icon_list.draw(pixelated=True)

        # Satu baris: "Wed, 00:00" — di-center horizontal & vertical panel.
        #
        #   ┌────────────────┐
        #   │ ☀ Wed, 12:00  │
        #   └────────────────┘
        clock_text     = f"{day_str.rstrip('.')}, {time_str}"
        cx             = panel_left + pw / 2.0 + 8   # geser sedikit ke kanan, beri ruang icon
        panel_center_y = panel_bottom + ph / 2.0

        self._hi_clock.text = clock_text
        self._hi_clock.x    = cx - 1
        self._hi_clock.y    = panel_center_y + 4
        self._hi_clock.draw()

        self._text_clock.text = clock_text
        self._text_clock.x    = cx
        self._text_clock.y    = panel_center_y + 4
        self._text_clock.draw()


# ===========================================================================
# GoldHUD
# Encapsulation: saldo gold dijaga via property, diubah via add_gold/remove_gold
# ===========================================================================

class GoldHUD:
    """
    Encapsulation: _gold hanya diakses via property gold,
    diubah via add_gold() dan remove_gold().
    """

    _ICON_SIZE   : int   = 40
    _FONT_SIZE   : int   = 20
    _ICON_GAP    : int   = 8
    _MARGIN_X    : float = 18.0
    _MARGIN_Y    : float = 18.0
    _TEXT_COLOR  : tuple[int, ...] = (255, 224, 64, 255)
    _OUTLINE_COLOR: tuple[int, ...] = (60, 30, 0, 220)

    @staticmethod
    def _load_coin_texture(path: str, icon_size: int) -> arcade.Texture:
        img = PILImage.open(path).convert("RGB")
        w, h = img.size
        r, g, b = img.split()

        def _threshold(px: int) -> int:
            return 255 if px > 10 else 0

        r_mask = r.point(_threshold)
        g_mask = g.point(_threshold)
        b_mask = b.point(_threshold)

        from PIL import ImageChops
        mask = ImageChops.lighter(ImageChops.lighter(r_mask, g_mask), b_mask)
        bbox = mask.getbbox()
        if bbox is None:
            bbox = (0, 0, w, h)

        pad = 8
        left  = max(0, bbox[0] - pad)
        upper = max(0, bbox[1] - pad)
        right = min(w, bbox[2] + pad)
        lower = min(h, bbox[3] + pad)
        cropped = img.crop((left, upper, right, lower))

        cropped_rgba = cropped.convert("RGBA")
        r_ch, g_ch, b_ch, _ = cropped_rgba.split()
        lut = [min(255, max(0, (i - 5) * 6)) for i in range(256)]
        a_from_r = r_ch.point(lut)
        a_from_g = g_ch.point(lut)
        a_from_b = b_ch.point(lut)
        from PIL import ImageChops as _IC
        alpha_ch = _IC.lighter(_IC.lighter(a_from_r, a_from_g), a_from_b)
        cropped_rgba.putalpha(alpha_ch)

        result = cropped_rgba.resize((icon_size, icon_size), PILImage.NEAREST)
        return arcade.Texture(result)

    def __init__(self) -> None:
        self._tex_icon   : arcade.Texture | None = None
        self._icon_sprite: arcade.Sprite  | None = None
        self._icon_list  : arcade.SpriteList | None = None

        try:
            self._tex_icon   = self._load_coin_texture("assets/ui/GOLD.png", self._ICON_SIZE)
            self._icon_sprite = arcade.Sprite()
            self._icon_sprite.texture = self._tex_icon
            self._icon_sprite.scale   = 1.0
            self._icon_list = arcade.SpriteList()
            self._icon_list.append(self._icon_sprite)
        except Exception as exc:
            pass

        self._gold: int = 100

    def add_gold(self, amount: int) -> None:
        self._gold += max(0, amount)

    def remove_gold(self, amount: int) -> None:
        self._gold = max(0, self._gold - amount)

    @property
    def gold(self) -> int:
        return self._gold

    def draw(self, screen_w: float, screen_h: float) -> None:
        label = str(self._gold)
        half  = self._ICON_SIZE / 2.0

        tmp    = arcade.Text(label, 0, 0, self._TEXT_COLOR, font_size=self._FONT_SIZE)
        text_w = tmp.content_width

        right_x  = screen_w - self._MARGIN_X
        center_y = screen_h - self._MARGIN_Y - half

        if self._icon_list is not None:
            widget_w = self._ICON_SIZE + self._ICON_GAP + text_w
            icon_cx  = right_x - widget_w + half
            text_x   = icon_cx + half + self._ICON_GAP
        else:
            label  = f"GOLD: {label}"
            text_x = right_x - text_w

        text_y = center_y + 4

        if self._icon_list is not None:
            self._icon_sprite.center_x = icon_cx
            self._icon_sprite.center_y = center_y
            self._icon_list.draw(pixelated=True)

        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            arcade.draw_text(
                label,
                text_x + dx, text_y + dy,
                self._OUTLINE_COLOR,
                font_size=self._FONT_SIZE,
                bold=True,
                anchor_x="left", anchor_y="center",
            )

        arcade.draw_text(
            label,
            text_x, text_y,
            self._TEXT_COLOR,
            font_size=self._FONT_SIZE,
            bold=True,
            anchor_x="left", anchor_y="center",
        )


# ===========================================================================
# Helper functions (private module-level)
# ===========================================================================

def _split_long_word(word: str) -> tuple[str, str]:
    VOWELS = set('aeiouAEIOU')
    n      = len(word)
    mid    = n // 2
    best = mid
    for offset in range(0, mid):
        for sign in (1, -1):
            pos = mid + sign * offset
            if pos < 3 or pos > n - 2:
                continue
            if word[pos - 1] not in VOWELS and word[pos - 2] in VOWELS:
                best = pos
                break
        else:
            continue
        break
    return (word[:best] + '-', word[best:])


_FLOWER_SEEDS: frozenset[str] = frozenset({
    "DAISY_SEED", "TULIP_SEED", "ROSE_SEED",
    "LAVENDER_SEED", "SUNFLOWER_SEED", "LILY_SEED",
})

_MAX_FLOWER_CHARS = 5


def _flower_lines(flower_name: str, qty: int) -> tuple[str, str, str]:
    """
    Format flower seed name with max 5 chars per line.
    If name <= 5 chars: (name, "Seed", "xN")
    If name >  5 chars: (name[:5]+"-", name[5:], "Seed xN")
    """
    if len(flower_name) <= _MAX_FLOWER_CHARS:
        return (flower_name, "Seed", f"x{qty}")
    else:
        part1 = flower_name[:_MAX_FLOWER_CHARS] + "-"
        part2 = flower_name[_MAX_FLOWER_CHARS:]
        return (part1, part2, f"Seed x{qty}")


def _slot_lines(name: str, qty: int, weight: float = 0.0) -> tuple[str, str, str]:
    if name.endswith('_SEED'):
        base  = name[:-5].replace('_', ' ').title()
        words = base.split()
        if len(words) == 1 and len(base) > 9:
            part1, part2 = _split_long_word(base)
            l1 = part1
            l2 = part2 + ' Seed'
        elif len(words) == 1:
            l1 = base
            l2 = 'Seed'
        else:
            l1 = ' '.join(words[:-1])
            l2 = words[-1] + ' Seed'
        return (l1, l2, f'x{qty}')

    words = name.split()
    if len(words) == 1:
        w = words[0]
        if len(w) <= 9:
            l1, l2 = w, ''
        else:
            l1, l2 = _split_long_word(w)
    elif len(words) == 2:
        l1, l2 = words[0], words[1]
    else:
        best_split = 1
        best_diff  = abs(len(' '.join(words[:1])) - len(' '.join(words[1:])))
        for i in range(2, len(words)):
            diff = abs(len(' '.join(words[:i])) - len(' '.join(words[i:])))
            if diff < best_diff:
                best_diff  = diff
                best_split = i
        l1 = ' '.join(words[:best_split])
        l2 = ' '.join(words[best_split:])

    if weight > 0.0:
        info = f'{weight:.1f}kg x{qty}'
    else:
        info = f'x{qty}'
    return (l1, l2, info)


def _wrap_item_label(name: str) -> tuple[str, str]:
    words = name.split()
    if len(words) == 1:
        return (name, "")
    if len(words) == 2:
        return (words[0], words[1])
    best_split = 1
    best_diff  = abs(len(" ".join(words[:1])) - len(" ".join(words[1:])))
    for i in range(2, len(words)):
        diff = abs(len(" ".join(words[:i])) - len(" ".join(words[i:])))
        if diff < best_diff:
            best_diff  = diff
            best_split = i
    return (" ".join(words[:best_split]), " ".join(words[best_split:]))


def _make_item(name: str, qty: int = 1, weight: float = 0.0) -> dict:
    return {"name": name, "qty": qty, "weight": weight}


def _try_stack(slots: list[dict | None], name: str, weight: float = 0.0) -> bool:
    """
    Stack item jika nama sama.
    Untuk item ikan (weight > 0): hanya stack jika weight juga sama persis.
    """
    for slot in slots:
        if slot is None:
            continue
        if slot["name"] != name:
            continue
        slot_weight = slot.get("weight", 0.0)
        if weight > 0.0:
            if abs(slot_weight - weight) < 1e-9:
                slot["qty"] += 1
                return True
        else:
            slot["qty"] += 1
            return True
    return False


def _first_empty(slots: list[dict | None]) -> int | None:
    for i, slot in enumerate(slots):
        if slot is None:
            return i
    return None


# ===========================================================================
# AbstractSlotContainer
# Abstraction: kontrak umum untuk InventoryUI dan HotbarUI
# Polymorphism: add_item(), try_stack(), try_place_empty() dipanggil seragam
# ===========================================================================

class AbstractSlotContainer(ABC):
    """
    Abstract Base Class untuk semua UI container slot.

    Abstraction: mendefinisikan interface add_item(), try_stack(),
    try_place_empty() tanpa detail implementasi grid/layout.

    Polymorphism: GameWindow bisa memanggil container.add_item(name)
    tanpa perlu tahu apakah itu InventoryUI atau HotbarUI.
    """

    @abstractmethod
    def try_stack(self, name: str, weight: float = 0.0) -> bool:
        """Coba stack item ke slot yang sudah berisi item dengan nama sama."""

    @abstractmethod
    def try_place_empty(self, name: str, weight: float = 0.0) -> bool:
        """Coba tempatkan item ke slot kosong pertama."""

    def add_item(self, name: str, weight: float = 0.0) -> None:
        """
        Polymorphism: implementasi default yang bekerja untuk semua
        subclass — coba stack dulu, lalu tempatkan di slot kosong.
        """
        if not self.try_stack(name, weight):
            self.try_place_empty(name, weight)

    @abstractmethod
    def clear_selection(self) -> None:
        """Batalkan seleksi slot aktif."""

    @abstractmethod
    def draw(self, screen_w: float, screen_h: float, mouse_x: float, mouse_y: float) -> None:
        """Render container ke layar."""


# ===========================================================================
# InventoryUI
# Inheritance: mewarisi AbstractSlotContainer
# Encapsulation: _items, _selected, _scroll_row dijaga private
# ===========================================================================

class InventoryUI(AbstractSlotContainer):
    """
    Inheritance: mewarisi AbstractSlotContainer.

    Encapsulation: _items diakses via add_item(), try_stack(),
    remove_selected_item(); _selected diakses via property.
    """

    _COLS        : int   = 5
    _ROWS        : int   = 12
    _VISIBLE_ROWS: int   = 4
    _BG_SCALE    : float = 1.0
    _SLOT_SIZE   : int   = 44
    _SLOT_PAD    : int   = 10
    _PANEL_TITLE_H : int   = 56
    _PANEL_BOT_PAD : int   = 40
    _PANEL_SIDE_PAD: int   = 26
    _PANEL_OFFSET_Y: float = 12.0

    def __init__(self) -> None:
        def _load(path: str) -> arcade.Texture:
            surf = pygame.image.load(path)
            return surface_to_arcade_texture(surf)

        self._tex_bg       = _load("assets/ui/inventory/BG_INVEN2.png")
        self._tex_empty    = _load("assets/ui/inventory/EMPTY2.png")
        self._tex_hover    = _load("assets/ui/inventory/HOVER2.png")
        self._tex_selected = _load("assets/ui/inventory/SELECTED2.png")

        self._selected   : int | None = None
        self._scroll_row : int        = 0

        self._scale_empty    : float = self._SLOT_SIZE / self._tex_empty.width
        self._scale_hover    : float = self._SLOT_SIZE / self._tex_hover.width
        self._scale_selected : float = self._SLOT_SIZE / self._tex_selected.width

        self._bg_sprite = arcade.Sprite()
        self._bg_sprite.texture = self._tex_bg
        self._bg_list = arcade.SpriteList()
        self._bg_list.append(self._bg_sprite)

        self._slot_sprites: list[arcade.Sprite] = []
        self._slot_list = arcade.SpriteList()
        for _ in range(self._COLS * self._VISIBLE_ROWS):
            s = arcade.Sprite()
            s.texture = self._tex_empty
            s.scale   = self._scale_empty
            self._slot_list.append(s)
            self._slot_sprites.append(s)

        self._sel_sprites: list[arcade.Sprite] = []
        self._sel_list = arcade.SpriteList()
        for _ in range(self._COLS * self._VISIBLE_ROWS):
            s = arcade.Sprite()
            s.texture = self._tex_selected
            s.scale   = self._scale_selected
            s.alpha   = 0
            self._sel_list.append(s)
            self._sel_sprites.append(s)

        self._hov_sprites: list[arcade.Sprite] = []
        self._hov_list = arcade.SpriteList()
        for _ in range(self._COLS * self._VISIBLE_ROWS):
            s = arcade.Sprite()
            s.texture = self._tex_hover
            s.scale   = self._scale_hover
            s.alpha   = 0
            self._hov_list.append(s)
            self._hov_sprites.append(s)

        self._items: list[dict | None] = [None] * 60

    def clear_selection(self) -> None:
        self._selected = None

    def remove_selected_item(self) -> dict | None:
        if self._selected is None or self._selected >= len(self._items):
            return None
        item = self._items[self._selected]
        self._items[self._selected] = None
        self._selected = None
        return item

    def add_existing_item(self, item: dict) -> None:
        idx = _first_empty(self._items)
        if idx is not None:
            self._items[idx] = item

    def swap_with_selected(self, item: dict) -> dict | None:
        if self._selected is None or self._selected >= len(self._items):
            return None
        old_item = self._items[self._selected]
        self._items[self._selected] = item
        self._selected = None
        return old_item

    def place_in_selected_empty(self, item: dict) -> bool:
        if self._selected is None or self._selected >= len(self._items):
            return False
        if self._items[self._selected] is not None:
            return False
        self._items[self._selected] = item
        self._selected = None
        return True

    def _step(self) -> int:
        return self._SLOT_SIZE + self._SLOT_PAD

    def _panel_rect(self, screen_w: float, screen_h: float) -> tuple[float, float, float, float]:
        tex_w = float(self._tex_bg.width)  * self._BG_SCALE
        tex_h = float(self._tex_bg.height) * self._BG_SCALE
        cx    = screen_w / 2.0
        cy    = screen_h / 2.0 + self._PANEL_OFFSET_Y
        left   = cx - tex_w / 2.0
        bottom = cy - tex_h / 2.0
        return (left, bottom, tex_w, tex_h)

    def _grid_origin(self, screen_w: float, screen_h: float) -> tuple[float, float]:
        step           = self._step()
        grid_w         = self._COLS         * step - self._SLOT_PAD
        grid_h         = self._VISIBLE_ROWS * step - self._SLOT_PAD
        left, bottom, tex_w, tex_h = self._panel_rect(screen_w, screen_h)
        usable_cx = left + self._PANEL_SIDE_PAD + (tex_w - self._PANEL_SIDE_PAD * 2) / 2.0
        usable_cy = bottom + self._PANEL_BOT_PAD + (tex_h - self._PANEL_TITLE_H - self._PANEL_BOT_PAD) / 2.0
        origin_x  = usable_cx - grid_w / 2.0
        origin_y  = usable_cy - grid_h / 2.0
        return (origin_x, origin_y)

    def _compute_slot_centers(self, screen_w: float, screen_h: float) -> list[tuple[float, float]]:
        step              = self._step()
        origin_x, origin_y = self._grid_origin(screen_w, screen_h)
        half              = self._SLOT_SIZE / 2.0
        centers: list[tuple[float, float]] = []
        for row in range(self._VISIBLE_ROWS):
            for col in range(self._COLS):
                cx = origin_x + col * step + half
                cy = origin_y + row * step + half
                centers.append((cx, cy))
        return centers

    def _hit_slot(self, mx: float, my: float, screen_w: float, screen_h: float) -> int | None:
        half = self._SLOT_SIZE / 2.0
        for vis_i, (cx, cy) in enumerate(self._compute_slot_centers(screen_w, screen_h)):
            if (cx - half) <= mx <= (cx + half) and (cy - half) <= my <= (cy + half):
                return self._scroll_row * self._COLS + vis_i
        return None

    def on_scroll(self, scroll_y: float) -> None:
        max_row = max(0, self._ROWS - self._VISIBLE_ROWS)
        if scroll_y > 0:
            self._scroll_row = max(0, self._scroll_row - 1)
        elif scroll_y < 0:
            self._scroll_row = min(max_row, self._scroll_row + 1)

    def try_stack(self, name: str, weight: float = 0.0) -> bool:
        return _try_stack(self._items, name, weight)

    def try_place_empty(self, name: str, weight: float = 0.0) -> bool:
        idx = _first_empty(self._items)
        if idx is not None:
            self._items[idx] = _make_item(name, weight=weight)
            return True
        return False

    @property
    def selected_item_name(self) -> str | None:
        if self._selected is None:
            return None
        if self._selected < len(self._items):
            item = self._items[self._selected]
            return item["name"] if item is not None else None
        return None

    def on_mouse_press(self, mx: float, my: float, screen_w: float, screen_h: float) -> None:
        slot = self._hit_slot(mx, my, screen_w, screen_h)
        if slot is not None:
            self._selected = None if self._selected == slot else slot

    def _bg_scale(self, screen_w: float, screen_h: float) -> float:
        return self._BG_SCALE

    def draw(self, screen_w: float, screen_h: float, mouse_x: float, mouse_y: float) -> None:
        bg_sc = self._bg_scale(screen_w, screen_h)
        self._bg_sprite.center_x = screen_w / 2.0
        self._bg_sprite.center_y = screen_h / 2.0 + self._PANEL_OFFSET_Y
        self._bg_sprite.scale    = bg_sc
        self._bg_list.draw(pixelated=True)

        centers = self._compute_slot_centers(screen_w, screen_h)
        hovered = self._hit_slot(mouse_x, mouse_y, screen_w, screen_h)

        for vis_i, (cx, cy) in enumerate(centers):
            s = self._slot_sprites[vis_i]
            s.center_x = cx
            s.center_y = cy
        self._slot_list.draw(pixelated=True)

        for vis_i, (cx, cy) in enumerate(centers):
            abs_i = self._scroll_row * self._COLS + vis_i
            s = self._sel_sprites[vis_i]
            s.center_x = cx
            s.center_y = cy
            s.alpha    = 255 if abs_i == self._selected else 0
        self._sel_list.draw(pixelated=True)

        for vis_i, (cx, cy) in enumerate(centers):
            abs_i = self._scroll_row * self._COLS + vis_i
            s = self._hov_sprites[vis_i]
            s.center_x = cx
            s.center_y = cy
            s.alpha    = 255 if abs_i == hovered else 0
        self._hov_list.draw(pixelated=True)

        if self._ROWS > self._VISIBLE_ROWS:
            step        = self._step()
            max_row     = self._ROWS - self._VISIBLE_ROWS
            origin_x, origin_y = self._grid_origin(screen_w, screen_h)
            grid_w      = self._COLS         * step - self._SLOT_PAD
            grid_h      = self._VISIBLE_ROWS * step - self._SLOT_PAD
            track_h     = float(grid_h)
            pan_left, pan_bot, pan_w, pan_h = self._panel_rect(screen_w, screen_h)
            track_cx    = pan_left + pan_w - self._PANEL_SIDE_PAD / 2.0
            track_cy    = origin_y + grid_h / 2.0

            arcade.draw_rect_filled(
                arcade.XYWH(track_cx, track_cy, 6, track_h),
                (55, 35, 15, 150),
            )

            thumb_h  = (self._VISIBLE_ROWS / self._ROWS) * track_h
            travel   = track_h - thumb_h
            progress = self._scroll_row / max_row if max_row > 0 else 0.0
            thumb_cy = (origin_y + grid_h) - thumb_h / 2.0 - progress * travel

            arcade.draw_rect_filled(
                arcade.XYWH(track_cx, thumb_cy, 6, thumb_h),
                (210, 165, 80, 240),
            )

        _FONT_NAME = 7
        _FONT_QTY  = 6
        _LINE_H    = 9.0
        _LINE_H_Q  = 8.0
        _GAP       = 2.0
        _FONT      = "assets/fonts/monogram-extended.ttf"
        _SHD       = (0, 0, 0, 130)
        _MAX_CHARS = 12   # karakter maksimal sebelum truncate

        for vis_i, (cx, cy) in enumerate(centers):
            abs_i = self._scroll_row * self._COLS + vis_i
            if abs_i < len(self._items) and self._items[abs_i] is not None:
                item   = self._items[abs_i]
                weight = item.get("weight", 0.0)
                iname  = item["name"]
                qty    = item.get("qty", 1)

                if iname in _FLOWER_SEEDS:
                    flower_name = iname[:-5].replace("_", " ").replace(" Flower", "").replace("Flower ", "").strip().title().split()[0]
                    fl1, fl2, info = _flower_lines(flower_name, qty)
                    total_h   = _LINE_H + _LINE_H + _GAP + _LINE_H_Q
                    block_top = cy + total_h / 2.0
                    l1_y      = block_top - _LINE_H / 2.0
                    l2_y      = l1_y - _LINE_H
                    qty_y     = l2_y - _LINE_H / 2.0 - _GAP - _LINE_H_Q / 2.0
                    arcade.draw_text(fl1,  cx + 1, l1_y - 1, _SHD,               font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(fl1,  cx,     l1_y,     (255, 255, 255, 245), font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(fl2,  cx + 1, l2_y - 1, _SHD,               font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(fl2,  cx,     l2_y,     (255, 255, 255, 225), font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(info, cx + 1, qty_y - 1, _SHD,               font_size=_FONT_QTY,  font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(info, cx,     qty_y,     (210, 185, 80, 210), font_size=_FONT_QTY,  font_name=_FONT, anchor_x="center", anchor_y="center")
                else:
                    raw = iname
                    if raw.endswith("_SEED"):
                        base_seed = raw[:-5].replace("_", " ").title()
                        label = base_seed + " Seed"
                    else:
                        label = raw.replace("_", " ").title()
                    label = label if len(label) <= _MAX_CHARS else label[:_MAX_CHARS - 2].rstrip() + ".."
                    info = f"{weight:.1f}kg x{qty}" if weight > 0.0 else f"x{qty}"
                    total_h   = _LINE_H + _GAP + _LINE_H_Q
                    block_top = cy + total_h / 2.0
                    l1_y      = block_top - _LINE_H / 2.0
                    qty_y     = l1_y - _LINE_H / 2.0 - _GAP - _LINE_H_Q / 2.0
                    arcade.draw_text(label, cx + 1, l1_y - 1, _SHD,               font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(label, cx,     l1_y,     (255, 255, 255, 245), font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(info,  cx + 1, qty_y - 1, _SHD,               font_size=_FONT_QTY,  font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(info,  cx,     qty_y,     (210, 185, 80, 210), font_size=_FONT_QTY,  font_name=_FONT, anchor_x="center", anchor_y="center")


# ===========================================================================
# HotbarUI
# Inheritance: mewarisi AbstractSlotContainer
# Encapsulation: _slot_items, _selected_slot dijaga private
# ===========================================================================

class HotbarUI(AbstractSlotContainer):
    """
    Inheritance: mewarisi AbstractSlotContainer.

    Encapsulation: _slot_items hanya diakses via try_stack(),
    try_place_empty(), assign_item(), remove_selected_item().
    """

    _SLOTS     : int   = 5
    _SLOT_SIZE : int   = 58
    _SLOT_PAD  : int   = 8
    _PANEL_PAD_X: int  = 23
    _PANEL_PAD_Y: int  = 14
    _MARGIN_Y  : float = 12.0

    def __init__(self) -> None:
        def _load(path: str) -> arcade.Texture:
            surf = pygame.image.load(path)
            return surface_to_arcade_texture(surf)

        self._tex_bg       = _load("assets/ui/inventory/HOTBAR_BG2.png")
        self._tex_empty    = _load("assets/ui/inventory/EMPTY2.png")
        self._tex_hover    = _load("assets/ui/inventory/HOVER2.png")
        self._tex_selected = _load("assets/ui/inventory/SELECTED2.png")

        self._selected_slot: int | None        = None
        self._slot_items   : list[dict | None] = [None] * self._SLOTS

        self._scale_empty    : float = self._SLOT_SIZE / self._tex_empty.width
        self._scale_hover    : float = self._SLOT_SIZE / self._tex_hover.width
        self._scale_selected : float = self._SLOT_SIZE / self._tex_selected.width

        self._bg_sprite = arcade.Sprite()
        self._bg_sprite.texture = self._tex_bg
        self._bg_list = arcade.SpriteList()
        self._bg_list.append(self._bg_sprite)

        self._slot_sprites: list[arcade.Sprite] = []
        self._slot_list = arcade.SpriteList()
        for _ in range(self._SLOTS):
            s = arcade.Sprite()
            s.texture = self._tex_empty
            s.scale   = self._scale_empty
            self._slot_list.append(s)
            self._slot_sprites.append(s)

        self._sel_sprites: list[arcade.Sprite] = []
        self._sel_list = arcade.SpriteList()
        for _ in range(self._SLOTS):
            s = arcade.Sprite()
            s.texture = self._tex_selected
            s.scale   = self._scale_selected
            s.alpha   = 0
            self._sel_list.append(s)
            self._sel_sprites.append(s)

        self._hov_sprites: list[arcade.Sprite] = []
        self._hov_list = arcade.SpriteList()
        for _ in range(self._SLOTS):
            s = arcade.Sprite()
            s.texture = self._tex_hover
            s.scale   = self._scale_hover
            s.alpha   = 0
            self._hov_list.append(s)
            self._hov_sprites.append(s)

    def clear_selection(self) -> None:
        self._selected_slot = None

    def select_slot(self, index: int) -> None:
        if 0 <= index < self._SLOTS:
            self._selected_slot = index

    def assign_item(self, slot: int, item: dict) -> dict | None:
        if not (0 <= slot < self._SLOTS):
            return None
        old_item = self._slot_items[slot]
        self._slot_items[slot] = {
            "name":   item["name"],
            "qty":    item["qty"],
            "weight": item.get("weight", 0.0),
        }
        return old_item

    def remove_selected_item(self) -> dict | None:
        if self._selected_slot is None:
            return None
        item = self._slot_items[self._selected_slot]
        self._slot_items[self._selected_slot] = None
        return item

    def get_slot_at(self, mx: float, my: float, screen_w: float, screen_h: float) -> int | None:
        return self._hit_slot(mx, my, screen_w, screen_h)

    def try_stack(self, name: str, weight: float = 0.0) -> bool:
        return _try_stack(self._slot_items, name, weight)

    def try_place_empty(self, name: str, weight: float = 0.0) -> bool:
        idx = _first_empty(self._slot_items)
        if idx is not None:
            self._slot_items[idx] = _make_item(name, weight=weight)
            return True
        return False

    def on_mouse_press(self, mx: float, my: float, screen_w: float, screen_h: float) -> None:
        slot = self._hit_slot(mx, my, screen_w, screen_h)
        if slot is not None:
            self._selected_slot = None if self._selected_slot == slot else slot

    @property
    def selected_slot(self) -> int | None:
        return self._selected_slot

    def _step(self) -> int:
        return self._SLOT_SIZE + self._SLOT_PAD

    def _panel_display_h(self) -> float:
        return float(self._SLOT_SIZE + self._PANEL_PAD_Y * 2)

    def _panel_center_y(self) -> float:
        return self._MARGIN_Y + self._panel_display_h() / 2.0

    def _slot_center_y(self) -> float:
        return self._panel_center_y()

    def _bg_scale(self) -> tuple[float, float]:
        step   = self._step()
        grid_w = self._SLOTS * step - self._SLOT_PAD
        target_w = float(grid_w + self._PANEL_PAD_X * 2)
        target_h = float(self._SLOT_SIZE + self._PANEL_PAD_Y * 2)
        sx = target_w / self._tex_bg.width
        sy = target_h / self._tex_bg.height
        return (sx, sy)

    def _compute_slot_centers(self, screen_w: float, screen_h: float) -> list[tuple[float, float]]:
        step      = self._step()
        grid_w    = self._SLOTS * step - self._SLOT_PAD
        grid_left = screen_w / 2.0 - grid_w / 2.0
        slot_cy   = self._slot_center_y()
        half      = self._SLOT_SIZE / 2.0
        centers: list[tuple[float, float]] = []
        for col in range(self._SLOTS):
            cx = grid_left + col * step + half
            centers.append((cx, slot_cy))
        return centers

    def _hit_slot(self, mx: float, my: float, screen_w: float, screen_h: float) -> int | None:
        half = self._SLOT_SIZE / 2.0
        for i, (cx, cy) in enumerate(self._compute_slot_centers(screen_w, screen_h)):
            if (cx - half) <= mx <= (cx + half) and (cy - half) <= my <= (cy + half):
                return i
        return None

    def draw(self, screen_w: float, screen_h: float, mouse_x: float, mouse_y: float) -> None:
        sx, sy = self._bg_scale()
        self._bg_sprite.center_x = screen_w / 2.0
        self._bg_sprite.center_y = self._panel_center_y()
        self._bg_sprite.scale_x  = sx
        self._bg_sprite.scale_y  = sy
        self._bg_list.draw(pixelated=True)

        centers = self._compute_slot_centers(screen_w, screen_h)
        hovered = self._hit_slot(mouse_x, mouse_y, screen_w, screen_h)

        for i, (cx, cy) in enumerate(centers):
            s = self._slot_sprites[i]
            s.center_x = cx
            s.center_y = cy
        self._slot_list.draw(pixelated=True)

        for i, (cx, cy) in enumerate(centers):
            s = self._hov_sprites[i]
            s.center_x = cx
            s.center_y = cy
            s.alpha    = 255 if i == hovered else 0
        self._hov_list.draw(pixelated=True)

        for i, (cx, cy) in enumerate(centers):
            s = self._sel_sprites[i]
            s.center_x = cx
            s.center_y = cy
            s.alpha    = 255 if i == self._selected_slot else 0
        self._sel_list.draw(pixelated=True)

        _FONT_NAME = 7
        _FONT_QTY  = 6
        _LINE_H    = 9.0
        _LINE_H_Q  = 8.0
        _GAP       = 2.0
        _FONT      = "assets/fonts/monogram-extended.ttf"
        _SHD       = (0, 0, 0, 130)
        _MAX_CHARS = 12

        for i, (cx, cy) in enumerate(centers):
            item = self._slot_items[i]
            if item is not None:
                weight = item.get("weight", 0.0)
                iname  = item["name"]
                qty    = item.get("qty", 1)

                if iname in _FLOWER_SEEDS:
                    flower_name = iname[:-5].replace("_", " ").replace(" Flower", "").replace("Flower ", "").strip().title().split()[0]
                    fl1, fl2, info = _flower_lines(flower_name, qty)
                    total_h   = _LINE_H + _LINE_H + _GAP + _LINE_H_Q
                    block_top = cy + total_h / 2.0
                    l1_y      = block_top - _LINE_H / 2.0
                    l2_y      = l1_y - _LINE_H
                    qty_y     = l2_y - _LINE_H / 2.0 - _GAP - _LINE_H_Q / 2.0
                    arcade.draw_text(fl1,  cx + 1, l1_y - 1, _SHD,               font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(fl1,  cx,     l1_y,     (255, 255, 255, 245), font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(fl2,  cx + 1, l2_y - 1, _SHD,               font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(fl2,  cx,     l2_y,     (255, 255, 255, 225), font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(info, cx + 1, qty_y - 1, _SHD,               font_size=_FONT_QTY,  font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(info, cx,     qty_y,     (210, 185, 80, 210), font_size=_FONT_QTY,  font_name=_FONT, anchor_x="center", anchor_y="center")
                else:
                    raw = iname
                    if raw.endswith("_SEED"):
                        base_seed = raw[:-5].replace("_", " ").title()
                        label = base_seed + " Seed"
                    else:
                        label = raw.replace("_", " ").title()
                    label = label if len(label) <= _MAX_CHARS else label[:_MAX_CHARS - 2].rstrip() + ".."
                    info = f"{weight:.1f}kg x{qty}" if weight > 0.0 else f"x{qty}"
                    total_h   = _LINE_H + _GAP + _LINE_H_Q
                    block_top = cy + total_h / 2.0
                    l1_y      = block_top - _LINE_H / 2.0
                    qty_y     = l1_y - _LINE_H / 2.0 - _GAP - _LINE_H_Q / 2.0
                    arcade.draw_text(label, cx + 1, l1_y - 1, _SHD,               font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(label, cx,     l1_y,     (255, 255, 255, 245), font_size=_FONT_NAME, font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(info,  cx + 1, qty_y - 1, _SHD,               font_size=_FONT_QTY,  font_name=_FONT, anchor_x="center", anchor_y="center")
                    arcade.draw_text(info,  cx,     qty_y,     (210, 185, 80, 210), font_size=_FONT_QTY,  font_name=_FONT, anchor_x="center", anchor_y="center")


# ===========================================================================
# AbstractPopup
# Abstraction: kontrak umum untuk semua popup UI
# Polymorphism: show(), hide(), draw() dipanggil seragam
# ===========================================================================

class AbstractPopup(ABC):
    """
    Abstract Base Class untuk semua popup UI.

    Abstraction: mendefinisikan interface show(), hide(), draw()
    tanpa detail implementasi visual masing-masing popup.

    Polymorphism: GameWindow memanggil popup.draw(w, h) dan popup.is_visible
    tanpa perlu tahu jenis popup-nya.
    """

    def __init__(self) -> None:
        self._visible: bool = False

    @property
    def is_visible(self) -> bool:
        return self._visible

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False

    @abstractmethod
    def draw(self, screen_w: float, screen_h: float) -> None:
        """Render popup ke layar."""


# ===========================================================================
# SellConfirmUI
# Inheritance: mewarisi AbstractPopup
# ===========================================================================

class SellConfirmUI(AbstractPopup):
    """
    Inheritance: mewarisi AbstractPopup.
    Polymorphism: draw() diimplementasikan spesifik untuk popup konfirmasi jual.
    """

    _TARGET_W_RATIO: float = 0.40

    def __init__(self) -> None:
        super().__init__()
        surf = pygame.image.load("assets/ui/SELL_CONFIRM.png")
        self._texture: arcade.Texture = surface_to_arcade_texture(surf)
        self._sprite = arcade.Sprite()
        self._sprite.texture = self._texture
        self._list = arcade.SpriteList()
        self._list.append(self._sprite)

    def draw(self, screen_w: float, screen_h: float) -> None:
        if not self._visible:
            return
        target_w = screen_w * self._TARGET_W_RATIO
        self._sprite.scale    = target_w / self._texture.width
        self._sprite.center_x = screen_w / 2.0
        self._sprite.center_y = screen_h / 2.0
        self._list.draw(pixelated=True)


# ===========================================================================
# ShopUI
# Inheritance: mewarisi AbstractPopup
# Encapsulation: _shop_stocks, _slot_data, _selected dijaga private
# ===========================================================================

class ShopUI(AbstractPopup):
    """
    Inheritance: mewarisi AbstractPopup.
    Encapsulation: _shop_stocks dan _slot_data diakses hanya via
                   show(), try_purchase(), reset_all_stocks().
    """

    _NUM_SLOTS     : int   = 3
    _TARGET_W_RATIO: float = 0.65

    _PAD_X_RATIO   : float = 0.09
    _PAD_TOP_RATIO : float = 0.18
    _PAD_BOT_RATIO : float = 0.12
    _GAP_RATIO     : float = 0.03

    _COLOR_NAME       : tuple[int, ...] = ( 55,  30,   8, 255)
    _COLOR_PRICE      : tuple[int, ...] = ( 70,  42,   8, 255)
    _COLOR_STOCK      : tuple[int, ...] = ( 85,  58,  18, 255)
    _COLOR_SOLD_OUT   : tuple[int, ...] = (120,  48,  28, 255)
    _COLOR_OUTLINE    : tuple[int, ...] = (230, 210, 165,  60)

    _COLOR_CD_NORMAL  : tuple[int, ...] = (255, 255, 255, 255)   # > 30 s  : putih
    _COLOR_CD_WARNING : tuple[int, ...] = (255, 220,  40, 255)   # <= 30 s : kuning
    _COLOR_CD_URGENT  : tuple[int, ...] = (220,  50,  40, 255)   # <= 10 s : merah

    _UI_FONT: str = "assets/fonts/monogram-extended.ttf"         # font utama game

    def __init__(self) -> None:
        super().__init__()

        surf_bg = pygame.image.load("assets/ui/SHOP_BG.png")
        self._tex_bg: arcade.Texture = surface_to_arcade_texture(surf_bg)
        self._bg_sprite = arcade.Sprite()
        self._bg_sprite.texture = self._tex_bg
        self._bg_list = arcade.SpriteList()
        self._bg_list.append(self._bg_sprite)

        surf_slot = pygame.image.load("assets/ui/SEED_SLOT.png")
        self._tex_slot: arcade.Texture = surface_to_arcade_texture(surf_slot)
        self._slot_native_ratio: float = self._tex_slot.width / self._tex_slot.height

        surf_sel = pygame.image.load("assets/ui/SEED_SLOT_SELECTED.png")
        self._tex_sel: arcade.Texture  = surface_to_arcade_texture(surf_sel)
        self._sel_native_ratio: float  = self._tex_sel.width / self._tex_sel.height

        self._slot_sprites: list[arcade.Sprite] = []
        self._slot_list = arcade.SpriteList()
        for _ in range(self._NUM_SLOTS):
            s = arcade.Sprite()
            s.texture = self._tex_slot
            self._slot_sprites.append(s)
            self._slot_list.append(s)

        self._sel_sprites: list[arcade.Sprite] = []
        self._sel_list = arcade.SpriteList()
        for _ in range(self._NUM_SLOTS):
            s = arcade.Sprite()
            s.texture = self._tex_sel
            s.alpha   = 0
            self._sel_sprites.append(s)
            self._sel_list.append(s)

        self._selected: int | None = None

        self._last_centers  : list[tuple[float, float]] = []
        self._last_slot_hw  : float = 0.0
        self._last_slot_hh  : float = 0.0

        _CROP_ASSETS: dict[str, str] = {
            "CARROT_SEED":     "assets/ui/CARROT.png",
            "RADISH_SEED":     "assets/ui/RADISH.png",
            "CORN_SEED":       "assets/ui/CORN.png",
            "TOMATO_SEED":     "assets/ui/TOMATO.png",
            "PUMPKIN_SEED":    "assets/ui/PUMPKIN.png",
            "WATERMELON_SEED": "assets/ui/WATERMELON.png",
            "DAISY_SEED":      "assets/ui/DAISY.png",
            "TULIP_SEED":      "assets/ui/TULIP.png",
            "ROSE_SEED":       "assets/ui/ROSE.png",
            "LAVENDER_SEED":   "assets/ui/LAVENDER.png",
            "SUNFLOWER_SEED":  "assets/ui/SUNFLOWER.png",
            "LILY_SEED":       "assets/ui/LILY.png",
        }
        self._crop_textures: dict[str, arcade.Texture] = {}
        for inv_key, path in _CROP_ASSETS.items():
            surf = pygame.image.load(path)
            self._crop_textures[inv_key] = surface_to_arcade_texture(surf)

        self._icon_sprites: list[arcade.Sprite] = []
        self._icon_list = arcade.SpriteList()
        for _ in range(self._NUM_SLOTS):
            s = arcade.Sprite()
            self._icon_sprites.append(s)
            self._icon_list.append(s)

        self._SEED_CATALOG: list[tuple[str, str, int, int, int, int]] = [
            # (display_name, inv_key, seed_price, tier, stock_min, stock_max)
            ("Carrot",     "CARROT_SEED",      5, 1, 8, 15),
            ("Radish",     "RADISH_SEED",      5, 1, 8, 15),
            ("Corn",       "CORN_SEED",       15, 2, 5,  7),
            ("Tomato",     "TOMATO_SEED",     15, 2, 5,  7),
            ("Pumpkin",    "PUMPKIN_SEED",    30, 3, 1,  5),
            ("Watermelon", "WATERMELON_SEED", 30, 3, 1,  5),
            ("Daisy",      "DAISY_SEED",       5, 1, 8, 15),  # Tier 1 — was 10
            ("Tulip",      "TULIP_SEED",       5, 1, 8, 15),  # Tier 1 — was 10
            ("Rose",       "ROSE_SEED",       15, 2, 5,  7),  # Tier 2 — was 20
            ("Lavender",   "LAVENDER_SEED",   15, 2, 5,  7),  # Tier 2 — was 20
            ("Sunflower",  "SUNFLOWER_SEED",  30, 3, 1,  5),  # Tier 3 — correct
            ("Lily",       "LILY_SEED",       30, 3, 1,  5),  # Tier 3 — correct
        ]

        self._shop_stocks: list[list[dict]] = [
            self._generate_shop_stock(),
            self._generate_shop_stock(),
            self._generate_shop_stock(),
        ]

        self._active_shop: int = 0
        self._slot_data: list[dict] = self._shop_stocks[0]

    _TIER_WEIGHTS: tuple[tuple[int, float], ...] = (
        (1, 0.55),
        (2, 0.90),
        (3, 1.00),
    )

    def _roll_tier(self) -> int:
        r = random.random()
        for tier_num, cumulative in self._TIER_WEIGHTS:
            if r <= cumulative:
                return tier_num
        return 3

    def _generate_shop_stock(self) -> list[dict]:
        tiers: dict[int, list] = {}
        for entry in self._SEED_CATALOG:
            name, inv_key, price, tier, smin, smax = entry
            tiers.setdefault(tier, []).append(entry)

        slots: list[dict] = []
        tier_labels = {1: "Tier 1", 2: "Tier 2", 3: "Tier 3"}

        for slot_idx in range(3):
            tier_num = self._roll_tier()
            chosen   = random.choice(tiers[tier_num])
            name, inv_key, price, tier, smin, smax = chosen
            slots.append({
                "name":    name,
                "inv_key": inv_key,
                "price":   price,
                "stock":   random.randint(smin, smax),
            })

        return slots

    def reset_all_stocks(self) -> None:
        for i in range(3):
            self._shop_stocks[i] = self._generate_shop_stock()
        self._slot_data = self._shop_stocks[self._active_shop]

    def show(self, shop_index: int = 0) -> None:
        self._active_shop = max(0, min(2, shop_index))
        self._slot_data   = self._shop_stocks[self._active_shop]
        self._visible     = True
        self._selected    = None

    def hide(self) -> None:
        self._visible  = False
        self._selected = None

    def _compute_layout(
        self,
        screen_w: float,
        screen_h: float,
        bg_scale: float,
        panel_offset_y: float = 0.0,
    ) -> tuple[list[tuple[float, float]], float, float]:
        bg_w = self._tex_bg.width  * bg_scale
        bg_h = self._tex_bg.height * bg_scale

        bg_left   = screen_w / 2.0 - bg_w / 2.0
        bg_bottom = screen_h / 2.0 - bg_h / 2.0 + panel_offset_y

        pad_x    = bg_w * self._PAD_X_RATIO
        pad_top  = bg_h * self._PAD_TOP_RATIO
        pad_bot  = bg_h * self._PAD_BOT_RATIO
        usable_w = bg_w - pad_x * 2.0
        usable_h = bg_h - pad_top - pad_bot

        total_gap = bg_w * self._GAP_RATIO * (self._NUM_SLOTS - 1)
        slot_render_w = (usable_w - total_gap) / self._NUM_SLOTS
        slot_render_h = slot_render_w / self._slot_native_ratio

        if slot_render_h > usable_h:
            slot_render_h = usable_h
            slot_render_w = slot_render_h * self._slot_native_ratio

        gap = (usable_w - self._NUM_SLOTS * slot_render_w) / max(1, self._NUM_SLOTS - 1)
        content_center_y = bg_bottom + pad_bot + usable_h / 2.0

        centers: list[tuple[float, float]] = []
        origin_x = bg_left + pad_x
        for i in range(self._NUM_SLOTS):
            cx = origin_x + i * (slot_render_w + gap) + slot_render_w / 2.0
            centers.append((cx, content_center_y))

        return centers, slot_render_w, slot_render_h

    def _hit_slot(self, mx: float, my: float) -> int | None:
        hw = self._last_slot_hw
        hh = self._last_slot_hh
        for i, (cx, cy) in enumerate(self._last_centers):
            if (cx - hw) <= mx <= (cx + hw) and (cy - hh) <= my <= (cy + hh):
                return i
        return None

    def on_mouse_press(self, mx: float, my: float, screen_w: float, screen_h: float) -> None:
        if not self._visible:
            return
        slot = self._hit_slot(mx, my)
        if slot is not None:
            if self._slot_data[slot]["stock"] <= 0:
                return
            if self._selected == slot:
                self._selected = None
            else:
                self._selected = slot

    def try_purchase(self, gold_hud) -> str | None:
        """
        Coba beli item dari slot yang sedang dipilih.
        Encapsulation: logika pembelian disembunyikan di sini.
        Return: inventory key seed yang dibeli, atau None jika gagal.
        """
        if not self._visible or self._selected is None:
            return None

        data    = self._slot_data[self._selected]
        price   = data["price"]
        stock   = data["stock"]
        name    = data["name"]
        inv_key = data.get("inv_key", name)

        if gold_hud.gold < price:
            return None
        if stock <= 0:
            return None

        gold_hud.remove_gold(price)
        data["stock"] -= 1
        return inv_key

    def _draw_outlined_text(
        self,
        text: str,
        x: float,
        y: float,
        font_size: int,
        color: tuple[int, ...],
        anchor_x: str = "center",
        anchor_y: str = "center",
        bold: bool = False,
        font_name: str | None = None,
    ) -> None:
        _fn = font_name if font_name is not None else self._UI_FONT
        arcade.draw_text(text, x + 1, y - 1, self._COLOR_OUTLINE, font_size=font_size, anchor_x=anchor_x, anchor_y=anchor_y, bold=bold, font_name=_fn)
        arcade.draw_text(text, x, y, color, font_size=font_size, anchor_x=anchor_x, anchor_y=anchor_y, bold=bold, font_name=_fn)

    def draw(self, screen_w: float, screen_h: float, refresh_remaining: float = 0.0) -> None:
        if not self._visible:
            return

        target_w = screen_w * self._TARGET_W_RATIO
        bg_scale  = target_w / self._tex_bg.width

        self._bg_sprite.scale    = bg_scale
        self._bg_sprite.center_x = screen_w / 2.0
        self._bg_sprite.center_y = screen_h / 2.0 + screen_h * 0.02
        self._bg_list.draw(pixelated=True)

        _panel_offset = screen_h * 0.02
        centers, slot_rw, slot_rh = self._compute_layout(screen_w, screen_h, bg_scale, _panel_offset)
        self._last_centers = centers
        self._last_slot_hw = slot_rw / 2.0
        self._last_slot_hh = slot_rh / 2.0

        scale_slot = slot_rh / self._tex_slot.height
        scale_sel  = slot_rh / self._tex_sel.height

        for i, (cx, cy) in enumerate(centers):
            s = self._slot_sprites[i]
            s.scale    = scale_slot
            s.center_x = cx
            s.center_y = cy
        self._slot_list.draw(pixelated=True)

        for i, (cx, cy) in enumerate(centers):
            s = self._sel_sprites[i]
            s.scale    = scale_sel
            s.center_x = cx
            s.center_y = cy
            s.alpha    = 255 if i == self._selected else 0
        self._sel_list.draw(pixelated=True)

        icon_size   = slot_rw * 0.463
        icon_cy_off = slot_rh * 0.17

        for i, (cx, cy) in enumerate(centers):
            data    = self._slot_data[i]
            inv_key = data.get("inv_key", "")
            tex     = self._crop_textures.get(inv_key)
            if tex is None:
                continue
            s = self._icon_sprites[i]
            s.texture  = tex
            native_max = max(tex.width, tex.height)
            s.scale    = icon_size / native_max
            s.center_x = cx
            s.center_y = cy + icon_cy_off
        self._icon_list.draw(pixelated=True)

        upper_center_y_base = -0.116
        panel_center_y_base = 0.366

        font_name  = max(11, int(slot_rh * 0.052))
        font_price = max(10, int(slot_rh * 0.062))
        font_stock = max( 9, int(slot_rh * 0.050))
        row_gap    = max(3, int(slot_rh * 0.050))

        for i, (cx, cy) in enumerate(centers):
            data  = self._slot_data[i]
            name  = data["name"]
            price = data["price"]
            stock = data["stock"]

            upper_y = cy + slot_rh * upper_center_y_base
            self._draw_outlined_text(name, cx, upper_y, font_name, self._COLOR_NAME, anchor_x="center", anchor_y="center", bold=False)

            panel_y  = cy - slot_rh * panel_center_y_base
            half_gap = row_gap * 0.5
            price_y  = panel_y + half_gap + font_price * 0.45 + slot_rh * 0.03
            stock_y  = panel_y - half_gap - font_stock * 0.45 + slot_rh * 0.06

            self._draw_outlined_text(f"{price} C", cx, price_y, font_price, self._COLOR_PRICE, anchor_x="center", anchor_y="center", bold=False)

            if stock <= 0:
                stock_text  = "Stok: 0"
                stock_color = self._COLOR_SOLD_OUT
            else:
                stock_text  = f"Stok: {stock}"
                stock_color = self._COLOR_STOCK

            self._draw_outlined_text(stock_text, cx, stock_y, font_stock, stock_color, anchor_x="center", anchor_y="center", bold=False)

        secs_left = max(0.0, float(refresh_remaining))
        mins      = int(secs_left) // 60
        secs      = int(secs_left) % 60
        cd_text   = f"REFRESH IN : {mins:02d}:{secs:02d}"

        if secs_left <= 10.0:
            cd_color = self._COLOR_CD_URGENT
        elif secs_left <= 30.0:
            cd_color = self._COLOR_CD_WARNING
        else:
            cd_color = self._COLOR_CD_NORMAL

        bg_w    = self._tex_bg.width  * bg_scale
        bg_h    = self._tex_bg.height * bg_scale
        bg_top  = (screen_h / 2.0 + screen_h * 0.02) + bg_h / 2.0
        pad_top = bg_h * self._PAD_TOP_RATIO

        cd_x = screen_w / 2.0
        cd_y = bg_top - pad_top * 1.300

        font_cd = max(10, int(bg_h * 0.04104))  # 0.0456 * 0.90 → kecil 10%
        self._draw_outlined_text(cd_text, cd_x, cd_y, font_cd, cd_color, anchor_x="center", anchor_y="center", bold=False)