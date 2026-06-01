"""
transitions.py — Definisi Transisi Antar Map (Berbasis Koordinat)

Semua koordinat dalam world pixels (Arcade: origin bawah-kiri).

Encapsulation: TransitionDef adalah frozen dataclass — tidak dapat
diubah setelah dibuat, menjamin integritas data transisi.

Abstraction: TransitionManager menyembunyikan detail iterasi zona
di balik method check() yang mengembalikan TransitionResult atau None.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from constants import MAP_LATAR_DEPAN, MAP_PASAR

_MAP_LATAR = str(MAP_LATAR_DEPAN)
_MAP_PASAR  = str(MAP_PASAR)


@dataclass(frozen=True)
class TransitionDef:
    """
    Encapsulation: frozen dataclass menjamin data zona transisi
    tidak dapat dimodifikasi secara tidak sengaja setelah dibuat.
    """
    source_map:    str
    trigger_x_min: float
    trigger_x_max: float
    trigger_y_min: float
    trigger_y_max: float
    target_map: str
    spawn_x:    float
    spawn_y:    float


TRANSITIONS: tuple[TransitionDef, ...] = (
    TransitionDef(
        source_map    = _MAP_LATAR,
        trigger_x_min = 1898.0,
        trigger_x_max = float("inf"),
        trigger_y_min = 265.0,
        trigger_y_max = 565.0,
        target_map    = _MAP_PASAR,
        spawn_x       = 120.0,
        spawn_y       = 310.0,
    ),
    TransitionDef(
        source_map    = _MAP_PASAR,
        trigger_x_min = 0.0,
        trigger_x_max = 40.0,
        trigger_y_min = 160.0,
        trigger_y_max = 460.0,
        target_map    = _MAP_LATAR,
        spawn_x       = 1800.0,
        spawn_y       = 415.0,
    ),
)


@dataclass(frozen=True)
class TransitionResult:
    """
    Encapsulation: frozen dataclass untuk hasil transisi yang immutable.
    """
    target_map: str
    spawn_x:    float
    spawn_y:    float


class TransitionManager:
    """
    Abstraction: menyembunyikan iterasi zona transisi di balik method check().
    Caller tidak perlu tahu format internal TRANSITIONS.
    """

    def check(
        self,
        player_x:    float,
        player_y:    float,
        current_map: str,
    ) -> Optional[TransitionResult]:
        for td in TRANSITIONS:
            if td.source_map != current_map:
                continue
            if (
                td.trigger_x_min <= player_x <= td.trigger_x_max
                and td.trigger_y_min <= player_y <= td.trigger_y_max
            ):
                return TransitionResult(
                    target_map = td.target_map,
                    spawn_x    = td.spawn_x,
                    spawn_y    = td.spawn_y,
                )
        return None
