from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from dotenv import load_dotenv
import os
import logging
logger = logging.getLogger(__name__)
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "NIWFNWIETNPFNKOFomefemtkmkpmewfwf")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=25)

    to_encode.update({"exp": expire, "token_type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)

    to_encode.update({"exp": expire, "token_type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_auth_token(data: dict, expires_delta: timedelta = None):
    return create_access_token(data, expires_delta)


def verify_token(token: str, expected_type: str = "access"):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("token_type")
        if token_type != expected_type:
            logger.error("Invalid token type: expected %s, got %s", expected_type, token_type)
            raise HTTPException(status_code=401, detail="Invalid token")
        logger.info("Token decoded successfully")
        return payload
    except ExpiredSignatureError:
        logger.error("Token has expired", exc_info=True)
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        logger.error("Invalid token", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_refresh_token(token: str):
    return verify_token(token, expected_type="refresh")


