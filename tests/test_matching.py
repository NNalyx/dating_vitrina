# tests/test_matching.py

import pytest
from services.matching import calculate_compatibility, gender_match


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
    assert calculate_compatibility(me, candidate) == 70


def test_gender_match_both_all():
    assert gender_match("male", "all", "female", "all") is True


def test_gender_match_unidirectional():
    assert gender_match("male", "female", "female", "male") is True


def test_gender_match_no_match():
    assert gender_match("male", "female", "male", "female") is False
