import base64
import json

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from config import SUPABASE_JWT_AUDIENCE, SUPABASE_URL
from schemas import AuthUser

_jwks_client: PyJWKClient | None = None


def _b64url_decode(value: str) -> bytes:
    value += "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value.encode())


def _jwt_header(token: str) -> dict:
    try:
        return json.loads(_b64url_decode(token.split(".")[0]))
    except Exception:
        raise HTTPException(401, "Invalid Supabase token")


def verify_supabase_jwt(token: str) -> dict:
    """Verify modern Supabase access tokens with the project's JWKS."""
    if not SUPABASE_URL:
        raise HTTPException(500, "SUPABASE_URL or VITE_SUPABASE_URL is missing")

    alg = _jwt_header(token).get("alg")
    if alg not in {"ES256", "RS256"}:
        raise HTTPException(401, "Invalid Supabase token")

    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        )

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=[alg],
            audience=SUPABASE_JWT_AUDIENCE,
            issuer=f"{SUPABASE_URL.rstrip('/')}/auth/v1",
            options={"require": ["sub", "aud", "iss", "exp"]},
        )
    except Exception:
        raise HTTPException(401, "Invalid Supabase token")


def user_from_authorization_header(authorization: str | None) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")

    claims = verify_supabase_jwt(authorization.removeprefix("Bearer "))
    return AuthUser(id=claims["sub"], email=claims.get("email", ""))
