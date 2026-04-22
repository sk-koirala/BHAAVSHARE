# BhaavShare

**AI-powered NEPSE stock analysis platform** — combines LSTM price forecasting, multilingual (English/Nepali) news sentiment analysis, and a Gemini-powered conversational chatbot for the Nepal Stock Exchange.

> Final Year Project — submitted April 2026.

---

## Features

- **LSTM Price Forecasting** — PyTorch sequential model (64 → 32 → Dense) trained per ticker; predicts next-day direction and close price.
- **Multilingual News Sentiment** — mBERT (`bert-base-multilingual-cased`) for English and Nepali financial news, with VADER fallback.
- **Automated News Pipeline** — APScheduler harvests NEPSE-related news every 4 hours and processes sentiment in the background.
- **AI Chatbot** — Google Gemini-powered assistant with chat history, context-aware responses about NEPSE tickers.
- **Authentication** — bcrypt-hashed passwords, JWT-issued tokens, OAuth scaffolding, admin role.
- **Prediction Validation** — daily cron compares yesterday's predictions against actual close to track model accuracy.
- **Admin Dashboard** — user management, news moderation, model metrics, notification feed.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy 2, Pydantic v2, APScheduler |
| ML / NLP | PyTorch (CPU), HuggingFace Transformers (mBERT), VADER, scikit-learn |
| Database | PostgreSQL 15 |
| AI | Google Gemini API (`google-genai`) |
| Frontend | React 19, Vite, Tailwind CSS, Recharts, React Router 7 |
| Auth | JWT (`python-jose`), bcrypt (`passlib`) |
| Deployment | Docker, Docker Compose |

---

## Quick Start (Docker)

The fastest way to run the full stack:

```bash
# 1. Clone
git clone https://github.com/sk-koirala/BHAAVSHARE.git
cd BHAAVSHARE

# 2. Create your .env (root)
cp .env.example .env
# Edit .env and set GEMINI_API_KEY

# 3. Launch
docker-compose up --build
```

Services:
- **Backend API** — http://localhost:8000 (Swagger docs at `/docs`)
- **Frontend** — http://localhost:5173
- **PostgreSQL** — localhost:5432 (user/password/bhaavshare)

---

## Manual Setup (no Docker)

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 15+ running locally
- A Google Gemini API key

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp ../.env.example ../.env
# Edit ../.env and set GEMINI_API_KEY

# Make sure DATABASE_URL points to your local Postgres
export DATABASE_URL="postgresql://user:password@localhost/bhaavshare"

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on http://localhost:3000 (vite default port; check `vite.config.js`).

---

## Default Admin Account

On first startup, an admin user is auto-created:

| Field | Value |
|---|---|
| Email | `admin@bhaavshare.com` (overridable via `ADMIN_EMAIL`) |
| Password | `admin123` (overridable via `ADMIN_PASSWORD`) |

**Change the password immediately in any non-local environment.**

---

## Environment Variables

Create `.env` at the project root:

```env
GEMINI_API_KEY=your-google-gemini-api-key
DATABASE_URL=postgresql://user:password@localhost/bhaavshare
SECRET_KEY=change-me-in-production
ADMIN_EMAIL=admin@bhaavshare.com
ADMIN_PASSWORD=admin123
```

---

## Project Structure

```
BhaavShare/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   ├── core/          # Config, security (JWT, hashing)
│   │   ├── db/            # SQLAlchemy engine, session
│   │   ├── models/        # ORM entities
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # Business logic (forecasting, NLP, scraper, validation)
│   │   └── main.py        # App entrypoint, lifespan, scheduler
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/               # React components, pages, hooks
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── data/
│   └── models/            # Trained .pth files + per-ticker metrics
├── docker-compose.yml
└── README.md
```

---

## Trained Models

Pre-trained LSTM models ship in `data/models/` for the following NEPSE tickers:

- **EBL** — Everest Bank
- **NABBC** — Nabil Balanced Capital
- **NABIL** — Nabil Bank
- **NICA** — NIC Asia Bank
- **UPPER** — Upper Tamakoshi Hydropower

Each ticker has three files: `<TICKER>.pth` (weights), `<TICKER>_metrics.json` (RMSE/accuracy), `<TICKER>_norm.json` (input normalisation parameters).

---

## API Highlights

Full interactive docs: **http://localhost:8000/docs**

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/auth/signup` | POST | Register a new user |
| `/api/v1/auth/login` | POST | Obtain JWT token |
| `/api/v1/predict/{symbol}` | GET | LSTM next-day forecast |
| `/api/v1/news` | GET | Latest news with sentiment scores |
| `/api/v1/scrape/run` | POST | Trigger news pipeline (admin) |
| `/api/v1/chat/sessions` | GET/POST | Chatbot conversation history |
| `/api/v1/chat/{session_id}/message` | POST | Send a chatbot message |
| `/api/v1/admin/*` | various | User & content management |
| `/health` | GET | Service + DB health check |

---

## Background Jobs

Two scheduled jobs run on the backend:

| Job | Schedule | Action |
|---|---|---|
| `scrape_news` | Every 4 hours (first run +10s after startup) | Harvest news, score sentiment, persist |
| `validate_predictions` | Daily at 00:10 | Compare yesterday's predictions to actuals |

---

## License

Academic project — provided as-is for educational and reference purposes.

## Author

**Suyash Koirala** — Final Year Project, 2026
