from pathlib import Path

SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE  = "Farming RPG"

TILE_SIZE        = 16
PIXEL_SCALE      = 3
SCALED_TILE_SIZE = TILE_SIZE * PIXEL_SCALE

PLAYER_MOVEMENT_SPEED     = 3.5
PLAYER_SCALE              = PIXEL_SCALE
PLAYER_COLLISION_OFFSET_Y = -14

CAMERA_LERP_SPEED = 0.12

LAYER_GROUND1 = "Ground1"
LAYER_GROUND2 = "Ground2"
LAYER_PATH1   = "Path1"
LAYER_PATH2   = "Path2"
LAYER_BOTTOM1        = "Bottom1"
LAYER_BOTTOM2        = "Bottom2"
LAYER_F1             = "F1"
LAYER_F2             = "F2"
LAYER_PLANTABLE_DIRT = "Plantable Dirt"
LAYER_PLAYER         = "Player"
LAYER_ABOVE1         = "Above1"
LAYER_ABOVE2         = "Above2"

LAYERS_BELOW_PLAYER = (
    LAYER_GROUND1,
    LAYER_GROUND2,
    LAYER_PATH1,
    LAYER_PATH2,
    LAYER_BOTTOM1,
    LAYER_BOTTOM2,
    LAYER_F1,
    LAYER_F2,
    LAYER_PLANTABLE_DIRT,
)

LAYERS_ABOVE_PLAYER = (
    LAYER_ABOVE1,
    LAYER_ABOVE2,
)

ABOVE_ALPHA_OPAQUE      = 255
ABOVE_ALPHA_TRANSPARENT = 80
ABOVE_FADE_SPEED        = 18

BASE_DIR     = Path(__file__).resolve().parent
ASSETS_DIR   = BASE_DIR / "assets"
MAPS_DIR     = ASSETS_DIR / "maps"
TILESETS_DIR = ASSETS_DIR / "tilesets"

MAP_LATAR_DEPAN  = str(MAPS_DIR / "Latar_Depan.tmx")
MAP_PASAR        = str(MAPS_DIR / "Pasar.tmx")
MAP_JALAN1       = str(MAPS_DIR / "Jalan1.tmx")
MAP_PANTAI       = str(MAPS_DIR / "Pantai.tmx")
MAP_PANTAI2      = str(MAPS_DIR / "Pantai2.tmx")
MAP_TAMAN        = str(MAPS_DIR / "Taman.tmx")
MAP_KAMAR_TIDUR  = str(MAPS_DIR / "Kamar_tidur.tmx")

STARTING_MAP = MAP_KAMAR_TIDUR