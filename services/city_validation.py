import re

_SPAM_WORDS = {"asdf", "ffff", "фффф", "qwerty", "йцукен", "abc", "xyz"}
_CITY_RE = re.compile(r"^[A-Za-zА-Яа-яЁё\s\-]+$")


def normalize_city(raw: str) -> str:
    """Trim, collapse spaces, strip edge hyphens and title-case."""
    cleaned = " ".join(raw.split()).strip("- ")
    return cleaned.title()


def is_valid_city(raw: str) -> bool:
    """Soft validation: reject obvious garbage but accept any real-looking city name."""
    if not raw:
        return False
    cleaned = normalize_city(raw)
    if len(cleaned) < 3 or len(cleaned) > 50:
        return False
    if not _CITY_RE.match(cleaned):
        return False
    if cleaned.lower() in _SPAM_WORDS:
        return False
    if not re.search(r"[A-Za-zА-Яа-яЁё]", cleaned):
        return False
    return True
