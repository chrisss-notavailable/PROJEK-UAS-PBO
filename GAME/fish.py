"""
fish.py  –  Sistem Ikan

Hierarki OOP:
  Rarity      – Enum rarity + bobot probabilitas
  Fish        – Data satu jenis ikan (name, rarity, sprite_path)
  FishPool    – Kolam seluruh ikan; pilih rarity → pilih ikan → return Fish
  FishReward  – Hasil tangkapan (Fish + berat random)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from constants import ASSETS_DIR

_FISH_DIR: Path = ASSETS_DIR / "Fish"


# ===========================================================================
# Rarity
# Abstraction: menyembunyikan detail bobot dan harga di balik enum
# ===========================================================================

class Rarity(Enum):
    """
    Enum tingkat kelangkaan ikan.

    Abstraction: caller hanya melihat .label, .weight, .price_multiplier
    tanpa perlu tahu implementasi internal random selection.
    """
    UMUM   = ("Umum",   40, 1)
    LANGKA = ("Langka", 30, 1)
    EPIC   = ("Epic",   20, 3)
    LEGEND = ("Legend", 10, 5)

    def __init__(self, label: str, weight: int, price_multiplier: int) -> None:
        self.label            = label
        self.weight           = weight
        self.price_multiplier = price_multiplier

    @classmethod
    def all_rarities(cls) -> list["Rarity"]:
        return list(cls)

    @classmethod
    def weights(cls) -> list[int]:
        return [r.weight for r in cls.all_rarities()]

    def __repr__(self) -> str:
        return f"<Rarity.{self.name} weight={self.weight}>"


# ===========================================================================
# Fish
# Encapsulation: frozen dataclass → immutable value object
# ===========================================================================

@dataclass(frozen=True)
class Fish:
    """
    Representasi satu jenis ikan.

    Encapsulation: frozen=True → instance tidak dapat diubah setelah dibuat.
    Polymorphism dasar: __str__ dan __repr__ di-override.
    """
    name:        str
    rarity:      Rarity
    sprite_path: Path

    @classmethod
    def from_filename(cls, name: str, rarity: Rarity, filename: str) -> "Fish":
        """Factory method: buat Fish dari nama file saja."""
        return cls(
            name        = name,
            rarity      = rarity,
            sprite_path = _FISH_DIR / filename,
        )

    def __str__(self) -> str:
        return f"{self.name} [{self.rarity.label}]"

    def __repr__(self) -> str:
        return (
            f"Fish(name={self.name!r}, "
            f"rarity={self.rarity.name}, "
            f"sprite={self.sprite_path.name!r})"
        )


# ===========================================================================
# Berat dan harga ikan
# ===========================================================================

_WEIGHT_RANGE: dict[Rarity, tuple[float, float]] = {
    Rarity.UMUM:   (0.5,  3.0),
    Rarity.LANGKA: (2.5,  5.0),
    Rarity.EPIC:   (4.5,  7.0),
    Rarity.LEGEND: (7.0, 15.0),
}

_GOLD_PER_KG: int = 10


def generate_weight(rarity: Rarity) -> float:
    lo, hi = _WEIGHT_RANGE.get(rarity, (0.5, 3.0))
    return round(random.uniform(lo, hi), 1)


def calculate_fish_price(weight: float, rarity: Rarity) -> int:
    """Hitung harga jual ikan: berat × 10 × price_multiplier."""
    return int(weight * _GOLD_PER_KG * rarity.price_multiplier)


# ===========================================================================
# FishReward
# Encapsulation: weight dan price diakses via property, bukan langsung
# ===========================================================================

@dataclass
class FishReward:
    """
    Hasil satu sesi tangkapan.

    Encapsulation: field weight dan price diakses via property.
    """
    fish:   Fish
    weight: float = field(default=-1.0)

    def __post_init__(self) -> None:
        if self.weight < 0:
            self.weight = generate_weight(self.fish.rarity)

    @property
    def weight_str(self) -> str:
        return f"{self.weight:.1f}kg"

    @property
    def price(self) -> int:
        """Harga jual ikan dihitung otomatis dari berat dan rarity."""
        return calculate_fish_price(self.weight, self.fish.rarity)

    def __str__(self) -> str:
        return f"FishReward: {self.fish} | {self.weight_str}"

    def __repr__(self) -> str:
        return f"FishReward(fish={self.fish!r}, weight={self.weight})"


# ===========================================================================
# FishPool
# Abstraction: menyembunyikan detail random selection di balik pick()/catch()
# ===========================================================================

class FishPool:
    """
    Kolam seluruh ikan yang tersedia.

    Abstraction: caller cukup panggil pick() atau catch() tanpa tahu
    detail implementasi weighted random selection.
    """

    def __init__(self) -> None:
        _definitions: dict[Rarity, list[tuple[str, str]]] = {
            Rarity.LEGEND: [
                ("Sea Serpent", "SeaSerpent.png"),
                ("Leviatan",    "Leviatan.png"),
                ("Kraken",      "Kraken.png"),
            ],
            Rarity.EPIC: [
                ("Lion Fish",           "LionFish.png"),
                ("Mandarin Dragonnet",  "MandarinDragonnet.png"),
                ("Royal Gramma",        "RoyalGramma.png"),
                ("Flame Angelfish",     "Flame AngelFish.png"),
            ],
            Rarity.LANGKA: [
                ("Buntal",    "Buntal.png"),
                ("Blue Tang", "BlueTang.png"),
                ("Badut",     "Badut.png"),
                ("Koi",       "Koi.png"),
            ],
            Rarity.UMUM: [
                ("Kerapu", "Kerapu.png"),
                ("Arwana", "Arwana.png"),
                ("Lele",   "Lele.png"),
                ("Sapu",   "Sapu.png"),
                ("Nila",   "Nila.png"),
            ],
        }

        self._pool: dict[Rarity, list[Fish]] = {}
        for rarity, entries in _definitions.items():
            self._pool[rarity] = [
                Fish.from_filename(name, rarity, filename)
                for name, filename in entries
            ]

        self._rarity_order: list[Rarity] = Rarity.all_rarities()
        self._weights:       list[int]   = Rarity.weights()

    def _pick_rarity(self) -> Rarity:
        return random.choices(self._rarity_order, weights=self._weights, k=1)[0]

    def _pick_fish_from(self, rarity: Rarity) -> Fish:
        candidates = self._pool.get(rarity, [])
        if not candidates:
            raise ValueError(f"Tidak ada ikan untuk rarity {rarity!r}")
        return random.choice(candidates)

    def pick(self) -> Fish:
        rarity = self._pick_rarity()
        return self._pick_fish_from(rarity)

    def catch(self) -> FishReward:
        """Simulasi menangkap ikan; return FishReward."""
        return FishReward(fish=self.pick())

    def all_fish(self) -> list[Fish]:
        result: list[Fish] = []
        for fish_list in self._pool.values():
            result.extend(fish_list)
        return result

    def fish_by_rarity(self, rarity: Rarity) -> list[Fish]:
        return list(self._pool.get(rarity, []))

    def __repr__(self) -> str:
        counts = {r.name: len(lst) for r, lst in self._pool.items()}
        return f"FishPool({counts})"
