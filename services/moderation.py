import re

# Built-in profanity list (Russian + English). Extend as needed.
_PROFANITY_WORDS = {
    # Russian
    "блядь", "блять", "сука", "суки", "хуй", "хуи", "хуёвый", "хуевый",
    "хуесос", "пизда", "пиздец", "ебать", "ебал", "ебёт", "ебет",
    "ёбарь", "ебарь", "ёбан", "ебан", "ебанутый", "ёбнутый", "пидор",
    "пидорас", "пидарас", "гандон", "гондон", "мудак", "мудила",
    "ублюдок", "тварь", "скотина", "шлюха", "проститутка", "курва",
    "член", "залупа", "дрочить", "дрочер",
    # English
    "fuck", "fucking", "fucker", "fucked", "shit", "shitty", "bitch",
    "whore", "slut", "cunt", "dick", "cock", "pussy", "asshole",
    "bastard",
}

# Pre-compile a single regex with word boundaries. Sort words by length descending
# so longer expressions are tried before shorter ones that they may contain.
_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(re.escape(w) for w in sorted(_PROFANITY_WORDS, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace/hyphens for consistent matching."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-+", "-", text)
    return text.strip(" -")


def contains_profanity(text: str) -> bool:
    """Return True if text contains a profane word as a whole word."""
    if not text:
        return False
    return bool(_PATTERN.search(_normalize(text)))


def is_clean_name(text: str) -> bool:
    """Return True if the display name is free of profanity."""
    return not contains_profanity(text)


def is_clean_city(text: str) -> bool:
    """Return True if the city name is free of profanity."""
    return not contains_profanity(text)
