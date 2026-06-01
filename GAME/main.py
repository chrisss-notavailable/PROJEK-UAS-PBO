"""
main.py — Entry point dan GameWindow

Inheritance: GameWindow mewarisi arcade.Window untuk integrasi
event-loop arcade (on_update, on_draw, on_key_press, dll.).

Polymorphism: interactable areas (FishingArea, PlantableArea,
WaterTakeArea, dll.) dipanggil seragam via is_nearby() dan
get_prompt_text() — GameWindow tidak perlu tahu jenis spesifiknya.

Polymorphism: AbstractSlotContainer (InventoryUI, HotbarUI) dipanggil
seragam via try_stack() dan try_place_empty() di _auto_fill_item().

Composition: GameWindow mengomposisi sistem-sistem terpisah
(FarmingSystem, NightLighting, AudioManager, MapManager, Player)
daripada mewarisi semuanya — menjaga Single Responsibility.
"""
import os
import math
import xml.etree.ElementTree as ET
import arcade
import random
import pygame
from pathlib import Path

from pygame_ui import FIndicator, HUD, InventoryUI, HotbarUI, GoldHUD, SellConfirmUI, ShopUI, ClockPanel

from constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_TITLE,
    CAMERA_LERP_SPEED,
    STARTING_MAP,
    PLAYER_MOVEMENT_SPEED,
    MAP_LATAR_DEPAN,
    MAP_PASAR,
    MAP_JALAN1,
    MAP_PANTAI,
    MAP_PANTAI2,
    MAP_TAMAN,
    MAP_KAMAR_TIDUR,
    SCALED_TILE_SIZE,
    PIXEL_SCALE,
)
from player import Player
from map_manager import MapManager
import world_registry
from fish_popup import FishPopup, RewardGenerator
from fish import FishPool, Rarity, calculate_fish_price
from npc_dog import DogNPC, spawn_dog
from farming import FarmingSystem
from lighting import NightLighting
from interactable import (
    FishingArea, PlantableArea, WaterTakeArea, WaterPlantArea,
    SellArea, BuyArea, SleepArea, HarvestArea,
)
from audio_manager import AudioManager
from save_manager import SaveManager
from fireflies import FireflySystem
from floating_text import FloatingTextManager, FT
from rain import RainSystem


# ── SISTEM HUJAN OTOMATIS ─────────────────────────────────────────────────────
from weather_system import WeatherSystem
from opening_story import OpeningStory
from main_menu import MainMenuState


PLAYER_SPRITESHEET = None

_ALL_MAPS     = (MAP_LATAR_DEPAN, MAP_PASAR, MAP_JALAN1, MAP_PANTAI, MAP_PANTAI2, MAP_TAMAN, MAP_KAMAR_TIDUR)
_FISHING_MAPS = (MAP_LATAR_DEPAN, MAP_PANTAI, MAP_PANTAI2)

# Map indoor — hujan tidak dirender di dalam map ini
# Tambahkan map indoor baru ke set ini jika ada di masa mendatang
_INDOOR_MAPS  = frozenset({MAP_KAMAR_TIDUR})

_UI_FONT = "assets/fonts/monogram-extended.ttf"   # font utama — konsisten dengan ClockPanel

_STATE_MAIN_MENU     = "main_menu"
_STATE_OPENING_STORY = "opening_story"
_STATE_GAMEPLAY      = "gameplay"

# _STATE_START_SCREEN dipertahankan sebagai alias untuk kompatibilitas internal
_STATE_START_SCREEN  = _STATE_MAIN_MENU

_FISH_NONE    = "none"
_FISH_CASTING = "casting"
_FISH_WAITING = "waiting"

_FISH_MINIGAME = "minigame"
_FISH_SUCCESS  = "success"
_FISH_FAIL     = "fail"

_FISH_REVERSE  = "reverse"
_FISH_ANIM_SPEED = 4


def _parse_tmx_rects(
    tmx_path:   str,
    layer_name: str,
    obj_name:   str | None = None,
    tag:        str = "[TMX]",
    recursive:  bool = False,
) -> list:
    rects: list = []
    try:
        root       = ET.parse(tmx_path).getroot()
        map_h_px   = int(root.get('height', 25)) * int(root.get('tileheight', 16))
        groups     = root.iter('objectgroup') if recursive else root.findall('objectgroup')
        for og in groups:
            if og.get('name') != layer_name:
                continue
            for obj in og.findall('object'):
                if obj_name is not None and obj.get('name') != obj_name:
                    continue
                x = float(obj.get('x', 0))
                y = float(obj.get('y', 0))
                w = float(obj.get('width',  0))
                h = float(obj.get('height', 0))
                left   = x * PIXEL_SCALE
                right  = (x + w) * PIXEL_SCALE
                bottom = (map_h_px - y - h) * PIXEL_SCALE
                top    = (map_h_px - y) * PIXEL_SCALE
                rects.append((left, right, bottom, top))
    except Exception as e:
        pass
    return rects


def _parse_plantable_rects(tmx_path: str) -> list:
    return _parse_tmx_rects(tmx_path, "Plantable", tag="[Plantable]")

def _parse_sell_rects(tmx_path: str) -> list:
    rects = _parse_tmx_rects(tmx_path, "Sell_Area", tag="[Sell]")
    return rects

def _parse_buy_rects(tmx_path: str) -> list:
    rects = _parse_tmx_rects(tmx_path, "Buy_Area", tag="[Buy]")
    return rects

def _parse_fishing_rects(tmx_path: str) -> list:
    return _parse_tmx_rects(tmx_path, "Fishing Area", tag="[Fishing]", recursive=True)

def _parse_water_rects(tmx_path: str) -> list:
    rects = _parse_tmx_rects(tmx_path, "Water", tag="[WATER]")
    return rects

def _parse_sleep_rects(tmx_path: str) -> list:
    rects = _parse_tmx_rects(tmx_path, "Sleep", tag="[Sleep]")
    if not rects:
        rects = _parse_tmx_rects(tmx_path, "Interaction", obj_name="sleep", tag="[Sleep]")
    return rects


def _parse_light_points(tmx_path: str) -> list[tuple[float, float]]:
    """
    Baca semua Point Object (Name=Lamp) dari layer 'Light' di sebuah TMX.
    Koordinat Y di-flip karena Tiled Y dari atas, Arcade dari bawah.
    """
    points: list[tuple[float, float]] = []
    try:
        root     = ET.parse(tmx_path).getroot()
        map_h_px = int(root.get('height', 25)) * int(root.get('tileheight', 16))
        for og in root.iter('objectgroup'):
            if og.get('name') != 'Light':
                continue
            for obj in og.findall('object'):
                x = float(obj.get('x', 0))
                y = float(obj.get('y', 0))
                wx = x       * PIXEL_SCALE
                wy = (map_h_px - y) * PIXEL_SCALE
                points.append((wx, wy))
    except Exception as e:
        pass
    return points


# ===========================================================================
# GameWindow
# Inheritance: mewarisi arcade.Window untuk event-loop dan rendering.
# Composition: mengomposisi Player, MapManager, FarmingSystem,
#              NightLighting, AudioManager, UI components — bukan mewarisi
#              semuanya — menjaga Single Responsibility tiap kelas.
# ===========================================================================

class GameWindow(arcade.Window):
    """
    Inheritance: mewarisi arcade.Window agar on_update(), on_draw(),
    on_key_press() dll. terdaftar otomatis ke event-loop arcade.

    Composition: GameWindow tidak mewarisi sistem game — ia memiliki
    referensi ke Player, MapManager, FarmingSystem, NightLighting,
    WeatherSystem, AudioManager, dll. Pola ini memisahkan tanggung
    jawab dan memudahkan pengujian (Single Responsibility Principle).

    Polymorphism: _interactables berisi dict AbstractInteractable.
    Semua dipanggil seragam via .is_nearby() di _check_* methods.

    Polymorphism: AbstractSlotContainer (InventoryUI, HotbarUI) dipanggil
    seragam via try_stack() dan try_place_empty() di _auto_fill_item().

    Polymorphism: AbstractPopup (SellConfirmUI, ShopUI) dipanggil
    seragam via .draw() di on_draw().
    """

    _TRANSITION_COOLDOWN_FRAMES = 45

    def __init__(self) -> None:

        super().__init__(
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
            SCREEN_TITLE,
            antialiasing=False,
        )

        self.background_color = arcade.color.BLACK

        # Composition: MapManager, Player, FarmingSystem masing-masing
        # memiliki tanggung jawab tunggal dan disusun di sini.
        self.map_manager  = MapManager()
        self.player       = Player(PLAYER_SPRITESHEET)
        self.player_list  = arcade.SpriteList()

        self.camera     = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()

        self.keys_pressed       = set()
        self._transition_cooldown = 0

        self._farming = FarmingSystem()

        # Polymorphism: semua interactable disimpan seragam via
        # AbstractInteractable dan dipanggil via is_nearby().
        self._interactables: dict[str, object] = {}

        self._show_plantable_f:   bool = False
        self._show_harvest_f:     bool = False
        self._show_fish_f:        bool = False
        self._show_water_take_f:  bool = False
        self._show_water_area_f:  bool = False
        self._show_sleep_f:       bool = False
        self._show_sell_e:        bool = False
        self._show_buy_e:         bool = False

        self._water_floats: list = []
        self._watering_anim: dict | None = None
        self._is_watering:   bool = False

        self._SLEEP_FADE_OUT_DUR: float = 1.5
        self._SLEEP_HOLD_DUR:     float = 1.0
        self._SLEEP_FADE_IN_DUR:  float = 1.5
        self._sleep_phase: str   = ""
        self._sleep_timer: float = 0.0
        self._sleep_alpha: int   = 0

        self._fishing_rects: dict = {}

        self._fish_state   = _FISH_NONE
        self._fish_frame   = 0
        self._fish_counter = 0

        self._fish_wait_timer  = 0.0
        self._fish_wait_target = 0.0

        self._fish_round     = 0
        self._fish_round_max = 3
        self._fish_success   = False

        self._indicator_y       = 0
        self._indicator_dir     = 1
        self._indicator_bounces = 0
        self._target_y          = 60

        self._tex_gauge     = None
        self._tex_indicator = None
        self._tex_line      = None

        self._popup_was_visible = False

        self._f_indicator       = FIndicator("assets/ui/interaction/f_fishing.png")
        self._f_indicator_plant = FIndicator("assets/ui/interaction/f_plant.png")
        self._hud               = HUD()
        self._clock_panel       = ClockPanel()
        self._f_prompt_time     = 0.0

        self._inventory_open = False
        self._inventory_ui   = InventoryUI()
        self._mouse_x: float = 0.0
        self._mouse_y: float = 0.0

        self._hotbar_ui = HotbarUI()

        self._gold_hud          = GoldHUD()
        self._reward_generator  = RewardGenerator()
        self._fish_popup        = FishPopup()

        _pool = FishPool()
        self._fish_name_lookup: dict = {f.name: f for f in _pool.all_fish()}
        self._known_fish_names: set  = set(self._fish_name_lookup.keys())

        self._dog_npc:  DogNPC | None = None
        self._dog_list  = arcade.SpriteList()

        self._sell_confirm_ui: SellConfirmUI = SellConfirmUI()
        self._shop_ui:         ShopUI        = ShopUI()
        self._active_shop_index: int   = 0
        self._shop_reset_timer:  float = 0.0
        self._SHOP_RESET_INTERVAL: float = 300.0

        self._shop_f_hold_timer:  float = -1.0
        self._shop_f_auto_active: bool  = False
        self._shop_f_buy_timer:   float = 0.0

        # Composition: NightLighting dikomposis ke GameWindow.
        # Semua logika shadow buffer, eraser pipeline, dan caching
        # didelegasikan ke objek NightLighting — bukan ditangani GameWindow.
        self._night_lighting = NightLighting()
        self._fireflies      = FireflySystem()
        self._ft             = FloatingTextManager()
        self._is_night: bool = False
        self._night_alpha: float = 0.0
        self._NIGHT_FADE_SPEED: float = 1.0

        self._lamp_points: dict[str, list[tuple[float, float]]] = {}

        self._audio = AudioManager()

        self._save_manager = SaveManager(self)

        # Rain visual effect
        self._rain_enabled: bool = False
        self._rain = RainSystem(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Composition: WeatherSystem dikomposis ke GameWindow (bukan diturunkan).
        # WeatherSystem bertanggung jawab tunggal: mengatur siklus hujan otomatis.
        self._weather = WeatherSystem()
        self._weather.set_callbacks(
            on_start = self._on_rain_start,
            on_stop  = self._on_rain_stop,
        )

        # Settings icon (pojok kiri bawah)
        try:
            self._settings_tex = arcade.load_texture("assets/ui/menu/SETTING.png")
        except Exception as _e:
            self._settings_tex = None

        # Menu background
        try:
            self._menu_tex = arcade.load_texture("assets/ui/menu/MENU.png")
        except Exception as _e:
            self._menu_tex = None

        # Menu buttons
        _btn_paths = {
            "resume": "assets/ui/menu/RESUME.png",
            "save":   "assets/ui/menu/SAVE.png",
            "sound":  "assets/ui/menu/SOUND.png",
            "exit1":  "assets/ui/menu/EXIT1.png",
            "exit2":  "assets/ui/menu/EXIT2.png",
        }
        self._menu_btn_textures: dict = {}
        for _key, _path in _btn_paths.items():
            try:
                self._menu_btn_textures[_key] = arcade.load_texture(_path)
            except Exception as _e:
                self._menu_btn_textures[_key] = None

        # Sound menu assets
        try:
            self._vlm_bar_tex  = arcade.load_texture("assets/ui/menu/VLM_BAR.png")
        except Exception as _e:
            self._vlm_bar_tex  = None
        try:
            self._vlm_knob_tex = arcade.load_texture("assets/ui/menu/VLM_KNOB.png")
        except Exception as _e:
            self._vlm_knob_tex = None

        self._menu_open:        bool  = False
        self._sound_menu_open:  bool  = False   # True = tampilkan sound menu, bukan main menu
        self._volume:           float = 0.5     # 0.0–1.0, default 50%
        self._knob_dragging:    bool  = False   # True saat user drag knob
        self._save_notif_timer: float = 0.0   # >0 = tampilkan "Game Saved"
        self._SAVE_NOTIF_DUR:   float = 2.0

        # --- Main Menu State ---
        # Main Menu berjalan di dalam window ini sebagai state biasa.
        # Tidak ada window terpisah; transisi cukup dengan mengganti _game_state.
        self._game_state: str = _STATE_MAIN_MENU

        self._main_menu = MainMenuState(SCREEN_WIDTH, SCREEN_HEIGHT)
        self._main_menu.on_play_callback     = self._on_main_menu_play
        self._main_menu.on_new_game_callback = self._on_main_menu_new_game
        self._main_menu.on_load_callback     = self._on_main_menu_new_game  # alias
        self._main_menu.on_exit_callback     = self._on_main_menu_exit

        # --- Opening Story State ---
        self._opening_story = OpeningStory(
            SCREEN_WIDTH, 
            SCREEN_HEIGHT, 
            "assets/ui/cerita"
        )
        self._opening_story.on_complete_callback = self._on_opening_story_complete

        self._setup()

    def _setup(self) -> None:
        self.map_manager.load(STARTING_MAP)

        for map_path in _ALL_MAPS:
            if map_path != STARTING_MAP:
                self.map_manager.preload(map_path)

        # Polymorphism: semua area interaksi dibuat dan disimpan sebagai
        # AbstractInteractable — dipanggil seragam via is_nearby().
        plantable_rects = _parse_plantable_rects(MAP_TAMAN)
        water_rects     = _parse_water_rects(MAP_TAMAN)
        sell_rects      = _parse_sell_rects(MAP_PASAR)
        buy_rects       = _parse_buy_rects(MAP_PASAR)
        sleep_rects     = _parse_sleep_rects(MAP_KAMAR_TIDUR)

        self._interactables["plantable"]   = PlantableArea(plantable_rects)
        self._interactables["water_take"]  = WaterTakeArea(water_rects)
        self._interactables["water_plant"] = WaterPlantArea(plantable_rects)
        self._interactables["sell"]        = SellArea(sell_rects)
        self._interactables["sleep"]       = SleepArea(sleep_rects)
        self._interactables["harvest"]     = HarvestArea([])

        self._buy_rects = buy_rects

        for mp in _FISHING_MAPS:
            self._fishing_rects[mp] = _parse_fishing_rects(mp)

        _LAMP_MAPS = (MAP_LATAR_DEPAN, MAP_PASAR, MAP_PANTAI2, MAP_TAMAN)
        for mp in _LAMP_MAPS:
            pts = _parse_light_points(mp)
            self._lamp_points[mp] = pts


        self._tex_gauge     = arcade.load_texture("assets/ui/Fishing/gauge1.png")
        self._tex_indicator = arcade.load_texture("assets/ui/Fishing/indikator1.png")
        self._tex_line      = arcade.load_texture("assets/ui/Fishing/line1.png")

        self.player.center_x = self.map_manager.map_pixel_width  / 2
        self.player.center_y = self.map_manager.map_pixel_height / 2

        self.player_list.clear()
        self.player_list.append(self.player)

        self._spawn_dog()
        self._snap_camera()
        self._audio.play_bgm("bgm1", loops=-1, fade_ms=0)
        # Terapkan master volume default (50%) ke seluruh audio sejak awal
        self._audio.set_master_volume(self._volume)

    def _on_opening_story_complete(self) -> None:
        """Callback ketika opening story selesai — lanjut ke gameplay."""
        self._game_state = _STATE_GAMEPLAY

    # ── Rain Callbacks ──────────────────────────────────────────────────────

    def _on_rain_start(self) -> None:
        """Dipanggil WeatherSystem saat hujan mulai."""
        self._rain_enabled = True
        self._audio.play("rain", loops=-1)

    def _on_rain_stop(self) -> None:
        """Dipanggil WeatherSystem saat hujan berhenti."""
        self._rain_enabled = False
        self._audio.stop("rain")

    # ── Main Menu Callbacks ───────────────────────────────────────────────────

    def _on_main_menu_play(self) -> None:
        """PLAY: load save terakhir lalu langsung gameplay.
        Jika tidak ada save, tampilkan notifikasi dan tetap di Main Menu.
        """
        if not self._save_manager.has_save():
            self._main_menu.show_no_save()
            return
        self._save_manager.load_game()
        self._game_state = _STATE_GAMEPLAY

    def _on_main_menu_new_game(self) -> None:
        """NEW GAME: jalankan opening story terlebih dahulu."""
        self._game_state = _STATE_OPENING_STORY

    def _on_main_menu_exit(self) -> None:
        """EXIT: tutup aplikasi."""
        self.close()

    def _spawn_dog(self) -> None:
        if self._dog_npc is not None:
            try:
                self.player_list.remove(self._dog_npc)
            except ValueError:
                pass

        self._dog_list.clear()
        self._dog_npc = None

        if self.map_manager.current_map_path != MAP_LATAR_DEPAN:
            return

        self._dog_npc = spawn_dog(
            collision_mask = self.map_manager.collision_mask,
            map_w          = self.map_manager.map_pixel_width,
            map_h          = self.map_manager.map_pixel_height,
            near_x         = self.player.center_x,
            near_y         = self.player.center_y,
        )

        if self._dog_npc is None:
            return

        self.player_list.append(self._dog_npc)

    def _snap_camera(self) -> None:
        self.camera.position = self._target_camera_pos()

    def _target_camera_pos(self) -> tuple[float, float]:
        tx = self.player.center_x
        ty = self.player.center_y

        half_w = SCREEN_WIDTH  / 2
        half_h = SCREEN_HEIGHT / 2

        map_w = self.map_manager.map_pixel_width
        map_h = self.map_manager.map_pixel_height

        tx = max(half_w, min(tx, map_w - half_w)) if map_w > SCREEN_WIDTH  else map_w / 2
        ty = max(half_h, min(ty, map_h - half_h)) if map_h > SCREEN_HEIGHT else map_h / 2

        return tx, ty

    def _player_screen_pos(self, offset_y: float = 48.0) -> tuple[float, float]:
        """Kembalikan posisi player dalam GUI-space (layar), dengan offset Y ke atas."""
        cam_x, cam_y = self.camera.position
        sx = self.player.center_x - cam_x + SCREEN_WIDTH  / 2
        sy = self.player.center_y - cam_y + SCREEN_HEIGHT / 2 + offset_y
        return sx, sy

    def _update_camera(self) -> None:
        tx, ty = self._target_camera_pos()
        cx, cy = self.camera.position
        a = CAMERA_LERP_SPEED
        self.camera.position = (cx + (tx - cx) * a, cy + (ty - cy) * a)

    def on_key_press(self, key: int, modifiers: int) -> None:
        # Saat main menu aktif — teruskan ke MainMenuState
        if self._game_state == _STATE_MAIN_MENU:
            # Konversi arcade key → pygame key untuk ESC
            import pygame as _pygame
            if key == arcade.key.ESCAPE:
                self._main_menu.on_key_press(_pygame.K_ESCAPE)
            return

        # Saat opening story: F untuk skip semua
        if self._game_state == _STATE_OPENING_STORY:
            if key == arcade.key.F:
                self._opening_story.skip_all()
            return

        self.keys_pressed.add(key)

        if self._sleep_phase:
            return

        if key == arcade.key.ESCAPE:
            if self._sound_menu_open:
                self._sound_menu_open = False   # kembali ke main menu, bukan tutup menu
                self._knob_dragging   = False
                return
            if self._menu_open:
                self._menu_open = False          # tutup main menu → kembali ke gameplay
                return
            if self._shop_ui.is_visible:
                self._shop_ui.hide()
                self._shop_f_hold_timer  = -1.0
                self._shop_f_auto_active = False
                self._shop_f_buy_timer   = 0.0
                self._audio.play_once("interact")
                return
            if self._sell_confirm_ui.is_visible:
                self._sell_confirm_ui.hide()
                self._audio.play_once("interact")
                return
            if self._inventory_open:
                self._inventory_open = False
                return
            return

        if key == arcade.key.F5:
            self._save_manager.save_game()
            _sx = SCREEN_WIDTH / 2
            _sy = self.height - 60
            self._ft.spawn("Game Saved", _sx, _sy, FT.SAVE)
            return

        if key == arcade.key.F9:
            self._save_manager.load_game()
            return

        if key == arcade.key.F11:
            self.set_fullscreen(not self.fullscreen)
            self._snap_camera()

        if key == arcade.key.N:
            if self._is_night_time():
                self._clock_panel._game_hour   = 7
                self._clock_panel._game_minute = 0
            else:
                self._clock_panel._game_hour   = 19
                self._clock_panel._game_minute = 0
            self._is_night = self._is_night_time()
            state = "Night" if self._is_night else "Day"

        if key == arcade.key.TAB:
            self._inventory_open = not self._inventory_open
            return

        if key == arcade.key.L:
            # Debug toggle — WeatherSystem mengurus audio + visual sekaligus
            self._weather.toggle()
            return

        _HOTBAR_KEYS = {
            arcade.key.KEY_1: 0,
            arcade.key.KEY_2: 1,
            arcade.key.KEY_3: 2,
            arcade.key.KEY_4: 3,
            arcade.key.KEY_5: 4,
        }
        if key in _HOTBAR_KEYS:
            self._hotbar_ui.select_slot(_HOTBAR_KEYS[key])
            return

        if self._fish_popup.is_visible:
            self._fish_popup.on_key_press(key)
            return

        if key == arcade.key.F:
            self._do_world_interact()

        if key == arcade.key.E:
            if self._sleep_phase:
                return
            if self._sell_confirm_ui.is_visible:
                self._sell_confirm_ui.hide()
                self._audio.play_once("interact")
                return
            if self._show_sell_e:
                self._sell_confirm_ui.show()
                self._audio.play_once("interact")
                return

        if key == arcade.key.E:
            if self._shop_ui.is_visible:
                self._shop_ui.hide()
                self._shop_f_hold_timer  = -1.0
                self._shop_f_auto_active = False
                self._shop_f_buy_timer   = 0.0
                self._audio.play_once("interact")
                return
            if self._show_buy_e:
                self._shop_ui.show(self._active_shop_index)
                self._audio.play_once("interact")
                return

        if key == arcade.key.E:
            if self._show_sleep_f and not self._sleep_phase:
                self._do_sleep()
                return

    def _do_world_interact(self) -> None:
        """Single source of truth untuk world interaction (F key & Mouse Left Click)."""
        if self._shop_ui.is_visible:
            inv_key = self._shop_ui.try_purchase(self._gold_hud)
            if inv_key is not None:
                self._auto_fill_item(inv_key)
                self._audio.play_once("buy")
            self._shop_f_hold_timer  = 0.0
            self._shop_f_auto_active = False
            self._shop_f_buy_timer   = 0.0
            return

        if self._sell_confirm_ui.is_visible:
            self._sell_all_fish()
            return

        if self._fish_state == _FISH_CASTING:
            self._reset_fishing()
            self._audio.stop("waiting")
            return

        elif self._fish_state == _FISH_WAITING:
            self._reset_fishing()
            self._audio.stop("waiting")
            return

        elif self._fish_state == _FISH_NONE and self._show_fish_f:
            self._fish_state = _FISH_CASTING
            self._fish_frame = 0
            self._fish_counter = 0
            self.player.fishing = True
            self._audio.play_once("casting")
            return

        elif self._fish_state == _FISH_MINIGAME:
            _TOLERANCE = 6
            ind_bottom = -22 + self._indicator_y * 0.975
            ind_top    = ind_bottom + 32
            line_bottom = self._target_y
            line_top    = self._target_y + 4

            if (ind_bottom - _TOLERANCE) <= line_top and (ind_top + _TOLERANCE) >= line_bottom:
                self._fish_round += 1
                self._audio.play_once("waiting")
                self._indicator_bounces = 0
                self._indicator_y       = 0
                self._indicator_dir     = 1
                self._target_y = random.randint(-90, 90)
            else:
                self._target_y = random.randint(-90, 90)

            if self._fish_round >= self._fish_round_max:
                self._fish_state = _FISH_SUCCESS

            return

        elif self._show_harvest_f:
            harvested = self._farming.harvest_plant(
                self.player.center_x,
                self.player.center_y,
                self._inventory_ui,
                self._hotbar_ui,
            )
            if harvested:
                self._audio.play_once("harvest")
                # Floating text: nama crop + qty acak (ambil dari yield terakhir)
                from farming import _HARVEST_YIELD
                import random as _rnd
                _ymin, _ymax = _HARVEST_YIELD.get(harvested, (1, 1))
                _qty = _rnd.randint(_ymin, _ymax)
                _name = harvested.capitalize()
                _sx, _sy = self._player_screen_pos(56)
                self._ft.spawn(f"+{_qty} {_name}", _sx, _sy, FT.ITEM)
            return

        elif self._show_plantable_f:
            plantable = self._interactables["plantable"]
            planted = self._farming.try_plant(
                self.player.center_x,
                self.player.center_y,
                plantable.rects,
                self._inventory_ui,
                self._hotbar_ui,
            )
            if planted:
                self._audio.play_once("plant")
            return

        elif self._show_water_take_f:
            self._do_take_water()
            return

        elif self._show_water_area_f and not self._is_watering:
            self._do_water_area()
            return

        elif self._show_sleep_f and not self._sleep_phase:
            return

    def _reset_fishing(self) -> None:
        self._fish_state        = _FISH_NONE
        self._fish_frame        = 0
        self._fish_counter      = 0
        self._fish_wait_timer   = 0.0
        self._fish_wait_target  = 0.0
        self._indicator_y       = 0
        self._indicator_dir     = 1
        self._indicator_bounces = 0
        self.player.fishing     = False
        self.player.is_moving   = False

    def on_key_release(self, key: int, modifiers: int) -> None:
        self.keys_pressed.discard(key)

        if key == arcade.key.F:
            self._shop_f_hold_timer  = -1.0
            self._shop_f_auto_active = False
            self._shop_f_buy_timer   = 0.0

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        self.camera.match_window()
        self.gui_camera.match_window()
        self._snap_camera()

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        self._mouse_x = x
        self._mouse_y = y
        # Forward ke main menu untuk hover efek tombol
        if self._game_state == _STATE_MAIN_MENU:
            self._main_menu.on_mouse_motion(x, y)
        if self._knob_dragging:
            geo = self._get_slider_geometry()
            if geo is not None:
                raw = (x - geo["rail_lx"]) / geo["rail_w"]
                self._volume = max(0.0, min(1.0, raw))
                # Real-time: langsung terapkan ke audio manager
                self._audio.set_master_volume(self._volume)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        self._knob_dragging = False

    def _clear_both_selections(self) -> None:
        self._inventory_ui.clear_selection()
        self._hotbar_ui.clear_selection()

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        # Saat main menu aktif — teruskan ke MainMenuState
        if self._game_state == _STATE_MAIN_MENU:
            if button == arcade.MOUSE_BUTTON_LEFT:
                self._main_menu.on_mouse_press(x, y)
            return

        # Saat opening story: Right Click untuk lanjut ke image berikutnya
        if self._game_state == _STATE_OPENING_STORY:
            if button == arcade.MOUSE_BUTTON_RIGHT:
                self._opening_story.next_image()
            return

        # Hitbox settings icon (pojok kiri bawah, 64x64, margin 16)
        _ICON_SIZE = 64
        _MARGIN    = 16
        _icon_cx   = _MARGIN + _ICON_SIZE / 2
        _icon_cy   = _MARGIN + _ICON_SIZE / 2
        if (abs(x - _icon_cx) <= _ICON_SIZE / 2 and
                abs(y - _icon_cy) <= _ICON_SIZE / 2):
            self._menu_open = not self._menu_open
            return

        # Saat menu terbuka, proses klik tombol menu
        if self._menu_open:
            # Saat sound menu aktif, cek drag knob
            if self._sound_menu_open:
                geo = self._get_slider_geometry()
                if geo is not None:
                    knob_cx = geo["rail_lx"] + geo["rail_w"] * self._volume
                    knob_cy = geo["bar_cy"]
                    hw = geo["knob_w"] / 2 + 6   # sedikit toleransi klik
                    hh = geo["knob_h"] / 2 + 6
                    if abs(x - knob_cx) <= hw and abs(y - knob_cy) <= hh:
                        self._knob_dragging = True
                return
            _btn_rects = self._get_menu_btn_rects()
            # RESUME
            lx, ly, rw, rh = _btn_rects["resume"]
            if lx <= x <= lx + rw and ly <= y <= ly + rh:
                self._menu_open = False
                return
            # SAVE
            lx, ly, rw, rh = _btn_rects["save"]
            if lx <= x <= lx + rw and ly <= y <= ly + rh:
                self._save_manager.save_game()
                self._save_notif_timer = self._SAVE_NOTIF_DUR
                _sx = SCREEN_WIDTH / 2
                _sy = self.height - 60
                self._ft.spawn("Game Saved", _sx, _sy, FT.SAVE)
                return
            # SOUND
            lx, ly, rw, rh = _btn_rects["sound"]
            if lx <= x <= lx + rw and ly <= y <= ly + rh:
                self._sound_menu_open = True
                return
            # EXIT1 — simpan lalu keluar ke desktop
            lx, ly, rw, rh = _btn_rects["exit1"]
            if lx <= x <= lx + rw and ly <= y <= ly + rh:
                self._save_manager.save_game()
                self.close()
                return
            # EXIT2 — simpan lalu kembali ke Main Menu
            lx, ly, rw, rh = _btn_rects["exit2"]
            if lx <= x <= lx + rw and ly <= y <= ly + rh:
                self._save_manager.save_game()
                self._menu_open       = False
                self._sound_menu_open = False
                # Reset main menu state agar tampil segar kembali
                self._main_menu = MainMenuState(SCREEN_WIDTH, SCREEN_HEIGHT)
                self._main_menu.on_play_callback     = self._on_main_menu_play
                self._main_menu.on_new_game_callback = self._on_main_menu_new_game
                self._main_menu.on_load_callback     = self._on_main_menu_new_game  # alias
                self._main_menu.on_exit_callback     = self._on_main_menu_exit
                self._game_state = _STATE_MAIN_MENU
                return
            return

        if self._shop_ui.is_visible:
            self._shop_ui.on_mouse_press(x, y, self.width, self.height)
            return

        if self._inventory_open:
            inv_sel     = self._inventory_ui._selected
            hb_sel      = self._hotbar_ui.selected_slot
            inv_clicked = self._inventory_ui._hit_slot(x, y, self.width, self.height)
            hb_clicked  = self._hotbar_ui.get_slot_at(x, y, self.width, self.height)

            if hb_sel is not None and inv_clicked is not None:
                hotbar_item = self._hotbar_ui._slot_items[hb_sel]
                if hotbar_item is not None:
                    inv_item = self._inventory_ui._items[inv_clicked]
                    if inv_item is None:
                        self._inventory_ui._items[inv_clicked] = hotbar_item
                        self._hotbar_ui._slot_items[hb_sel] = None
                    else:
                        self._hotbar_ui._slot_items[hb_sel] = inv_item
                        self._inventory_ui._items[inv_clicked] = hotbar_item
                    self._clear_both_selections()
                    return
                self._clear_both_selections()

            if inv_sel is not None and hb_clicked is not None:
                saved_inv_sel = inv_sel
                item = self._inventory_ui.remove_selected_item()
                if item is not None:
                    old_item = self._hotbar_ui.assign_item(hb_clicked, item)
                    if old_item is not None:
                        self._inventory_ui._items[saved_inv_sel] = old_item
                self._clear_both_selections()
                return

            if inv_clicked is not None:
                self._inventory_ui.on_mouse_press(x, y, self.width, self.height)
                self._hotbar_ui.clear_selection()
                return

            if hb_clicked is not None:
                self._hotbar_ui.on_mouse_press(x, y, self.width, self.height)
                self._inventory_ui.clear_selection()
                return

            return

        self._hotbar_ui.on_mouse_press(x, y, self.width, self.height)

        # Mouse Left Click = F (world interact), hanya saat tidak ada UI aktif.
        # Guard: semua UI sudah ditangani di atas (early return),
        # sehingga kode ini hanya tercapai saat gameplay aktif.
        if button == arcade.MOUSE_BUTTON_LEFT and not self._sleep_phase:
            self._do_world_interact()

    def _auto_fill_item(self, name: str, weight: float = 0.0) -> None:
        """
        Polymorphism: AbstractSlotContainer.try_stack() dan try_place_empty()
        dipanggil seragam — tidak perlu membedakan InventoryUI dan HotbarUI.
        """
        if self._hotbar_ui.try_stack(name, weight):
            return
        if self._inventory_ui.try_stack(name, weight):
            return
        if self._hotbar_ui.try_place_empty(name, weight):
            return
        self._inventory_ui.try_place_empty(name, weight)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        if self._inventory_open:
            self._inventory_ui.on_scroll(scroll_y)

    def on_update(self, delta_time: float) -> None:
        # Saat main menu aktif, update MainMenuState saja
        if self._game_state == _STATE_MAIN_MENU:
            self._main_menu.update(delta_time)
            return

        # Saat opening story aktif, update opening story saja
        if self._game_state == _STATE_OPENING_STORY:
            self._opening_story.update(delta_time)
            return

        if self._fish_popup.is_visible:
            self._popup_was_visible = True
            return

        if self._popup_was_visible:
            self._popup_was_visible = False
            self._fish_state   = _FISH_CASTING
            self._fish_frame   = 0
            self._fish_counter = 0
            self.player.fishing = True

        if self._shop_ui.is_visible:
            self.player.change_x = 0.0
            self.player.change_y = 0.0
            self.player.is_moving = False
            self.player.update()

            if self._shop_f_hold_timer >= 0.0:
                self._shop_f_hold_timer += delta_time

                if not self._shop_f_auto_active:
                    if self._shop_f_hold_timer >= 0.5:
                        self._shop_f_auto_active = True
                        self._shop_f_buy_timer   = 0.2
                else:
                    self._shop_f_buy_timer += delta_time
                    if self._shop_f_buy_timer >= 0.2:
                        self._shop_f_buy_timer -= 0.2
                        inv_key = self._shop_ui.try_purchase(self._gold_hud)
                        if inv_key is not None:
                            self._auto_fill_item(inv_key)
                            self._audio.play_once("buy")
        elif self._menu_open:
            self.player.change_x = 0.0
            self.player.change_y = 0.0
            self.player.is_moving = False
            self.player.update()
        elif self._sleep_phase:
            self.player.change_x = 0.0
            self.player.change_y = 0.0
            self.player.is_moving = False
            self.player.update()
        else:
            self.player.process_keys(self.keys_pressed)
            self.player.move_with_collision(self.map_manager.collision_mask)
            self.player.update()

        self.map_manager.update_above_transparency(
            player_x = self.player.center_x,
            player_y = self.player.center_y,
            player_w = self.player.width,
            player_h = self.player.height,
        )

        self._check_transition()
        self._check_plantable()
        self._check_harvest()
        self._farming.update(delta_time)
        self._check_fishing_area()
        self._update_fishing()
        self._check_kamar_exit()
        self._check_sleep_interaction()
        self._check_sell_area()
        self._check_buy_area()

        self._check_water_take()
        self._check_water_area_prompt()
        self._update_water_floats(delta_time)
        self._update_watering_anim(delta_time)
        self._update_sleep(delta_time)

        self._shop_reset_timer += delta_time
        if self._shop_reset_timer >= self._SHOP_RESET_INTERVAL:
            self._shop_reset_timer -= self._SHOP_RESET_INTERVAL
            self._shop_ui.reset_all_stocks()

        if self._dog_npc is not None:
            self._dog_npc.update_npc(
                delta_time     = delta_time,
                collision_mask = self.map_manager.collision_mask,
                map_w          = self.map_manager.map_pixel_width,
                map_h          = self.map_manager.map_pixel_height,
            )

        self._update_camera()
        self._update_footsteps()

        self._clock_panel.update(delta_time)

        if self._save_notif_timer > 0:
            self._save_notif_timer = max(0.0, self._save_notif_timer - delta_time)

        self._is_night = self._is_night_time()

        target = 1.0 if self._is_night else 0.0
        step = delta_time / max(self._NIGHT_FADE_SPEED, 0.001)
        if self._night_alpha < target:
            self._night_alpha = min(self._night_alpha + step, target)
        elif self._night_alpha > target:
            self._night_alpha = max(self._night_alpha - step, target)

        # Fireflies — hanya aktif saat malam, tidak aktif di dalam kamar
        _in_kamar = self.map_manager.current_map_path == MAP_KAMAR_TIDUR
        self._fireflies.update(
            delta_time  = delta_time,
            night_alpha = 0.0 if _in_kamar else self._night_alpha,
            player_x    = self.player.center_x,
            player_y    = self.player.center_y,
        )

        self._ft.update(delta_time)

        if self._rain_enabled:
            self._rain.update(delta_time)

        # ── Update sistem hujan otomatis (hanya saat gameplay) ──
        if self._game_state == _STATE_GAMEPLAY:
            self._weather.update(delta_time)

    def _update_footsteps(self) -> None:
        in_kamar = self.map_manager.current_map_path == MAP_KAMAR_TIDUR
        active   = "footsteps_kamar" if in_kamar else "footsteps"
        inactive = "footsteps"       if in_kamar else "footsteps_kamar"

        self._audio.stop(inactive)

        if self.player.is_moving:
            self._audio.play(active)
        else:
            self._audio.stop(active)

    def _get_front_tile_pos(self) -> tuple[float, float]:
        px   = self.player.center_x
        py   = self.player.center_y
        step = SCALED_TILE_SIZE
        if self.player.facing == self.player.DIR_DOWN:
            return px, py - step
        if self.player.facing == self.player.DIR_UP:
            return px, py + step
        if self.player.facing == self.player.DIR_LEFT:
            return px - step, py
        return px + step, py

    def _check_plantable(self) -> None:
        if self.map_manager.current_map_path != MAP_TAMAN:
            self._show_plantable_f = False
            return

        if not self._has_active_seed():
            self._show_plantable_f = False
            return

        # Polymorphism: PlantableArea.is_nearby() dipanggil via AbstractInteractable
        plantable = self._interactables["plantable"]
        self._show_plantable_f = plantable.is_nearby(
            self.player.center_x,
            self.player.center_y,
            farming=self._farming,
        )

    _SEED_KEYS: frozenset = frozenset({
        "CARROT_SEED", "RADISH_SEED", "CORN_SEED",
        "TOMATO_SEED", "PUMPKIN_SEED", "WATERMELON_SEED",
        "DAISY_SEED",  "TULIP_SEED",   "ROSE_SEED",
        "LAVENDER_SEED", "SUNFLOWER_SEED", "LILY_SEED",
    })

    def _has_active_seed(self) -> bool:
        hb_sel = self._hotbar_ui.selected_slot
        if hb_sel is not None:
            item = self._hotbar_ui._slot_items[hb_sel]
            if item is not None and item["name"] in self._SEED_KEYS:
                return True
        inv_sel = self._inventory_ui._selected
        if inv_sel is not None and inv_sel < len(self._inventory_ui._items):
            item = self._inventory_ui._items[inv_sel]
            if item is not None and item["name"] in self._SEED_KEYS:
                return True
        return False

    def _check_harvest(self) -> None:
        if self.map_manager.current_map_path != MAP_TAMAN:
            self._show_harvest_f = False
            return
        # Polymorphism: HarvestArea.is_nearby() didelegasikan ke farming system
        harvest = self._interactables["harvest"]
        self._show_harvest_f = harvest.is_nearby(
            self.player.center_x,
            self.player.center_y,
            farming=self._farming,
        )

    def _check_fishing_area(self) -> None:
        if self._fish_state != _FISH_NONE:
            self._show_fish_f = False
            return
        cur   = self.map_manager.current_map_path
        rects = self._fishing_rects.get(cur, [])
        if not rects:
            self._show_fish_f = False
            return
        fx, fy = self._get_front_tile_pos()
        # Polymorphism: FishingArea.is_nearby() menggunakan front-tile detection
        fishing_area = FishingArea(rects)
        self._show_fish_f = fishing_area.is_nearby(
            self.player.center_x,
            self.player.center_y,
            front_x=fx,
            front_y=fy,
        )

    def _get_fishing_texture(self):
        left_facing = (self.player.facing == self.player.DIR_LEFT)
        is_casting  = self._fish_state in (_FISH_CASTING, _FISH_REVERSE)
        frames = self.player.get_fishing_frames(casting=is_casting, facing_left=left_facing)
        if not frames:
            return None
        return frames[self._fish_frame % len(frames)]

    def _update_fishing(self) -> None:
        if self._fish_state == _FISH_NONE:
            return

        tex = self._get_fishing_texture()
        if tex is not None:
            self.player.texture = tex

        self._fish_counter += 1
        if self._fish_counter < _FISH_ANIM_SPEED:
            return

        self._fish_counter = 0

        if self._fish_state == _FISH_CASTING:
            if self._fish_frame < 14:
                self._fish_frame += 1
            else:
                self._fish_state       = _FISH_WAITING
                self._fish_frame       = 0
                self._fish_wait_timer  = 0.0
                self._fish_wait_target = random.uniform(2.0, 5.0)
                self._audio.play_once("umpan")
                self._audio.play("waiting")

        elif self._fish_state == _FISH_WAITING:
            self._fish_frame = (self._fish_frame + 1) % 9
            self._fish_wait_timer += _FISH_ANIM_SPEED / 60

            if self._fish_wait_timer >= self._fish_wait_target:
                self._fish_state        = _FISH_MINIGAME
                self._fish_round        = 0
                self._indicator_y       = 0
                self._indicator_dir     = 1
                self._indicator_bounces = 0

        elif self._fish_state == _FISH_MINIGAME:
            self._fish_frame = (self._fish_frame + 1) % 9

            self._indicator_y += 8.50 * self._indicator_dir

            if self._indicator_y >= 100:
                self._indicator_y   = 100
                self._indicator_dir = -1
                self._indicator_bounces += 1
                if self._indicator_bounces >= 12:
                    self._fish_state = _FISH_FAIL

            elif self._indicator_y <= -100:
                self._indicator_y   = -100
                self._indicator_dir = 1
                self._indicator_bounces += 1
                if self._indicator_bounces >= 12:
                    self._fish_state = _FISH_FAIL

            return

        elif self._fish_state == _FISH_SUCCESS:
            reward = self._reward_generator.generate()
            self._fish_popup.show(reward)
            self._auto_fill_item(reward.fish.name, reward.weight)
            self._audio.stop("waiting")
            self._audio.play_once("reward")

            self._fish_state    = _FISH_NONE
            self.player.fishing = False
            self._fish_frame    = 0
            self._fish_counter  = 0
            self._fish_round    = 0
            self._indicator_y   = 0
            self._indicator_dir = 1
            return

        elif self._fish_state == _FISH_FAIL:
            self._fish_frame = 14
            self._fish_state = _FISH_REVERSE

        elif self._fish_state == _FISH_REVERSE:
            if self._fish_frame > 0:
                self._fish_frame -= 1
            else:
                self._fish_state      = _FISH_NONE
                self.player.fishing   = False
                self.player.is_moving = False

    def _check_transition(self) -> None:
        if self._transition_cooldown > 0:
            self._transition_cooldown -= 1
            return

        result = world_registry.check_transition(
            player_x    = self.player.center_x,
            player_y    = self.player.center_y,
            current_map = self.map_manager.current_map_path,
        )

        if result is None:
            return


        self.map_manager.load(result.target_map)

        if result.target_map == MAP_KAMAR_TIDUR:
            self.player.center_x = self.map_manager.map_pixel_width / 2
            self.player.center_y = SCALED_TILE_SIZE * 2.5
        else:
            self.player.center_x = result.spawn_x
            self.player.center_y = result.spawn_y

        self._spawn_dog()
        self._snap_camera()
        self._transition_cooldown = self._TRANSITION_COOLDOWN_FRAMES

    def _check_kamar_exit(self) -> None:
        if self.map_manager.current_map_path != MAP_KAMAR_TIDUR:
            return
        if self._transition_cooldown > 0:
            return

        map_w       = self.map_manager.map_pixel_width
        center_x    = map_w / 2
        half_3tiles = SCALED_TILE_SIZE * 1.5

        x_min = center_x - half_3tiles
        x_max = center_x + half_3tiles
        y_max = SCALED_TILE_SIZE * 1.5

        px = self.player.center_x
        py = self.player.center_y

        if x_min <= px <= x_max and py <= y_max:
            self.map_manager.load(MAP_LATAR_DEPAN)
            self.player.center_x = 167.0
            self.player.center_y = 830.0
            self._spawn_dog()
            self._snap_camera()
            self._transition_cooldown = self._TRANSITION_COOLDOWN_FRAMES

    def _check_sleep_interaction(self) -> None:
        if self.map_manager.current_map_path != MAP_KAMAR_TIDUR:
            self._show_sleep_f = False
            return
        # Polymorphism: SleepArea.is_nearby() via AbstractInteractable
        sleep = self._interactables["sleep"]
        self._show_sleep_f = sleep.is_nearby(self.player.center_x, self.player.center_y)

    def _draw_sleep_f_prompt(self) -> None:
        if not self._show_sleep_f or self._sleep_phase:
            return
        cam_x, cam_y = self.camera.position
        sx = self.player.center_x - cam_x + SCREEN_WIDTH  / 2
        sy = self.player.center_y + 36    - cam_y + SCREEN_HEIGHT / 2
        arcade.draw_text("[E] Sleep", sx, sy, (255, 220, 180, 255), font_size=13, bold=True, anchor_x="center", anchor_y="center")

    def _do_sleep(self) -> None:
        self._sleep_phase = "fade_out"
        self._sleep_timer = 0.0
        self._sleep_alpha = 0
        self.player.change_x = 0.0
        self.player.change_y = 0.0
        _sx = SCREEN_WIDTH  / 2
        _sy = SCREEN_HEIGHT / 2 + 40
        self._ft.spawn("Sleeping...", _sx, _sy, FT.SLEEP)

    def _update_sleep(self, delta_time: float) -> None:
        if not self._sleep_phase:
            return

        self._sleep_timer += delta_time

        if self._sleep_phase == "fade_out":
            progress = min(self._sleep_timer / self._SLEEP_FADE_OUT_DUR, 1.0)
            self._sleep_alpha = int(255 * progress)
            if progress >= 1.0:
                self._sleep_phase = "hold"
                self._sleep_timer = 0.0

        elif self._sleep_phase == "hold":
            self._sleep_alpha = 255
            if self._sleep_timer >= self._SLEEP_HOLD_DUR:
                if self._is_night_time():
                    self._clock_panel._game_day    = (self._clock_panel._game_day + 1) % 7
                    self._clock_panel._game_hour   = 7
                    self._clock_panel._game_minute = 0
                else:
                    self._clock_panel._game_hour   = 19
                    self._clock_panel._game_minute = 0
                self._is_night = self._is_night_time()
                self._save_manager.save_game()
                self._save_notif_timer = self._SAVE_NOTIF_DUR
                _sx = SCREEN_WIDTH / 2
                _sy = self.height - 60
                self._ft.spawn("Game Saved", _sx, _sy, FT.SAVE)
                self._sleep_phase = "fade_in"
                self._sleep_timer = 0.0

        elif self._sleep_phase == "fade_in":
            progress = min(self._sleep_timer / self._SLEEP_FADE_IN_DUR, 1.0)
            self._sleep_alpha = int(255 * (1.0 - progress))
            if progress >= 1.0:
                self._sleep_alpha = 0
                self._sleep_phase = ""

    def _draw_sleep_overlay(self) -> None:
        if not self._sleep_phase and self._sleep_alpha == 0:
            return
        arcade.draw_rect_filled(
            arcade.XYWH(self.width / 2, self.height / 2, self.width, self.height),
            (0, 0, 0, self._sleep_alpha),
        )

    def _draw_harvest_f_prompt(self) -> None:
        if not self._show_harvest_f:
            return
        cam_x, cam_y = self.camera.position
        sx = self.player.center_x - cam_x + SCREEN_WIDTH  / 2
        sy = self.player.center_y + 36    - cam_y + SCREEN_HEIGHT / 2
        arcade.draw_text(
            "[F] Harvest",
            sx, sy,
            (100, 220, 80, 255),
            font_size=13,
            bold=True,
            anchor_x="center",
            anchor_y="center",
        )

    def _has_active_water_bucket(self) -> bool:
        hb_sel = self._hotbar_ui.selected_slot
        if hb_sel is not None:
            item = self._hotbar_ui._slot_items[hb_sel]
            if item is not None and item["name"] == "WATER_BUCKET":
                return True
        inv_sel = self._inventory_ui._selected
        if inv_sel is not None and inv_sel < len(self._inventory_ui._items):
            item = self._inventory_ui._items[inv_sel]
            if item is not None and item["name"] == "WATER_BUCKET":
                return True
        return False

    def _get_water_bucket_qty(self) -> int:
        for slot in self._hotbar_ui._slot_items:
            if slot is not None and slot["name"] == "WATER_BUCKET":
                return slot["qty"]
        for slot in self._inventory_ui._items:
            if slot is not None and slot["name"] == "WATER_BUCKET":
                return slot["qty"]
        return 0

    def _consume_water_bucket(self) -> None:
        for i, slot in enumerate(self._hotbar_ui._slot_items):
            if slot is not None and slot["name"] == "WATER_BUCKET":
                slot["qty"] -= 1
                if slot["qty"] <= 0:
                    self._hotbar_ui._slot_items[i] = None
                return
        for i, slot in enumerate(self._inventory_ui._items):
            if slot is not None and slot["name"] == "WATER_BUCKET":
                slot["qty"] -= 1
                if slot["qty"] <= 0:
                    self._inventory_ui._items[i] = None
                return

    def _add_water_bucket(self, qty: int) -> None:
        for slot in self._hotbar_ui._slot_items:
            if slot is not None and slot["name"] == "WATER_BUCKET":
                slot["qty"] += qty
                return
        for slot in self._inventory_ui._items:
            if slot is not None and slot["name"] == "WATER_BUCKET":
                slot["qty"] += qty
                return
        for i, slot in enumerate(self._hotbar_ui._slot_items):
            if slot is None:
                self._hotbar_ui._slot_items[i] = {"name": "WATER_BUCKET", "qty": qty, "weight": 0.0}
                return
        for i, slot in enumerate(self._inventory_ui._items):
            if slot is None:
                self._inventory_ui._items[i] = {"name": "WATER_BUCKET", "qty": qty, "weight": 0.0}
                return

    def _check_water_take(self) -> None:
        if self.map_manager.current_map_path != MAP_TAMAN:
            self._show_water_take_f = False
            return
        if self._has_active_water_bucket():
            self._show_water_take_f = False
            return
        fx, fy = self._get_front_tile_pos()
        # Polymorphism: WaterTakeArea.is_nearby() menggunakan front-tile detection
        water_take = self._interactables["water_take"]
        self._show_water_take_f = water_take.is_nearby(
            self.player.center_x, self.player.center_y,
            front_x=fx, front_y=fy,
        )

    def _check_water_area_prompt(self) -> None:
        if self.map_manager.current_map_path != MAP_TAMAN:
            self._show_water_area_f = False
            return
        if self._is_watering:
            self._show_water_area_f = False
            return
        if not self._has_active_water_bucket():
            self._show_water_area_f = False
            return
        if self._get_water_bucket_qty() <= 0:
            self._show_water_area_f = False
            return
        # Polymorphism: WaterPlantArea.is_nearby() menggunakan inside-rect detection
        water_plant = self._interactables["water_plant"]
        self._show_water_area_f = water_plant.is_nearby(
            self.player.center_x, self.player.center_y,
        )

    def _do_take_water(self) -> None:
        self._add_water_bucket(5)
        self._audio.play_once("ambil")

    def _do_water_area(self) -> None:
        if self._is_watering:
            return

        px = self.player.center_x
        py = self.player.center_y
        water_plant = self._interactables["water_plant"]
        for left, right, bottom, top in water_plant.rects:
            if left <= px <= right and bottom <= py <= top:
                cx = (left + right) / 2.0
                cy = (bottom + top) / 2.0

                self._is_watering     = True
                self.player.watering  = True
                self.player.is_moving = False
                self._watering_anim = {
                    "frame_idx":   0,
                    "frame_timer": 0.0,
                    "frame_dur":   0.07,
                    "rect":        (left, right, bottom, top),
                    "wx":          cx,
                    "wy":          cy,
                }
                self._consume_water_bucket()
                self._audio.play_once("siram")
                return

    def _update_water_floats(self, delta_time: float) -> None:
        _FLOAT_DURATION = 1.0
        alive = []
        for f in self._water_floats:
            f["timer"] += delta_time
            progress = min(f["timer"] / _FLOAT_DURATION, 1.0)
            f["alpha"] = int(255 * (1.0 - progress))
            f["wy_off"] = progress * 20.0
            if f["timer"] < _FLOAT_DURATION:
                alive.append(f)
        self._water_floats = alive

    def _draw_water_take_prompt(self) -> None:
        if not self._show_water_take_f:
            return
        cam_x, cam_y = self.camera.position
        sx = self.player.center_x - cam_x + SCREEN_WIDTH  / 2
        sy = self.player.center_y + 36    - cam_y + SCREEN_HEIGHT / 2
        arcade.draw_text("[F] Take Water", sx, sy, (100, 200, 255, 255), font_size=13, bold=True, anchor_x="center", anchor_y="center")

    def _draw_water_area_prompt(self) -> None:
        if not self._show_water_area_f:
            return
        cam_x, cam_y = self.camera.position
        sx = self.player.center_x - cam_x + SCREEN_WIDTH  / 2
        sy = self.player.center_y + 36    - cam_y + SCREEN_HEIGHT / 2
        arcade.draw_text("[F] Water This Area", sx, sy, (100, 200, 255, 255), font_size=13, bold=True, anchor_x="center", anchor_y="center")

    def _draw_water_floats(self) -> None:
        cam_x, cam_y = self.camera.position
        for f in self._water_floats:
            sx = f["wx"] - cam_x + SCREEN_WIDTH  / 2
            sy = f["wy"] + f.get("wy_off", 0) - cam_y + SCREEN_HEIGHT / 2
            alpha = f["alpha"]
            arcade.draw_text("\U0001f4a7 -5%", sx, sy, (100, 200, 255, alpha), font_size=14, bold=True, anchor_x="center", anchor_y="center")

    def _update_watering_anim(self, delta_time: float) -> None:
        if self._watering_anim is None:
            return

        anim   = self._watering_anim
        frames = self.player.get_watering_frames()

        if not frames:
            self._finish_watering_effect(anim)
            self._watering_anim   = None
            self._is_watering     = False
            self.player.watering  = False
            return

        idx = min(anim["frame_idx"], len(frames) - 1)
        self.player.texture = frames[idx]

        anim["frame_timer"] += delta_time
        if anim["frame_timer"] >= anim["frame_dur"]:
            anim["frame_timer"] -= anim["frame_dur"]
            anim["frame_idx"]   += 1

            if anim["frame_idx"] >= len(frames):
                self._finish_watering_effect(anim)
                self._watering_anim   = None
                self._is_watering     = False
                self.player.watering  = False

    def _finish_watering_effect(self, anim: dict) -> None:
        left, right, bottom, top = anim["rect"]
        self._farming.water_area(left, right, bottom, top)
        self._water_floats.append({
            "wx":     anim["wx"],
            "wy":     anim["wy"],
            "timer":  0.0,
            "alpha":  255,
            "wy_off": 0.0,
        })

    def _check_sell_area(self) -> None:
        if self.map_manager.current_map_path != MAP_PASAR:
            self._show_sell_e = False
            return
        # Polymorphism: SellArea.is_nearby() via AbstractInteractable
        sell = self._interactables["sell"]
        self._show_sell_e = sell.is_nearby(self.player.center_x, self.player.center_y)

    def _check_buy_area(self) -> None:
        if self.map_manager.current_map_path != MAP_PASAR:
            self._show_buy_e = False
            if self._shop_ui.is_visible:
                self._shop_ui.hide()
                self._shop_f_hold_timer  = -1.0
                self._shop_f_auto_active = False
                self._shop_f_buy_timer   = 0.0
            return

        px = self.player.center_x
        py = self.player.center_y

        for idx, (left, right, bottom, top) in enumerate(self._buy_rects):
            if left <= px <= right and bottom <= py <= top:
                self._show_buy_e = True
                self._active_shop_index = idx
                return

        self._show_buy_e = False

    def _draw_buy_e_prompt(self) -> None:
        if not self._show_buy_e or self._shop_ui.is_visible:
            return
        cam_x, cam_y = self.camera.position
        sx = self.player.center_x - cam_x + SCREEN_WIDTH  / 2
        sy = self.player.center_y + 36    - cam_y + SCREEN_HEIGHT / 2
        arcade.draw_text("[E]", sx, sy, (255, 220, 60, 255), font_size=14, bold=True, anchor_x="center", anchor_y="center")

    _CROP_SELL_PRICE: dict = {
        "CARROT":     3,
        "RADISH":     3,
        "CORN":       18,
        "TOMATO":     18,
        "PUMPKIN":    20,
        "WATERMELON": 20,
        "DAISY":      3,
        "TULIP":      3,
        "ROSE":       18,
        "LAVENDER":   18,
        "SUNFLOWER":  20,
        "LILY":       20,
    }

    def _sell_all_fish(self) -> None:
        total_gold = 0

        for i, item in enumerate(self._inventory_ui._items):
            if item is None:
                continue
            name   = item.get("name", "")
            weight = item.get("weight", 0.0)
            qty    = item.get("qty", 1)

            if name in self._known_fish_names:
                fish_obj = self._fish_name_lookup[name]
                price_each = calculate_fish_price(weight, fish_obj.rarity)
                total_gold += price_each * qty
                self._inventory_ui._items[i] = None

            elif name in self._CROP_SELL_PRICE:
                total_gold += self._CROP_SELL_PRICE[name] * qty
                self._inventory_ui._items[i] = None

        for i, item in enumerate(self._hotbar_ui._slot_items):
            if item is None:
                continue
            name   = item.get("name", "")
            weight = item.get("weight", 0.0)
            qty    = item.get("qty", 1)

            if name in self._known_fish_names:
                fish_obj = self._fish_name_lookup[name]
                price_each = calculate_fish_price(weight, fish_obj.rarity)
                total_gold += price_each * qty
                self._hotbar_ui._slot_items[i] = None

            elif name in self._CROP_SELL_PRICE:
                total_gold += self._CROP_SELL_PRICE[name] * qty
                self._hotbar_ui._slot_items[i] = None

        if total_gold > 0:
            self._gold_hud.add_gold(total_gold)
            self._audio.play_once("sell")
            _sx, _sy = self._player_screen_pos(56)
            self._ft.spawn(f"+{total_gold} Gold", _sx, _sy, FT.GOLD)
        else:
            pass

        self._sell_confirm_ui.hide()

    def _draw_sell_e_prompt(self) -> None:
        if not self._show_sell_e or self._sell_confirm_ui.is_visible:
            return
        cam_x, cam_y = self.camera.position
        sx = self.player.center_x - cam_x + SCREEN_WIDTH  / 2
        sy = self.player.center_y + 36    - cam_y + SCREEN_HEIGHT / 2
        arcade.draw_text("[E]", sx, sy, (255, 220, 60, 255), font_size=14, bold=True, anchor_x="center", anchor_y="center")

    def _draw_pygame_fishing_prompt(self):
        if not self._show_fish_f or self._fish_state != _FISH_NONE:
            return
        cam_x, cam_y = self.camera.position
        sx = self.player.center_x - cam_x + SCREEN_WIDTH  / 2
        sy = self.player.center_y + 28    - cam_y + SCREEN_HEIGHT / 2
        self._f_indicator.draw(sx, sy)

    def _draw_plant_f_prompt(self) -> None:
        if not self._show_plantable_f:
            return
        cam_x, cam_y = self.camera.position
        sx = self.player.center_x - cam_x + SCREEN_WIDTH  / 2
        sy = self.player.center_y + 28    - cam_y + SCREEN_HEIGHT / 2
        self._f_indicator_plant.draw(sx, sy)

    def on_draw(self) -> None:
        self.clear()

        # Tampilkan main menu jika state adalah MAIN_MENU
        if self._game_state == _STATE_MAIN_MENU:
            self.gui_camera.use()
            self._main_menu.draw()
            return

        # Tampilkan opening story jika state adalah OPENING_STORY
        if self._game_state == _STATE_OPENING_STORY:
            self.gui_camera.use()
            self._opening_story.draw()
            return

        self.camera.use()

        self.map_manager.draw_below_player()

        if self.map_manager.current_map_path == MAP_TAMAN:
            _crop_sprites   = list(self._farming.sprites)
            _entity_sprites = list(self.player_list)
            _all_sprites    = _crop_sprites + _entity_sprites
            _all_sprites.sort(key=lambda s: s.center_y - s.height / 2.0)
            _sorted_list = arcade.SpriteList()
            for _spr in _all_sprites:
                _sorted_list.append(_spr)
            _sorted_list.draw(pixelated=True)
        else:
            self.player_list.draw(pixelated=True)

        self.map_manager.draw_above_player()

        self._draw_night_system()

        # Fireflies digambar di world-space, setelah night overlay,
        # agar kunang-kunang tampak "menembus" kegelapan malam.
        _in_kamar = self.map_manager.current_map_path == MAP_KAMAR_TIDUR
        if not _in_kamar:
            self._fireflies.draw(self._night_alpha)

        self.gui_camera.use()

        # Rain effect — screen-space, digambar sebelum UI agar tampil di bawah panel
        # Tidak dirender saat di indoor map; status hujan tetap aktif (tidak direset)
        _is_outdoor = self.map_manager.current_map_path not in _INDOOR_MAPS
        if self._rain_enabled and _is_outdoor:
            self._rain.draw()

        self._draw_hud()

        self._draw_pygame_fishing_prompt()
        self._draw_plant_f_prompt()
        self._draw_sleep_f_prompt()
        self._draw_harvest_f_prompt()
        self._draw_sell_e_prompt()
        self._draw_buy_e_prompt()
        self._draw_water_take_prompt()
        self._draw_water_area_prompt()
        self._draw_water_floats()

        # Polymorphism: AbstractPopup.draw() dipanggil seragam untuk
        # SellConfirmUI dan ShopUI — GameWindow tidak perlu tahu jenis popup-nya.
        self._sell_confirm_ui.draw(self.width, self.height)
        self._shop_ui.draw(
            self.width,
            self.height,
            refresh_remaining=self._SHOP_RESET_INTERVAL - self._shop_reset_timer,
        )

        if self._fish_state == _FISH_MINIGAME:
            gauge     = self._tex_gauge
            indikator = self._tex_indicator
            line_tex  = self._tex_line

            arcade.draw_texture_rect(gauge, arcade.LBWH(SCREEN_WIDTH - 170, SCREEN_HEIGHT / 2 - 150, 64, 300), pixelated=True)
            arcade.draw_texture_rect(indikator, arcade.LBWH(SCREEN_WIDTH - 154, SCREEN_HEIGHT / 2 - 22 + self._indicator_y * 0.975, 32, 32), pixelated=True)
            arcade.draw_texture_rect(line_tex, arcade.LBWH(SCREEN_WIDTH - 166, SCREEN_HEIGHT / 2 + self._target_y, 56, 4), pixelated=True)
            arcade.draw_text("PRESS F", SCREEN_WIDTH - 190 + SCREEN_WIDTH * 0.01, SCREEN_HEIGHT / 2 - 176, arcade.color.YELLOW, 16, font_name=_UI_FONT)

        self._fish_popup.draw()

        if self._inventory_open:
            self._inventory_ui.draw(self.width, self.height, self._mouse_x, self._mouse_y)

        self._hotbar_ui.draw(self.width, self.height, self._mouse_x, self._mouse_y)
        self._gold_hud.draw(self.width, self.height)

        self._draw_settings_icon()

        if self._menu_open:
            if self._sound_menu_open:
                self._draw_sound_menu()
            else:
                self._draw_menu()

        if self._save_notif_timer > 0:
            self._draw_save_notif()

        self._draw_sleep_overlay()

        self._ft.draw()

    def _draw_night_system(self) -> None:
        """
        Composition: mendelegasikan rendering night lighting ke NightLighting.
        GameWindow hanya menyiapkan data (night_alpha, posisi lampu, kamera)
        dan meneruskan ke _night_lighting.draw() — tidak menangani detail
        shadow buffer, eraser surface, atau texture upload sendiri.
        """
        if self._night_alpha <= 0.001:
            return
        if self.map_manager.current_map_path == MAP_KAMAR_TIDUR:
            return

        cam_x, cam_y = self.camera.position
        cur   = self.map_manager.current_map_path
        lamps = self._lamp_points.get(cur, [])

        self._night_lighting.draw(
            night_alpha          = self._night_alpha,
            lamp_world_positions = lamps,
            cam_x                = cam_x,
            cam_y                = cam_y,
            screen_w             = self.width,
            screen_h             = self.height,
        )

        a    = self._night_alpha
        WARM = [
            (10, int(200 * a), (255, 250, 200)),
            (24, int(120 * a), (255, 210, 100)),
            (44, int(55  * a), (255, 170,  60)),
        ]
        for (wx, wy) in lamps:
            for (r_w, alpha_w, col) in WARM:
                arcade.draw_circle_filled(wx, wy, r_w, (*col, alpha_w))

    def _is_night_time(self) -> bool:
        """Kembalikan True jika jam game saat ini adalah malam (19:00–06:59)."""
        h = self._clock_panel.game_hour
        return h >= 19 or h < 7

    def _draw_hud(self) -> None:
        self._clock_panel.draw(self.height)

    def _draw_settings_icon(self) -> None:
        """Render settings icon di pojok kiri bawah, di atas HUD layer."""
        if self._settings_tex is None:
            return
        _ICON_SIZE   = 64
        _MARGIN      = 16
        cx = _MARGIN + _ICON_SIZE / 2
        cy = _MARGIN + _ICON_SIZE / 2
        scale = _ICON_SIZE / max(self._settings_tex.width, self._settings_tex.height)
        arcade.draw_texture_rect(
            self._settings_tex,
            arcade.LBWH(
                cx - _ICON_SIZE / 2,
                cy - _ICON_SIZE / 2,
                _ICON_SIZE,
                _ICON_SIZE,
            ),
            pixelated=True,
        )

    def _get_menu_btn_rects(self) -> dict:
        """
        Hitung hitbox (left, bottom, width, height) tiap tombol menu.
        Logika layout identik dengan _draw_menu agar hitbox selalu sinkron.
        """
        _MENU_SCALE  = 0.31493
        menu_w = self._menu_tex.width  * _MENU_SCALE
        menu_h = self._menu_tex.height * _MENU_SCALE
        cx = self.width  / 2
        cy = self.height / 2

        _HEADER_PCT  = 0.16
        header_h     = menu_h * _HEADER_PCT
        content_top  = cy + menu_h / 2 - header_h
        content_bot  = cy - menu_h / 2

        _BTN_NATIVE_W = 2508.0
        _BTN_NATIVE_H = 627.0
        _BTN_SCALE    = 0.0849
        btn_w = _BTN_NATIVE_W * _BTN_SCALE
        btn_h = _BTN_NATIVE_H * _BTN_SCALE

        _BTN_ORDER = ["resume", "save", "sound", "exit1", "exit2"]
        n         = len(_BTN_ORDER)
        content_h = content_top - content_bot
        gap       = min((content_h - n * btn_h) / (n + 1), btn_h * 0.18)

        rects = {}
        for i, key in enumerate(_BTN_ORDER):
            btn_cy = content_top - gap * (i + 1) - btn_h * (i + 0.5)
            rects[key] = (cx - btn_w / 2, btn_cy - btn_h / 2, btn_w, btn_h)
        return rects

    def _draw_save_notif(self) -> None:
        """Tampilkan indikator 'Game Saved' di bawah panel jam selama 2 detik."""
        # Fade out di detik terakhir
        alpha = min(255, int(self._save_notif_timer / self._SAVE_NOTIF_DUR * 255 * 3))
        alpha = max(0, min(255, alpha))
        pad_x, pad_y = 18, 6
        sx = self.width / 2
        sy = self.height - 80   # tepat di bawah clock panel
        arcade.draw_rect_filled(
            arcade.XYWH(sx, sy, 160, 28),
            (30, 20, 10, min(200, alpha)),
        )
        arcade.draw_text(
            "Game Saved",
            sx, sy,
            (220, 190, 100, alpha),
            font_size=14,
            bold=True,
            anchor_x="center",
            anchor_y="center",
        )

    def _draw_menu(self) -> None:
        """Render menu background + tombol di tengah layar."""
        if self._menu_tex is None:
            return

        _MENU_SCALE   = 0.31493
        menu_w = self._menu_tex.width  * _MENU_SCALE   # 307.2
        menu_h = self._menu_tex.height * _MENU_SCALE   # 460.8
        cx = self.width  / 2
        cy = self.height / 2

        # Render panel background
        arcade.draw_texture_rect(
            self._menu_tex,
            arcade.LBWH(cx - menu_w / 2, cy - menu_h / 2, menu_w, menu_h),
            pixelated=True,
        )

        # Layout tombol di dalam panel
        # Header (MAIN MENU title) ~16% dari tinggi panel
        _HEADER_PCT  = 0.16
        _BORDER_PCT  = 0.14   # border kiri/kanan masing-masing
        header_h     = menu_h * _HEADER_PCT
        inner_w      = menu_w * (1.0 - _BORDER_PCT * 2)
        content_top  = cy + menu_h / 2 - header_h   # batas atas area konten
        content_bot  = cy - menu_h / 2              # batas bawah panel

        # Hitung ukuran tombol agar pas dengan inner width
        _BTN_NATIVE_W = 2508.0
        _BTN_NATIVE_H = 627.0
        _BTN_SCALE    = 0.0849
        btn_w     = _BTN_NATIVE_W * _BTN_SCALE
        btn_h     = _BTN_NATIVE_H * _BTN_SCALE

        _BTN_ORDER = ["resume", "save", "sound", "exit1", "exit2"]
        n          = len(_BTN_ORDER)
        content_h  = content_top - content_bot
        gap        = min((content_h - n * btn_h) / (n + 1), btn_h * 0.18)

        for i, key in enumerate(_BTN_ORDER):
            tex = self._menu_btn_textures.get(key)
            if tex is None:
                continue
            # Posisi center-y tombol dari atas ke bawah
            btn_cy = content_top - gap * (i + 1) - btn_h * (i + 0.5)
            arcade.draw_texture_rect(
                tex,
                arcade.LBWH(cx - btn_w / 2, btn_cy - btn_h / 2, btn_w, btn_h),
                pixelated=True,
            )

    def _get_slider_geometry(self) -> dict | None:
        """
        Kembalikan dict geometri slider yang konsisten antara draw dan hit-test.
        Memperhitungkan padding transparan pada VLM_BAR dan VLM_KNOB.

        BAR  (3287x478): padding kiri=96px, kanan=95px, atas=101px, bawah=86px
        KNOB (1254x1254): padding semua sisi ~337-349px

        Keys:
          bar_lx, bar_ly   — pojok kiri-bawah texture BAR di layar
          bar_w, bar_h     — ukuran render texture BAR di layar
          bar_cy           — center-Y BAR di layar (tengah konten vertikal)
          rail_lx          — X kiri rel aktif (setelah padding kiri)
          rail_rx          — X kanan rel aktif (sebelum padding kanan)
          rail_w           — lebar rel aktif
          knob_w, knob_h   — ukuran render texture KNOB di layar
        """
        if self._menu_tex is None or self._vlm_bar_tex is None:
            return None

        # --- Rasio padding dari pengukuran pixel asset asli ---
        _BAR_PAD_L_RATIO  = 96  / 3287   # 0.02921
        _BAR_PAD_R_RATIO  = 95  / 3287   # 0.02891
        _BAR_PAD_T_RATIO  = 101 / 478    # 0.21130  (untuk vertical center)
        _BAR_PAD_B_RATIO  = 86  / 478    # 0.17991

        _MENU_SCALE = 0.31493
        menu_w = self._menu_tex.width  * _MENU_SCALE
        menu_h = self._menu_tex.height * _MENU_SCALE
        cx = self.width  / 2
        cy = self.height / 2

        _HEADER_PCT = 0.16
        header_h    = menu_h * _HEADER_PCT
        content_top = cy + menu_h / 2 - header_h
        content_bot = cy - menu_h / 2

        # Judul — duplikat logika title_bot dari _draw_sound_menu
        tex_sound = self._menu_btn_textures.get("sound")
        if tex_sound is not None:
            _TITLE_W  = menu_w * 0.60
            _TITLE_H  = _TITLE_W * tex_sound.height / tex_sound.width
            title_bot = content_top - _TITLE_H - menu_h * 0.04
        else:
            title_bot = content_top - menu_h * 0.18

        _BAR_W = menu_w * 0.72
        _BAR_H = _BAR_W * self._vlm_bar_tex.height / self._vlm_bar_tex.width
        bar_cy_tex = (title_bot + content_bot) / 2 + menu_h * 0.20  # center texture
        bar_lx = cx - _BAR_W / 2
        bar_ly = bar_cy_tex - _BAR_H / 2

        # Pusat vertikal rel aktif (tengah konten BAR, bukan tengah texture)
        bar_content_top = bar_ly + _BAR_H * _BAR_PAD_T_RATIO
        bar_content_bot = bar_ly + _BAR_H * (1.0 - _BAR_PAD_B_RATIO)
        bar_cy = (bar_content_top + bar_content_bot) / 2

        # Batas horizontal rel aktif
        rail_lx = bar_lx + _BAR_W * (_BAR_PAD_L_RATIO + 0.05)
        rail_rx = bar_lx + _BAR_W * (1.0 - _BAR_PAD_R_RATIO - 0.05)
        rail_w  = rail_rx - rail_lx

        # KNOB: ukuran render = tinggi konten rel × 1.5, dikecilkan ~17% dari sebelumnya
        # Sebelumnya: knob_h = _BAR_H * 1.8  (mengacu ke texture penuh)
        # Sekarang: proporsi terhadap tinggi konten rel, lalu scale lebih kecil
        bar_content_h = bar_content_bot - bar_content_top
        knob_h = bar_content_h * 2.2   # ~17% lebih kecil dari 1.8 × _BAR_H
        knob_w = (knob_h * self._vlm_knob_tex.width / self._vlm_knob_tex.height
                  if self._vlm_knob_tex is not None else knob_h)

        return {
            "bar_lx":  bar_lx,  "bar_ly":  bar_ly,
            "bar_w":   _BAR_W,  "bar_h":   _BAR_H,
            "bar_cy":  bar_cy,
            "rail_lx": rail_lx, "rail_rx": rail_rx, "rail_w": rail_w,
            "knob_w":  knob_w,  "knob_h":  knob_h,
        }

    def _draw_sound_menu(self) -> None:
        """Render sound menu — panel MENU.png dengan judul SOUND, VLM_BAR, dan VLM_KNOB."""
        if self._menu_tex is None:
            return

        # Panel — identik dengan _draw_menu
        _MENU_SCALE = 0.31493
        menu_w = self._menu_tex.width  * _MENU_SCALE
        menu_h = self._menu_tex.height * _MENU_SCALE
        cx = self.width  / 2
        cy = self.height / 2

        arcade.draw_texture_rect(
            self._menu_tex,
            arcade.LBWH(cx - menu_w / 2, cy - menu_h / 2, menu_w, menu_h),
            pixelated=True,
        )

        # Area konten (bawah header ~16%)
        _HEADER_PCT = 0.16
        header_h    = menu_h * _HEADER_PCT
        content_top = cy + menu_h / 2 - header_h
        content_bot = cy - menu_h / 2
        content_mid = (content_top + content_bot) / 2

        # --- Judul "SOUND" ---
        tex_sound = self._menu_btn_textures.get("sound")
        if tex_sound is not None:
            # Render judul lebih kecil dari tombol biasa — 60% lebar panel
            _TITLE_W = menu_w * 0.60
            _TITLE_H = _TITLE_W * tex_sound.height / tex_sound.width
            arcade.draw_texture_rect(
                tex_sound,
                arcade.LBWH(cx - _TITLE_W / 2, content_top - _TITLE_H - menu_h * 0.04,
                             _TITLE_W, _TITLE_H),
                pixelated=True,
            )
            title_bot = content_top - _TITLE_H - menu_h * 0.04
        else:
            # Fallback teks jika texture gagal load
            arcade.draw_text(
                "SOUND",
                cx, content_top - menu_h * 0.10,
                (80, 45, 10, 255),
                font_size=18, bold=True,
                anchor_x="center", anchor_y="center",
            )
            title_bot = content_top - menu_h * 0.18

        # --- VLM_BAR + VLM_KNOB via geometry helper ---
        geo = self._get_slider_geometry()
        if geo is not None:
            bar_lx = geo["bar_lx"]; bar_ly = geo["bar_ly"]
            bar_w  = geo["bar_w"];  bar_h  = geo["bar_h"]
            bar_cy = geo["bar_cy"]
            knob_w = geo["knob_w"]; knob_h = geo["knob_h"]

            # Teks "MASTER VOLUME X%" tepat di atas bar
            vol_pct = int(round(self._volume * 100))
            arcade.draw_text(
                f"MASTER VOLUME {vol_pct}%",
                cx, bar_ly + bar_h + 10,
                (80, 45, 10, 255),
                font_size=13, bold=True,
                anchor_x="center", anchor_y="bottom",
            )

            arcade.draw_texture_rect(
                self._vlm_bar_tex,
                arcade.LBWH(bar_lx, bar_ly, bar_w, bar_h),
                pixelated=True,
            )

            if self._vlm_knob_tex is not None:
                knob_cx = geo["rail_lx"] + geo["rail_w"] * self._volume
                knob_cy = geo["bar_cy"]
                arcade.draw_texture_rect(
                    self._vlm_knob_tex,
                    arcade.LBWH(knob_cx - knob_w / 2, knob_cy - knob_h / 2,
                                knob_w, knob_h),
                    pixelated=True,
                )


def main() -> None:
    GameWindow()
    arcade.run()


if __name__ == "__main__":
    main()