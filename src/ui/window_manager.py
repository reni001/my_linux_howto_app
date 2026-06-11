import os
import platform

from kivy.core.window import Window
from kivy.clock import Clock

def setup_window(*args):
    """
    Set the default portrait window size and position it near the top centre.
    This is only meant for desktop mode.
    """
    # ✅ get real screen size AFTER window is ready
    screen_w, screen_h = Window.system_size

    # ✅ use most of height
    HEIGHT = int(screen_h * 0.95)

    # ✅ phone ratio (9:16)
    WIDTH = int(HEIGHT * 9 / 16)

    Window.size = (WIDTH, HEIGHT)

    # ✅ center window
    Window.left = int((screen_w - WIDTH) / 2)

    # ✅ stick to TOP
    Window.top = screen_h - HEIGHT


def apply_desktop_window_defaults():
    """
    Apply desktop-only defaults and schedule the initial portrait window setup.
    """
    if platform.system() != "Linux" or "ANDROID_ARGUMENT" not in os.environ:
        Window.minimum_width = 480
        Window.minimum_height = 850
        Window.resizable = True

        # Start with a safe desktop size before refining with setup_window
        Window.size = (700, 1200)

        Clock.schedule_once(setup_window, 0.1)

#--------- screen rotation ----------

def toggle_orientation(app):
    """
    Toggle between portrait and landscape.
    Uses app state stored on the App instance:
      - app.is_landscape
      - app.previous_size
    """
    # Save current size before switching to landscape
    if not app.is_landscape:
        app.previous_size = Window.size

    min_w = Window.minimum_width or 480
    min_h = Window.minimum_height or 850

    if not app.is_landscape:
        # Landscape mode
        new_w = max(1000, min_w)
        new_h = max(600, min_h)

        Window.size = (new_w, new_h)
        app.is_landscape = True
    else:
        # Restore previous portrait size
        if app.previous_size:
            Window.size = app.previous_size
        else:
            Window.size = (800, 1300)

        app.is_landscape = False

    # Force relayout after resizing so controls do not become unresponsive
    Clock.schedule_once(lambda dt: fix_layout(app), 0)


def fix_layout(app):
    """
    Force Kivy to recompute the current layout after a window resize.
    """
    if hasattr(app, "root") and app.root:
        app.root.do_layout()


