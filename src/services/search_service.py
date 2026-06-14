import re


def _safe_str(value):
    if value is None:
        return ""
    return str(value)


def _normalize(text: str) -> str:
    text = text.lower()

    # ✅ replace special separators with space
    text = re.sub(r"[-_/\\\.]", " ", text)

    # ✅ remove all non-alphanumeric (keep spaces)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)

    # ✅ collapse spaces
    text = " ".join(text.split())

    return text


def build_search_blob(topic: dict, steps: list[dict]) -> str:
    parts = []

    # ✅ ALL topic fields
    for value in topic.values():
        parts.append(_safe_str(value))

    # ✅ ALL step fields
    for s in steps:
        for value in s.values():
            parts.append(_safe_str(value))

    raw_blob = " ".join(parts)

    return _normalize(raw_blob)


def topic_matches(query: str, topic: dict, steps: list[dict]) -> bool:
    if not query:
        return True

    blob = build_search_blob(topic, steps)

    # ✅ EXTRACT EXACT SEARCH (with quotes)
    query = query.strip()

    if query.startswith('"') and query.endswith('"'):
        exact = query[1:-1]  # remove quotes

        # ✅ IMPORTANT: do NOT normalize for exact search
        raw_blob = " ".join(
            [_safe_str(v) for v in topic.values()] +
            [_safe_str(v) for s in steps for v in s.values()]
        ).lower()

        return exact.lower() in raw_blob

    # ✅ NORMAL SEARCH (fuzzy)
    normalized_query = _normalize(query)
    words = normalized_query.split()

    return all(word in blob for word in words)
