import pytest
from auth.password import (
    hash_password, verify_password, validate_policy,
    generate_temp_password, is_in_history,
)


def test_hash_and_verify():
    pwd = "Cybersecuritylogadmin@12798"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True


def test_wrong_password_fails():
    hashed = hash_password("Cybersecuritylogadmin@12798")
    assert verify_password("WrongPassword!123XYZ", hashed) is False


def test_policy_valid():
    ok, violations = validate_policy("Cybersecuritylogadmin@12798")
    assert ok is True
    assert violations == []


def test_policy_too_short():
    ok, violations = validate_policy("Short@1")
    assert ok is False
    assert any("20" in v for v in violations)


def test_policy_missing_upper():
    ok, violations = validate_policy("security@bosch#96932613")
    assert ok is False
    assert any("uppercase" in v.lower() for v in violations)


def test_policy_missing_digit():
    ok, violations = validate_policy("Security@bosch#ABCDEFGH")
    assert ok is False
    assert any("digit" in v.lower() for v in violations)


def test_policy_missing_special():
    ok, violations = validate_policy("SecurityBosch9693261348")
    assert ok is False
    assert any("special" in v.lower() for v in violations)


def test_temp_password_meets_policy():
    for _ in range(10):
        temp = generate_temp_password()
        ok, violations = validate_policy(temp)
        assert ok is True, f"Temp password failed policy: {violations}"
        assert len(temp) >= 20


def test_is_in_history_detects_reuse():
    pwd = "Cybersecuritylogadmin@12798"
    hashed = hash_password(pwd)
    assert is_in_history(pwd, [hashed]) is True


def test_is_in_history_no_match():
    hashed = hash_password("Cybersecuritylogadmin@12798")
    assert is_in_history("Different@pass#9999999999", [hashed]) is False


def test_is_in_history_empty():
    assert is_in_history("Anything@pass#99999X", []) is False
