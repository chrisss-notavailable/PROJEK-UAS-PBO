"""
fireflies.py — Efek kunang-kunang malam untuk Farming RPG

Desain:
  • Murni partikel sederhana — tidak pakai sprite, tidak pakai physics.
  • Setiap Firefly menyimpan posisi dunia (world-space) sehingga
    fireflies mengikuti kamera secara otomatis saat digambar.
  • FireflySystem mengelola spawn/despawn otomatis di sekitar player.
  • Hanya aktif saat night_alpha > 0  (tidak perlu logika jam di sini,
    caller meneruskan night_alpha dan sistem mati sendiri saat siang).

Gerakan:
  • Bukan sinus naik-turun kaku.
  • Setiap firefly punya velocity (vx, vy) yang berubah terus lewat
    steering acak — hasilnya terbang ke segala arah, berhenti sebentar,
    lalu pergi lagi. Natural seperti kunang-kunang sungguhan.

Penggunaan di main.py:
    # __init__ / setup
    from fireflies import FireflySystem
    self._fireflies = FireflySystem()

    # on_update
    self._fireflies.update(
        delta_time  = delta_time,
        night_alpha = self._night_alpha,
        player_x    = self.player.center_x,
        player_y    = self.player.center_y,
    )

    # on_draw  (setelah _draw_night_system, masih pakai world camera)
    self._fireflies.draw(self._night_alpha)
"""
from __future__ import annotations
import math
import random
import arcade

# ── Konstanta tuning ──────────────────────────────────────────────────────────
_COUNT_MIN    = 15           # jumlah kunang-kunang minimum
_COUNT_MAX    = 25           # jumlah kunang-kunang maksimum
_SPAWN_RADIUS = 400.0        # radius spawn di sekitar player (px)

# Kecepatan maksimum (px/s) — firefly bisa berhenti hampir total lalu terbang lagi
_SPEED_MAX    = 40.0

# Steering: seberapa kuat "tarikan" arah baru (0.0–1.0 per detik)
# Nilai tinggi = gerakan lebih responsif / patah-patah
# Nilai rendah = gerakan lebih mengalir
_STEER_STRENGTH_MIN = 0.8
_STEER_STRENGTH_MAX = 2.2

# Seberapa sering target arah baru dipilih (detik)
_STEER_INTERVAL_MIN = 0.3
_STEER_INTERVAL_MAX = 1.6

# Sesekali firefly "pause" — velocity ditarik ke nol
_PAUSE_CHANCE = 0.18         # 18% kemungkinan saat pilih target baru → diam sebentar
_PAUSE_DUR_MIN = 0.3
_PAUSE_DUR_MAX = 0.9

# Kedip
_BLINK_SPEED_MIN = 0.3
_BLINK_SPEED_MAX = 1.1
_ALPHA_MIN   = 40
_ALPHA_MAX   = 230

# Visual
_RADIUS_MIN  = 2.0
_RADIUS_MAX  = 4.0

# Palet warna kuning hangat kunang-kunang
_COLORS = [
    (255, 230, 80),    # kuning cerah
    (255, 241, 118),   # kuning pucat
    (255, 213, 60),    # kuning amber
    (255, 255, 160),   # kuning hampir putih
    (240, 200, 50),    # kuning gelap keemasan
]

# Despawn jika keluar dari radius ini
_DESPAWN_RADIUS = _SPAWN_RADIUS * 1.35


class _Firefly:
    """
    Satu partikel kunang-kunang dengan gerakan steering bebas.

    Gerakan:
      • vx, vy — velocity aktual (px/s), berubah halus tiap frame
      • _tvx, _tvy — target velocity yang sedang dikejar
      • Setiap _steer_timer detik, target velocity baru dipilih acak
        ke segala arah (bukan cuma naik-turun)
      • Steering = interpolasi eksponensial vx → tvx, hasilnya mengalir
        bukan teleport
      • Sesekali target velocity = (0, 0) → firefly "melayang diam"
        lalu terbang lagi — persis seperti aslinya
    """

    __slots__ = (
        "x", "y",
        "_vx", "_vy",          # velocity aktual
        "_tvx", "_tvy",        # target velocity
        "_steer_k",            # kekuatan steering (per detik)
        "_steer_timer",        # countdown ganti target
        "_pause_timer",        # > 0 = sedang pause
        "_blink_phase",
        "_blink_speed",
        "radius",
        "color",
    )

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

        # Velocity awal acak ke segala arah
        angle     = random.uniform(0, math.tau)
        speed     = random.uniform(0, _SPEED_MAX * 0.6)
        self._vx  = math.cos(angle) * speed
        self._vy  = math.sin(angle) * speed

        self._tvx, self._tvy = self._random_target_vel()
        self._steer_k        = random.uniform(_STEER_STRENGTH_MIN, _STEER_STRENGTH_MAX)
        self._steer_timer    = random.uniform(0.0, _STEER_INTERVAL_MAX)  # fase awal acak
        self._pause_timer    = 0.0

        # Kedip — fase awal acak agar tidak sinkron
        self._blink_phase = random.uniform(0, math.tau)
        self._blink_speed = random.uniform(_BLINK_SPEED_MIN, _BLINK_SPEED_MAX) * math.tau

        self.radius = random.uniform(_RADIUS_MIN, _RADIUS_MAX)
        self.color  = random.choice(_COLORS)

    @staticmethod
    def _random_target_vel() -> tuple[float, float]:
        """Pilih target velocity acak ke segala arah (bukan cuma vertikal)."""
        angle = random.uniform(0, math.tau)
        # Kecepatan bervariasi lebar — kadang lambat, kadang cepat
        speed = random.uniform(_SPEED_MAX * 0.05, _SPEED_MAX)
        return math.cos(angle) * speed, math.sin(angle) * speed

    def update(self, dt: float) -> None:
        # ── Pause timer ──────────────────────────────────────────────────────
        if self._pause_timer > 0:
            self._pause_timer -= dt
            # Saat pause, tarik velocity ke nol perlahan
            decay = math.exp(-self._steer_k * 3.0 * dt)
            self._vx *= decay
            self._vy *= decay
        else:
            # ── Countdown ganti target arah ──────────────────────────────────
            self._steer_timer -= dt
            if self._steer_timer <= 0:
                if random.random() < _PAUSE_CHANCE:
                    # Masuk mode pause sebentar
                    self._pause_timer = random.uniform(_PAUSE_DUR_MIN, _PAUSE_DUR_MAX)
                    self._tvx, self._tvy = 0.0, 0.0
                else:
                    self._tvx, self._tvy = self._random_target_vel()
                self._steer_timer = random.uniform(_STEER_INTERVAL_MIN, _STEER_INTERVAL_MAX)

            # ── Steering: interpolasi eksponensial velocity → target ──────────
            # Rumus: v += (target - v) * (1 - exp(-k*dt))
            # Hasilnya: mengalir halus, tidak teleport, tidak overshoot
            t = 1.0 - math.exp(-self._steer_k * dt)
            self._vx += (self._tvx - self._vx) * t
            self._vy += (self._tvy - self._vy) * t

        # ── Terapkan velocity ke posisi ──────────────────────────────────────
        self.x += self._vx * dt
        self.y += self._vy * dt

        # ── Kedip ────────────────────────────────────────────────────────────
        self._blink_phase += self._blink_speed * dt

    @property
    def alpha(self) -> int:
        t = (math.sin(self._blink_phase) + 1.0) * 0.5
        return int(_ALPHA_MIN + t * (_ALPHA_MAX - _ALPHA_MIN))


class FireflySystem:
    """
    Sistem partikel kunang-kunang.

    Interface publik:
        update(delta_time, night_alpha, player_x, player_y)
        draw(night_alpha)
    """

    def __init__(self) -> None:
        self._flies: list[_Firefly] = []
        self._target_count: int = 0

    def update(
        self,
        delta_time:  float,
        night_alpha: float,
        player_x:    float,
        player_y:    float,
    ) -> None:
        if night_alpha <= 0.001:
            self._target_count = 0
        else:
            frac = min(1.0, night_alpha / 0.4)
            self._target_count = int(_COUNT_MIN + frac * (_COUNT_MAX - _COUNT_MIN))

        for fly in self._flies:
            fly.update(delta_time)

        # Despawn yang terlalu jauh dari player
        self._flies = [
            f for f in self._flies
            if math.hypot(f.x - player_x, f.y - player_y) <= _DESPAWN_RADIUS
        ]

        # Spawn hingga mencapai target
        missing = self._target_count - len(self._flies)
        for _ in range(max(0, missing)):
            self._flies.append(self._spawn_near(player_x, player_y))

    @staticmethod
    def _spawn_near(cx: float, cy: float) -> _Firefly:
        angle = random.uniform(0, math.tau)
        r     = _SPAWN_RADIUS * math.sqrt(random.random())
        return _Firefly(
            x = cx + math.cos(angle) * r,
            y = cy + math.sin(angle) * r,
        )

    def draw(self, night_alpha: float) -> None:
        if night_alpha <= 0.001 or not self._flies:
            return

        for fly in self._flies:
            halo_alpha = int(fly.alpha * night_alpha * 0.25)
            if halo_alpha > 4:
                arcade.draw_circle_filled(
                    fly.x, fly.y,
                    fly.radius * 2.8,
                    (*fly.color, halo_alpha),
                )
            core_alpha = int(fly.alpha * night_alpha)
            arcade.draw_circle_filled(
                fly.x, fly.y,
                fly.radius,
                (*fly.color, core_alpha),
            )
