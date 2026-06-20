import re
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivy.app import App
from kivy.utils import escape_markup

from src.ui.theme import (
    COLOR_TEXT_DARK,
    COLOR_BLUE,
    COLOR_ORANGE,
    COLOR_HIGHLIGHT,
)


def rgba_to_hex(color):
    r, g, b = [int(c * 255) for c in color[:3]]
    return f"{r:02x}{g:02x}{b:02x}"


def apply_inline_markup(text: str, query: str):
    if not text:
        return ""

    escaped = escape_markup(text)

    # ✅ bold
    escaped = re.sub(r"\*\*(.*?)\*\*", r"[b]\1[/b]", escaped)

    # ✅ inline code
    escaped = re.sub(
        r"`(.+?)`",
        r"[font=RobotoMono][color=ffaa66]\1[/color][/font]",
        escaped
    )

    # ✅ highlight
    if query:
        words = re.sub(r"[^a-z0-9 ]+", " ", query.lower()).split()
        color = rgba_to_hex(COLOR_HIGHLIGHT)

        for w in set(words):
            if len(w) < 2:
                continue

            escaped = re.sub(
                re.escape(w),
                lambda m: f"[b][color={color}]{m.group(0)}[/color][/b]",
                escaped,
                flags=re.IGNORECASE
            )

    return escaped


def build_rich_widgets(text, app, query=""):
    if not text:
        return []

    widgets = []
    lines = text.splitlines()

    for line in lines:
        stripped = line.strip()

        # ✅ HEADERS
        if stripped.startswith("### "):
            widgets.append(Label(
                text=apply_inline_markup(stripped[4:], query),
                markup=True,
                bold=True,
                font_size=app.FONT_TEXT * 1.2,
                color=COLOR_BLUE,
                size_hint_y=None,
                halign="left"
            ))
            continue

        if stripped.startswith("## "):
            widgets.append(Label(
                text=apply_inline_markup(stripped[3:], query),
                markup=True,
                bold=True,
                font_size=app.FONT_SUBCATEGORY * 1.1,
                color=COLOR_ORANGE,
                size_hint_y=None,
                halign="left"
            ))
            continue

        if stripped.startswith("# "):
            widgets.append(Label(
                text=apply_inline_markup(stripped[2:], query),
                markup=True,
                bold=True,
                font_size=app.FONT_TITLE,
                color=COLOR_BLUE,
                size_hint_y=None,
                halign="left"
            ))
            continue

        # ✅ WARNINGS
        if stripped.startswith("!warn:"):
            widgets.append(Label(
                text=f"[b][color=ff4444]⚠ {apply_inline_markup(stripped[6:], query)}[/color][/b]",
                markup=True,
                size_hint_y=None,
                halign="left"
            ))
            continue

        if stripped.startswith("!tip:"):
            widgets.append(Label(
                text=f"[b][color=4dabf7]💡 {apply_inline_markup(stripped[5:], query)}[/color][/b]",
                markup=True,
                size_hint_y=None,
                halign="left"
            ))
            continue

        # ✅ BULLETS (WITH BETTER INDENT)
        if stripped.startswith("- "):
            indent = (len(line) - len(line.lstrip(" "))) // 4

            prefix = "\u00A0" * (indent * 6) + "• "

            widgets.append(Label(
                text=prefix + apply_inline_markup(stripped[2:], query),
                markup=True,
                size_hint_y=None,
                halign="left"
            ))
            continue

        # ✅ NORMAL TEXT
        widgets.append(Label(
            text=apply_inline_markup(line, query),
            markup=True,
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            halign="left"
        ))

    # auto-height
    for w in widgets:
        w.bind(
            size=lambda s, w: setattr(s, 'text_size', (s.width, None)),
            texture_size=lambda inst, val: setattr(inst, 'height', val[1])
        )

    return widgets