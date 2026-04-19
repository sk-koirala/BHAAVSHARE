import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from app.db.database import get_db
from app.models import entities as db_models
from app.schemas import entities as schemas
from app.core.security import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
)
from app.services.scraper import scrape_all_news, RSS_SOURCES, REDDIT_SUBREDDITS
from app.services.nlp import process_news_batch
from app.services.forecasting import predict_direction, train_model, get_metrics
from app.services.chatbot import generate_chatbot_response
from app.services import stocks as stock_svc

router = APIRouter()


# =====================================================================
# Auth helpers
# =====================================================================
def _user_from_token(token: str, db: Session) -> Optional[db_models.User]:
    payload = decode_access_token(token)
    if not payload:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        return db.query(db_models.User).filter(db_models.User.id == int(sub)).first()
    except Exception:
        return None


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> db_models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    user = _user_from_token(token, db)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[db_models.User]:
    """Lenient auth — returns user if valid token, else None (no error)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return _user_from_token(authorization.split(" ", 1)[1], db)
    except Exception:
        return None


def get_admin_user(user: db_models.User = Depends(get_current_user)) -> db_models.User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


# =====================================================================
# Notification helper — admin-facing activity feed
# =====================================================================
def _notify(
    db: Session,
    event_type: str,
    title: str,
    body: Optional[str] = None,
    actor: Optional[db_models.User] = None,
    actor_email: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """Insert an admin-facing notification. Safe: any exception is swallowed
    so user-flow endpoints never fail because of logging side-effects."""
    try:
        n = db_models.Notification(
            event_type=event_type,
            title=title,
            body=body,
            actor_user_id=actor.id if actor else None,
            actor_email=(actor.email if actor else actor_email),
            meta=json.dumps(meta) if meta else None,
        )
        db.add(n)
        db.commit()
    except Exception:
        db.rollback()


# =====================================================================
# Auth endpoints
# =====================================================================
@router.post("/auth/signup", response_model=schemas.TokenResponse)
def signup(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(db_models.User).filter(db_models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # First user bootstrap as admin
    is_first = db.query(db_models.User).count() == 0
    user = db_models.User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_admin=is_first,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _notify(
        db,
        event_type="signup",
        title=f"New user signed up: {user.email}",
        body=f"{user.full_name or user.email} just created a BhaavShare account.",
        actor=user,
    )

    token = create_access_token(subject=user.id, extra={"email": user.email, "admin": user.is_admin})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(db_models.User).filter(db_models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    if not user.is_admin:
        _notify(
            db,
            event_type="login",
            title=f"User logged in: {user.email}",
            body=f"{user.full_name or user.email} just logged in.",
            actor=user,
        )

    token = create_access_token(subject=user.id, extra={"email": user.email, "admin": user.is_admin})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/auth/me", response_model=schemas.UserResponse)
def read_me(user: db_models.User = Depends(get_current_user)):
    return user


@router.put("/auth/me", response_model=schemas.UserResponse)
def update_me(
    payload: schemas.UserUpdate,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allow any authenticated user to update their own profile."""
    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if hasattr(user, k):
            setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/avatar", response_model=schemas.UserResponse)
def upload_avatar(
    payload: schemas.AvatarUpload,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a profile picture as a base64 data URL.

    Validates the prefix and rejects anything not a small PNG/JPEG/WebP.
    Storing inline keeps deployment simple (no object storage dependency).
    """
    url = (payload.data_url or "").strip()
    allowed_prefixes = (
        "data:image/png;base64,",
        "data:image/jpeg;base64,",
        "data:image/jpg;base64,",
        "data:image/webp;base64,",
        "data:image/gif;base64,",
    )
    if not any(url.startswith(p) for p in allowed_prefixes):
        raise HTTPException(status_code=400, detail="Only PNG, JPEG, WebP or GIF data URLs are accepted.")

    # Rough byte-size cap: base64 is ~4/3 of raw bytes. 600KB encoded ≈ 450KB raw.
    if len(url) > 600_000:
        raise HTTPException(status_code=413, detail="Image is too large. Please upload something under 400KB.")

    user.avatar_url = url
    db.commit()
    db.refresh(user)
    _notify(
        db,
        event_type="profile_update",
        title=f"Avatar updated: {user.email}",
        body=f"{user.full_name or user.email} uploaded a new profile picture.",
        actor=user,
    )
    return user


@router.post("/auth/change-password")
def change_password(
    payload: schemas.PasswordChange,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    _notify(
        db,
        event_type="password_change",
        title=f"Password changed: {user.email}",
        body=f"{user.full_name or user.email} updated their password.",
        actor=user,
    )
    return {"ok": True, "message": "Password updated successfully"}


# =====================================================================
# Watchlist
# =====================================================================
@router.get("/watchlist", response_model=List[schemas.WatchlistItem])
def get_watchlist(user: db_models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(db_models.Watchlist).filter(db_models.Watchlist.user_id == user.id).order_by(db_models.Watchlist.added_at.desc()).all()


@router.post("/watchlist", response_model=schemas.WatchlistItem)
def add_watchlist(payload: schemas.WatchlistCreate, user: db_models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    sym = payload.symbol.upper().strip()
    if sym not in stock_svc.NEPSE_STOCKS:
        raise HTTPException(status_code=400, detail=f"Unknown symbol {sym}")
    existing = db.query(db_models.Watchlist).filter_by(user_id=user.id, symbol=sym).first()
    if existing:
        return existing
    item = db_models.Watchlist(user_id=user.id, symbol=sym)
    db.add(item)
    db.commit()
    db.refresh(item)
    _notify(
        db,
        event_type="watchlist_add",
        title=f"Watchlist add: {sym}",
        body=f"{user.full_name or user.email} added {sym} to their watchlist.",
        actor=user,
        meta={"symbol": sym},
    )
    return item


@router.delete("/watchlist/{symbol}")
def remove_watchlist(symbol: str, user: db_models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(db_models.Watchlist).filter_by(user_id=user.id, symbol=symbol.upper()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not in watchlist")
    db.delete(item)
    db.commit()
    _notify(
        db,
        event_type="watchlist_remove",
        title=f"Watchlist remove: {symbol.upper()}",
        body=f"{user.full_name or user.email} removed {symbol.upper()} from their watchlist.",
        actor=user,
        meta={"symbol": symbol.upper()},
    )
    return {"ok": True}


# =====================================================================
# Contact
# =====================================================================
@router.post("/contact")
def post_contact(payload: schemas.ContactCreate, db: Session = Depends(get_db)):
    msg = db_models.ContactMessage(
        name=payload.name,
        email=payload.email,
        subject=payload.subject,
        message=payload.message,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    _notify(
        db,
        event_type="contact_message",
        title=f"New contact message from {payload.name}",
        body=(payload.subject or "") + " — " + (payload.message[:200] if payload.message else ""),
        actor_email=payload.email,
        meta={"contact_id": msg.id, "subject": payload.subject},
    )
    return {"ok": True, "id": msg.id, "message": "Thanks! We'll get back to you soon."}


# =====================================================================
# Stocks / Market / Technicals
# =====================================================================
@router.get("/stocks/list")
def list_stocks():
    return {
        "count": len(stock_svc.NEPSE_STOCKS),
        "symbols": stock_svc.NEPSE_STOCKS,
        "sectors": stock_svc.SECTORS,
    }


@router.get("/stocks/{symbol}")
def stock_detail(symbol: str):
    data = stock_svc.stock_summary(symbol.upper())
    if not data.get("available"):
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return data


@router.get("/stocks/{symbol}/history")
def stock_history_route(symbol: str, days: int = 120):
    days = max(10, min(days, 800))
    data = stock_svc.stock_history(symbol.upper(), days=days)
    if not data.get("available"):
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return data


@router.get("/market/overview")
def market_overview_route():
    return stock_svc.market_overview()


# =====================================================================
# Scraper / News / Sentiment — ADMIN-ONLY write, public read
# =====================================================================
@router.post("/scrape/run")
def trigger_scrape(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: db_models.User = Depends(get_admin_user),  # 🔒 admin-only
):
    def run_pipeline():
        try:
            raw_news = scrape_all_news()
            processed_news = process_news_batch(raw_news)
            for item in processed_news:
                try:
                    exists = db.query(db_models.NewsItem).filter(db_models.NewsItem.url == item['url']).first()
                    if not exists:
                        db_item = db_models.NewsItem(
                            title=item.get('title', ''),
                            url=item.get('url', ''),
                            summary=item.get('summary', ''),
                            source=item.get('source', ''),
                            source_type=item.get('source_type'),
                            category=item.get('category'),
                            language=item.get('language', 'en'),
                            sentiment_label=item.get('sentiment_label'),
                            sentiment_score=item.get('sentiment_score'),
                        )
                        db.add(db_item)
                except Exception:
                    continue
            db.commit()
        except Exception:
            db.rollback()

    background_tasks.add_task(run_pipeline)
    return {"message": "Scraping and NLP pipeline started in background by admin."}


@router.get("/news/sources")
def list_news_sources():
    """Public: show what sources we aggregate from."""
    return {
        "rss": [{"name": s["name"], "language": s["lang"], "focus": s["focus"]} for s in RSS_SOURCES],
        "reddit": [{"name": f"r/{s['name']}", "focus": s["focus"]} for s in REDDIT_SUBREDDITS],
        "total": len(RSS_SOURCES) + len(REDDIT_SUBREDDITS),
    }


@router.get("/news")
def get_news(
    skip: int = 0,
    limit: int = 50,
    language: Optional[str] = None,
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    source_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(db_models.NewsItem)
    if language:
        q = q.filter(db_models.NewsItem.language == language)
    if sentiment:
        q = q.filter(db_models.NewsItem.sentiment_label == sentiment)
    if category:
        q = q.filter(db_models.NewsItem.category == category)
    if source_type:
        q = q.filter(db_models.NewsItem.source_type == source_type)
    news = q.order_by(db_models.NewsItem.published_at.desc()).offset(skip).limit(limit).all()
    if not news:
        raw = scrape_all_news()
        return process_news_batch(raw)
    return news


@router.get("/sentiment/live", response_model=schemas.SentimentSummary)
def get_live_sentiment(symbol: str = None, db: Session = Depends(get_db)):
    news = get_news(skip=0, limit=30, db=db)
    pos = neg = 0
    for n in news:
        label = n.get('sentiment_label', '') if isinstance(n, dict) else getattr(n, 'sentiment_label', '')
        if label == 'positive':
            pos += 1
        elif label == 'negative':
            neg += 1
    neu = len(news) - pos - neg
    return {"positive": pos, "negative": neg, "neutral": neu, "total_analyzed": len(news)}


# =====================================================================
# LSTM Forecasting — prediction is public, TRAINING is admin-only
# =====================================================================
@router.get("/predict/{symbol}")
def get_prediction(symbol: str):
    return predict_direction(symbol=symbol.upper())


@router.get("/predict/{symbol}/metrics")
def get_model_metrics(symbol: str):
    """Return the saved train/val/test metrics for a symbol's LSTM model."""
    m = get_metrics(symbol.upper())
    if not m:
        raise HTTPException(
            status_code=404,
            detail=f"No trained model or metrics found for {symbol.upper()}. Train it first."
        )
    return m


@router.get("/predict/{symbol}/history")
def get_prediction_history(
    symbol: str,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Public: recent predictions for a symbol with prediction-vs-actual comparison.

    Returns each PredictionLog entry enriched with prev_close and error_margin_pct
    computed from the live OHLCV history. error_margin_pct = 100·(actual−prev)/prev.
    """
    sym = symbol.upper()
    rows = (
        db.query(db_models.PredictionLog)
        .filter(db_models.PredictionLog.symbol == sym)
        .order_by(db_models.PredictionLog.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )

    # Fetch CSV once so we can locate prev_close at each prediction's created_at.
    df = None
    try:
        from app.services.forecasting import _fetch_history
        df = _fetch_history(sym).sort_values("date").reset_index(drop=True)
    except Exception:
        df = None

    def _prev_close(ts):
        if df is None or df.empty or ts is None:
            return None
        try:
            mask = df["date"].dt.date <= ts.date()
            if not mask.any():
                return None
            return float(df.loc[mask, "close"].iloc[-1])
        except Exception:
            return None

    out = []
    correct = incorrect = pending = 0
    for r in rows:
        prev = _prev_close(r.created_at)
        err_pct = None
        if r.actual_close is not None and prev:
            err_pct = round((r.actual_close - prev) / prev * 100.0, 3)
        status = (r.validation_status or "pending").lower()
        if status == "correct":
            correct += 1
        elif status == "incorrect":
            incorrect += 1
        else:
            pending += 1
        out.append({
            "id": r.id,
            "symbol": r.symbol,
            "predicted_date": r.predicted_date.isoformat() if r.predicted_date else None,
            "predicted_direction": r.predicted_direction,
            "confidence": round(r.confidence or 0.0, 4),
            "actual_direction": r.actual_direction,
            "actual_close": r.actual_close,
            "prev_close": prev,
            "error_margin_pct": err_pct,
            "validation_status": status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "validated_at": r.validated_at.isoformat() if r.validated_at else None,
        })

    validated = correct + incorrect
    accuracy = (correct / validated) if validated > 0 else None
    return {
        "symbol": sym,
        "items": out,
        "summary": {
            "total": len(out),
            "correct": correct,
            "incorrect": incorrect,
            "pending": pending,
            "accuracy": round(accuracy, 4) if accuracy is not None else None,
        },
    }


@router.post("/predict/train/{symbol}")
def trigger_training(
    symbol: str,
    epochs: int = 15,
    admin: db_models.User = Depends(get_admin_user),  # 🔒 admin-only
):
    try:
        return train_model(symbol=symbol.upper(), epochs=epochs)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# =====================================================================
# Admin — Management & Analytics
# =====================================================================
@router.get("/admin/stats")
def admin_stats(admin: db_models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    # Prediction metrics
    total_preds = db.query(db_models.PredictionLog).count()
    validated_preds = db.query(db_models.PredictionLog).filter(db_models.PredictionLog.validation_status != 'pending').count()
    correct_preds = db.query(db_models.PredictionLog).filter(db_models.PredictionLog.validation_status == 'correct').count()
    accuracy = (correct_preds / validated_preds) if validated_preds > 0 else 0

    return {
        "users_total": db.query(db_models.User).count(),
        "users_active": db.query(db_models.User).filter(db_models.User.is_active == True).count(),  # noqa: E712
        "admins": db.query(db_models.User).filter(db_models.User.is_admin == True).count(),  # noqa: E712
        "news_total": db.query(db_models.NewsItem).count(),
        "news_positive": db.query(db_models.NewsItem).filter(db_models.NewsItem.sentiment_label == "positive").count(),
        "news_negative": db.query(db_models.NewsItem).filter(db_models.NewsItem.sentiment_label == "negative").count(),
        "watchlist_total": db.query(db_models.Watchlist).count(),
        "contact_messages": db.query(db_models.ContactMessage).count(),
        "contact_unread": db.query(db_models.ContactMessage).filter(db_models.ContactMessage.is_read == False).count(),  # noqa: E712
        "stocks_tracked": len(stock_svc.NEPSE_STOCKS),
        "news_sources": len(RSS_SOURCES) + len(REDDIT_SUBREDDITS),
        "predictions": {
            "total": total_preds,
            "validated": validated_preds,
            "correct": correct_preds,
            "accuracy": round(accuracy, 4)
        }
    }


@router.post("/admin/predictions/validate-now")
def admin_trigger_validation(admin: db_models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    from app.services.validation import run_prediction_validation
    count = run_prediction_validation(db)
    return {"ok": True, "count": count}


@router.get("/admin/users", response_model=List[schemas.UserResponse])
def admin_list_users(admin: db_models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(db_models.User).order_by(db_models.User.created_at.desc()).all()


@router.post("/admin/users/{user_id}/toggle-active")
def admin_toggle_active(user_id: int, admin: db_models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    u = db.query(db_models.User).filter(db_models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")
    u.is_active = not u.is_active
    db.commit()
    return {"id": u.id, "is_active": u.is_active}


@router.post("/admin/users/{user_id}/toggle-admin")
def admin_toggle_admin(user_id: int, admin: db_models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    u = db.query(db_models.User).filter(db_models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_admin = not u.is_admin
    db.commit()
    return {"id": u.id, "is_admin": u.is_admin}


@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: db_models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    u = db.query(db_models.User).filter(db_models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db.delete(u)
    db.commit()
    return {"ok": True}


@router.get("/admin/contacts", response_model=List[schemas.ContactResponse])
def admin_list_contacts(admin: db_models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(db_models.ContactMessage).order_by(db_models.ContactMessage.created_at.desc()).all()


@router.post("/admin/contacts/{msg_id}/read")
def admin_mark_read(msg_id: int, admin: db_models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    m = db.query(db_models.ContactMessage).filter(db_models.ContactMessage.id == msg_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Not found")
    m.is_read = True
    db.commit()
    return {"ok": True}


@router.delete("/admin/news/{news_id}")
def admin_delete_news(news_id: int, admin: db_models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    n = db.query(db_models.NewsItem).filter(db_models.NewsItem.id == news_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(n)
    db.commit()
    return {"ok": True}


# =====================================================================
# Admin notifications — activity feed
# =====================================================================
@router.get("/admin/notifications", response_model=List[schemas.NotificationResponse])
def admin_list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    admin: db_models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(db_models.Notification)
    if unread_only:
        q = q.filter(db_models.Notification.is_read == False)  # noqa: E712
    limit = max(1, min(limit, 200))
    return q.order_by(db_models.Notification.created_at.desc()).limit(limit).all()


@router.get("/admin/notifications/unread-count")
def admin_unread_count(
    admin: db_models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    count = db.query(db_models.Notification).filter(
        db_models.Notification.is_read == False  # noqa: E712
    ).count()
    return {"unread": count}


@router.post("/admin/notifications/{notif_id}/read")
def admin_mark_notification_read(
    notif_id: int,
    admin: db_models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    n = db.query(db_models.Notification).filter(db_models.Notification.id == notif_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    n.is_read = True
    db.commit()
    return {"ok": True, "id": n.id}


@router.post("/admin/notifications/read-all")
def admin_mark_all_read(
    admin: db_models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    updated = db.query(db_models.Notification).filter(
        db_models.Notification.is_read == False  # noqa: E712
    ).update({db_models.Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"ok": True, "updated": int(updated or 0)}


@router.delete("/admin/notifications/{notif_id}")
def admin_delete_notification(
    notif_id: int,
    admin: db_models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    n = db.query(db_models.Notification).filter(db_models.Notification.id == notif_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(n)
    db.commit()
    return {"ok": True}


# =====================================================================
# Chat Sessions — persistent conversation history
# =====================================================================
@router.get("/chat/sessions", response_model=List[schemas.ChatSessionResponse])
def list_chat_sessions(
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(db_models.ChatSession)
        .filter(db_models.ChatSession.user_id == user.id)
        .order_by(db_models.ChatSession.updated_at.desc())
        .limit(50)
        .all()
    )
    return sessions


@router.post("/chat/sessions", response_model=schemas.ChatSessionResponse)
def create_chat_session(
    payload: schemas.ChatSessionCreate,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db_models.ChatSession(
        user_id=user.id,
        title=payload.title or "New Chat",
        symbol=payload.symbol,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/chat/sessions/{session_id}/messages", response_model=List[schemas.ChatMessageResponse])
def get_chat_messages(
    session_id: int,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(db_models.ChatSession).filter(
        db_models.ChatSession.id == session_id,
        db_models.ChatSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.messages


@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(db_models.ChatSession).filter(
        db_models.ChatSession.id == session_id,
        db_models.ChatSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"ok": True}


# =====================================================================
# Enhanced chatbot with session persistence
# =====================================================================
class ChatRequest(BaseModel):
    message: str
    symbol: str = "NEPSE"
    session_id: Optional[int] = None
    history: Optional[List[Dict[str, str]]] = None


@router.post("/chatbot")
def chat_with_bot(
    req: ChatRequest,
    user: Optional[db_models.User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    # 1. Gather context (same as before, but consolidated)
    sentiment_data = get_live_sentiment(symbol=req.symbol, db=db)
    label = 'neutral'
    if sentiment_data['positive'] > sentiment_data['negative']:
        label = 'positive'
    elif sentiment_data['negative'] > sentiment_data['positive']:
        label = 'negative'

    pred = predict_direction(symbol=req.symbol)

    # Market movers
    try:
        overview = stock_svc.market_overview()
        top_gainers = [g.get("symbol") for g in (overview.get("gainers") or [])[:3]]
        top_losers = [g.get("symbol") for g in (overview.get("losers") or [])[:3]]
    except Exception:
        top_gainers = top_losers = []

    # Recent news
    try:
        recent_news = db.query(db_models.NewsItem).order_by(
            db_models.NewsItem.published_at.desc()
        ).limit(6).all()
        headlines = [{"title": n.title, "source": n.source, "sentiment": n.sentiment_label} for n in recent_news]
    except Exception:
        headlines = []

    # Watchlist
    watchlist_syms = []
    if user:
        try:
            watchlist_syms = [w.symbol for w in db.query(db_models.Watchlist).filter(
                db_models.Watchlist.user_id == user.id
            ).limit(10).all()]
        except Exception:
            pass

    context = {
        'symbol': req.symbol,
        'sentiment_label': label,
        'news_count': sentiment_data['total_analyzed'],
        'predicted_direction': pred['predicted_direction'],
        'confidence': pred['confidence'],
        'top_gainers': top_gainers,
        'top_losers': top_losers,
        'recent_headlines': headlines,
        'user_watchlist': watchlist_syms,
        'user_name': user.full_name if user else None,
        'history': req.history or [],
    }

    # 2. Get AI Response
    try:
        response = generate_chatbot_response(req.message, context)
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        response = f"I'm sorry, I'm having trouble processing that right now. ({str(e)[:100]})"

    # 3. Persist to DB if session exists
    if user and req.session_id:
        try:
            session = db.query(db_models.ChatSession).filter(
                db_models.ChatSession.id == req.session_id,
                db_models.ChatSession.user_id == user.id,
            ).first()
            if session:
                user_msg = db_models.ChatMessage(session_id=session.id, role="user", content=req.message)
                bot_msg = db_models.ChatMessage(session_id=session.id, role="assistant", content=response)
                db.add_all([user_msg, bot_msg])
                
                # Update session title if it's the first message
                message_count = db.query(db_models.ChatMessage).filter(db_models.ChatMessage.session_id == session.id).count()
                if message_count < 2:
                    session.title = (req.message[:50] + "...") if len(req.message) > 50 else req.message
                
                session.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist chat message: {e}")
            db.rollback()

    return {"response": response}


# =====================================================================
# OAuth — Google and GitHub
# =====================================================================
from fastapi.responses import RedirectResponse

def _oauth_error_redirect(provider: str, message: str) -> RedirectResponse:
    """Route OAuth failures back to the frontend /login with an error banner
    instead of returning raw JSON — the user is in a browser redirect flow."""
    from app.core.config import settings
    from urllib.parse import quote
    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend}/login?oauth_error={quote(message)}&provider={provider}")


def _callback_uri(path: str) -> str:
    """Absolute callback URL. Must match exactly what's registered with the
    OAuth provider, including the /api/v1 router prefix."""
    from app.core.config import settings
    base = getattr(settings, "OAUTH_REDIRECT_BASE", "http://localhost:8000").rstrip("/")
    return f"{base}/api/v1{path}"


@router.get("/auth/google")
def oauth_google_redirect():
    """Redirect user to Google OAuth consent screen."""
    from app.core.config import settings
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
    if not client_id:
        return _oauth_error_redirect("google", "Google OAuth is not configured on the server.")
    redirect_uri = _callback_uri("/auth/google/callback")
    scope = "openid email profile"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
    )
    return RedirectResponse(url)


@router.get("/auth/google/callback")
async def oauth_google_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Exchange Google auth code for tokens, create/login user."""
    from app.core.config import settings
    import httpx

    if error or not code:
        return _oauth_error_redirect("google", error or "Authorization was cancelled.")

    redirect_uri = _callback_uri("/auth/google/callback")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
            if token_resp.status_code != 200:
                return _oauth_error_redirect("google", "Token exchange failed.")
            tokens = token_resp.json()
            user_resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={
                "Authorization": f"Bearer {tokens['access_token']}"
            })
        if user_resp.status_code != 200:
            return _oauth_error_redirect("google", "Could not fetch profile.")
    except Exception as e:
        logger.warning(f"Google OAuth exception: {e}")
        return _oauth_error_redirect("google", "Network error during sign-in.")

    google_user = user_resp.json()
    return _oauth_create_or_login(db, "google", google_user.get("id"), google_user.get("email"), google_user.get("name"))


@router.get("/auth/github")
def oauth_github_redirect():
    """Redirect user to GitHub OAuth."""
    from app.core.config import settings
    client_id = getattr(settings, "GITHUB_CLIENT_ID", None)
    if not client_id:
        return _oauth_error_redirect("github", "GitHub OAuth is not configured on the server.")
    redirect_uri = _callback_uri("/auth/github/callback")
    url = f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=user:email"
    return RedirectResponse(url)


@router.get("/auth/github/callback")
async def oauth_github_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Exchange GitHub auth code for tokens, create/login user."""
    from app.core.config import settings
    import httpx

    if error or not code:
        return _oauth_error_redirect("github", error or "Authorization was cancelled.")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post("https://github.com/login/oauth/access_token", data={
                "code": code,
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
            }, headers={"Accept": "application/json"})
            if token_resp.status_code != 200:
                return _oauth_error_redirect("github", "Token exchange failed.")
            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                return _oauth_error_redirect("github", "Token missing from response.")

            user_resp = await client.get("https://api.github.com/user", headers={
                "Authorization": f"token {access_token}"
            })
            email_resp = await client.get("https://api.github.com/user/emails", headers={
                "Authorization": f"token {access_token}"
            })
    except Exception as e:
        logger.warning(f"GitHub OAuth exception: {e}")
        return _oauth_error_redirect("github", "Network error during sign-in.")

    gh_user = user_resp.json()
    gh_emails = email_resp.json() if email_resp.status_code == 200 else []
    primary_email = gh_user.get("email")
    if not primary_email and isinstance(gh_emails, list):
        for e in gh_emails:
            if e.get("primary") and e.get("verified"):
                primary_email = e["email"]
                break
        if not primary_email and gh_emails:
            primary_email = gh_emails[0].get("email")

    if not primary_email:
        return _oauth_error_redirect("github", "Could not retrieve email from GitHub — make sure it's public or verified.")

    return _oauth_create_or_login(
        db, "github", str(gh_user.get("id")),
        primary_email, gh_user.get("name") or gh_user.get("login")
    )


def _oauth_create_or_login(
    db: Session, provider: str, oauth_id: str,
    email: Optional[str], full_name: Optional[str],
):
    """Shared logic: find existing user by email or oauth_id, or create new."""
    from app.core.config import settings

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from OAuth provider")

    user = db.query(db_models.User).filter(db_models.User.email == email).first()
    if user:
        # Link OAuth if not already linked
        if not user.oauth_id:
            user.auth_provider = provider
            user.oauth_id = oauth_id
            db.commit()
    else:
        user = db_models.User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(f"oauth_{provider}_{oauth_id}"),  # placeholder
            auth_provider=provider,
            oauth_id=oauth_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        _notify(db, "signup", f"New user: {email}", f"Signed up via {provider}", actor=user)

    token = create_access_token(subject=user.id, extra={"email": user.email, "admin": user.is_admin})
    frontend_base = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_base}/auth/callback?token={token}&provider={provider}")


# =====================================================================
# Admin Predictions — view and manage prediction validation
# =====================================================================
@router.get("/admin/predictions", response_model=List[schemas.PredictionResponse])
def admin_list_predictions(
    admin: db_models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(db_models.PredictionLog)
        .order_by(db_models.PredictionLog.created_at.desc())
        .limit(200)
        .all()
    )
