from services.profile import format_profile


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
