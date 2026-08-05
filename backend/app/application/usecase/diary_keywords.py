def normalize_diary_tomorrow(raw: object, *, max_length: int = 100) -> str | None:
    """LLM이 낸 '내일 한 가지' 정규화 — 문자열이 아니거나 비었으면 None (지어내기 방지)."""
    if not isinstance(raw, str):
        return None
    tomorrow = raw.strip()
    if not tomorrow or tomorrow.lower() == "null":
        return None
    return tomorrow[:max_length]


def normalize_diary_keywords(raw: object, *, limit: int = 3) -> list[str]:
    if not isinstance(raw, list):
        return []

    keywords: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        keyword = item.strip()
        if not keyword or keyword in seen:
            continue
        keywords.append(keyword[:20])
        seen.add(keyword)
        if len(keywords) >= limit:
            break
    return keywords
