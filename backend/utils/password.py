

import logging
import os
import re
from dataclasses import dataclass, field
from typing import List

import bcrypt

logger = logging.getLogger("fundforge.utils.password")





_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
_MAX_LENGTH: int = int(os.getenv("PASSWORD_MAX_LENGTH", "128"))
_BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

_SPECIAL_CHARS: str = r"!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~"
_UPPERCASE_RE = re.compile(r"[A-Z]")
_LOWERCASE_RE = re.compile(r"[a-z]")
_DIGIT_RE = re.compile(r"\d")
_SPECIAL_RE = re.compile(rf"[{_SPECIAL_CHARS}]")


_COMMON_PASSWORDS: frozenset = frozenset({
    "password", "password1", "password123", "123456", "12345678",
    "qwerty", "qwerty123", "letmein", "welcome", "admin",
    "iloveyou", "monkey", "dragon", "master", "abc123",
    "111111", "sunshine", "princess", "passw0rd", "login",
})






@dataclass
class PasswordValidationResult:
    

    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    strength: str = "weak"
    score: int = 0

    def to_dict(self) -> dict:
        
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "strength": self.strength,
            "score": self.score,
        }






def validate_password(password: str) -> PasswordValidationResult:
    
    if not isinstance(password, str):
        return PasswordValidationResult(
            is_valid=False,
            errors=["Password must be a string."],
            strength="weak",
            score=0,
        )

    errors: List[str] = []
    score: int = 0

    
    if len(password) < _MIN_LENGTH:
        errors.append(f"Password must be at least {_MIN_LENGTH} characters long.")
    elif len(password) > _MAX_LENGTH:
        errors.append(f"Password must not exceed {_MAX_LENGTH} characters.")
    else:
        score += 1

    
    if not _UPPERCASE_RE.search(password):
        errors.append("Password must contain at least one uppercase letter (A–Z).")
    else:
        score += 1

    if not _LOWERCASE_RE.search(password):
        errors.append("Password must contain at least one lowercase letter (a–z).")
    else:
        score += 1

    if not _DIGIT_RE.search(password):
        errors.append("Password must contain at least one digit (0–9).")
    else:
        score += 1

    if not _SPECIAL_RE.search(password):
        errors.append(
            "Password must contain at least one special character "
            "(!@#$%^&*(),.?\":{}|<>_-+=[]\\;'/`~)."
        )
    else:
        score += 1

    
    if not errors and password.lower() in _COMMON_PASSWORDS:
        errors.append("This password is too common. Please choose something more unique.")
        score = max(0, score - 2)

    
    if re.fullmatch(r"(.)\1+", password):
        errors.append("Password must not consist entirely of repeated characters.")
        score = max(0, score - 1)

    is_valid = len(errors) == 0
    strength = _score_to_strength(score)

    result = PasswordValidationResult(
        is_valid=is_valid,
        errors=errors,
        strength=strength,
        score=score,
    )

    logger.debug(
        "Password validation: is_valid=%s strength=%s score=%d",
        is_valid,
        strength,
        score,
    )
    return result


def hash_password(plaintext: str) -> str:
    
    if not plaintext:
        raise ValueError("Cannot hash an empty password.")
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    hashed: bytes = bcrypt.hashpw(plaintext.encode("utf-8"), salt)
    logger.debug("Password hashed with %d rounds.", _BCRYPT_ROUNDS)
    return hashed.decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    
    if not plaintext or not hashed:
        return False
    try:
        return bcrypt.checkpw(
            plaintext.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except Exception as exc:
        logger.warning("bcrypt verification error (possible hash corruption): %s", exc)
        return False


def validate_and_hash(plaintext: str) -> tuple:
    
    result = validate_password(plaintext)
    if not result.is_valid:
        return result, None
    return result, hash_password(plaintext)


def is_strong_enough(plaintext: str) -> bool:
    
    return validate_password(plaintext).is_valid






def _score_to_strength(score: int) -> str:
    
    if score <= 1:
        return "weak"
    if score == 2:
        return "fair"
    if score in (3, 4):
        return "strong"
    return "very_strong"
