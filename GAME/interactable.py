"""
interactable.py — Abstract Base Class untuk area interaksi

Abstraction: AbstractInteractable mendefinisikan kontrak (interface) yang
harus dipenuhi oleh setiap area interaksi dalam game.

Polymorphism: setiap area interaksi mengimplementasikan is_nearby() dan
get_prompt_text() dengan cara yang berbeda, tanpa if-else di pemanggil.

Hierarki:
  AbstractInteractable (ABC)
    ├── RectInteractable      – area berbasis bounding rect
    │     ├── FishingArea
    │     ├── PlantableArea
    │     ├── WaterTakeArea
    │     ├── WaterPlantArea
    │     ├── SellArea
    │     ├── BuyArea
    │     └── SleepArea
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


# ===========================================================================
# AbstractInteractable
# Abstraction: mendefinisikan kontrak umum untuk semua area interaksi
# ===========================================================================

class AbstractInteractable(ABC):
    """
    Abstract Base Class untuk seluruh area interaksi.

    Abstraction: mendefinisikan interface is_nearby() dan get_prompt_text()
    tanpa menyebutkan bagaimana detail deteksi dan prompt diimplementasikan.

    Polymorphism: pemanggil cukup panggil interactable.is_nearby(px, py)
    dan interactable.get_prompt_text() tanpa perlu tahu jenis interaktable-nya.
    """

    @abstractmethod
    def is_nearby(self, player_x: float, player_y: float, **kwargs: Any) -> bool:
        """Return True jika player berada dalam jangkauan area interaksi."""

    @abstractmethod
    def get_prompt_text(self) -> str:
        """Return teks prompt yang ditampilkan di atas kepala player."""

    @property
    def is_active(self) -> bool:
        """Override di subclass jika interactable bisa dinonaktifkan."""
        return True


# ===========================================================================
# RectInteractable
# Concrete base: interactable berbasis bounding rect
# ===========================================================================

class RectInteractable(AbstractInteractable):
    """
    Implementasi dasar AbstractInteractable berbasis daftar bounding rect.

    Inheritance: subclass dapat meng-override is_nearby() untuk logika
    deteksi yang berbeda (proximity vs. inside-rect vs. front-tile).
    """

    def __init__(self, rects: list[tuple[float, float, float, float]]) -> None:
        self._rects = rects

    @property
    def rects(self) -> list[tuple[float, float, float, float]]:
        """Encapsulation: rects diakses via property, bukan langsung."""
        return self._rects

    def is_nearby(self, player_x: float, player_y: float, **kwargs: Any) -> bool:
        for left, right, bottom, top in self._rects:
            if left <= player_x <= right and bottom <= player_y <= top:
                return True
        return False

    def get_prompt_text(self) -> str:
        return "[F]"


# ===========================================================================
# Area-area konkret
# Polymorphism: masing-masing mengimplementasikan get_prompt_text() sendiri
# ===========================================================================

class FishingArea(RectInteractable):
    """
    Polymorphism: override get_prompt_text() untuk prompt memancing.
    Override is_nearby() untuk deteksi front-tile, bukan inside-rect.
    """

    def is_nearby(self, player_x: float, player_y: float, **kwargs: Any) -> bool:
        front_x = kwargs.get("front_x", player_x)
        front_y = kwargs.get("front_y", player_y)
        for left, right, bottom, top in self._rects:
            if left <= front_x <= right and bottom <= front_y <= top:
                return True
        return False

    def get_prompt_text(self) -> str:
        return "[F] Mancing"


class PlantableArea(RectInteractable):
    """
    Polymorphism: override is_nearby() untuk proximity-based detection.
    """

    def is_nearby(self, player_x: float, player_y: float, **kwargs: Any) -> bool:
        from constants import SCALED_TILE_SIZE
        radius_sq = (SCALED_TILE_SIZE * 1.5) ** 2
        farming   = kwargs.get("farming")
        if farming is None:
            return False
        for left, right, bottom, top in self._rects:
            col_start = int(left        // SCALED_TILE_SIZE)
            col_end   = int((right - 1) // SCALED_TILE_SIZE)
            row_start = int(bottom      // SCALED_TILE_SIZE)
            row_end   = int((top   - 1) // SCALED_TILE_SIZE)
            for row in range(row_start, row_end + 1):
                for col in range(col_start, col_end + 1):
                    if farming.is_planted(col, row):
                        continue
                    cx = col * SCALED_TILE_SIZE + SCALED_TILE_SIZE / 2.0
                    cy = row * SCALED_TILE_SIZE + SCALED_TILE_SIZE / 2.0
                    if not (left <= cx <= right and bottom <= cy <= top):
                        continue
                    if (cx - player_x) ** 2 + (cy - player_y) ** 2 <= radius_sq:
                        return True
        return False

    def get_prompt_text(self) -> str:
        return "[F] Tanam"


class WaterTakeArea(RectInteractable):
    """
    Polymorphism: override is_nearby() untuk front-tile detection.
    """

    def is_nearby(self, player_x: float, player_y: float, **kwargs: Any) -> bool:
        front_x = kwargs.get("front_x", player_x)
        front_y = kwargs.get("front_y", player_y)
        for left, right, bottom, top in self._rects:
            if left <= front_x <= right and bottom <= front_y <= top:
                return True
        return False

    def get_prompt_text(self) -> str:
        return "[F] Take Water"


class WaterPlantArea(RectInteractable):
    """
    Polymorphism: override is_nearby() untuk inside-rect player detection.
    """

    def get_prompt_text(self) -> str:
        return "[F] Water This Area"


class SellArea(RectInteractable):
    """
    Polymorphism: menggunakan tombol E, bukan F.
    """

    def get_prompt_text(self) -> str:
        return "[E]"


class BuyArea(RectInteractable):
    """
    Polymorphism: menggunakan tombol E untuk membuka toko.
    """

    def get_prompt_text(self) -> str:
        return "[E]"


class SleepArea(RectInteractable):
    """
    Polymorphism: override is_nearby() untuk proximity detection.
    """

    def is_nearby(self, player_x: float, player_y: float, **kwargs: Any) -> bool:
        from constants import SCALED_TILE_SIZE
        pad = SCALED_TILE_SIZE
        for left, right, bottom, top in self._rects:
            if (left - pad <= player_x <= right + pad and
                    bottom - pad <= player_y <= top + pad):
                return True
        return False

    def get_prompt_text(self) -> str:
        return "[F] Tidur"


class HarvestArea(RectInteractable):
    """
    Polymorphism: deteksi dilakukan via farming system, bukan rect.
    """

    def is_nearby(self, player_x: float, player_y: float, **kwargs: Any) -> bool:
        farming = kwargs.get("farming")
        if farming is None:
            return False
        return farming.has_mature_plant_nearby(player_x, player_y)

    def get_prompt_text(self) -> str:
        return "[F] Harvest"
