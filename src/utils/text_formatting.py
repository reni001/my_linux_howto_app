import re

from src.ui.theme import COLOR_ORANGE

def format_rich_text(text: str) -> str:
    if not text:
        return ""

    lines = text.splitlines()
    formatted = []

    for line in lines:
        raw = line.rstrip()

        # detect indent
        indent = len(raw) - len(raw.lstrip(' '))
        level = indent // 4

        stripped = raw.strip()

        # ✅ BULLETS
        if stripped.startswith("- "):
            content = stripped[2:]

            # ✅ theme color
            color = _rgba_to_hex(COLOR_ORANGE)

            # ✅ slightly bigger bullet using size markup
            bullet = f"[color={color}][size=18]•[/size][/color] "

            indent = "  " * level

            formatted.append(indent + bullet + content)

        else:
            formatted.append(raw)

    result = "\n".join(formatted)

    # ✅ BOLD
    result = re.sub(r"\*\*(.*?)\*\*", r"[b]\1[/b]", result)

    # ✅ INLINE CODE (very light)
    result = re.sub(
        r"`(.+?)`",
        r"[font=RobotoMono]\1[/font]",
        result
    )

    return result