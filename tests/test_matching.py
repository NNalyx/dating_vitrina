# tests/test_matching.py

import pytest
from services.matching import calculate_compatibility, filter_candidates, gender_match


def test_calculate_compatibility_perfect_match():
    me = {"age": 20, "goal": "relationship", "interests": "Dota 2,Аниме"}
    candidate = {"age": 20, "goal": "relationship", "interests": "Dota 2,Аниме"}
    assert calculate_compatibility(me, candidate) == 100


def test_calculate_compatibility_no_common_interests():
    me = {"age": 20, "goal": "relationship", "interests": "Dota 2,Аниме"}
    candidate = {"age": 20, "goal": "relationship", "interests": "Футбол,Кулинария"}
    assert calculate_compatibility(me, candidate) == 60


def test_calculate_compatibility_different_goal():
    me = {"age": 20, "goal": "relationship", "interests": "Dota 2"}
    candidate = {"age": 20, "goal": "friendship", "interests": "Dota 2"}
    # Same age + identical interests + goal mismatch penalty = 30 + 40 + 10
    assert calculate_compatibility(me, candidate) == 80


def test_gender_match_both_all():
    assert gender_match("male", "all", "female", "all") is True


def test_gender_match_unidirectional():
    assert gender_match("male", "female", "female", "male") is True


def test_gender_match_no_match():
    assert gender_match("male", "female", "male", "female") is False


def test_filter_by_age_range():
    me = {
        "user_id": 1,
        "age": 25,
        "gender": "male",
        "looking_for": "female",
        "filter_min_age": 22,
        "filter_max_age": 28,
        "filter_only_my_city": 0,
        "city": "Москва",
    }
    candidates = [
        {"user_id": 2, "age": 21, "gender": "female", "looking_for": "male", "city": "Москва"},
        {"user_id": 3, "age": 24, "gender": "female", "looking_for": "male", "city": "Москва"},
        {"user_id": 4, "age": 30, "gender": "female", "looking_for": "male", "city": "Москва"},
    ]
    result = filter_candidates(me, candidates, set())
    assert [c["user_id"] for c in result] == [3]


def test_filter_only_my_city():
    me = {
        "user_id": 1,
        "age": 25,
        "gender": "male",
        "looking_for": "female",
        "filter_min_age": 16,
        "filter_max_age": 100,
        "filter_only_my_city": 1,
        "city": "Москва",
    }
    candidates = [
        {"user_id": 2, "age": 24, "gender": "female", "looking_for": "male", "city": "СПб"},
        {"user_id": 3, "age": 24, "gender": "female", "looking_for": "male", "city": "Москва"},
    ]
    result = filter_candidates(me, candidates, set())
    assert [c["user_id"] for c in result] == [3]


def test_city_bonus_in_compatibility():
    base = {"age": 25, "goal": "relationship", "interests": "Dota 2", "city": "Москва"}
    same_city = {"age": 25, "goal": "relationship", "interests": "Dota 2,CS2", "city": "москва"}
    other_city = {"age": 25, "goal": "relationship", "interests": "Dota 2,CS2", "city": "СПб"}
    same_score = calculate_compatibility(base, same_city)
    other_score = calculate_compatibility(base, other_city)
    assert same_score == 90
    assert other_score == 80
    assert same_score - other_score == 10
