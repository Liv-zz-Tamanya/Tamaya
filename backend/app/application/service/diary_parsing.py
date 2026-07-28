"""LLM 일기 출력 파싱 헬퍼.

satisfaction의 '모름'(null·키 누락·타입 오류)과 실제 '중립 50' 판단을 구분한다.
BUG-07: 값은 0~100으로 클램프 (DEC-020).
"""


def parse_satisfaction(raw: object) -> tuple[int, bool]:
    """LLM 출력의 satisfaction을 (값, estimated)로 파싱한다.

    estimated=True면 LLM이 판단하지 못했거나 값이 부적절한 경우다.
    저장 값은 중립 50이지만, 인사이트 집계·상관분석에서는 제외해야 한다.

    호출부는 ``diary_data.get("satisfaction")``처럼 기본값 인자 없이 넘겨야
    키 누락이 estimated=True로 흐른다 — 기본값 인자를 쓰면 결측이 다시 은폐된다.
    """
    if raw is None or isinstance(raw, bool):
        return 50, True
    try:
        return max(0, min(100, int(raw))), False
    except (TypeError, ValueError):
        return 50, True
