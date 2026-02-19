from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, AdminCreate, Token, User as UserSchema

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_token_response(user: User) -> Token:
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserSchema.model_validate(user),
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=body.email,
        password_hash=get_password_hash(body.password),
        full_name=body.full_name,
        phone=body.phone,
        avatar_url=body.avatar_url,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _build_token_response(user)


@router.post("/admin/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def admin_register(body: AdminCreate, db: Session = Depends(get_db)):
    if body.admin_secret != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin secret",
        )
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=body.email,
        password_hash=get_password_hash(body.password),
        full_name=body.full_name,
        phone=body.phone,
        avatar_url=body.avatar_url,
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _build_token_response(user)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )
    return _build_token_response(user)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout the current user.
    Since we are using stateless JWTs, the client should discard the token.
    This endpoint serves as a confirmation and can be extended for token blacklisting if needed.
    """
    return {"message": "Successfully logged out"}
