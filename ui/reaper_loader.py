"""
reaper_loader.py
----------------
Animated MP4 loading widget shown during searches.
Picks a random animation from ui/assets and updates the text.
"""

import os
import random
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, QUrl
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget

# ANIMATION CONFIGURATION
# Map filenames to their display text and optional attribution
ANIMATIONS = {
    "grim_reaper.mp4": {
        "text": "The Reaper is searching the archives...",
        "attr": "Grim Reaper by Akiko"
    },
    "grim_reaper_2.mp4": {
        "text": "The Reaper is gathering souls...",
        "attr": "Grim Reaper by Irina Bonko"
    },
    "zombie.mp4": {
        "text": "Crawling from grave to grave...",
        "attr": "Halloween Zombie by Si Tolan"
    }
}

class ReaperLoader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(900, 700)
        self.setStyleSheet("background-color: white; border-radius: 0px;")
        
        # Initialize Media Player
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        
        self.init_ui()
        self.setVisible(False)

        # Animation for sliding up/down
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(800)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.finished.connect(self._on_anim_done)
        
        self._hiding = False

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Video fills the area
        self.layout.addWidget(self.video_widget)

        # Text overlay container
        self.text_container = QWidget()
        self.text_container.setFixedHeight(60)
        self.text_container.setStyleSheet("background-color: rgba(255, 255, 255, 220);")
        text_layout = QVBoxLayout(self.text_container)
        text_layout.setContentsMargins(0, 5, 0, 5)
        text_layout.setSpacing(2)

        self.label = QLabel("Initializing...")
        self.label.setStyleSheet(
            "color: #1a2333; font-weight: bold; font-size: 22px; background: transparent;"
        )
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_layout.addWidget(self.label)

        # Very subtle attribution
        self.attr_label = QLabel("")
        self.attr_label.setStyleSheet("color: #ecf0f1; font-size: 8px; background: transparent;")
        self.attr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_layout.addWidget(self.attr_label)
        
        self.layout.addWidget(self.text_container)

    def _on_anim_done(self):
        if self._hiding:
            self.setVisible(False)
            self._hiding = False
            self.media_player.stop()

    def start_loading(self):
        if not self.parent():
            return
            
        # PICK RANDOM ANIMATION
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        available_files = [f for f in os.listdir(assets_dir) if f.endswith(".mp4") and f in ANIMATIONS]
        
        if not available_files:
            logger.error("No valid animations found in assets folder.")
            return

        choice = random.choice(available_files)
        config = ANIMATIONS[choice]
        
        # Update UI
        self.label.setText(config["text"])
        self.attr_label.setText(config["attr"])
        
        asset_path = os.path.join(assets_dir, choice)
        self.media_player.setSource(QUrl.fromLocalFile(asset_path))
        
        self._hiding = False
        parent_rect = self.parent().rect()
        start_x = (parent_rect.width() - self.width()) // 2
        start_y = parent_rect.height()

        self.move(start_x, start_y)
        self.setVisible(True)
        self.raise_()
        
        self.media_player.play()

        self.anim.setStartValue(QPoint(start_x, start_y))
        self.anim.setEndValue(
            QPoint(start_x, (parent_rect.height() - self.height()) // 2)
        )
        self.anim.start()

    def stop_loading(self):
        self._hiding = True
        current_pos = self.pos()
        self.anim.setStartValue(current_pos)
        self.anim.setEndValue(
            QPoint(current_pos.x(), self.parent().height() + 100)
        )
        self.anim.start()
