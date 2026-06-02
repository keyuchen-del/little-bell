import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QFont

ASSETS_DIR = Path(__file__).parent / "assets" / "pet"


class BubbleWidget(QLabel):
    """Notification bubble that appears above the pet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(
            "background-color: rgba(50, 50, 50, 220);"
            "color: white;"
            "border-radius: 10px;"
            "padding: 8px 12px;"
            "font-size: 13px;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setMaximumWidth(200)
        self.hide()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_message(self, text, duration_ms=4000):
        self.setText(text)
        self.adjustSize()
        self.show()
        self._hide_timer.start(duration_ms)


class PetWidget(QWidget):
    """Floating desktop pet - a cute bell character."""

    def __init__(self, config):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._config = config
        self._size = config["pet"]["size"]
        self._state = "idle"  # idle, alert, happy
        self._frame_index = 0
        self._frames = {"idle": [], "alert": []}
        self._dragging = False
        self._drag_offset = QPoint()

        self.setFixedSize(self._size, self._size + 20)
        self.move(config["pet"]["position_x"], config["pet"]["position_y"])

        self._label = QLabel(self)
        self._label.setFixedSize(self._size, self._size)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setScaledContents(True)

        self._bubble = BubbleWidget()

        self._load_frames()

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._next_frame)
        self._anim_timer.start(300)

        self._alert_timer = QTimer(self)
        self._alert_timer.setSingleShot(True)
        self._alert_timer.timeout.connect(self._return_to_idle)

    def _load_frames(self):
        for state in ["idle", "alert"]:
            for i in range(4):
                path = ASSETS_DIR / f"{state}_{i}.png"
                if path.exists():
                    pixmap = QPixmap(str(path))
                    self._frames[state].append(pixmap)
                else:
                    img = QPixmap(self._size, self._size)
                    img.fill(Qt.GlobalColor.transparent)
                    self._frames[state].append(img)

    def _next_frame(self):
        frames = self._frames.get(self._state, self._frames["idle"])
        if not frames:
            return
        self._frame_index = (self._frame_index + 1) % len(frames)
        self._label.setPixmap(frames[self._frame_index])

    def trigger_alert(self, message=None):
        self._state = "alert"
        self._frame_index = 0
        self._anim_timer.setInterval(100)

        if message:
            self._bubble.move(self.x() + self._size // 2 - 100, self.y() - 50)
            self._bubble.show_message(message)

        self._alert_timer.start(5000)

    def _return_to_idle(self):
        self._state = "idle"
        self._frame_index = 0
        self._anim_timer.setInterval(300)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._dragging:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
            if self._bubble.isVisible():
                self._bubble.move(new_pos.x() + self._size // 2 - 100, new_pos.y() - 50)

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def mouseDoubleClickEvent(self, event):
        self._return_to_idle()
        self._bubble.show_message("小铃铛在守护你~ 🔔")
