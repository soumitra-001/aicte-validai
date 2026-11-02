"""JWT authentication, password hashing, and role-based access dependencies."""
from __future__ import annotations

import datetime as dt
import os
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Role, User

SECRET_KEY = os.environ.get("AICTE_VALIDAI_SECRET", "dev-secret-change-me-please-32bytes!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("AICTE_VALIDAI_TOKEN_MIN", "480"))

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# --------------------------------------------------------------------------- #
# Password helpers
# --------------------------------------------------------------------------- #
def hash_password(plain: str) -> str:
    """Return bcrypt hash of the plaintext password."""
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time verify of plaintext against stored hash."""
    try:
        return pwd_ctx.verify(plain, hashed)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Token helpers
# --------------------------------------------------------------------------- #
def create_access_token(username: str, role: str) -> str:
    """Create a signed JWT with sub=username and role claim."""
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# --------------------------------------------------------------------------- #
# Dependencies
# --------------------------------------------------------------------------- #
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Resolve the JWT bearer to a User row, or 401."""
    payload = _decode(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token missing subject")
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles: str | Role) -> Iterable:
    """Return a dependency factory enforcing one of the given roles."""
    allowed = {r.value if isinstance(r, Role) else r for r in roles}

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role privileges")
        return user

    return _dep


# Convenience dependencies
require_applicant = require_roles(Role.APPLICANT)
require_officer = require_roles(Role.SCRUTINY_OFFICER, Role.ADMIN)
require_admin = require_roles(Role.ADMIN)
require_any = get_current_user