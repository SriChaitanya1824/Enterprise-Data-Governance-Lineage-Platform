from datetime import timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models.entities import Person, now

passwords = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_db)]


def token_for(user: Person):
    settings = get_settings()
    return jwt.encode(
        {
            "sub": str(user.id),
            "exp": now() + timedelta(minutes=settings.jwt_expiry_minutes),
            "iat": now(),
            "iss": "enterprise-governance",
            "aud": "governance-ui",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def current_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    try:
        if not credentials:
            raise ValueError("Missing token")
        payload = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            issuer="enterprise-governance",
            audience="governance-ui",
        )
        user = db.get(Person, int(payload["sub"]))
        if not user or not user.active:
            raise ValueError("Inactive user")
        return user
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            401, "Invalid or expired authentication", headers={"WWW-Authenticate": "Bearer"}
        )


User = Annotated[Person, Depends(current_user)]


def authorize(user, *roles):
    if user.role != "ADMIN" and user.role not in roles:
        raise HTTPException(403, "Your role does not permit this action")
