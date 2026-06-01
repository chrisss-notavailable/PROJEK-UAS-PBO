"""
opening_story.py — Opening Story (Prolog) Slideshow

Fitur:
    pass
- Slideshow gambar cerita (1.png - 32.png) dengan background BG.png
- Fade transitions antar gambar
- Auto-advance: 5 detik per gambar
- Kontrol: Right Click = next image, F = skip semua
- Gambar ditampilkan di tengah layar dengan aspect ratio terjaga
- Background fullscreen selalu terlihat di sekeliling gambar cerita
"""

import os
import arcade
from pathlib import Path


class OpeningStory:
    """Slideshow opening story dengan fade transitions."""
    
    def __init__(self, screen_width: int, screen_height: int, asset_folder: str):
        """
        Args:
            screen_width: Lebar layar
            screen_height: Tinggi layar
            asset_folder: Path ke folder assets/ui/cerita/
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.asset_folder = asset_folder
        
        # Load background dan gambar cerita
        self.bg_tex = None
        self.story_textures = []
        self._load_assets()
        
        # State
        self.current_image_index = 0
        self.image_timer = 0.0
        self.image_duration = 5.0  # 5 detik per gambar
        self.fade_duration = 0.3   # 0.3 detik untuk fade
        
        # Fade state: 0.0 = invisible, 1.0 = fully visible
        self.fade_alpha = 0.0
        self.is_fading_in = True
        self.fade_timer = 0.0
        
        # Finished callback
        self.on_complete_callback = None
        
        # Flag untuk skip
        self.is_skipped = False
        self.is_complete = False
        
    def _load_assets(self) -> None:
        """Load BG.png dan semua gambar cerita (1.png - 32.png)."""
        try:
            # Load background
            bg_path = os.path.join(self.asset_folder, "BG.png")
            if os.path.exists(bg_path):
                self.bg_tex = arcade.load_texture(bg_path)
        except Exception as e:
            pass
        
        # Load story images (1.png - 32.png)
        for i in range(1, 33):
            try:
                img_path = os.path.join(self.asset_folder, f"{i}.png")
                if os.path.exists(img_path):
                    tex = arcade.load_texture(img_path)
                    self.story_textures.append(tex)
                else:
                    self.story_textures.append(None)
            except Exception as e:
                self.story_textures.append(None)
        
    
    def update(self, delta_time: float) -> None:
        """Update timer dan fade logic."""
        if self.is_complete or self.is_skipped:
            return
        
        # Update fade
        if self.is_fading_in:
            self.fade_timer += delta_time
            if self.fade_timer >= self.fade_duration:
                self.fade_alpha = 1.0
                self.is_fading_in = False
                self.fade_timer = 0.0
            else:
                self.fade_alpha = self.fade_timer / self.fade_duration
        else:
            # Gambar terlihat penuh, tunggu image_duration
            self.image_timer += delta_time
            if self.image_timer >= self.image_duration:
                self._next_image()
    
    def _next_image(self) -> None:
        """Lanjut ke gambar berikutnya."""
        self.current_image_index += 1
        
        if self.current_image_index >= len(self.story_textures):
            # Selesai
            self.is_complete = True
            if self.on_complete_callback:
                self.on_complete_callback()
        else:
            # Mulai fade in untuk gambar baru
            self.image_timer = 0.0
            self.fade_timer = 0.0
            self.is_fading_in = True
            self.fade_alpha = 0.0
    
    def skip_all(self) -> None:
        """Skip seluruh opening story (F key)."""
        self.is_skipped = True
        if self.on_complete_callback:
            self.on_complete_callback()
    
    def next_image(self) -> None:
        """Lanjut ke gambar berikutnya (Right Click)."""
        if not self.is_complete and not self.is_skipped:
            self._next_image()
    
    def draw(self) -> None:
        """Draw background + gambar cerita dengan fade."""
        # Fill background dengan warna hitam
        # arcade.draw_rectangle_filled dihapus di Arcade 3.x
        # Gunakan draw_lbwh_rectangle_filled(left, bottom, width, height, color)
        arcade.draw_lbwh_rectangle_filled(
            0,
            0,
            self.screen_width,
            self.screen_height,
            arcade.color.BLACK
        )
        
        # Draw background texture jika ada
        if self.bg_tex is not None:
            arcade.draw_texture_rect(
                self.bg_tex,
                arcade.LBWH(0, 0, self.screen_width, self.screen_height),
                pixelated=True,
            )
        
        # Draw story image di tengah dengan aspect ratio terjaga
        if self.current_image_index < len(self.story_textures):
            tex = self.story_textures[self.current_image_index]
            if tex is not None:
                # Hitung ukuran gambar dengan aspect ratio terjaga
                img_width = tex.width
                img_height = tex.height
                aspect_ratio = img_width / img_height if img_height > 0 else 1.0
                
                # Skala agar pas di layar dengan padding
                max_width = self.screen_width * 0.9
                max_height = self.screen_height * 0.9
                
                if aspect_ratio > (max_width / max_height):
                    # Limited by width
                    display_width = max_width
                    display_height = max_width / aspect_ratio
                else:
                    # Limited by height
                    display_height = max_height
                    display_width = max_height * aspect_ratio
                
                # Posisi di tengah
                img_x = (self.screen_width - display_width) / 2
                img_y = (self.screen_height - display_height) / 2
                
                # Draw dengan fade alpha
                arcade.draw_texture_rect(
                    tex,
                    arcade.LBWH(img_x, img_y, display_width, display_height),
                    pixelated=True,
                    alpha=int(255 * self.fade_alpha),
                )
        
        # Draw "[F] Skip" di pojok kiri bawah
        skip_text = "[F] Skip"
        arcade.draw_text(
            skip_text,
            20, 20,
            arcade.color.WHITE,
            font_size=16,
            bold=True,
            anchor_x="left",
            anchor_y="bottom",
        )