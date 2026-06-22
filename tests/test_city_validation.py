import pytest

from services.city_validation import is_valid_city, normalize_city


def test_normalize_city():
    assert normalize_city("  москва ") == "Москва"
    assert normalize_city("САНКТ-ПЕТЕРБУРГ") == "Санкт-Петербург"


def test_valid_city():
    assert is_valid_city("Москва") is True
    assert is_valid_city("Санкт-Петербург") is True
    assert is_valid_city("Нижний Новгород") is True


def test_invalid_city_too_short():
    assert is_valid_city("Аб") is False


def test_invalid_city_numbers():
    assert is_valid_city("Москва123") is False


def test_invalid_city_spam():
    assert is_valid_city("фффф") is False
    assert is_valid_city("asdf") is False


def test_invalid_city_only_symbols():
    assert is_valid_city("---") is False
    assert is_valid_city("   ") is False
