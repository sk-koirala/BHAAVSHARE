import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime

# Password policy: 8+ chars, at least 1 uppercase, 1 lowercase, 1 digit.
# The frontend should mirror this exact policy so error messages align.
_PASSWORD_POLICY_MSG = (
    "Password must be 8+ characters and contain at least one uppercase letter, "
    "one lowercase letter, and one digit."
)


def _validate_password_strength(pw: str) -> str:
    if len(pw) < 8:
        raise ValueError(_PASSWORD_POLICY_MSG)
    if not re.search(r"[A-Z]", pw):
        raise ValueError(_PASSWORD_POLICY_MSG)
    if not re.search(r"[a-z]", pw):
        raise ValueError(_PASSWORD_POLICY_MSG)
    if not re.search(r"\d", pw):
        raise ValueError(_PASSWORD_POLICY_MSG)
    return pw


# --- Auth / User ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def _check_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        if not re.match(r"^[A-Za-z\u0900-\u097F\s\.'-]+$", v):
            raise ValueError("Full name contains invalid characters.")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=40)
    location: Optional[str] = Field(None, max_length=100)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _check_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class AvatarUpload(BaseModel):
    """Base64-encoded image data URL, e.g. 'data:image/png;base64,iVBORw...'.
    Kept small (<= ~400KB encoded) to fit comfortably in the DB column."""
    data_url: str = Field(min_length=20, max_length=600_000)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Watchlist ---
class WatchlistCreate(BaseModel):
    symbol: str


class WatchlistItem(BaseModel):
    id: int
    symbol: str
    added_at: datetime

    class Config:
        from_attributes = True


# --- News ---
class NewsItemBase(BaseModel):
    title: str
    url: str
    summary: Optional[str] = None
    source: str
    language: str


class NewsItemResponse(NewsItemBase):
    id: int
    source_type: Optional[str] = None
    category: Optional[str] = None
    published_at: datetime
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None

    class Config:
        from_attributes = True


# --- Stock Prices ---
class StockPriceBase(BaseModel):
    symbol: str
    close_price: float
    volume: float
    turnover: Optional[float] = None


class StockPriceResponse(StockPriceBase):
    id: int
    date: datetime

    class Config:
        from_attributes = True


# --- Contact ---
class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    subject: Optional[str] = None
    message: str


class ContactResponse(BaseModel):
    id: int
    name: str
    email: str
    subject: Optional[str] = None
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Market / Sentiment ---
class SentimentSummary(BaseModel):
    positive: int
    negative: int
    neutral: int
    total_analyzed: int


# --- Notifications (admin) ---
class NotificationResponse(BaseModel):
    id: int
    event_type: str
    title: str
    body: Optional[str] = None
    actor_user_id: Optional[int] = None
    actor_email: Optional[str] = None
    meta: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Chat History ---
class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"
    symbol: Optional[str] = None


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    symbol: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Prediction Validation ---
class PredictionResponse(BaseModel):
    id: int
    symbol: str
    predicted_date: datetime
    predicted_direction: str
    confidence: float
    created_at: datetime
    actual_direction: Optional[str] = None
    actual_close: Optional[float] = None
    validation_status: Optional[str] = "pending"
    validated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
