"""
world_registry.py — Registry Zona Transisi Antar Map

Encapsulation: daftar zona transisi disimpan sebagai modul-level
constant (_REGISTRY) dan hanya diakses via fungsi publik
check_transition() dan is_transition_corridor().

Abstraction: caller tidak perlu tahu format internal TransitionZone —
cukup berikan posisi player dan map saat ini, fungsi mengembalikan
TransitionResult atau None.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from constants import (
    MAP_LATAR_DEPAN, MAP_PASAR, MAP_JALAN1,
    MAP_PANTAI, MAP_PANTAI2,
    MAP_TAMAN, MAP_KAMAR_TIDUR,
    SCALED_TILE_SIZE,
)


@dataclass(frozen=True)
class TransitionResult:
    """
    Encapsulation: immutable value object untuk hasil transisi.
    """
    target_map: str
    spawn_x: float
    spawn_y: float


@dataclass(frozen=True)
class TransitionZone:
    """
    Encapsulation: frozen dataclass menjamin data zona transisi
    tidak berubah setelah inisialisasi.
    """
    from_map: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    target_map: str
    spawn_x: float
    spawn_y_mode: str
    spawn_y_fixed: float


_PASAR_LEFT_SPAWN_X   = SCALED_TILE_SIZE * 0.6
_LATAR_RIGHT_SPAWN_X  = SCALED_TILE_SIZE * 39.0
_TAMAN_RIGHT_SPAWN_X  = SCALED_TILE_SIZE * 38.0
_LATAR_LEFT_SPAWN_X   = SCALED_TILE_SIZE * 1.0
_PANTAI2_LEFT_SPAWN_X = SCALED_TILE_SIZE * 1.0
_PASAR_RIGHT_SPAWN_X  = 1890.0

_REGISTRY: list[TransitionZone] = [
    # Latar Depan ↔ Pasar
    TransitionZone(
        from_map      = MAP_LATAR_DEPAN,
        x_min         = 1890.0,
        x_max         = float("inf"),
        y_min         = 310.0,
        y_max         = 415.0,
        target_map    = MAP_PASAR,
        spawn_x       = _PASAR_LEFT_SPAWN_X,
        spawn_y_mode  = "preserve",
        spawn_y_fixed = 0.0,
    ),
    TransitionZone(
        from_map      = MAP_PASAR,
        x_min         = 0.0,
        x_max         = SCALED_TILE_SIZE * 1.5,
        y_min         = 310.0,
        y_max         = 415.0,
        target_map    = MAP_LATAR_DEPAN,
        spawn_x       = _LATAR_RIGHT_SPAWN_X,
        spawn_y_mode  = "preserve",
        spawn_y_fixed = 0.0,
    ),
    # Latar Depan ↔ Jalan1
    TransitionZone(
        from_map      = MAP_LATAR_DEPAN,
        x_min         = 1263.0,
        x_max         = 1330.0,
        y_min         = -30.0,
        y_max         = 70.0,
        target_map    = MAP_JALAN1,
        spawn_x       = 0.0,
        spawn_y_mode  = "mirror",
        spawn_y_fixed = 1120.0,
    ),
    TransitionZone(
        from_map      = MAP_JALAN1,
        x_min         = 1263.0,
        x_max         = 1330.0,
        y_min         = 1130.0,
        y_max         = float("inf"),
        target_map    = MAP_LATAR_DEPAN,
        spawn_x       = 0.0,
        spawn_y_mode  = "mirror",
        spawn_y_fixed = 80.0,
    ),
    # Jalan1 ↔ Pantai
    TransitionZone(
        from_map      = MAP_JALAN1,
        x_min         = 1260.0,
        x_max         = 1346.0,
        y_min         = -30.0,
        y_max         = 70.0,
        target_map    = MAP_PANTAI,
        spawn_x       = 0.0,
        spawn_y_mode  = "mirror",
        spawn_y_fixed = 1120.0,
    ),
    TransitionZone(
        from_map      = MAP_PANTAI,
        x_min         = 1252.0,
        x_max         = 1346.0,
        y_min         = 1130.0,
        y_max         = float("inf"),
        target_map    = MAP_JALAN1,
        spawn_x       = 0.0,
        spawn_y_mode  = "mirror",
        spawn_y_fixed = 80.0,
    ),
    # Pasar → Pantai2 : zona 1 (Y 301–434)
    TransitionZone(
        from_map      = MAP_PASAR,
        x_min         = 1907.0,
        x_max         = float("inf"),
        y_min         = 301.0,
        y_max         = 434.0,
        target_map    = MAP_PANTAI2,
        spawn_x       = _PANTAI2_LEFT_SPAWN_X,
        spawn_y_mode  = "preserve",
        spawn_y_fixed = 0.0,
    ),
    # Pasar → Pantai2 : zona 2 (Y 878–1000)
    TransitionZone(
        from_map      = MAP_PASAR,
        x_min         = 1907.0,
        x_max         = float("inf"),
        y_min         = 878.0,
        y_max         = 1000.0,
        target_map    = MAP_PANTAI2,
        spawn_x       = _PANTAI2_LEFT_SPAWN_X,
        spawn_y_mode  = "preserve",
        spawn_y_fixed = 0.0,
    ),
    # Pantai2 → Pasar : zona 1 (Y 301–434)
    TransitionZone(
        from_map      = MAP_PANTAI2,
        x_min         = 0.0,
        x_max         = SCALED_TILE_SIZE * 1.5,
        y_min         = 301.0,
        y_max         = 434.0,
        target_map    = MAP_PASAR,
        spawn_x       = _PASAR_RIGHT_SPAWN_X,
        spawn_y_mode  = "preserve",
        spawn_y_fixed = 0.0,
    ),
    # Pantai2 → Pasar : zona 2 (Y 878–1000)
    TransitionZone(
        from_map      = MAP_PANTAI2,
        x_min         = 0.0,
        x_max         = SCALED_TILE_SIZE * 1.5,
        y_min         = 878.0,
        y_max         = 1000.0,
        target_map    = MAP_PASAR,
        spawn_x       = _PASAR_RIGHT_SPAWN_X,
        spawn_y_mode  = "preserve",
        spawn_y_fixed = 0.0,
    ),
    # Latar Depan → Kamar Tidur
    TransitionZone(
        from_map      = MAP_LATAR_DEPAN,
        x_min         = 159.0,
        x_max         = 176.0,
        y_min         = 848.0,
        y_max         = float("inf"),
        target_map    = MAP_KAMAR_TIDUR,
        spawn_x       = 0.0,
        spawn_y_mode  = "fixed",
        spawn_y_fixed = 0.0,
    ),
    # Latar Depan ↔ Taman
    TransitionZone(
        from_map      = MAP_LATAR_DEPAN,
        x_min         = 0.0,
        x_max         = 13.0,
        y_min         = 680.0,
        y_max         = 828.0,
        target_map    = MAP_TAMAN,
        spawn_x       = _TAMAN_RIGHT_SPAWN_X,
        spawn_y_mode  = "preserve",
        spawn_y_fixed = 0.0,
    ),
    TransitionZone(
        from_map      = MAP_TAMAN,
        x_min         = SCALED_TILE_SIZE * 39.0,
        x_max         = float("inf"),
        y_min         = 680.0,
        y_max         = 828.0,
        target_map    = MAP_LATAR_DEPAN,
        spawn_x       = _LATAR_LEFT_SPAWN_X,
        spawn_y_mode  = "preserve",
        spawn_y_fixed = 0.0,
    ),
]


def is_transition_corridor(
    world_x: float,
    world_y: float,
    current_map: str,
) -> bool:
    for zone in _REGISTRY:
        if zone.from_map != current_map:
            continue
        if not (zone.y_min <= world_y <= zone.y_max):
            continue
        if not (zone.x_min <= world_x <= zone.x_max):
            continue
        return True
    return False


def check_transition(
    player_x: float,
    player_y: float,
    current_map: str,
) -> Optional[TransitionResult]:
    """
    Abstraction: caller cukup berikan posisi player dan map saat ini.
    Detail iterasi zona dan perhitungan spawn disembunyikan di sini.
    """
    for zone in _REGISTRY:
        if zone.from_map != current_map:
            continue
        if not (zone.x_min <= player_x <= zone.x_max):
            continue
        if not (zone.y_min <= player_y <= zone.y_max):
            continue

        if zone.spawn_y_mode == "preserve":
            spawn_y = player_y
        else:
            spawn_y = zone.spawn_y_fixed

        if zone.spawn_y_mode == "mirror":
            spawn_x = player_x
        else:
            spawn_x = zone.spawn_x

        return TransitionResult(
            target_map = zone.target_map,
            spawn_x    = spawn_x,
            spawn_y    = spawn_y,
        )
    return None
