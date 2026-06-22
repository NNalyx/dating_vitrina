import pytest

from services.moderation import contains_profanity, is_clean_city, is_clean_name


class TestContainsProfanity:
    def test_clean_text_returns_false(self):
        assert contains_profanity("Анна") is False
        assert contains_profanity("Москва") is False
        assert contains_profanity("Ivan") is False
        assert contains_profanity("London") is False

    def test_russian_profanity_detected(self):
        assert contains_profanity("блядь") is True

    def test_english_profanity_detected(self):
        assert contains_profanity("fuck") is True

    def test_case_insensitive(self):
        assert contains_profanity("БЛЯДЬ") is True
        assert contains_profanity("Fuck") is True

    def test_surrounding_whitespace_normalized(self):
        assert contains_profanity("  блядь  ") is True
        assert contains_profanity("Fuck ") is True

    def test_word_boundary_avoids_false_positives(self):
        # Assuming 'dick' is in the English list, Dickens should be allowed.
        assert contains_profanity("Dickens") is False


class TestIsCleanName:
    def test_clean_name(self):
        assert is_clean_name("Анна") is True

    def test_dirty_name(self):
        assert is_clean_name("блядь") is False


class TestIsCleanCity:
    def test_clean_city(self):
        assert is_clean_city("Москва") is True

    def test_dirty_city(self):
        assert is_clean_city("блядь") is False
