from services.profile import format_browse_card, format_profile


def test_browse_card_includes_city():
    user = {
        "name": "Анна",
        "age": 25,
        "goal": "relationship",
        "interests": "музыка, спорт",
        "city": "Москва",
    }
    text = format_browse_card(user, compatibility=80)
    assert "📍 <b>Город:</b> Москва" in text


def test_browse_card_omits_city_when_missing():
    user = {
        "name": "Анна",
        "age": 25,
        "goal": "relationship",
        "interests": "музыка, спорт",
        "city": None,
    }
    text = format_browse_card(user, compatibility=80)
    assert "📍 Город" not in text


def test_format_profile_shows_city():
    user = {
        "name": "Alice",
        "age": 25,
        "gender": "female",
        "looking_for": "male",
        "goal": "relationship",
        "interests": "Dota 2,Аниме",
        "city": "Москва",
    }
    text = format_profile(user)
    assert "📍 Город:" in text
    assert "Москва" in text


def test_format_profile_hides_missing_city():
    user = {
        "name": "Alice",
        "age": 25,
        "gender": "female",
        "looking_for": "male",
        "goal": "relationship",
        "interests": "Dota 2",
    }
    text = format_profile(user)
    assert "Город" not in text
