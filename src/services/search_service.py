import re
from kivy.utils import escape_markup
from src.ui.theme import COLOR_HIGHLIGHT


def _safe_str(value):
    if value is None:
        return ""
    return str(value)


def rgba_to_hex(color):
    r, g, b = [int(c * 255) for c in color[:3]]
    return f"#{r:02x}{g:02x}{b:02x}"


def _normalize(text: str) -> str:
    text = _safe_str(text).lower()

    # replace common separators with spaces
    text = re.sub(r"[-_/\\.:]", " ", text)

    # remove everything except letters, numbers and spaces
    text = re.sub(r"[^a-z0-9 ]+", " ", text)

    # collapse repeated spaces
    text = " ".join(text.split())

    return text


def build_search_blob(topic: dict, steps: list[dict]) -> str:
    parts = []

    # all topic fields
    for value in topic.values():
        parts.append(_safe_str(value))

    # all step fields
    for step in steps:
        for value in step.values():
            parts.append(_safe_str(value))

    raw_blob = " ".join(parts)
    return _normalize(raw_blob)


def topic_matches(query: str, topic: dict, steps: list[dict]) -> bool:
    if not query:
        return True

    blob = build_search_blob(topic, steps)

    query = query.strip()

    # exact search if user types "..."
    if query.startswith('"') and query.endswith('"'):
        exact = query[1:-1].strip().lower()

        raw_blob = " ".join(
            [_safe_str(v) for v in topic.values()] +
            [_safe_str(v) for s in steps for v in s.values()]
        ).lower()

        return exact in raw_blob

    normalized_query = _normalize(query)
    words = normalized_query.split()

    return all(word in blob for word in words)


def highlight_text(text: str, query: str) -> str:
    """
    Safe highlight:
    - does NOT break existing [color=...] syntax highlighting
    - works for normal text (titles, descriptions, instructions)
    """

    if not text or not query:
        return text

    import re

    # ✅ IMPORTANT: if already contains color markup (code block), skip
    if "[color=" in text:
        return text

    from src.ui.theme import COLOR_HIGHLIGHT

    def rgba_to_hex(color):
        r, g, b = [int(c * 255) for c in color[:3]]
        return f"#{r:02x}{g:02x}{b:02x}"

    color = rgba_to_hex(COLOR_HIGHLIGHT)

    normalized_query = re.sub(r"[^a-z0-9 ]+", " ", query.lower())
    words = normalized_query.split()

    result = text

    for word in set(words):
        if len(word) < 2:
            continue

        pattern = re.compile(re.escape(word), re.IGNORECASE)

        result = pattern.sub(
            lambda m: f"[b][color={color}]{m.group(0)}[/color][/b]",
            result
        )

    return result


def _matches_field(query: str, value) -> bool:
    if not query:
        return False

    if query.startswith('"') and query.endswith('"'):
        exact = query[1:-1].strip().lower()
        return exact in _safe_str(value).lower()

    words = _normalize(query).split()
    field_blob = _normalize(value)
    return all(word in field_blob for word in words)


def find_match_location(query: str, topic: dict, steps: list[dict]) -> str:
    if not query:
        return ""

    # topic fields first
    if _matches_field(query, topic.get("Title", "")):
        return "Title"
    if _matches_field(query, topic.get("Description", "")):
        return "Description"
    if _matches_field(query, topic.get("URLs", "")):
        return "Topic URL"

    # step fields
    for idx, step in enumerate(steps, start=1):
        if _matches_field(query, step.get("Code_Snippet", "")):
            return f"Step {idx} (Code)"
        if _matches_field(query, step.get("Instruction", "")):
            return f"Step {idx} (Instruction)"
        if _matches_field(query, step.get("Notes", "")):
            return f"Step {idx} (Notes)"
        if _matches_field(query, step.get("Headline", "")):
            return f"Step {idx} (Headline)"
        if _matches_field(query, step.get("Header_2", "")):
            return f"Step {idx} (Header)"
        if _matches_field(query, step.get("URLs", "")):
            return f"Step {idx} (URL)"

    return "Topic"