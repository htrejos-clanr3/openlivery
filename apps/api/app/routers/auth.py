"""Extend agency auth: Google OR password, forgot/set password."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Agency, OAuthAccount, User
from ..ratelimit import login_rate_limit
from ..schemas import (
    AuthOptionsOut,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SetPasswordRequest,
    UserOut,
)
from ..security import create_access_token, hash_password, verify_password
from ..services import mailer
from ..services.auth_identity import (
    consume_password_token,
    generic_forgot_message,
    issue_password_token,
    link_or_get_oauth,
    verify_google_id_token,
)
from ..services.inbox_desk import seed_default_canned
from ..services.legal_consent import record_register_acceptance
from ..slugs import unique_slug


router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_session_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    response.set_cookie(
        key="access_token",
        value=create_access_token(str(user.id)),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )


@router.get("/options", response_model=AuthOptionsOut)
def auth_options():
    settings = get_settings()
    client_id = settings.google_oauth_client_id.strip() or None
    return AuthOptionsOut(google_enabled=bool(client_id), google_client_id=client_id)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(login_rate_limit)],
)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if not payload.accept_terms or not payload.accept_privacy:
        raise HTTPException(status_code=400, detail="Terms and privacy must be accepted to register")
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="A user with that email already exists")
    agency_name = payload.agency_name.strip()
    agency = Agency(name=agency_name, slug=unique_slug(db, Agency, "slug", agency_name))
    user = User(
        agency=agency,
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    seed_default_canned(db, user.agency_id)
    record_register_acceptance(db, user=user)
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, user)
    return user


@router.post("/login", response_model=UserOut, dependencies=[Depends(login_rate_limit)])
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    _set_session_cookie(response, user)
    return user


@router.post("/google", response_model=UserOut, dependencies=[Depends(login_rate_limit)])
def google_login(payload: GoogleAuthRequest, response: Response, db: Session = Depends(get_db)):
    identity = verify_google_id_token(payload.id_token)
    oauth = db.scalar(
        select(OAuthAccount).where(OAuthAccount.provider == "google", OAuthAccount.subject == identity.subject)
    )
    user: User | None = None
    if oauth and oauth.user_id:
        user = db.get(User, oauth.user_id)
    if not user:
        user = db.scalar(select(User).where(User.email == identity.email))
    if not user:
        # Google-only registration creates agency from display name.
        agency = Agency(name=f"{identity.name}'s Agency", slug=unique_slug(db, Agency, "slug", identity.name))
        user = User(agency=agency, name=identity.name, email=identity.email, password_hash=None)
        db.add(user)
        db.flush()
        seed_default_canned(db, user.agency_id)
    link_or_get_oauth(db, identity=identity, user=user)
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, user)
    return user


@router.post("/forgot-password", response_model=ForgotPasswordResponse, dependencies=[Depends(login_rate_limit)])
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    message = generic_forgot_message()
    if payload.audience != "agency":
        # Portal forgot is handled under /portal/{slug}/forgot-password.
        return ForgotPasswordResponse(message=message)

    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        return ForgotPasswordResponse(message=message)

    has_google = bool(
        db.scalar(select(OAuthAccount).where(OAuthAccount.user_id == user.id, OAuthAccount.provider == "google"))
    )
    if not user.password_hash and has_google:
        # Standard path: no password to reset — offer set-password after email proof.
        raw = issue_password_token(db, email=email, audience="agency", purpose="set", user=user)
        db.commit()
        mailer.send_email(
            to=user.email,
            subject="Configura tu contraseña de Fast Livery",
            text=(
                "Abre este enlace para crear tu contraseña:\n\n"
                f"{mailer.password_reset_link(raw, 'set')}\n\n"
                "El enlace caduca en 2 horas."
            ),
        )
        return ForgotPasswordResponse(
            message=message,
            account_kind="google_only",
            reset_token=raw if settings.auth_expose_reset_token else None,
        )

    if not user.password_hash:
        return ForgotPasswordResponse(message=message)

    raw = issue_password_token(db, email=email, audience="agency", purpose="reset", user=user)
    db.commit()
    mailer.send_email(
        to=user.email,
        subject="Restablece tu contraseña de Fast Livery",
        text=(
            "Abre este enlace para restablecer tu contraseña:\n\n"
            f"{mailer.password_reset_link(raw, 'reset')}\n\n"
            "El enlace caduca en 2 horas. Si no lo solicitaste, ignora este mensaje."
        ),
    )
    return ForgotPasswordResponse(
        message=message,
        account_kind="reset_sent",
        reset_token=raw if settings.auth_expose_reset_token else None,
    )


@router.post("/reset-password", response_model=UserOut)
def reset_password(payload: ResetPasswordRequest, response: Response, db: Session = Depends(get_db)):
    row = consume_password_token(db, payload.token, purpose="reset")
    if row.audience != "agency" or not row.user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, user)
    return user


@router.post("/set-password", response_model=UserOut)
def set_password(payload: SetPasswordRequest, response: Response, db: Session = Depends(get_db)):
    """Create a password for Google-only accounts (after email-linked token)."""
    row = consume_password_token(db, payload.token, purpose="set")
    if row.audience != "agency" or not row.user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie("access_token", path="/")


@router.post("/change-password", response_model=UserOut)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Change (or create) the signed-in agency user's password from Settings."""
    new_password = payload.new_password
    if user.password_hash:
        if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        if verify_password(new_password, user.password_hash):
            raise HTTPException(status_code=400, detail="New password must be different from the current password")
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
