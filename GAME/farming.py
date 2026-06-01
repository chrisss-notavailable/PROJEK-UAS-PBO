"""
farming.py — Sistem Farming dengan Growth System

Hierarki OOP:
  AbstractCrop (ABC)    – kontrak untuk semua crop (Abstraction)
    └── PlantData       – state satu tanaman yang ditanam di dunia

Polymorphism: setiap tahapan pertumbuhan direpresentasikan sebagai
konstanta stage, bukan if-else rantai panjang.

Tahapan: STAGE_1 → STAGE_2 → FINAL CROP
Transisi antar stage menggunakan fade out → swap → fade in (0.25 detik).
"""
from __future__ import annotations

import random
import time
import pygame
import arcade

from abc import ABC, abstractmethod
from constants import SCALED_TILE_SIZE, PIXEL_SCALE, TILE_SIZE

_SEED_KEYS: frozenset[str] = frozenset({
    "CARROT_SEED",
    "RADISH_SEED",
    "CORN_SEED",
    "TOMATO_SEED",
    "PUMPKIN_SEED",
    "WATERMELON_SEED",
    "DAISY_SEED",
    "TULIP_SEED",
    "ROSE_SEED",
    "LAVENDER_SEED",
    "SUNFLOWER_SEED",
    "LILY_SEED",
})

_STAGE_ASSET_SHARED = {
    "STAGE_1": "assets/plant/STAGE_1.png",
    "STAGE_2": "assets/plant/STAGE_2.png",
}

_CROP_FINAL_ASSET: dict[str, str] = {
    "CARROT_SEED":     "assets/plant/CARROT.png",
    "RADISH_SEED":     "assets/plant/RADISH.png",
    "CORN_SEED":       "assets/plant/CORN.png",
    "TOMATO_SEED":     "assets/plant/TOMATO.png",
    "PUMPKIN_SEED":    "assets/plant/PUMPKIN.png",
    "WATERMELON_SEED": "assets/plant/WATERMELON.png",
    "DAISY_SEED":      "assets/plant/DAISY.png",
    "TULIP_SEED":      "assets/plant/TULIP.png",
    "ROSE_SEED":       "assets/plant/ROSE.png",
    "LAVENDER_SEED":   "assets/plant/LAVENDER.png",
    "SUNFLOWER_SEED":  "assets/plant/SUNFLOWER.png",
    "LILY_SEED":       "assets/plant/LILY.png",
}

_GROW_TIME: dict[str, tuple[float, float]] = {
    "CARROT_SEED":     (120.0, 120.0),
    "RADISH_SEED":     (120.0, 120.0),
    "CORN_SEED":       (180.0, 180.0),
    "TOMATO_SEED":     (180.0, 180.0),
    "PUMPKIN_SEED":    (240.0, 240.0),
    "WATERMELON_SEED": (240.0, 240.0),
    "DAISY_SEED":      (120.0, 120.0),
    "TULIP_SEED":      (120.0, 120.0),
    "ROSE_SEED":       (180.0, 180.0),
    "LAVENDER_SEED":   (180.0, 180.0),
    "SUNFLOWER_SEED":  (240.0, 240.0),
    "LILY_SEED":       (240.0, 240.0),
}

FADE_DURATION: float = 0.25

_STAGE_TARGET_H_PX: dict[str, float] = {
    "STAGE_1": 36.0,
    "STAGE_2": 36.0,
}

_CROP_FINAL_TARGET_H_PX: dict[str, float] = {
    "CARROT_SEED":     36.0,
    "RADISH_SEED":     36.0,
    "CORN_SEED":       44.0,
    "TOMATO_SEED":     44.0,
    "PUMPKIN_SEED":    30.0,
    "WATERMELON_SEED": 30.0,
    "DAISY_SEED":      30.0,
    "TULIP_SEED":      30.0,
    "ROSE_SEED":       30.0,
    "LAVENDER_SEED":   30.0,
    "SUNFLOWER_SEED":  30.0,
    "LILY_SEED":       30.0,
}

_CROP_SCALE_EXTRA: dict[str, float] = {
    "CARROT_SEED":     1.05 * 1.03,
    "RADISH_SEED":     1.05 * 1.03,
    "CORN_SEED":       1.05 * 1.03 * 1.03,
    "TOMATO_SEED":     1.05 * 1.03 * 1.03,
    "PUMPKIN_SEED":    1.05 * 1.03 * 1.05,
    "WATERMELON_SEED": 1.05 * 1.03 * 1.05,
    "DAISY_SEED":      1.05 * 1.03 * 1.05,
    "TULIP_SEED":      1.05 * 1.03 * 1.05 * 1.10,
    "ROSE_SEED":       1.05 * 1.03 * 1.05,
    "LAVENDER_SEED":   1.05 * 1.03 * 1.05,
    "SUNFLOWER_SEED":  1.05 * 1.03 * 1.05 * 1.10,
    "LILY_SEED":       1.05 * 1.03 * 1.05 * 1.10,
}

_SEED_TO_CROP: dict[str, str] = {
    "CARROT_SEED":     "CARROT",
    "RADISH_SEED":     "RADISH",
    "CORN_SEED":       "CORN",
    "TOMATO_SEED":     "TOMATO",
    "PUMPKIN_SEED":    "PUMPKIN",
    "WATERMELON_SEED": "WATERMELON",
    "DAISY_SEED":      "DAISY",
    "TULIP_SEED":      "TULIP",
    "ROSE_SEED":       "ROSE",
    "LAVENDER_SEED":   "LAVENDER",
    "SUNFLOWER_SEED":  "SUNFLOWER",
    "LILY_SEED":       "LILY",
}

_HARVEST_YIELD: dict[str, tuple[int, int]] = {
    "CARROT":     (2, 4),
    "RADISH":     (2, 4),
    "CORN":       (1, 3),
    "TOMATO":     (1, 3),
    "PUMPKIN":    (1, 2),
    "WATERMELON": (1, 2),
    "DAISY":      (2, 4),
    "TULIP":      (2, 4),
    "ROSE":       (1, 3),
    "LAVENDER":   (1, 3),
    "SUNFLOWER":  (1, 2),
    "LILY":       (1, 2),
}

STAGE_1   = "STAGE_1"
STAGE_2   = "STAGE_2"
STAGE_FINAL = "FINAL"

_FADE_IDLE = 0
_FADE_OUT  = 1
_FADE_SWAP = 2
_FADE_IN   = 3


def _world_to_tile(wx: float, wy: float) -> tuple[int, int]:
    col = int(wx // SCALED_TILE_SIZE)
    row = int(wy // SCALED_TILE_SIZE)
    return col, row


def _tile_center(col: int, row: int) -> tuple[float, float]:
    cx = col * SCALED_TILE_SIZE + SCALED_TILE_SIZE / 2.0
    cy = row * SCALED_TILE_SIZE + SCALED_TILE_SIZE / 2.0
    return cx, cy


def surface_to_arcade_texture(surf: pygame.Surface) -> arcade.Texture:
    from PIL import Image as PILImage
    raw  = pygame.image.tostring(surf, "RGBA")
    w, h = surf.get_size()
    pil  = PILImage.frombytes("RGBA", (w, h), raw)
    name = f"_farming_{id(surf)}"
    return arcade.Texture(pil, name=name)


# ===========================================================================
# AbstractCrop
# Abstraction: mendefinisikan kontrak data state untuk setiap tanaman
# ===========================================================================

class AbstractCrop(ABC):
    """
    Abstract Base Class untuk representasi satu tanaman di dunia.

    Abstraction: mendefinisikan interface stage, is_mature,
    dan can_be_watered tanpa detail implementasi.
    """

    @property
    @abstractmethod
    def stage(self) -> str:
        """Stage saat ini: STAGE_1, STAGE_2, atau FINAL."""

    @stage.setter
    @abstractmethod
    def stage(self, value: str) -> None:
        """Set stage tanaman."""

    @property
    def is_mature(self) -> bool:
        """Return True jika tanaman sudah di stage FINAL."""
        return self.stage == STAGE_FINAL

    @property
    def can_be_watered(self) -> bool:
        """Return True jika tanaman masih bisa disiram."""
        return not self.is_mature


# ===========================================================================
# PlantData
# Inheritance: mewarisi AbstractCrop
# Encapsulation: semua field internal dijaga via __slots__
# ===========================================================================

class PlantData(AbstractCrop):
    """
    Menyimpan state satu tanaman di dunia.

    Inheritance: mewarisi AbstractCrop — memenuhi kontrak is_mature
    dan can_be_watered secara otomatis dari parent.

    Encapsulation: __slots__ mencegah penambahan atribut sembarangan.
    """
    __slots__ = (
        "seed_name", "_stage", "age",
        "t1", "t2",
        "fade_state", "fade_timer", "next_stage",
    )

    def __init__(self, seed_name: str) -> None:
        self.seed_name  = seed_name
        self._stage     = STAGE_1
        self.age        = 0.0
        s1, s2          = _GROW_TIME.get(seed_name, (120.0, 120.0))
        self.t1         = s1
        self.t2         = s1 + s2
        self.fade_state = _FADE_IDLE
        self.fade_timer = 0.0
        self.next_stage: str | None = None

    @property
    def stage(self) -> str:
        return self._stage

    @stage.setter
    def stage(self, value: str) -> None:
        self._stage = value


# ===========================================================================
# FarmingSystem
# Encapsulation: state _plants, _textures, _tile_sprites dijaga private
# ===========================================================================

class FarmingSystem:
    """
    Mengelola penanaman, growth timer, dan transisi visual antar stage.

    Encapsulation: _plants dan _tile_sprites diakses hanya melalui
    method publik (is_planted, try_plant, harvest_plant, water_area).
    """

    def __init__(self) -> None:
        self._plants: dict[tuple[int, int], PlantData] = {}

        self._textures: dict[str, arcade.Texture] = {}
        self._scales:   dict[str, float]          = {}

        self._load_textures()

        self._plant_list   = arcade.SpriteList()
        self._tile_sprites: dict[tuple[int, int], arcade.Sprite] = {}

        self._planted_tiles: dict[tuple[int, int], str] = {}

    def _load_textures(self) -> None:
        for stage_key, path in _STAGE_ASSET_SHARED.items():
            surf = pygame.image.load(path)
            tex  = surface_to_arcade_texture(surf)
            self._textures[stage_key] = tex
            target_h = _STAGE_TARGET_H_PX[stage_key]
            native_h = tex.height
            self._scales[stage_key] = (target_h / native_h if native_h > 0 else 1.0) * (1.05 * 1.03)

        for seed_key, path in _CROP_FINAL_ASSET.items():
            surf = pygame.image.load(path)
            tex  = surface_to_arcade_texture(surf)
            self._textures[seed_key] = tex
            target_h = _CROP_FINAL_TARGET_H_PX[seed_key]
            native_h = tex.height
            extra    = _CROP_SCALE_EXTRA.get(seed_key, 1.0)
            self._scales[seed_key] = (target_h / native_h if native_h > 0 else 1.0) * extra

    def _tex_key_for_stage(self, plant: PlantData) -> str:
        if plant.stage == STAGE_FINAL:
            return plant.seed_name
        return plant.stage

    def _get_tex_and_scale(self, tex_key: str) -> tuple[arcade.Texture, float]:
        return self._textures[tex_key], self._scales[tex_key]

    def _sprite_position(self, col: int, row: int, scale: float, tex_h: int) -> tuple[float, float]:
        tile_center_x = col * SCALED_TILE_SIZE + SCALED_TILE_SIZE / 2.0
        tile_bottom_y = row * SCALED_TILE_SIZE
        sprite_h      = tex_h * scale
        cx = tile_center_x
        cy = tile_bottom_y + sprite_h / 2.0 + SCALED_TILE_SIZE * 0.18
        return cx, cy

    def is_planted(self, col: int, row: int) -> bool:
        return (col, row) in self._plants

    def is_planted_at_world(self, wx: float, wy: float) -> bool:
        return self.is_planted(*_world_to_tile(wx, wy))

    def has_mature_plant_nearby(
        self,
        player_x: float,
        player_y: float,
        max_dist: float | None = None,
    ) -> bool:
        if max_dist is None:
            max_dist = SCALED_TILE_SIZE * 1.5
        max_dist_sq = max_dist * max_dist
        for (col, row), plant in self._plants.items():
            if not plant.is_mature:
                continue
            cx, cy = _tile_center(col, row)
            dist_sq = (cx - player_x) ** 2 + (cy - player_y) ** 2
            if dist_sq <= max_dist_sq:
                return True
        return False

    def get_nearest_mature_plant(
        self,
        player_x: float,
        player_y: float,
        max_dist: float | None = None,
    ) -> tuple[int, int] | None:
        if max_dist is None:
            max_dist = SCALED_TILE_SIZE * 1.5
        max_dist_sq = max_dist * max_dist
        best_tile: tuple[int, int] | None = None
        best_dist_sq = float("inf")
        for (col, row), plant in self._plants.items():
            if not plant.is_mature:
                continue
            cx, cy = _tile_center(col, row)
            dist_sq = (cx - player_x) ** 2 + (cy - player_y) ** 2
            if dist_sq <= max_dist_sq and dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_tile = (col, row)
        return best_tile

    def harvest_plant(
        self,
        player_x: float,
        player_y: float,
        inventory_ui,
        hotbar_ui,
        max_dist: float | None = None,
    ) -> str | None:
        """
        Panen tanaman matang terdekat.
        Encapsulation: akses inventory dilakukan melalui method ini,
        bukan langsung dari luar.
        """
        tile = self.get_nearest_mature_plant(player_x, player_y, max_dist)
        if tile is None:
            return None

        col, row = tile
        plant = self._plants[col, row]
        crop_name = _SEED_TO_CROP.get(plant.seed_name)

        sprite = self._tile_sprites.pop((col, row), None)
        if sprite is not None:
            self._plant_list.remove(sprite)

        del self._plants[(col, row)]
        self._planted_tiles.pop((col, row), None)

        if crop_name is None:
            return None

        yield_min, yield_max = _HARVEST_YIELD.get(crop_name, (1, 1))
        qty = random.randint(yield_min, yield_max)

        self._add_crop_to_inventory(crop_name, qty, inventory_ui, hotbar_ui)
        return crop_name

    def _add_crop_to_inventory(
        self,
        crop_name: str,
        qty: int,
        inventory_ui,
        hotbar_ui,
    ) -> None:
        """
        Encapsulation: akses inventory dilakukan melalui method ini.
        """
        remaining = qty

        for slot in hotbar_ui._slot_items:
            if slot is not None and slot["name"] == crop_name:
                slot["qty"] += remaining
                return

        for slot in inventory_ui._items:
            if slot is not None and slot["name"] == crop_name:
                slot["qty"] += remaining
                return

        for i, slot in enumerate(hotbar_ui._slot_items):
            if slot is None:
                hotbar_ui._slot_items[i] = {"name": crop_name, "qty": remaining, "weight": 0.0}
                return

        for i, slot in enumerate(inventory_ui._items):
            if slot is None:
                inventory_ui._items[i] = {"name": crop_name, "qty": remaining, "weight": 0.0}
                return

    def try_plant(
        self,
        player_x: float,
        player_y: float,
        plantable_rects: list,
        inventory_ui,
        hotbar_ui,
    ) -> bool:
        target = self._find_nearest_tile(player_x, player_y, plantable_rects)
        if target is None:
            return False

        col, row = target

        seed_source, seed_name = self._find_active_seed(inventory_ui, hotbar_ui)
        if seed_name is None:
            return False

        self._consume_seed(seed_source, inventory_ui, hotbar_ui)
        self._place_plant(col, row, seed_name)
        return True

    def update(self, delta_time: float) -> None:
        for tile_pos, plant in self._plants.items():
            self._update_plant(tile_pos, plant, delta_time)

    def _update_plant(
        self,
        tile_pos: tuple[int, int],
        plant: PlantData,
        dt: float,
    ) -> None:
        sprite = self._tile_sprites.get(tile_pos)
        if sprite is None:
            return

        if plant.fade_state != _FADE_IDLE:
            plant.fade_timer += dt

            if plant.fade_state == _FADE_OUT:
                progress = min(plant.fade_timer / FADE_DURATION, 1.0)
                sprite.alpha = int(255 * (1.0 - progress))
                if progress >= 1.0:
                    plant.stage      = plant.next_stage
                    plant.next_stage = None
                    tex_key          = self._tex_key_for_stage(plant)
                    tex, scale       = self._get_tex_and_scale(tex_key)
                    sprite.texture   = tex
                    sprite.scale     = scale
                    cx, cy = self._sprite_position(
                        tile_pos[0], tile_pos[1], scale, tex.height
                    )
                    sprite.center_x = cx
                    sprite.center_y = cy
                    sprite.alpha    = 0
                    plant.fade_state = _FADE_IN
                    plant.fade_timer = 0.0

            elif plant.fade_state == _FADE_IN:
                progress = min(plant.fade_timer / FADE_DURATION, 1.0)
                sprite.alpha = int(255 * progress)
                if progress >= 1.0:
                    sprite.alpha     = 255
                    plant.fade_state = _FADE_IDLE
                    plant.fade_timer = 0.0

            return

        if plant.is_mature:
            return

        plant.age += dt

        next_stage = None
        if plant.stage == STAGE_1 and plant.age >= plant.t1:
            next_stage = STAGE_2
        elif plant.stage == STAGE_2 and plant.age >= plant.t2:
            next_stage = STAGE_FINAL

        if next_stage is not None:
            plant.next_stage = next_stage
            plant.fade_state = _FADE_OUT
            plant.fade_timer = 0.0

    def _find_nearest_tile(
        self,
        player_x: float,
        player_y: float,
        plantable_rects: list,
    ) -> tuple[int, int] | None:
        best_tile: tuple[int, int] | None = None
        best_dist = float("inf")

        for left, right, bottom, top in plantable_rects:
            col_start = int(left        // SCALED_TILE_SIZE)
            col_end   = int((right - 1) // SCALED_TILE_SIZE)
            row_start = int(bottom      // SCALED_TILE_SIZE)
            row_end   = int((top   - 1) // SCALED_TILE_SIZE)

            for row in range(row_start, row_end + 1):
                for col in range(col_start, col_end + 1):
                    if (col, row) in self._plants:
                        continue
                    cx, cy = _tile_center(col, row)
                    if not (left <= cx <= right and bottom <= cy <= top):
                        continue
                    dist = (cx - player_x) ** 2 + (cy - player_y) ** 2
                    if dist < best_dist:
                        best_dist = dist
                        best_tile = (col, row)

        return best_tile

    def _find_active_seed(
        self,
        inventory_ui,
        hotbar_ui,
    ) -> tuple[str | None, str | None]:
        inv_sel = inventory_ui._selected
        if inv_sel is not None and inv_sel < len(inventory_ui._items):
            item = inventory_ui._items[inv_sel]
            if item is not None and item["name"] in _SEED_KEYS:
                return "inventory", item["name"]

        hb_sel = hotbar_ui.selected_slot
        if hb_sel is not None:
            item = hotbar_ui._slot_items[hb_sel]
            if item is not None and item["name"] in _SEED_KEYS:
                return "hotbar", item["name"]

        return None, None

    def _consume_seed(self, source: str, inventory_ui, hotbar_ui) -> None:
        if source == "inventory":
            sel  = inventory_ui._selected
            item = inventory_ui._items[sel]
            item["qty"] -= 1
            if item["qty"] <= 0:
                inventory_ui._items[sel] = None
                inventory_ui._selected   = None
        elif source == "hotbar":
            sel  = hotbar_ui._selected_slot
            item = hotbar_ui._slot_items[sel]
            item["qty"] -= 1
            if item["qty"] <= 0:
                hotbar_ui._slot_items[sel] = None
                hotbar_ui._selected_slot   = None

    def _place_plant(self, col: int, row: int, seed_name: str) -> None:
        tex_key      = STAGE_1
        tex, scale   = self._get_tex_and_scale(tex_key)
        cx, cy       = self._sprite_position(col, row, scale, tex.height)

        s           = arcade.Sprite()
        s.texture   = tex
        s.scale     = scale
        s.center_x  = cx
        s.center_y  = cy
        s.alpha     = 255

        plant = PlantData(seed_name)

        self._plants[(col, row)]        = plant
        self._planted_tiles[(col, row)] = seed_name
        self._tile_sprites[(col, row)]  = s
        self._plant_list.append(s)

    def draw(self) -> None:
        self._plant_list.draw(pixelated=True)

    def water_area(
        self,
        left: float,
        right: float,
        bottom: float,
        top: float,
    ) -> int:
        """
        Siram semua tanaman di dalam rect.
        Encapsulation: efek grow time acceleration disembunyikan di sini.
        """
        watered = 0
        for (col, row), plant in self._plants.items():
            if not plant.can_be_watered:
                continue

            cx, cy = _tile_center(col, row)
            if not (left <= cx <= right and bottom <= cy <= top):
                continue

            remaining = plant.t2 - plant.age
            if remaining <= 0:
                continue

            bonus     = plant.t2 * 0.05         
            plant.age = min(plant.age + bonus, plant.t2)
            watered += 1

        if watered > 0:
            pass
        return watered

    def clear(self) -> None:
        self._plants.clear()
        self._planted_tiles.clear()
        self._tile_sprites.clear()
        self._plant_list.clear()

    @property
    def sprites(self) -> arcade.SpriteList:
        """Expose sprite list untuk Y-sorting eksternal."""
        return self._plant_list