"""
fish_popup.py  –  Sistem Popup Hasil Tangkapan

Kelas-kelas:
  RewardGenerator – menghasilkan FishReward dari FishPool
  FishPopup       – menampilkan popup ikan yang tertangkap

Penggunaan:
    popup = FishPopup()
    popup.show(fish_reward)
    popup.draw()
    popup.is_visible
    popup.close()
"""

from __future__ import annotations

from pathlib import Path
import arcade

from constants import SCREEN_WIDTH, SCREEN_HEIGHT, ASSETS_DIR
from fish import Fish, FishPool, FishReward, Rarity

_UI_FISHING_DIR: Path = ASSETS_DIR / "ui" / "Fishing"
_FISH_DIR:        Path = ASSETS_DIR / "Fish"

_POPUP_W = 480
_POPUP_H = 300

_DIV_Y_OFFSET    = -44.5
_FISH_CY_OFFSET  = +53.0
_FISH_MAX_W      = 512
_FISH_MAX_H      = 320

_NAME_CY_OFFSET  = -63.0
_RAR_CY_OFFSET   = -93.0
_HINT_CY_OFFSET  = -130.0

_ANIM_START = 0.30
_ANIM_SPEED = 0.08

_RARITY_COLORS: dict[Rarity, tuple] = {
    Rarity.UMUM:   ( 70, 130, 255, 255),
    Rarity.LANGKA: (255, 135,  30, 255),
    Rarity.EPIC:   (155,  55, 215, 255),
    Rarity.LEGEND: (215,  35,  35, 255),
}

_NAME_COLOR  = (55, 28, 8, 255)
_HINT_COLOR  = (140, 100, 45, 200)
_FRAME_COLOR = (30, 18, 8, 255)


# ===========================================================================
# RewardGenerator
# Encapsulation: FishPool disembunyikan di balik interface generate()
# ===========================================================================

class RewardGenerator:
    """
    Membungkus FishPool; menghasilkan FishReward saat player menang.

    Encapsulation: _pool tidak diakses langsung dari luar.
    """

    ROUNDS_DEFAULT: int = 3
    ROUNDS_LEGEND:  int = 5

    def __init__(self) -> None:
        self._pool = FishPool()

    def generate(self) -> FishReward:
        """Hasilkan FishReward acak berdasarkan probabilitas pool."""
        return self._pool.catch()

    @staticmethod
    def rounds_for(reward: FishReward) -> int:
        if reward.fish.rarity == Rarity.LEGEND:
            return RewardGenerator.ROUNDS_LEGEND
        return RewardGenerator.ROUNDS_DEFAULT


# ===========================================================================
# FishPopup
# Encapsulation: state _visible, _reward, tekstur dijaga private
# ===========================================================================

class FishPopup:
    """
    Popup hasil tangkapan ikan.

    Encapsulation: semua state internal (visibility, tekstur, animasi)
    diakses hanya melalui public API: show(), close(), draw(), is_visible.
    """

    def __init__(self) -> None:
        self._visible:    bool                  = False
        self._reward:     FishReward | None     = None
        self._tex_bg:     arcade.Texture | None = None
        self._tex_fish:   arcade.Texture | None = None
        self._anim_scale: float                 = 1.0

        bg_path = str(_UI_FISHING_DIR / "caught1.png")
        try:
            self._tex_bg = arcade.load_texture(bg_path)
        except Exception as e:
            pass

    @property
    def is_visible(self) -> bool:
        return self._visible

    def show(self, reward: FishReward) -> None:
        self._reward     = reward
        self._visible    = True
        self._anim_scale = _ANIM_START
        self._load_fish_texture(reward.fish)

    def close(self) -> None:
        self._visible  = False
        self._reward   = None
        self._tex_fish = None

    def on_key_press(self, key: int) -> None:
        if self._visible and key == arcade.key.F:
            self.close()

    def draw(self) -> None:
        if not self._visible or self._reward is None:
            return

        if self._anim_scale < 1.0:
            self._anim_scale = min(1.0, self._anim_scale + _ANIM_SPEED)

        s  = self._anim_scale
        cx = SCREEN_WIDTH  / 2
        cy = SCREEN_HEIGHT / 2

        pw = _POPUP_W * s
        ph = _POPUP_H * s

        arcade.draw_lrbt_rectangle_filled(
            cx - pw / 2, cx + pw / 2,
            cy - ph / 2, cy + ph / 2,
            _FRAME_COLOR,
        )

        if self._tex_bg is not None:
            arcade.draw_texture_rect(
                self._tex_bg,
                arcade.XYWH(cx, cy, pw, ph),
            )
        else:
            arcade.draw_lrbt_rectangle_outline(
                cx - pw / 2, cx + pw / 2,
                cy - ph / 2, cy + ph / 2,
                (200, 160, 40, 255), 3,
            )

        fish   = self._reward.fish
        rarity = fish.rarity

        fish_cx = cx
        fish_cy = cy + _FISH_CY_OFFSET * s

        if self._tex_fish is not None:
            fw, fh     = self._tex_fish.size
            max_w      = _FISH_MAX_W * s
            max_h      = _FISH_MAX_H * s
            scale_f    = min(max_w / fw, max_h / fh)
            draw_w     = fw * scale_f
            draw_h     = fh * scale_f
            arcade.draw_texture_rect(
                self._tex_fish,
                arcade.XYWH(fish_cx, fish_cy, draw_w, draw_h),
            )
        else:
            bw, bh = 100 * s, 80 * s
            arcade.draw_lrbt_rectangle_filled(
                fish_cx - bw / 2, fish_cx + bw / 2,
                fish_cy - bh / 2, fish_cy + bh / 2,
                (80, 130, 200, 255),
            )

        name_y    = cy + _NAME_CY_OFFSET * s
        name_text = fish.name.upper()

        font_name = max(8, int(24 * s))
        while font_name > 8:
            est_w = font_name * 0.62 * len(name_text)
            if est_w <= pw * 0.82:
                break
            font_name -= 1

        arcade.draw_text(
            name_text,
            cx, name_y,
            _NAME_COLOR,
            font_size = font_name,
            bold      = True,
            anchor_x  = "center",
            anchor_y  = "center",
        )

        rarity_y     = cy + _RAR_CY_OFFSET * s
        font_rarity  = max(6, int(18 * s))
        rarity_color = _RARITY_COLORS.get(rarity, (255, 255, 255, 255))
        rarity_text  = f"\u25c6 {rarity.label.upper()} \u25c6"

        arcade.draw_text(
            rarity_text,
            cx, rarity_y,
            rarity_color,
            font_size = font_rarity,
            bold      = True,
            anchor_x  = "center",
            anchor_y  = "center",
        )

        hint_y    = cy + _HINT_CY_OFFSET * s
        font_hint = max(5, int(11 * s))
        arcade.draw_text(
            "[F] Tutup",
            cx, hint_y,
            _HINT_COLOR,
            font_size = font_hint,
            anchor_x  = "center",
            anchor_y  = "center",
        )

    def _load_fish_texture(self, fish: Fish) -> None:
        path = str(fish.sprite_path)
        try:
            self._tex_fish = arcade.load_texture(path)
        except Exception as e:
            self._tex_fish = None
