from keyboards import filters_keyboard, settings_keyboard


def test_settings_keyboard_has_filters_button():
    kb = settings_keyboard(True)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "🔍 Фильтры ленты" in texts


def test_filters_keyboard_structure():
    kb = filters_keyboard(min_age=20, max_age=30, only_my_city=True)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("20" in t and "30" in t for t in texts)
    assert any("Только мой город" in t for t in texts)
