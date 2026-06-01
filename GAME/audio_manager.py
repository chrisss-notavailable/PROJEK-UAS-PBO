"""
audio_manager.py — Manajer Audio Terpusat

Encapsulation: seluruh state audio (_sounds, _channels, _ready)
dijaga private. Caller hanya berinteraksi melalui play(), stop(),
play_bgm(), dan stop_bgm() — tanpa mengakses pygame.mixer secara langsung.

Penggunaan:
    from audio_manager import AudioManager
    audio = AudioManager()
    audio.play("footsteps")
    audio.stop("footsteps")
"""

import pygame

_SFX_PATHS: dict[str, str] = {
    "footsteps":       "assets/Audio/Sfx/footsteps.wav",
    "footsteps_kamar": "assets/Audio/Sfx/Walking_kamar.wav",
    "casting":         "assets/Audio/Sfx/Casting.wav",
    "umpan":           "assets/Audio/Sfx/Umpan.wav",
    "waiting":         "assets/Audio/Sfx/Waiting.wav",
    "reward":          "assets/Audio/Sfx/Reward.wav",
    "plant":           "assets/Audio/Sfx/plant.wav",
    "harvest":         "assets/Audio/Sfx/harvest.wav",
    "interact":        "assets/Audio/Sfx/Interact.wav",
    "buy":             "assets/Audio/Sfx/Buy.wav",
    "sell":            "assets/Audio/Sfx/Sell.wav",
    "siram":           "assets/Audio/Sfx/Siram.wav",
    "ambil":           "assets/Audio/Sfx/Ambil.wav",
    "rain":            "assets/Audio/Sfx/rain.wav",
}

_BGM_PATHS: dict[str, str] = {
    "bgm1": "assets/Audio/Bgm/Bgm1.mp3",
}

_DEFAULT_SFX_VOLUME: float = 0.16   #
_SFX_VOLUME_OVERRIDE: dict[str, float] = {
    "reward":          0.02,   #
    "footsteps":       0.06,   
    "footsteps_kamar": 0.16,   #
    "waiting":         0.06,   # 
    "rain":            0.10,   # 
}

_DEFAULT_BGM_VOLUME: float = 0.04   


class AudioManager:
    """
    Encapsulation: semua state audio dan channel pygame disembunyikan
    di balik interface publik play(), stop(), play_bgm(), stop_bgm().

    Caller tidak perlu tahu tentang pygame.mixer.Sound, channel index,
    atau detail inisialisasi — semua dikelola internal.

    Master Volume:
        set_master_volume(v)  — ubah master volume (0.0–1.0) secara real-time.
        Semua SFX dan BGM yang sedang / akan diputar mengikuti nilai ini.
        Volume tiap SFX dihitung:  base_volume × master_volume
        Volume BGM dihitung:        _DEFAULT_BGM_VOLUME × master_volume
    """

    _DEFAULT_MASTER_VOLUME: float = 0.5   # 50%

    def __init__(self) -> None:
        self._ready: bool = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._channels: dict[str, pygame.mixer.Channel] = {}

        self._base_sfx_vol: dict[str, float] = {}
        self._master_volume: float = self._DEFAULT_MASTER_VOLUME

        self._init_mixer()
        self._load_all_sfx()

    def _init_mixer(self) -> None:
        if not pygame.get_init():
            pygame.init()

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except pygame.error as e:
                return

        self._ready = True

    def _load_all_sfx(self) -> None:
        if not self._ready:
            return

        needed = len(_SFX_PATHS)
        if pygame.mixer.get_num_channels() < needed:
            pygame.mixer.set_num_channels(needed + 4)

        for name, path in _SFX_PATHS.items():
            if path.lower().endswith(".mp3"):
                continue

            try:
                sound = pygame.mixer.Sound(path)
                base_vol = _SFX_VOLUME_OVERRIDE.get(name, _DEFAULT_SFX_VOLUME)
                self._base_sfx_vol[name] = base_vol
                sound.set_volume(base_vol * self._master_volume)

                channel_index = list(_SFX_PATHS.keys()).index(name)
                channel = pygame.mixer.Channel(channel_index)

                self._sounds[name]   = sound
                self._channels[name] = channel

            except (FileNotFoundError, pygame.error) as e:
                pass

    def play(self, name: str, loops: int = -1) -> None:
        """

        """
        if not self._ready:
            return

        channel = self._channels.get(name)
        sound   = self._sounds.get(name)

        if channel is None or sound is None:
            return

        if not channel.get_busy():
            channel.play(sound, loops=loops)

    def play_once(self, name: str) -> None:
       
        self.play(name, loops=0)

    def stop(self, name: str) -> None:
        """Hentikan SFX dengan nama tertentu."""
        if not self._ready:
            return

        channel = self._channels.get(name)
        if channel is None:
            return

        if channel.get_busy():
            channel.stop()

    def set_sfx_volume(self, name: str, volume: float) -> None:
        """Ubah volume SFX tertentu (0.0 – 1.0)."""
        sound = self._sounds.get(name)
        if sound:
            sound.set_volume(max(0.0, min(1.0, volume)))

    def set_all_sfx_volume(self, volume: float) -> None:
        """Ubah volume semua SFX sekaligus."""
        for sound in self._sounds.values():
            sound.set_volume(max(0.0, min(1.0, volume)))

    def play_bgm(self, name: str, loops: int = -1, fade_ms: int = 1000) -> None:
        """
        Putar BGM via pygame.mixer.music dengan fade-in.
        loops=-1 = loop selamanya.
        """
        if not self._ready:
            return

        path = _BGM_PATHS.get(name)
        if path is None:
            return

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(_DEFAULT_BGM_VOLUME * self._master_volume)
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
        except pygame.error as e:
            pass

    def stop_bgm(self, fade_ms: int = 500) -> None:
        """Hentikan BGM dengan fade out."""
        if not self._ready:
            return
        pygame.mixer.music.fadeout(fade_ms)

    def set_bgm_volume(self, volume: float) -> None:
        """Ubah volume BGM (0.0 – 1.0)."""
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    def set_master_volume(self, master: float) -> None:
        """
        Ubah MASTER VOLUME secara real-time (0.0 – 1.0).

        Langsung memperbarui:
          • Volume BGM yang sedang diputar (tanpa reload/restart).
          • Volume seluruh SFX (dihitung ulang dari base volume masing-masing).

        """
        self._master_volume = max(0.0, min(1.0, master))

        # --- BGM ---
        if self._ready:
            pygame.mixer.music.set_volume(_DEFAULT_BGM_VOLUME * self._master_volume)

        # --- Semua SFX ---
        for name, sound in self._sounds.items():
            base = self._base_sfx_vol.get(name, _DEFAULT_SFX_VOLUME)
            sound.set_volume(base * self._master_volume)

    @property
    def master_volume(self) -> float:
        """Kembalikan nilai master volume saat ini (0.0 – 1.0)."""
        return self._master_volume

    def stop_all_sfx(self) -> None:
        """Hentikan semua SFX yang sedang playing."""
        for name in self._channels:
            self.stop(name)

    def is_playing(self, name: str) -> bool:
        """Return True jika SFX tertentu sedang playing."""
        channel = self._channels.get(name)
        return channel.get_busy() if channel else False

    def quit(self) -> None:
        """Bersihkan mixer saat game ditutup."""
        if pygame.mixer.get_init():
            pygame.mixer.quit()
