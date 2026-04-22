from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.database import engine, Base, SessionLocal
import app.models.entities  # noqa: F401  — MUST import before create_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Create tables (In a real app, use Alembic)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error(f"Database not ready at startup: {e}")


def _migrate_columns():
    """Lightweight ALTER TABLE migrations for newly added columns.
    Postgres-flavored; no-op if the column already exists."""
    from sqlalchemy import text
    alters = [
        # users profile fields
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS location VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()",
        # OAuth fields
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR DEFAULT 'local'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_id VARCHAR",
        # news metadata
        "ALTER TABLE news_items ADD COLUMN IF NOT EXISTS source_type VARCHAR",
        "ALTER TABLE news_items ADD COLUMN IF NOT EXISTS category VARCHAR",
        # prediction validation fields
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS actual_direction VARCHAR",
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS actual_close FLOAT",
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS validation_status VARCHAR DEFAULT 'pending'",
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS validated_at TIMESTAMP WITH TIME ZONE",
        # notifications table
        """CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR NOT NULL,
            title VARCHAR NOT NULL,
            body TEXT,
            actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            actor_email VARCHAR,
            meta TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_notifications_event_type ON notifications(event_type)",
        "CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read)",
        "CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at)",
        # chat sessions table
        """CREATE TABLE IF NOT EXISTS chat_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR DEFAULT 'New Chat',
            symbol VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions(user_id)",
        # chat messages table
        """CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role VARCHAR NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages(session_id)",
    ]
    try:
        with engine.begin() as conn:
            for sql in alters:
                try:
                    conn.execute(text(sql))
                except Exception as e:
                    logger.warning(f"Migration skipped ({sql[:60]}...): {e}")
    except Exception as e:
        logger.error(f"Migration pass failed: {e}")


try:
    _migrate_columns()
except Exception as e:
    logger.error(f"_migrate_columns error: {e}")


def _bootstrap_admin():
    """Create the default admin account if no users exist yet."""
    try:
        from app.models.entities import User
        from app.core.security import hash_password
        db = SessionLocal()
        try:
            if db.query(User).count() == 0:
                admin = User(
                    email=settings.ADMIN_EMAIL,
                    full_name="BhaavShare Admin",
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    is_admin=True,
                )
                db.add(admin)
                db.commit()
                logger.info(f"Bootstrapped admin: {settings.ADMIN_EMAIL}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Admin bootstrap failed: {e}")


def _start_scheduler():
    """Start background tasks for validation and scraping."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.services.validation import run_prediction_validation
    from app.services.scraper import scrape_all_news
    from app.services.nlp import process_news_batch
    from app.models.entities import NewsItem

    scheduler = BackgroundScheduler()

    def _validate_job():
        db = SessionLocal()
        try:
            run_prediction_validation(db)
        except Exception as e:
            logger.error(f"validate_predictions job failed: {e}")
        finally:
            db.close()

    def _scrape_job():
        db = SessionLocal()
        try:
            raw = scrape_all_news()
            processed = process_news_batch(raw)
            added = 0
            for item in processed:
                try:
                    if not db.query(NewsItem).filter(NewsItem.url == item.get("url")).first():
                        db.add(NewsItem(
                            title=item.get('title', ''),
                            url=item.get('url', ''),
                            summary=item.get('summary', ''),
                            source=item.get('source', ''),
                            source_type=item.get('source_type'),
                            category=item.get('category'),
                            language=item.get('language', 'en'),
                            sentiment_label=item.get('sentiment_label'),
                            sentiment_score=item.get('sentiment_score'),
                        ))
                        added += 1
                except Exception:
                    continue
            db.commit()
            logger.info(f"Scheduled news scrape: {added} new items.")
        except Exception as e:
            logger.error(f"scrape_news job failed: {e}")
            db.rollback()
        finally:
            db.close()

    from datetime import datetime, timedelta
    scheduler.add_job(_validate_job, 'cron', hour=0, minute=10, id='validate_predictions')
    scheduler.add_job(_scrape_job, 'interval', hours=4, id='scrape_news',
                      next_run_time=datetime.now() + timedelta(seconds=10))
    scheduler.start()
    logger.info("Background scheduler started: prediction validation @00:10, news scraping every 4h (first run in 10s).")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: bootstrap + background tasks")
    _bootstrap_admin()
    _start_scheduler()
    yield
    logger.info("Application shutdown")


from app.api.routes import router as api_router  # noqa: E402

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"message": "Welcome to BhaavShare API", "docs": "/docs"}


@app.get("/health")
def health():
    from sqlalchemy import text
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unavailable",
        "service": settings.PROJECT_NAME,
    }
