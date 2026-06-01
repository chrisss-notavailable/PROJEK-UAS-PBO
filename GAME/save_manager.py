"""
save_manager.py — Sistem Save / Load

Menyimpan dan memuat state game ke/dari file savegame.json.

Data yang disimpan:
  - Player   : posisi x, posisi y, map aktif
  - Clock    : day_index, game_hour, game_minute
  - Economy  : gold
  - Inventory: seluruh item (id + quantity)
  - Hotbar   : seluruh slot (id + quantity)
  - Farming  : semua tanaman yang ditanam beserta progressnya
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameWindow

SAVE_FILE = "savegame.json"


class SaveManager:
    """
    Mengelola operasi save dan load ke/dari file savegame.json.

    Usage:
        manager = SaveManager(game_window)
        manager.save_game()
        manager.load_game()
        manager.has_save()
    """

    def __init__(self, game: "GameWindow") -> None:
        self._game = game

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def has_save(self) -> bool:
        """Return True jika file savegame.json sudah ada."""
        return Path(SAVE_FILE).exists()

    def save_game(self) -> None:
        """Simpan seluruh state game ke savegame.json."""
        data = {
            "player":        self._serialize_player(),
            "clock":         self._serialize_clock(),
            "economy":       self._serialize_economy(),
            "inventory":     self._serialize_inventory(),
            "hotbar":        self._serialize_hotbar(),
            "farming":       self._serialize_farming(),
            "master_volume": self._serialize_master_volume(),
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_game(self) -> None:
        """Muat state game dari savegame.json."""
        if not self.has_save():
            return

        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._deserialize_player(data.get("player", {}))
        self._deserialize_clock(data.get("clock", {}))
        self._deserialize_economy(data.get("economy", {}))
        self._deserialize_inventory(data.get("inventory", []))
        self._deserialize_hotbar(data.get("hotbar", []))
        self._deserialize_farming(data.get("farming", []))
        self._deserialize_master_volume(data.get("master_volume", {}))

    # -----------------------------------------------------------------------
    # Serialize helpers
    # -----------------------------------------------------------------------

    def _serialize_player(self) -> dict:
        g = self._game
        return {
            "x":        g.player.center_x,
            "y":        g.player.center_y,
            "map_path": g.map_manager.current_map_path,
        }

    def _serialize_clock(self) -> dict:
        c = self._game._clock_panel
        return {
            "day_index":   c._game_day,
            "game_hour":   c._game_hour,
            "game_minute": c._game_minute,
        }

    def _serialize_economy(self) -> dict:
        return {
            "gold": self._game._gold_hud._gold,
        }

    def _serialize_inventory(self) -> list:
        items = []
        for slot in self._game._inventory_ui._items:
            if slot is None:
                items.append(None)
            else:
                items.append({
                    "name":   slot["name"],
                    "qty":    slot["qty"],
                    "weight": slot.get("weight", 0.0),
                })
        return items

    def _serialize_hotbar(self) -> list:
        slots = []
        for slot in self._game._hotbar_ui._slot_items:
            if slot is None:
                slots.append(None)
            else:
                slots.append({
                    "name":   slot["name"],
                    "qty":    slot["qty"],
                    "weight": slot.get("weight", 0.0),
                })
        return slots

    def _serialize_farming(self) -> list:
        plants = []
        farming = self._game._farming
        for (col, row), plant in farming._plants.items():
            plants.append({
                "col":        col,
                "row":        row,
                "seed_name":  plant.seed_name,
                "stage":      plant._stage,
                "age":        plant.age,
                "t1":         plant.t1,
                "t2":         plant.t2,
                "fade_state": plant.fade_state,
                "fade_timer": plant.fade_timer,
                "next_stage": plant.next_stage,
            })
        return plants

    def _serialize_master_volume(self) -> dict:
        """Simpan nilai master volume saat ini (0.0–1.0)."""
        return {"value": self._game._volume}

    # -----------------------------------------------------------------------
    # Deserialize helpers
    # -----------------------------------------------------------------------

    def _deserialize_player(self, data: dict) -> None:
        if not data:
            return
        g = self._game
        map_path = data.get("map_path", "")
        if map_path and map_path != g.map_manager.current_map_path:
            g.map_manager.load(map_path)
            g._snap_camera()
        g.player.center_x = data.get("x", g.player.center_x)
        g.player.center_y = data.get("y", g.player.center_y)

    def _deserialize_clock(self, data: dict) -> None:
        if not data:
            return
        c = self._game._clock_panel
        c._game_day    = data.get("day_index",   c._game_day)
        c._game_hour   = data.get("game_hour",   c._game_hour)
        c._game_minute = data.get("game_minute", c._game_minute)
        # Sync is_night flag di GameWindow
        self._game._is_night = self._game._is_night_time()

    def _deserialize_economy(self, data: dict) -> None:
        if not data:
            return
        self._game._gold_hud._gold = data.get("gold", self._game._gold_hud._gold)

    def _deserialize_inventory(self, data: list) -> None:
        if not data:
            return
        inv = self._game._inventory_ui._items
        for i, slot in enumerate(data):
            if i >= len(inv):
                break
            if slot is None:
                inv[i] = None
            else:
                inv[i] = {
                    "name":   slot["name"],
                    "qty":    slot["qty"],
                    "weight": slot.get("weight", 0.0),
                }

    def _deserialize_hotbar(self, data: list) -> None:
        if not data:
            return
        hb = self._game._hotbar_ui._slot_items
        for i, slot in enumerate(data):
            if i >= len(hb):
                break
            if slot is None:
                hb[i] = None
            else:
                hb[i] = {
                    "name":   slot["name"],
                    "qty":    slot["qty"],
                    "weight": slot.get("weight", 0.0),
                }

    def _deserialize_farming(self, data: list) -> None:
        if not data:
            return
        from farming import PlantData, STAGE_1, STAGE_2, STAGE_FINAL, _FADE_IDLE
        farming = self._game._farming

        # Bersihkan semua tanaman yang ada terlebih dahulu
        farming.clear()

        for entry in data:
            col       = entry["col"]
            row       = entry["row"]
            seed_name = entry["seed_name"]

            plant            = PlantData(seed_name)
            plant._stage     = entry.get("stage",      STAGE_1)
            plant.age        = entry.get("age",        0.0)
            plant.t1         = entry.get("t1",         plant.t1)
            plant.t2         = entry.get("t2",         plant.t2)
            plant.fade_state = entry.get("fade_state", _FADE_IDLE)
            plant.fade_timer = entry.get("fade_timer", 0.0)
            plant.next_stage = entry.get("next_stage", None)

            # Buat sprite menggunakan internal method FarmingSystem
            farming._place_plant(col, row, seed_name)

            # Ganti plant yang baru dibuat dengan plant yang sudah kita restore
            farming._plants[(col, row)] = plant

            # Update texture sprite agar sesuai dengan stage yang tersimpan
            sprite = farming._tile_sprites.get((col, row))
            if sprite is not None:
                tex_key = farming._tex_key_for_stage(plant)
                tex, scale = farming._get_tex_and_scale(tex_key)
                sprite.texture  = tex
                sprite.scale    = scale
                cx, cy = farming._sprite_position(col, row, scale, tex.height)
                sprite.center_x = cx
                sprite.center_y = cy
                sprite.alpha    = 255

    def _deserialize_master_volume(self, data: dict) -> None:
        """
        Kembalikan master volume ke nilai yang tersimpan.
        Mengupdate:
          • self._game._volume  (slider visual)
          • self._game._audio   (audio manager — BGM + semua SFX)
        Default 0.5 (50%) jika key tidak ada.
        """
        if not data:
            return
        vol = float(data.get("value", 0.5))
        vol = max(0.0, min(1.0, vol))
        self._game._volume = vol
        self._game._audio.set_master_volume(vol)
