"""Authentication routes: register, login with 2FA OTP, forgot password."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth_utils import (
    create_access_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from fastapi.security import HTTPAuthorizationCredentials
from auth_utils import security
from database import get_db
from models import User
from otp_service import create_and_send_otp, verify_otp

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(default="", max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_admin: bool = False




class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class OtpPendingResponse(BaseModel):
    requires_otp: bool = True
    email: str
    message: str
    access_token: str | None = None
    user: UserResponse | None = None


def _user_response(user: User) -> UserResponse:
    is_admin = user.email.lower().strip() == "yashrakeshsoni@gmail.com"
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_admin=is_admin,
    )


def _admin_response() -> UserResponse:
    return UserResponse(
        id="admin",
        email="admin@hyundai.local",
        full_name="Yash Admin",
        is_admin=True,
    )


@router.post("/register", response_model=OtpPendingResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
    )
    db.add(user)
    db.commit()

    create_and_send_otp(db, email, "register_verify")
    return OtpPendingResponse(
        email=email,
        message="Account created. Enter the 6-digit verification code sent to your email.",
    )


@router.post("/verify-register-otp", response_model=AuthTokenResponse)
def verify_register_otp(body: OtpVerifyRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    verify_otp(db, email, body.otp, "register_verify")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    token = create_access_token(user.id, user.email, role="admin" if email == "yashrakeshsoni@gmail.com" else "user")
    return AuthTokenResponse(access_token=token, user=_user_response(user))


@router.post("/login", response_model=OtpPendingResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    
    # Special bypass for Yash's credentials
    if email == "yashrakeshsoni@gmail.com" and body.password == "adminisyash":
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                password_hash=hash_password(body.password),
                full_name="Yash Admin",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        token = create_access_token(user.id, user.email, role="admin")
        return OtpPendingResponse(
            requires_otp=False,
            email=email,
            message="Logged in as admin successfully.",
            access_token=token,
            user=_user_response(user),
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    create_and_send_otp(db, email, "login_2fa")
    return OtpPendingResponse(
        email=email,
        message="A 6-digit verification code has been sent to your email.",
    )


@router.post("/admin-login", response_model=AuthTokenResponse)
def admin_login(body: AdminLoginRequest, db: Session = Depends(get_db)):
    username = body.username.strip().lower()
    if (username == "yash" and body.password == "yashisadmin") or (username == "yashrakeshsoni@gmail.com" and body.password == "adminisyash"):
        user_id = "admin"
        email = username
        full_name = "Yash Admin"
        if username == "yashrakeshsoni@gmail.com":
            user = db.query(User).filter(User.email == username).first()
            if not user:
                user = User(
                    email=username,
                    password_hash=hash_password(body.password),
                    full_name="Yash Admin",
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            user_id = user.id
            full_name = user.full_name
            email = user.email
            
        token = create_access_token(user_id, email, role="admin")
        return AuthTokenResponse(
            access_token=token,
            user=UserResponse(
                id=user_id,
                email=email,
                full_name=full_name,
                is_admin=True,
            )
        )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")


@router.post("/verify-login-otp", response_model=AuthTokenResponse)
def verify_login_otp(body: OtpVerifyRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    verify_otp(db, email, body.otp, "login_2fa")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    token = create_access_token(user.id, user.email, role="admin" if email == "yashrakeshsoni@gmail.com" else "user")
    return AuthTokenResponse(access_token=token, user=_user_response(user))


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found in our records")

    create_and_send_otp(db, email, "password_reset")
    return {"message": "Password reset OTP sent to your email.", "email": email}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    verify_otp(db, email, body.otp, "password_reset")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated successfully. You can now sign in."}


@router.get("/me", response_model=UserResponse)
def get_me(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is not None and credentials.credentials:
        payload = decode_token(credentials.credentials)
        if payload.get("role") == "admin":
            email = payload.get("email", "admin@hyundai.local").lower().strip()
            if email == "yashrakeshsoni@gmail.com":
                user = db.query(User).filter(User.email == email).first()
                if user:
                    return _user_response(user)
            return _admin_response()
    user = get_current_user(credentials, db)
    return _user_response(user)
