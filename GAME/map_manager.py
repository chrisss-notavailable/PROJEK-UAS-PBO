"""
map_manager.py — Manajer Peta

Encapsulation: tile_map, scene, collision_mask, layer lists semua
dijaga private dan diakses via method/property.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import arcade
from arcade.tilemap import TileMap

from constants import (
    PIXEL_SCALE,
    SCALED_TILE_SIZE,
    LAYER_PLAYER,
    ABOVE_ALPHA_OPAQUE,
    ABOVE_ALPHA_TRANSPARENT,
    ABOVE_FADE_SPEED,
)
from collision_mask import CollisionMask, get_collision_png_path

LAYER_FISHING_AREA = "Fishing Area"


class MapManager:
    """
    Encapsulation: seluruh state map (tile_map, scene, collision_mask,
    layer lists) dijaga private; diakses via draw_*(), load(), preload().
    """

    def __init__(self) -> None:
        self.tile_map: Optional[TileMap]      = None
        self._scene:   Optional[arcade.Scene] = None

        self.map_pixel_width:  float = 0.0
        self.map_pixel_height: float = 0.0

        self.collision_mask = CollisionMask()

        self._current_tmx: str = ""

        self._above_sprite_lists: list[arcade.SpriteList] = []
        self._sprite_alpha: dict[int, float] = {}

        self._layers_below: list[str] = []
        self._layers_above: list[str] = []

        self._cache: dict[str, tuple] = {}

    @staticmethod
    def _parse_tmx_layers(tmx_path: str) -> tuple[list[str], list[str]]:
        """
        Baca semua layer dari TMX tanpa hardcode nama.

        Returns:
            tile_layers   — nama <layer> (tile, digambar)
            object_layers — nama <objectgroup> (interaksi, tidak digambar)
        """
        tile_layers:   list[str] = []
        object_layers: list[str] = []
        try:
            root = ET.parse(tmx_path).getroot()
            for elem in root.iter():
                name = elem.get("name", "").strip()
                if not name:
                    continue
                if elem.tag == "layer":
                    tile_layers.append(name)
                elif elem.tag == "objectgroup":
                    object_layers.append(name)
        except Exception as exc:
            pass
        return tile_layers, object_layers

    def _load_into_cache(self, tmx_path_str: str) -> None:
        if tmx_path_str in self._cache:
            return

        tile_layers, object_layers = self._parse_tmx_layers(tmx_path_str)
        all_names = tile_layers + object_layers

        layer_options: dict[str, dict] = {
            name: {"use_spatial_hash": False}
            for name in all_names
        }

        tile_map = arcade.load_tilemap(
            tmx_path_str,
            scaling=PIXEL_SCALE,
            layer_options=layer_options,
        )
        scene = arcade.Scene.from_tilemap(tile_map)

        w = tile_map.width  * SCALED_TILE_SIZE
        h = tile_map.height * SCALED_TILE_SIZE

        cm = CollisionMask()
        cm.load(
            get_collision_png_path(tmx_path_str),
            map_pixel_width  = w,
            map_pixel_height = h,
            current_map      = tmx_path_str,
        )

        layers_below: list[str] = []
        layers_above: list[str] = []
        found_player = False
        for name in tile_layers:
            if name == LAYER_PLAYER:
                found_player = True
                continue
            if not found_player:
                layers_below.append(name)
            else:
                layers_above.append(name)

        self._cache[tmx_path_str] = (tile_map, scene, cm, w, h, layers_below, layers_above)


    def preload(self, tmx_path: str | Path) -> None:
        self._load_into_cache(str(tmx_path))

    def load(self, tmx_path: str | Path) -> None:
        tmx_path_str = str(tmx_path)
        self._current_tmx = tmx_path_str

        self._load_into_cache(tmx_path_str)

        tile_map, scene, cm, w, h, layers_below, layers_above = self._cache[tmx_path_str]

        self.tile_map         = tile_map
        self._scene           = scene
        self.collision_mask   = cm
        self.map_pixel_width  = w
        self.map_pixel_height = h
        self._layers_below    = layers_below
        self._layers_above    = layers_above

        self._cache_above_sprites()


    def _cache_above_sprites(self) -> None:
        self._above_sprite_lists = []
        self._sprite_alpha = {}

        if self._scene is None:
            return

        for layer_name in self._layers_above:
            try:
                sprite_list = self._scene[layer_name]
                self._above_sprite_lists.append(sprite_list)
                for sprite in sprite_list:
                    sprite.alpha = ABOVE_ALPHA_OPAQUE
                    self._sprite_alpha[id(sprite)] = float(ABOVE_ALPHA_OPAQUE)
            except (KeyError, AttributeError):
                pass

    def get_fishing_area_list(self) -> Optional[arcade.SpriteList]:
        """Kembalikan SpriteList 'Fishing Area' dari scene aktif, atau None."""
        if self._scene is None:
            return None
        try:
            return self._scene[LAYER_FISHING_AREA]
        except (KeyError, AttributeError):
            return None

    def update_above_transparency(
        self,
        player_x: float,
        player_y: float,
        player_w: float,
        player_h: float,
    ) -> None:
        if not self._above_sprite_lists:
            return

        p_left   = player_x - player_w * 0.5
        p_right  = player_x + player_w * 0.5
        p_bottom = player_y - player_h * 0.5
        p_top    = player_y + player_h * 0.5

        for sprite_list in self._above_sprite_lists:
            for sprite in sprite_list:
                overlaps = not (
                    sprite.right  <= p_left  or
                    sprite.left   >= p_right or
                    sprite.top    <= p_bottom or
                    sprite.bottom >= p_top
                )

                target  = float(ABOVE_ALPHA_TRANSPARENT if overlaps else ABOVE_ALPHA_OPAQUE)
                current = self._sprite_alpha.get(id(sprite), float(ABOVE_ALPHA_OPAQUE))

                if current < target:
                    current = min(current + ABOVE_FADE_SPEED, target)
                elif current > target:
                    current = max(current - ABOVE_FADE_SPEED, target)

                self._sprite_alpha[id(sprite)] = current
                sprite.alpha = int(current)

    def draw_below_player(self) -> None:
        if self._scene is None:
            return
        for layer_name in self._layers_below:
            self._draw_layer(layer_name)

    def draw_above_player(self) -> None:
        if self._scene is None:
            return
        for layer_name in self._layers_above:
            self._draw_layer(layer_name)

    def _draw_layer(self, name: str) -> None:
        if self._scene is None:
            return
        try:
            self._scene[name].draw(pixelated=True)
        except (KeyError, AttributeError):
            pass

    @property
    def current_map_path(self) -> str:
        return self._current_tmx

    @property
    def loaded(self) -> bool:
        return self.tile_map is not None
