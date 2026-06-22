# services/matching.py

INTEREST_WEIGHT = 40
AGE_WEIGHT = 30
GOAL_WEIGHT = 30
GOAL_MISMATCH_WEIGHT = 10
AGE_DIFF_MAX = 10
CITY_BONUS = 10


def _parse_interests(interests: str | None) -> set[str]:
    if not interests:
        return set()
    return {item.strip() for item in interests.split(",") if item.strip()}


def gender_match(
    my_gender: str, my_looking_for: str, their_gender: str, their_looking_for: str
) -> bool:
    """Return True if both users fit each other's gender preferences."""
    i_like_them = my_looking_for == "all" or my_looking_for == their_gender
    they_like_me = their_looking_for == "all" or their_looking_for == my_gender
    return i_like_them and they_like_me


def calculate_compatibility(me: dict, candidate: dict) -> int:
    """Return compatibility percentage (0-100)."""
    my_interests = _parse_interests(me.get("interests"))
    their_interests = _parse_interests(candidate.get("interests"))

    union = my_interests | their_interests
    if union:
        intersection = my_interests & their_interests
        interest_score = len(intersection) / len(union) * INTEREST_WEIGHT
    else:
        interest_score = 0

    age_diff = abs(me["age"] - candidate["age"])
    age_score = max(0, 1 - age_diff / AGE_DIFF_MAX) * AGE_WEIGHT

    goal_score = GOAL_WEIGHT if me["goal"] == candidate["goal"] else GOAL_MISMATCH_WEIGHT

    score = round(interest_score + age_score + goal_score)

    my_city = me.get("city")
    their_city = candidate.get("city")
    if my_city and their_city and my_city.lower() == their_city.lower():
        score = min(100, score + CITY_BONUS)

    return score


def filter_candidates(me: dict, candidates: list[dict], viewed_ids: set[int]) -> list[dict]:
    """Return candidates matching filters, excluding self and already viewed."""
    min_age = me.get("filter_min_age", 16)
    max_age = me.get("filter_max_age", 100)
    only_my_city = bool(me.get("filter_only_my_city", 0))
    my_city = me.get("city")

    results = []
    for candidate in candidates:
        cid = candidate["user_id"]
        if cid == me["user_id"] or cid in viewed_ids:
            continue
        if not gender_match(
            me["gender"],
            me["looking_for"],
            candidate["gender"],
            candidate["looking_for"],
        ):
            continue
        if candidate["age"] < min_age or candidate["age"] > max_age:
            continue
        if only_my_city and my_city and candidate.get("city", "").lower() != my_city.lower():
            continue
        results.append(candidate)
    return results


def score_candidates(me: dict, candidates: list[dict]) -> list[tuple[dict, int]]:
    """Return candidates sorted by compatibility descending."""
    scored = [(c, calculate_compatibility(me, c)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
