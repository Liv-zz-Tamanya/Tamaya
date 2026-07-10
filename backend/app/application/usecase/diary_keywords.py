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
