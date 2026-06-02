"""浮窗宠物 - 使用 PyObjC 原生实现，与 rumps 共享 AppKit RunLoop。"""
import objc
from AppKit import (
    NSWindow,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSFloatingWindowLevel,
    NSImageView,
    NSImage,
    NSMakeRect,
    NSView,
    NSColor,
    NSTextField,
    NSFont,
    NSTimer,
    NSScreen,
)
from Foundation import NSObject
from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets" / "pet"


class CocoaPet:
    def __init__(self, config):
        self._size = config["pet"]["size"]
        self._x = config["pet"]["position_x"]
        self._y = config["pet"]["position_y"]
        self._state = "idle"
        self._frame_index = 0
        self._frames = {"idle": [], "alert": []}

        # Load frames
        for state in ["idle", "alert"]:
            for i in range(4):
                path = ASSETS_DIR / f"{state}_{i}.png"
                if path.exists():
                    img = NSImage.alloc().initWithContentsOfFile_(str(path))
                    if img:
                        self._frames[state].append(img)

        # Create transparent floating window
        screen = NSScreen.mainScreen()
        screen_height = screen.frame().size.height

        rect = NSMakeRect(self._x, screen_height - self._y - self._size - 40, self._size, self._size + 40)
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setLevel_(NSFloatingWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setMovableByWindowBackground_(True)
        self._window.setHasShadow_(False)
        self._window.setIgnoresMouseEvents_(False)

        # Image view for pet
        content = self._window.contentView()
        self._image_view = NSImageView.alloc().initWithFrame_(
            NSMakeRect(0, 40, self._size, self._size)
        )
        if self._frames["idle"]:
            self._image_view.setImage_(self._frames["idle"][0])
        content.addSubview_(self._image_view)

        # Bubble label (hidden initially)
        self._bubble = NSTextField.alloc().initWithFrame_(
            NSMakeRect(0, 0, self._size, 35)
        )
        self._bubble.setEditable_(False)
        self._bubble.setBordered_(False)
        self._bubble.setDrawsBackground_(True)
        self._bubble.setBackgroundColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.2, 0.2, 0.2, 0.85)
        )
        self._bubble.setTextColor_(NSColor.whiteColor())
        self._bubble.setFont_(NSFont.systemFontOfSize_(10))
        self._bubble.setAlignment_(1)  # center
        self._bubble.setStringValue_("")
        self._bubble.setHidden_(True)
        content.addSubview_(self._bubble)

        # Animation timer (every 300ms)
        self._timer = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            0.3, True, self._animate
        )

        self._alert_timer = None

    def _animate(self, timer):
        frames = self._frames.get(self._state, self._frames.get("idle", []))
        if not frames:
            return
        self._frame_index = (self._frame_index + 1) % len(frames)
        self._image_view.setImage_(frames[self._frame_index])

    def show(self):
        self._window.orderFront_(None)

    def hide(self):
        self._window.orderOut_(None)

    def trigger_alert(self, message=None):
        self._state = "alert"
        self._frame_index = 0

        if message:
            display_msg = message[:30] + "..." if len(message) > 30 else message
            self._bubble.setStringValue_(display_msg)
            self._bubble.setHidden_(False)

            # Hide bubble after 4 seconds
            if self._alert_timer:
                self._alert_timer.invalidate()
            self._alert_timer = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                4.0, False, self._return_to_idle
            )

    def _return_to_idle(self, timer=None):
        self._state = "idle"
        self._frame_index = 0
        self._bubble.setHidden_(True)
