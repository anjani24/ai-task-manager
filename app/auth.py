from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
import os
from dotenv import load_dotenv
import secrets
import hashlib
load_dotenv()

password_hash = PasswordHash.recommended()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return token

def verify_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            return None

        return user_id

    except jwt.InvalidTokenError:
        return None

def create_refresh_token():
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str):
    return hashlib.sha256(token.encode()).hexdigest()