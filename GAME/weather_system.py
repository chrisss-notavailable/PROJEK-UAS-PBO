"""
weather_system.py — Sistem Cuaca Otomatis

Class:
    WeatherSystem

Encapsulation: state hujan (_raining, _timer) dijaga private;
               diakses hanya melalui property rain_enabled dan method publik.

Composition: GameWindow memiliki satu instance WeatherSystem (bukan
             mewarisinya), sesuai pola Single Responsibility Principle.

Penggunaan:
    from weather_system import WeatherSystem

    weather = WeatherSystem()
    weather.set_callbacks(on_start=..., on_stop=...)

    # on_update
    weather.update(delta_time)

    # cek status
    if weather.rain_enabled:
        ...
"""
from __future__ import annotations

import random


class WeatherSystem:
    """
    Mengatur hujan otomatis dengan durasi dan jeda random.

    Encapsulation: _raining dan _timer adalah state internal yang hanya
    diubah melalui _do_start() / _do_stop() — tidak diakses langsung.

    Durasi hujan : 3–7 menit  (180–420 detik)
    Jeda antar hujan: 5–15 menit (300–900 detik)

    Interface publik:
        update(dt)      — panggil tiap frame
        rain_enabled    — property bool, True jika sedang hujan
        toggle()        — debug toggle (tombol L)
        start_rain()    — paksa mulai hujan
        stop_rain()     — paksa hentikan hujan
    """

    _DUR_MIN  =  3 * 60   # 3 menit minimum durasi hujan
    _DUR_MAX  =  7 * 60   # 7 menit maksimum durasi hujan
    _COOL_MIN =  5 * 60   # 5 menit minimum jeda antar hujan
    _COOL_MAX = 15 * 60   # 15 menit maksimum jeda antar hujan

    def __init__(self) -> None:
        self._raining: bool  = False
        # Mulai dengan cooldown random agar tidak langsung hujan saat game start
        self._timer:   float = random.uniform(self._COOL_MIN, self._COOL_MAX)
        self._on_rain_start = None
        self._on_rain_stop  = None

    def set_callbacks(self, on_start, on_stop) -> None:
        """Daftarkan callback yang dipanggil saat hujan mulai/berhenti."""
        self._on_rain_start = on_start
        self._on_rain_stop  = on_stop

    def update(self, dt: float) -> None:
        """Update timer cuaca setiap frame."""
        self._timer -= dt
        if self._timer <= 0.0:
            if self._raining:
                self._do_stop()
            else:
                self._do_start()

    def _do_start(self) -> None:
        self._raining = True
        self._timer   = random.uniform(self._DUR_MIN, self._DUR_MAX)
        if self._on_rain_start:
            self._on_rain_start()

    def _do_stop(self) -> None:
        self._raining = False
        self._timer   = random.uniform(self._COOL_MIN, self._COOL_MAX)
        if self._on_rain_stop:
            self._on_rain_stop()

    @property
    def rain_enabled(self) -> bool:
        """Return True jika sedang hujan."""
        return self._raining

    def toggle(self) -> None:
        """Debug toggle — dipanggil via tombol L di GameWindow."""
        if self._raining:
            self._do_stop()
            self._timer = random.uniform(self._COOL_MIN, self._COOL_MAX)
        else:
            self._do_start()

    def start_rain(self) -> None:
        """Paksa mulai hujan (jika belum hujan)."""
        if not self._raining:
            self._do_start()

    def stop_rain(self) -> None:
        """Paksa hentikan hujan (jika sedang hujan)."""
        if self._raining:
            self._do_stop()
