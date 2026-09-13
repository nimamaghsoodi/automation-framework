"""
Authentication routes:
  POST /api/v1/auth/login          – email + password → JWT
  GET  /api/v1/auth/me             – current user info
  GET  /api/v1/auth/oauth/{p}      – start OAuth2 (google|github)
  GET  /api/v1/auth/oauth/{p}/callback – OAuth2 callback
  GET  /api/v1/auth/saml/login     – redirect to IdP (SAML, if enabled)
  POST /api/v1/auth/saml/acs       – SAML assertion consumer service
  GET  /api/v1/auth/saml/metadata  – SP metadata XML
"""
from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.models.user import User
from app.services.auth import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# ── provider registry ──────────────────────────────────────────────────────────

_PROVIDERS: dict[str, dict] = {
    "google": {
        "auth_url":     "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url":    "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope":        "openid email profile",
    },
    "github": {
        "auth_url":     "https://github.com/login/oauth/authorize",
        "token_url":    "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "email_url":    "https://api.github.com/user/emails",
        "scope":        "read:user user:email",
    },
}

_CLIENT_ID: dict[str, str | None] = {
    "google": settings.google_client_id,
    "github": settings.github_client_id,
}
_CLIENT_SECRET: dict[str, str | None] = {
    "google": settings.google_client_secret,
    "github": settings.github_client_secret,
}

# ── schemas ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# ── local auth ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    token = create_access_token(user.id, user.email, user.role)
    return {"access_token": token, "user": _user_out(user)}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return _user_out(user)

# ── OAuth2 ─────────────────────────────────────────────────────────────────────

@router.get("/oauth/{provider}")
async def oauth_start(provider: str):
    cfg = _get_provider(provider)
    client_id = _CLIENT_ID.get(provider)
    if not client_id:
        raise HTTPException(status_code=404, detail=f"OAuth provider '{provider}' not configured. Set {provider.upper()}_CLIENT_ID.")
    state = secrets.token_urlsafe(32)
    callback_url = f"{settings.oauth_redirect_base}/api/v1/auth/oauth/{provider}/callback"
    params = {
        "client_id": client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
    }
    redirect = RedirectResponse(url=f"{cfg['auth_url']}?{urlencode(params)}")
    redirect.set_cookie("oauth_state", state, max_age=600, httponly=True, samesite="lax")
    return redirect


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    oauth_state: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not oauth_state or state != oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state — CSRF check failed")
    cfg = _get_provider(provider)
    client_id = _CLIENT_ID[provider]
    client_secret = _CLIENT_SECRET[provider]
    callback_url = f"{settings.oauth_redirect_base}/api/v1/auth/oauth/{provider}/callback"

    async with httpx.AsyncClient(timeout=15) as client:
        # Exchange code → access token
        token_resp = await client.post(
            cfg["token_url"],
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        # Fetch user profile
        userinfo_resp = await client.get(
            cfg["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

        email = _extract_email(provider, userinfo)
        # GitHub: if email is private, fetch from /user/emails
        if not email and provider == "github" and "email_url" in cfg:
            emails_resp = await client.get(
                cfg["email_url"],
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            emails_resp.raise_for_status()
            primary = next((e for e in emails_resp.json() if e.get("primary")), None)
            email = primary["email"] if primary else None

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from OAuth provider")

    subject = f"{provider}:{_extract_subject(provider, userinfo)}"
    user = await _find_or_create_sso_user(db, email, subject)
    jwt_token = create_access_token(user.id, user.email, user.role)
    # Redirect to frontend auth-callback route with token
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?token={jwt_token}")

# ── SAML ───────────────────────────────────────────────────────────────────────

@router.get("/saml/metadata")
async def saml_metadata():
    _require_saml()
    from app.services.saml_service import get_sp_metadata
    from fastapi.responses import Response as R
    metadata, errors = get_sp_metadata()
    if errors:
        raise HTTPException(status_code=500, detail=f"SAML metadata errors: {errors}")
    return R(content=metadata, media_type="text/xml")


@router.get("/saml/login")
async def saml_login(request: Request):
    _require_saml()
    from app.services.saml_service import build_login_url
    req_data = _saml_request_data(request)
    return RedirectResponse(url=build_login_url(req_data))


@router.post("/saml/acs")
async def saml_acs(request: Request, db: AsyncSession = Depends(get_db)):
    _require_saml()
    from app.services.saml_service import process_response
    form = await request.form()
    req_data = {**_saml_request_data(request), "post_data": dict(form)}
    try:
        attrs = process_response(req_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    user = await _find_or_create_sso_user(db, attrs["email"], f"saml:{attrs['name_id']}")
    jwt_token = create_access_token(user.id, user.email, user.role)
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?token={jwt_token}")

# ── helpers ────────────────────────────────────────────────────────────────────

def _user_out(user: User) -> dict:
    return {"id": str(user.id), "email": user.email, "role": user.role, "is_active": user.is_active}


def _get_provider(provider: str) -> dict:
    if provider not in _PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown OAuth provider '{provider}'")
    return _PROVIDERS[provider]


def _extract_email(provider: str, userinfo: dict) -> str | None:
    if provider == "google":
        return userinfo.get("email")
    if provider == "github":
        return userinfo.get("email")  # may be None for private emails
    return None


def _extract_subject(provider: str, userinfo: dict) -> str:
    if provider == "google":
        return str(userinfo["sub"])
    if provider == "github":
        return str(userinfo["id"])
    return str(userinfo.get("id") or userinfo.get("sub") or "unknown")


async def _find_or_create_sso_user(db: AsyncSession, email: str, sso_subject: str) -> User:
    # Try by SSO subject first (returning user via same provider)
    result = await db.execute(select(User).where(User.sso_subject == sso_subject))
    user = result.scalar_one_or_none()
    if user:
        return user
    # Try by email (link with existing local account)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.sso_subject = sso_subject
        await db.commit()
        return user
    # Create new user (viewer by default — admin promotes later)
    user = User(email=email, role="viewer", sso_subject=sso_subject, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _require_saml() -> None:
    if not settings.saml_enabled:
        raise HTTPException(status_code=404, detail="SAML is not enabled. Set SAML_ENABLED=true.")


def _saml_request_data(request: Request) -> dict:
    return {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.headers.get("host", "localhost"),
        "script_name": str(request.url.path),
        "server_port": str(request.url.port or (443 if request.url.scheme == "https" else 80)),
        "get_data": dict(request.query_params),
        "post_data": {},
    }
