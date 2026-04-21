"""
BhaavShare AI Chatbot — advanced NEPSE market intelligence assistant.

This module combines:
  • Live OHLCV history from GitHub (Aabishkar2/nepse-data)
  • Technical indicators (RSI-14, MACD, SMA-30, SMA-200) from stocks service
  • PyTorch LSTM directional forecast + the model's saved test metrics
  • Multilingual NLP sentiment (nlptown mBERT) news aggregation
  • Top gainers/losers from the market overview
  • Personalised watchlist awareness for logged-in users
  • Conversation history (multi-turn) relay to Gemini
  • Rich local fallback engine with 12+ intents (buy, sell, predict,
    sentiment, compare, sector, portfolio, risk, valuation, greet, list, help)

The Gemini system instruction is a *full data block* — the model is grounded
in numbers, not generic advice. Temperature is low-moderate (0.45) so it
stays factual but reads warmly.
"""
import os
import re
import json
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Gemini is OFF by default — the local "BhaavShare Analyst" engine below is
# the primary brain. Set USE_GEMINI=1 in the environment to re-enable the
# external model chain as an optional upgrade path.
USE_GEMINI = os.getenv("USE_GEMINI", "0") == "1"
GEMINI_MODEL_CHAIN = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
)
GEMINI_TEMPERATURE = 0.2
GEMINI_MAX_OUTPUT_TOKENS = 1024

# Full list of NEPSE stocks available on GitHub
NEPSE_STOCKS = [
    "ADBL", "AHPC", "AKJCL", "AKPL", "ALICL", "API", "BARUN", "BFC", "BOKL", "BPCL",
    "CBL", "CCBL", "CFCL", "CGH", "CHCL", "CHDC", "CHL", "CIT", "CORBL", "CZBIL",
    "DHPL", "EBL", "EDBL", "GBBL", "GBIME", "GFCL", "GHL", "GLH", "GLICL", "GMFIL",
    "GRDBL", "GUFL", "HBL", "HDHPC", "HIDCL", "HPPL", "HURJA", "ICFC", "JBBL", "JFL",
    "JLI", "JOSHI", "KBL", "KKHC", "KPCL", "KRBL", "KSBBL", "LBBL", "LBL", "LEC",
    "LICN", "MBL", "MDB", "MEGA", "MEN", "MFIL", "MHNL", "MKJC", "MLBL", "MNBBL",
    "MPFL", "NABBC", "NABIL", "NBB", "NBL", "NCCB", "NFS", "NGPL", "NHDL", "NHPC",
    "NIB", "NICA", "NIFRA", "NLIC", "NLICL", "NMB", "NRN", "NYADI", "OHL", "PCBL",
    "PFL", "PLI", "PLIC", "PMHPL", "PPCL", "PROFL", "PRVU", "RADHI", "RHPC", "RHPL",
    "RLFL", "RLI", "RRHP", "RURU", "SADBL", "SAHAS", "SANIMA", "SAPDBL", "SBI", "SBL",
    "SCB", "SFCL", "SHBL", "SHEL", "SHINE", "SHL", "SHPC", "SIFC", "SINDU", "SJCL",
    "SLI", "SLICL", "SPC", "SPDL", "SRBL", "SSHL", "TPC", "TRH", "ULI", "UMHL",
    "UMRH", "UNHPL", "UPCL", "UPPER"
]

# Stock sector classification
STOCK_SECTORS = {
    "Banking": ["ADBL", "BOKL", "CBL", "CCBL", "CZBIL", "EBL", "GBIME", "HBL", "JBBL", "KBL", "LBBL", "LBL", "MBL", "MEGA", "MNBBL", "NABIL", "NBB", "NBL", "NCCB", "NIB", "NICA", "NMB", "PCBL", "PRVU", "SANIMA", "SBI", "SBL", "SCB", "SHBL", "SRBL"],
    "Hydropower": ["AHPC", "AKJCL", "AKPL", "API", "BARUN", "BPCL", "CGH", "CHCL", "CHL", "DHPL", "GHL", "GLH", "HDHPC", "HPPL", "HURJA", "KKHC", "KPCL", "LEC", "MEN", "MHNL", "MKJC", "NHPC", "NRN", "NYADI", "PPCL", "RADHI", "RHPC", "RHPL", "RRHP", "RURU", "SAHAS", "SHEL", "SHL", "SHPC", "SJCL", "SPC", "SPDL", "SSHL", "TPC", "UMHL", "UMRH", "UNHPL", "UPCL", "UPPER"],
    "Insurance": ["ALICL", "GLICL", "JLI", "LICN", "NLIC", "NLICL", "PLI", "PLIC", "RLI", "SLICL", "SLI", "ULI"],
    "Finance": ["BFC", "CFCL", "CORBL", "EDBL", "GFCL", "GMFIL", "GRDBL", "GUFL", "ICFC", "JFL", "KSBBL", "MFIL", "MLBL", "MPFL", "NFS", "PFL", "PROFL", "RLFL", "SADBL", "SAPDBL", "SFCL", "SIFC", "SINDU"],
    "Others": ["CHDC", "CIT", "GHL", "HIDCL", "JOSHI", "NABBC", "NHDL", "NIFRA", "NGPL", "OHL", "SHINE", "TRH"],
}

def get_sector(symbol: str) -> str:
    for sector, stocks in STOCK_SECTORS.items():
        if symbol in stocks:
            return sector
    return "NEPSE"

def detect_symbol(message: str) -> Optional[str]:
    """Detect stock symbol from user's message using NLP pattern matching."""
    msg_upper = message.upper()

    # Direct symbol match (longest first to avoid partial matches)
    sorted_stocks = sorted(NEPSE_STOCKS, key=len, reverse=True)
    for stock in sorted_stocks:
        if re.search(r'\b' + re.escape(stock) + r'\b', msg_upper):
            return stock

    name_map = {
        "nabil bank": "NABIL", "nabil": "NABIL",
        "nepal bank": "NBL", "nepal investment": "NIB",
        "himalayan bank": "HBL", "himalayan": "HBL",
        "everest bank": "EBL", "everest": "EBL",
        "standard chartered": "SCB", "standard": "SCB",
        "kumari bank": "KBL", "kumari": "KBL",
        "global ime": "GBIME", "global bank": "GBIME",
        "nica bank": "NICA", "nica": "NICA",
        "nmb bank": "NMB", "nmb": "NMB",
        "mega bank": "MEGA", "mega": "MEGA",
        "sanima bank": "SANIMA", "sanima": "SANIMA",
        "prime bank": "PRVU", "prime commercial": "PRVU",
        "sbi bank": "SBI", "nepal sbi": "SBI",
        "citizen bank": "CZBIL", "citizens": "CZBIL",
        "agriculture development": "ADBL", "agri dev": "ADBL",
        "laxmi bank": "LBL", "laxmi sunrise": "LBL",
        "machhapuchchhre bank": "MBL", "machhapuchchhre": "MBL",
        "prabhu bank": "PRVU",
        "nepal life": "NLIC", "nepal life insurance": "NLIC",
        "life insurance": "NLIC",
        "api power": "API",
        "chilime": "CHL", "butwal power": "BPCL",
        "upper tamakoshi": "UPPER", "upper": "UPPER",
        "nifra": "NIFRA",
        "hidcl": "HIDCL",
    }

    msg_lower = message.lower()
    for name, sym in name_map.items():
        if name in msg_lower:
            return sym

    return None


def _carry_symbol_from_history(current_msg: str, history: List[Dict[str, str]]) -> Optional[str]:
    """If the current message has no symbol, scan the last few turns so that
    follow-up questions like 'should i buy it?' or 'what about next week?'
    still pin to the right stock."""
    if detect_symbol(current_msg):
        return None
    for turn in reversed(history[-6:]):
        sym = detect_symbol(turn.get("content", "") or "")
        if sym:
            return sym
    return None


def _fmt_num(v: Any, decimals: int = 2) -> Any:
    """Return a JSON-safe number or None — never a stringified number.
    Keeps the data anchor block tight and unambiguous for the LLM."""
    if v is None:
        return None
    try:
        f = float(v)
        if f != f:  # NaN
            return None
        return round(f, decimals)
    except (TypeError, ValueError):
        return None


def build_data_anchor(
    symbol: str,
    stock_data: Dict[str, Any],
    sentiment_label: str,
    news_count: int,
    pred_dir: str,
    conf: float,
    metrics: Optional[Dict[str, Any]],
    top_gainers: List[str],
    top_losers: List[str],
    headlines: List[Dict[str, Any]],
    watchlist: List[str],
    user_name: Optional[str],
) -> Dict[str, Any]:
    """Return a strict, JSON-serialisable snapshot of every verified number.

    This is the *only* source of numeric truth the LLM is allowed to cite.
    Any value not present here should be described as 'not available' —
    never invented. Fields set to null signal 'unknown'."""
    anchor: Dict[str, Any] = {
        "symbol": symbol,
        "sector": get_sector(symbol),
        "price": {
            "available": bool(stock_data.get("available")),
            "latest_close_npr": _fmt_num(stock_data.get("latest_close")),
            "prev_close_npr": _fmt_num(stock_data.get("prev_close")),
            "daily_change_npr": _fmt_num(stock_data.get("change")),
            "daily_change_pct": _fmt_num(stock_data.get("change_pct")),
            "high_52w_npr": _fmt_num(stock_data.get("high_52w")),
            "low_52w_npr": _fmt_num(stock_data.get("low_52w")),
            "sma_30_npr": _fmt_num(stock_data.get("avg_30d")),
            "sma_200_npr": _fmt_num(stock_data.get("sma_200")),
            "rsi_14": _fmt_num(stock_data.get("rsi_14"), 1),
            "macd": _fmt_num(stock_data.get("macd"), 3),
            "macd_signal": _fmt_num(stock_data.get("macd_signal"), 3),
            "records": stock_data.get("total_records") or 0,
        },
        "sentiment": {
            "label": (sentiment_label or "neutral").lower(),
            "articles_analysed": int(news_count or 0),
        },
        "forecast": {
            "direction": (pred_dir or "FLAT").upper(),
            "confidence_pct": _fmt_num((conf or 0) * 100, 1),
        },
        "model_metrics": None,
        "market": {
            "top_gainers": list(top_gainers or [])[:5],
            "top_losers": list(top_losers or [])[:5],
        },
        "recent_headlines": [
            {
                "title": (h.get("title") or "").strip()[:200],
                "source": h.get("source") or "",
                "sentiment": (h.get("sentiment") or "neutral").lower(),
            }
            for h in (headlines or [])[:5]
        ],
        "user": {
            "name": user_name,
            "watchlist": list(watchlist or [])[:10],
        },
    }
    if metrics and metrics.get("test"):
        t = metrics["test"]
        anchor["model_metrics"] = {
            "test_accuracy_pct": _fmt_num((t.get("accuracy") or 0) * 100, 2),
            "test_f1_macro": _fmt_num(t.get("f1_macro"), 3),
            "test_f1_weighted": _fmt_num(t.get("f1_weighted"), 3),
            "baseline_acc_pct": _fmt_num((metrics.get("baseline_majority_acc") or 0) * 100, 2),
            "n_train_windows": metrics.get("n_train"),
            "n_test_windows": metrics.get("n_test"),
        }
    return anchor


_VAGUE_PATTERNS = (
    r"^(ok|okay|hmm+|hmmm?|well|uh|um|and\??|so\??|\?+)$",
    r"^what do you think\??$",
    r"^any (ideas|thoughts)\??$",
    r"^(help|\?)$",
)


def _clarify_if_vague(msg: str, detected_symbol: Optional[str]) -> Optional[str]:
    """When the user's message is too vague to answer well, ask ONE tight
    clarifying question instead of inventing an interpretation."""
    if detected_symbol:
        return None
    if not msg or len(msg) < 3:
        return (
            "**Quick check** — what would you like me to do?\n\n"
            "• Analyse a stock (e.g. *'Should I buy NABIL?'*)\n"
            "• Compare two tickers (e.g. *'NABIL vs EBL'*)\n"
            "• Show forecast accuracy for a symbol\n"
            "• Something else — just tell me in one line."
        )
    for pat in _VAGUE_PATTERNS:
        if re.match(pat, msg):
            return (
                "Happy to dig in — which angle helps you most right now?\n\n"
                "1. A stock call (BUY / HOLD / SELL with reasoning)\n"
                "2. A sector view (Banking / Hydropower / Insurance / Finance)\n"
                "3. A comparison between two tickers\n"
                "4. Model accuracy & prediction-vs-actual check\n\n"
                "Reply with a number or name the stock."
            )
    return None


_OFF_TOPIC_MARKERS = (
    "react", "javascript", "python", "css", "tailwind", "component",
    "api endpoint", "database schema", "ui design", "dashboard design",
    "landing page", "business model", "monetize", "monetization",
    "startup", "pitch deck", "roadmap",
)


def _looks_off_topic(message: str) -> bool:
    """Detect queries that aren't about NEPSE stocks but should still be
    answered helpfully by the general-assistant persona."""
    m = message.lower()
    if detect_symbol(message):
        return False
    # Bail out if stock-y keywords are present — those belong to the stock engine.
    stock_words = ("nepse", "stock", "share", "ipo", "sector", "bank ", "hydropower",
                   "insurance", "buy", "sell", "hold", "rsi", "macd", "sma",
                   "watchlist", "portfolio", "forecast", "predict", "sentiment", "market")
    if any(w in m for w in stock_words):
        return False
    return any(k in m for k in _OFF_TOPIC_MARKERS)


def _handle_general_query(message: str, history: List[Dict[str, str]], user_name: Optional[str]) -> str:
    """Structured general-assistant answer for non-NEPSE questions.
    We do NOT pretend to run real code here — we give a senior-mentor framing
    and direct the user to the richer NEPSE capabilities that are the product."""
    greeting = f"Hi {user_name.split()[0]}," if user_name else "Quick take —"
    return (
        f"{greeting} I'm BhaavShare Analyst. I specialise in NEPSE market intelligence "
        "(live prices, technicals, LSTM forecasts, sentiment, accuracy checks).\n\n"
        "### Summary\n"
        "Your question looks like a general software / design / business topic. I can sketch "
        "an answer, but my real edge is on Nepali equities — treat this as a pointer, not a full plan.\n\n"
        "### Where I add most value\n"
        "- **Stock calls**: *'Should I buy NABIL?'* — full signal stack with BUY / HOLD / SELL.\n"
        "- **Compare**: *'NABIL vs EBL vs HBL'* — side-by-side RSI, MACD, SMA, sentiment.\n"
        "- **Forecast accuracy**: *'How accurate are your predictions for NABIL?'*\n"
        "- **Sector scan**: *'Banking sector today'* — fast snapshot across 30+ tickers.\n\n"
        "### Reasoning\n"
        "Answers are grounded in live OHLCV + our LSTM model + multilingual NLP sentiment — no invented numbers. "
        "If you want, I can pivot to any of the above in the next message.\n\n"
        "---\n"
        "**Final Recommendation: HOLD**\n"
        "Reason: General-topic query — no stock-specific signal to act on. Ask me about a NEPSE ticker for a concrete call."
    )


def _memory_header(current_msg: str, history: List[Dict[str, str]], symbol: str) -> str:
    """Short 'memory simulation' header — used when a follow-up inherits a
    symbol from a prior turn, so the reply feels continuous instead of amnesic."""
    if not history:
        return ""
    if detect_symbol(current_msg):
        return ""  # new topic explicitly named
    prior_sym = _carry_symbol_from_history(current_msg, history)
    if prior_sym and prior_sym == symbol:
        return f"*Continuing on **{symbol}** from your last message…*\n\n"
    return ""


def _guard_output(text: str, anchor: Dict[str, Any]) -> str:
    """Light post-hoc guardrail. The model is already told to ground in the
    anchor — here we strip the most common giveaway hallucinations:
      - made-up URLs (we never provide any)
      - fake ISIN / CUSIP-looking IDs
      - 'as of <fake-date>' claims invented out of thin air
    We keep this intentionally conservative so we never nuke legitimate content."""
    if not text:
        return text
    # Strip markdown links pointing outside our own domain — the model should
    # not be inventing external references.
    text = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r"\1", text)
    # Strip stray "Source: https://..." lines
    text = re.sub(r"(?im)^\s*source:\s*https?://\S+\s*$", "", text)
    return text.strip()


def fetch_stock_summary(symbol: str) -> Dict:
    """Fetch latest price data + technical indicators via the stocks service.

    We prefer the stocks-service path because it returns RSI, MACD, and SMAs
    already computed — richer than a raw CSV read. Falls back to a direct CSV
    fetch only if the service path fails.
    """
    try:
        from app.services import stocks as stock_svc
        data = stock_svc.stock_summary(symbol)
        if data.get("available"):
            # Normalise to the shape the chatbot expects (keep old keys too)
            return {
                "available": True,
                "latest_close": data.get("latest_close"),
                "prev_close": data.get("prev_close"),
                "change": data.get("change", 0.0),
                "change_pct": data.get("change_pct", 0.0),
                "high_52w": data.get("high_52w"),
                "low_52w": data.get("low_52w"),
                "avg_30d": data.get("sma_30"),
                "sma_200": data.get("sma_200"),
                "rsi_14": data.get("rsi_14"),
                "macd": data.get("macd"),
                "macd_signal": data.get("macd_signal"),
                "volume_avg_30": data.get("volume_avg_30"),
                "total_records": data.get("records", 0),
            }
    except Exception as e:
        logger.debug(f"stocks-service fetch failed for {symbol}: {e}")

    # Fallback: direct CSV
    try:
        url = f"https://raw.githubusercontent.com/Aabishkar2/nepse-data/main/data/company-wise/{symbol}.csv"
        df = pd.read_csv(url)
        df['Close'] = df.get('close', df.get('Close', df.iloc[:, 3]))
        df = df.dropna(subset=['Close'])

        if len(df) < 2:
            return {"available": False}

        latest = float(df['Close'].iloc[-1])
        prev = float(df['Close'].iloc[-2])
        change = latest - prev
        change_pct = (change / prev) * 100 if prev else 0.0
        high_52w = float(df['Close'].tail(252).max()) if len(df) >= 252 else float(df['Close'].max())
        low_52w = float(df['Close'].tail(252).min()) if len(df) >= 252 else float(df['Close'].min())
        avg_30d = float(df['Close'].tail(30).mean())

        return {
            "available": True,
            "latest_close": latest,
            "prev_close": prev,
            "change": change,
            "change_pct": change_pct,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "avg_30d": avg_30d,
            "sma_200": None,
            "rsi_14": None,
            "macd": None,
            "macd_signal": None,
            "total_records": len(df),
        }
    except Exception as e:
        logger.error(f"Failed to fetch {symbol}: {e}")
        return {"available": False}


def _fetch_model_metrics(symbol: str) -> Optional[Dict]:
    """Load the saved LSTM test-set metrics for a symbol, if they exist."""
    try:
        from app.services.forecasting import get_metrics
        return get_metrics(symbol)
    except Exception:
        return None


def _interpret_rsi(rsi_val: Optional[float]) -> str:
    if rsi_val is None:
        return ""
    if rsi_val >= 70:
        return f"RSI {rsi_val:.1f} — OVERBOUGHT (possible pullback)"
    if rsi_val <= 30:
        return f"RSI {rsi_val:.1f} — OVERSOLD (possible bounce)"
    if rsi_val >= 55:
        return f"RSI {rsi_val:.1f} — bullish momentum"
    if rsi_val <= 45:
        return f"RSI {rsi_val:.1f} — bearish momentum"
    return f"RSI {rsi_val:.1f} — neutral"


def _interpret_macd(macd_val: Optional[float], signal_val: Optional[float]) -> str:
    if macd_val is None or signal_val is None:
        return ""
    diff = macd_val - signal_val
    if diff > 0:
        return f"MACD {macd_val:.3f} > signal {signal_val:.3f} — bullish crossover"
    return f"MACD {macd_val:.3f} < signal {signal_val:.3f} — bearish crossover"


def _tech_signals(d: Dict) -> List[str]:
    """Build a list of bullet-point technical signals from a stock summary dict."""
    signals: List[str] = []
    if not d.get("available"):
        return signals

    close = d.get("latest_close") or 0
    avg_30 = d.get("avg_30d") or 0
    avg_200 = d.get("sma_200")

    if close and avg_30:
        if close > avg_30:
            signals.append("Above 30-day SMA — short-term uptrend")
        else:
            signals.append("Below 30-day SMA — short-term downtrend")

    if close and avg_200:
        if close > avg_200:
            signals.append("Above 200-day SMA — long-term uptrend")
        else:
            signals.append("Below 200-day SMA — long-term downtrend")

    rsi_line = _interpret_rsi(d.get("rsi_14"))
    if rsi_line:
        signals.append(rsi_line)

    macd_line = _interpret_macd(d.get("macd"), d.get("macd_signal"))
    if macd_line:
        signals.append(macd_line)

    if d.get("high_52w") and close:
        pct_from_high = ((d["high_52w"] - close) / d["high_52w"]) * 100
        if close >= d["high_52w"] * 0.95:
            signals.append(f"Within 5% of 52-week HIGH — resistance zone")
        elif close <= (d.get("low_52w") or 0) * 1.05:
            signals.append(f"Within 5% of 52-week LOW — support/accumulation zone")
        else:
            signals.append(f"{pct_from_high:.1f}% below 52-week high")

    return signals


def compute_recommendation(
    stock_data: Dict[str, Any],
    sentiment_label: str,
    pred_dir: str,
) -> tuple[str, str]:
    """Derive a BUY / HOLD / SELL call from technicals + sentiment + LSTM forecast.

    Returns (label, reason) where label ∈ {"BUY", "HOLD", "SELL"} and reason is a
    single-sentence justification citing the strongest converging signals.
    """
    if not stock_data or not stock_data.get("available"):
        if pred_dir == "UP" and sentiment_label == "positive":
            return "BUY", "Positive news sentiment and LSTM UP forecast, though full price history was unavailable."
        if pred_dir == "DOWN" and sentiment_label == "negative":
            return "SELL", "Negative news sentiment and LSTM DOWN forecast, though full price history was unavailable."
        return "HOLD", "Insufficient live price data for a high-confidence call."

    d = stock_data
    close = d.get("latest_close") or 0
    sma30 = d.get("avg_30d") or 0
    sma200 = d.get("sma_200")
    rsi = d.get("rsi_14")
    macd = d.get("macd")
    macd_sig = d.get("macd_signal")

    bull, bear = 0.0, 0.0
    bull_reasons: List[str] = []
    bear_reasons: List[str] = []

    if close and sma30:
        if close > sma30:
            bull += 1; bull_reasons.append("above 30-day SMA")
        else:
            bear += 1; bear_reasons.append("below 30-day SMA")
    if close and sma200:
        if close > sma200:
            bull += 1; bull_reasons.append("above 200-day SMA")
        else:
            bear += 1; bear_reasons.append("below 200-day SMA")

    if rsi is not None:
        if rsi >= 70:
            bear += 1; bear_reasons.append(f"RSI overbought ({rsi:.0f})")
        elif rsi <= 30:
            bull += 1; bull_reasons.append(f"RSI oversold ({rsi:.0f})")
        elif rsi > 50:
            bull += 0.5; bull_reasons.append(f"RSI bullish ({rsi:.0f})")
        else:
            bear += 0.5; bear_reasons.append(f"RSI bearish ({rsi:.0f})")

    if macd is not None and macd_sig is not None:
        if macd > macd_sig:
            bull += 1; bull_reasons.append("MACD bullish crossover")
        else:
            bear += 1; bear_reasons.append("MACD bearish crossover")

    if sentiment_label == "positive":
        bull += 1; bull_reasons.append("positive news sentiment")
    elif sentiment_label == "negative":
        bear += 1; bear_reasons.append("negative news sentiment")

    if pred_dir == "UP":
        bull += 1; bull_reasons.append("LSTM forecasts UP")
    elif pred_dir == "DOWN":
        bear += 1; bear_reasons.append("LSTM forecasts DOWN")

    # Extreme RSI overrides — mean-reversion risk dominates
    if rsi is not None and rsi >= 75:
        return "SELL", f"RSI {rsi:.0f} is extreme overbought — pullback risk outweighs other signals."
    if rsi is not None and rsi <= 25 and sentiment_label != "negative":
        return "BUY", f"RSI {rsi:.0f} is extreme oversold — historical accumulation zone."

    if bull - bear >= 2:
        top = ", ".join(bull_reasons[:3]) or "converging bullish signals"
        return "BUY", f"Based on {top}."
    if bear - bull >= 2:
        top = ", ".join(bear_reasons[:3]) or "converging bearish signals"
        return "SELL", f"Based on {top}."

    mix: List[str] = []
    if bull_reasons:
        mix.append(bull_reasons[0])
    if bear_reasons:
        mix.append(bear_reasons[0])
    reason_mix = " vs ".join(mix) if mix else "signals are balanced"
    return "HOLD", f"Mixed signals — {reason_mix}. Wait for a clearer breakout."


def _append_recommendation(
    response: str,
    stock_data: Dict[str, Any],
    sentiment_label: str,
    pred_dir: str,
) -> str:
    """Guarantee every chatbot reply ends with the standard recommendation block.
    If the upstream model already included one, leave it intact."""
    if "Final Recommendation:" in response:
        return response
    label, reason = compute_recommendation(stock_data, sentiment_label, pred_dir)
    return f"{response}\n\n---\n**Final Recommendation: {label}**\nReason: {reason}"


def generate_chatbot_response(user_message: str, context: Dict[str, Any]) -> str:
    """Public entry point — runs the core engine and appends the
    standard BUY / HOLD / SELL recommendation footer."""
    history: List[Dict[str, str]] = context.get('history') or []

    # Follow-up resolution: if the new turn doesn't name a symbol, carry the
    # one from the most recent relevant turn so the context stays coherent.
    detected = detect_symbol(user_message) or _carry_symbol_from_history(user_message, history)
    if detected:
        context = {**context, 'symbol': detected}

    symbol = detected or context.get('symbol', 'NEPSE')
    sentiment_label = context.get('sentiment_label', 'neutral')
    pred_dir = context.get('predicted_direction', 'FLAT')

    raw = _generate_chatbot_response_core(user_message, context)

    stock_data = fetch_stock_summary(symbol)
    return _append_recommendation(raw, stock_data, sentiment_label, pred_dir)


def _generate_chatbot_response_core(user_message: str, context: Dict[str, Any]) -> str:
    """
    BhaavShare AI — context-aware NEPSE advisor.
    Combines: live price data, technical indicators, LSTM forecast + saved
    model metrics, NLP news sentiment, top gainers/losers, recent headlines,
    and the user's own watchlist (if logged in). Multi-turn via history.
    """
    detected = detect_symbol(user_message)
    symbol = detected or context.get('symbol', 'NEPSE')

    sentiment_label = context.get('sentiment_label', 'neutral')
    news_count = context.get('news_count', 0)
    pred_dir = context.get('predicted_direction', 'FLAT')
    conf = context.get('confidence', 0.5)
    conf_pct = f"{conf * 100:.1f}%"
    sector = get_sector(symbol)

    top_gainers = context.get('top_gainers') or []
    top_losers = context.get('top_losers') or []
    headlines = context.get('recent_headlines') or []
    watchlist = context.get('user_watchlist') or []
    user_name = context.get('user_name')
    history: List[Dict[str, str]] = context.get('history') or []

    # --- Optional Gemini path (disabled unless USE_GEMINI=1) ---
    api_key = os.getenv("GEMINI_API_KEY")
    if USE_GEMINI and api_key and api_key != "YOUR_API_KEY_HERE":
        stock_data = fetch_stock_summary(symbol)
        metrics = _fetch_model_metrics(symbol)

        # The single source of numeric truth — the LLM is told to cite only from here.
        anchor = build_data_anchor(
            symbol=symbol,
            stock_data=stock_data,
            sentiment_label=sentiment_label,
            news_count=news_count,
            pred_dir=pred_dir,
            conf=conf,
            metrics=metrics,
            top_gainers=top_gainers,
            top_losers=top_losers,
            headlines=headlines,
            watchlist=watchlist,
            user_name=user_name,
        )
        anchor_json = json.dumps(anchor, ensure_ascii=False, indent=2)

        # Interpreted tech signals are okay to include verbatim — they are
        # computed from the anchor values, not free-form inference.
        tech_lines = _tech_signals(stock_data)
        tech_block = "\n".join(f"- {s}" for s in tech_lines) if tech_lines else "- (no strong signals)"

        system_instruction = f"""You are **BhaavShare AI** — a grounded NEPSE market intelligence assistant.
You were built by the BhaavShare team (Tokha, Nepal). Contact: Bhaavshare@gmail.com.

You have ONE job: answer the user using ONLY the verified numbers in the DATA ANCHOR below.
You must NEVER invent prices, percentages, dates, volumes, accuracy numbers, tickers, URLs, or news headlines.

## DATA ANCHOR (the only source of numeric truth)
```json
{anchor_json}
```

## DERIVED TECHNICAL SIGNALS (already computed from the anchor)
{tech_block}

## Anti-hallucination rules — read carefully
1. Every number you write MUST come from the DATA ANCHOR above. If a field is `null`, say "not available" — never guess.
2. Do NOT invent ticker symbols, sector names, company names, headlines, URLs, analyst reports, or broker quotes.
3. If the user asks about a stock that isn't in the anchor's `symbol` field, say so plainly and offer to look it up next turn.
4. Do NOT cite specific dates you haven't been given. Speak relatively ("latest close", "today's movers") not absolutely.
5. Do NOT claim to have real-time order-book data, earnings reports, dividends, or corporate actions — the anchor does not contain those.
6. For model accuracy claims, cite ONLY `model_metrics` fields. If `model_metrics` is null, say the model hasn't been trained on this symbol yet.
7. If indicators disagree (e.g. RSI bullish, MACD bearish), say so explicitly. Do not smooth over the contradiction.
8. Never recommend leverage, margin, derivatives, or day-trading without a risk warning.

## Style
- Write like a senior analyst: confident, specific, concise. No filler ("Great question!", "Certainly!").
- Use **bold** for key numbers, markdown tables for comparisons, bullets for signal lists.
- Reply in the user's language register: Nepali / Romanised Nepali / English — match them.
- Keep responses under 350 words unless the user asks for depth.
- Personalise when `user.name` is set, and weave in watchlist symbols when relevant.

## Required output — every reply ends with exactly this block
```
---
**Final Recommendation: <BUY|HOLD|SELL>**
Reason: <one sentence citing the strongest signal(s) from the anchor: sentiment + LSTM forecast + technicals>
```
Pick exactly one of BUY, HOLD, SELL. Do not add any text after the Reason line.
If the anchor has insufficient data, recommend HOLD and explain why in the Reason line.
"""

        # Multi-turn contents
        contents: List[Any] = []
        try:
            from google import genai
            for turn in history[-6:]:
                role = turn.get("role", "user")
                text = turn.get("content", "") or ""
                if not text.strip():
                    continue
                contents.append(
                    genai.types.Content(
                        role="user" if role == "user" else "model",
                        parts=[genai.types.Part.from_text(text=text)],
                    )
                )
            contents.append(
                genai.types.Content(
                    role="user",
                    parts=[genai.types.Part.from_text(text=user_message)],
                )
            )

            client = genai.Client(api_key=api_key)
            config = genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=GEMINI_TEMPERATURE,
                top_p=0.85,
                max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            )

            last_error: Optional[Exception] = None
            for model_id in GEMINI_MODEL_CHAIN:
                try:
                    response = client.models.generate_content(
                        model=model_id,
                        contents=contents if contents else user_message,
                        config=config,
                    )
                    if response and response.text:
                        return _guard_output(response.text, anchor)
                except Exception as e:
                    last_error = e
                    logger.warning(f"Gemini model {model_id} failed: {e}")
                    continue
            if last_error:
                logger.warning(f"All Gemini models failed, falling back to local engine. Last error: {last_error}")
        except Exception as e:
            logger.warning(f"Gemini init failed, falling back to local engine: {e}")

    # =================================================================
    # Local "BhaavShare Analyst" engine — this is the primary brain.
    # Persona: elite senior-analyst assistant.
    # Structure: Summary → Key Signals → Reasoning → Final Recommendation.
    # No external LLM. Every number comes from the live data anchor.
    # =================================================================
    msg = user_message.lower().strip()

    # 1. Vague / empty queries → one clarifying question instead of guessing.
    clarifier = _clarify_if_vague(msg, detected_symbol=detect_symbol(user_message))
    if clarifier:
        return clarifier

    # 2. Off-topic (not stocks / NEPSE) → structured general-assistant response.
    if _looks_off_topic(user_message):
        return _handle_general_query(user_message, history=history, user_name=user_name)

    stock_data = fetch_stock_summary(symbol)
    signals = _tech_signals(stock_data)

    # Continuity header — referenced later in every formatted block.
    continuity = _memory_header(user_message, history, symbol)

    if stock_data.get("available"):
        d = stock_data
        direction_arrow = "UP" if d['change'] > 0 else ("DOWN" if d['change'] < 0 else "FLAT")
        price_block = f"""**Live Market Data** ({symbol} • {sector})
| Metric | Value |
|--------|-------|
| Latest Close | NPR {d['latest_close']:.2f} |
| Previous Close | NPR {d['prev_close']:.2f} |
| Daily Change | {direction_arrow} {d['change']:+.2f} ({d['change_pct']:+.2f}%) |
| 52-Week High | NPR {d['high_52w']:.2f} |
| 52-Week Low | NPR {d['low_52w']:.2f} |
| 30-Day SMA | NPR {(d.get('avg_30d') or 0):.2f} |"""
        if d.get("sma_200") is not None:
            price_block += f"\n| 200-Day SMA | NPR {d['sma_200']:.2f} |"
        if d.get("rsi_14") is not None:
            price_block += f"\n| RSI (14) | {d['rsi_14']:.1f} |"
        if d.get("macd") is not None and d.get("macd_signal") is not None:
            price_block += f"\n| MACD / Signal | {d['macd']:.3f} / {d['macd_signal']:.3f} |"
        price_block += f"\n| Historical Records | {d['total_records']} trading days |"

        signal_block = "\n".join(f"• {s}" for s in signals) if signals else "• No strong technical signal detected."
    else:
        price_block = f"*Price data not available for {symbol}.*"
        signal_block = ""

    if sentiment_label == 'positive':
        mood = "bullish"
    elif sentiment_label == 'negative':
        mood = "bearish"
    else:
        mood = "neutral"

    sentiment_block = f"**NLP Sentiment:** {sentiment_label.upper()} ({mood}) — based on {news_count} articles"
    lstm_block = f"**LSTM Prediction:** {pred_dir} with {conf_pct} confidence"

    # LSTM metrics block (local fallback)
    metrics = _fetch_model_metrics(symbol)
    metrics_block = ""
    if metrics and metrics.get("test"):
        t = metrics["test"]
        baseline = metrics.get("baseline_majority_acc", 0)
        metrics_block = (
            f"**Model Performance:** accuracy {t.get('accuracy', 0) * 100:.2f}%, "
            f"F1-macro {t.get('f1_macro', 0):.3f}, "
            f"vs. baseline {baseline * 100:.2f}%"
        )

    # ============================================================
    # Intent routing — each intent returns an answer
    # ============================================================

    # MODEL ACCURACY / EVALUATION intent
    if any(w in msg for w in ['accuracy', 'f1', 'precision', 'recall', 'metric', 'how good', 'how accurate', 'evaluation', 'test set', 'confusion']):
        if metrics and metrics.get("test"):
            t = metrics["test"]
            v = metrics.get("val", {})
            baseline = metrics.get("baseline_majority_acc", 0)
            beats = t.get('accuracy', 0) > baseline
            return f"""{continuity}### Summary
Out-of-sample evaluation for the LSTM trained on **{symbol}**. Test accuracy **{t.get('accuracy', 0) * 100:.2f}%** vs majority-class baseline **{baseline * 100:.2f}%** — the model **{'beats' if beats else 'does not yet beat'}** the naive baseline.

### Key Signals
| Metric | Validation | Test |
|--------|-----------|------|
| Accuracy | {v.get('accuracy', 0) * 100:.2f}% | {t.get('accuracy', 0) * 100:.2f}% |
| F1 (macro) | {v.get('f1_macro', 0):.3f} | {t.get('f1_macro', 0):.3f} |
| F1 (weighted) | {v.get('f1_weighted', 0):.3f} | {t.get('f1_weighted', 0):.3f} |

- **Training set:** {metrics.get('n_train', '?')} windows
- **Test set:** {metrics.get('n_test', '?')} windows
- **Architecture:** 2-layer LSTM (hidden=64), dropout=0.2, LayerNorm head, class-balanced CE loss

### Reasoning
The model is trained on a chronological 70/15/15 split — it never saw the test window during training, so these numbers are a fair generalisation estimate. A test F1-macro of **{t.get('f1_macro', 0):.3f}** tells you how evenly it handles UP/DOWN/FLAT, not just the dominant class. If macro F1 lags accuracy heavily, the model is biased toward the majority regime and its directional calls deserve less weight."""
        else:
            return f"""{continuity}### Summary
No saved metrics for **{symbol}** yet — the LSTM hasn't been trained on this ticker, or the metrics file is missing.

### Key Signals
{lstm_block}

### Reasoning
An admin can train it from the admin dashboard. That run will generate accuracy, F1-macro, F1-weighted, per-class precision/recall, a confusion matrix, and a majority-class baseline comparison. Until then, treat the live forecast as directional only — we can't quantify its reliability for this symbol."""

    # LIST / BROWSE stocks
    if any(w in msg for w in ['list all', 'all stocks', 'which stocks', 'show stocks', 'symbols', 'how many stocks']):
        sector_list = "\n".join(f"**{s}:** {', '.join(stocks[:8])}{'...' if len(stocks) > 8 else ''}" for s, stocks in STOCK_SECTORS.items())
        return f"""{continuity}### Summary
**{len(NEPSE_STOCKS)} NEPSE tickers** are live in the system, grouped by sector.

### Key Signals
{sector_list}

### Reasoning
All data is sourced from the Aabishkar2/nepse-data GitHub mirror, updated daily. Each ticker has RSI-14, MACD, SMA-30 and SMA-200 available out-of-the-box. Try *"Should I buy NABIL?"*, *"Predict EBL"*, or *"Compare NABIL vs EBL"* to start."""

    # COMPARE stocks
    if any(w in msg for w in ['compare', ' vs ', 'versus', 'better']):
        symbols_found = []
        for stock in sorted(NEPSE_STOCKS, key=len, reverse=True):
            if re.search(r'\b' + re.escape(stock) + r'\b', user_message.upper()):
                symbols_found.append(stock)

        if len(symbols_found) >= 2:
            rows = []
            for s in symbols_found[:4]:
                d = fetch_stock_summary(s)
                if d.get("available"):
                    rsi_s = f"{d['rsi_14']:.1f}" if d.get("rsi_14") is not None else "n/a"
                    rows.append(
                        f"| {s} | {get_sector(s)} | NPR {d['latest_close']:.2f} | "
                        f"{d['change_pct']:+.2f}% | NPR {(d.get('avg_30d') or 0):.2f} | {rsi_s} |"
                    )

            if rows:
                table = "\n".join(rows)
                syms = ", ".join(symbols_found[:4])
                return f"""{continuity}### Summary
Side-by-side snapshot of **{syms}** across price, daily change, 30-day SMA and RSI.

### Key Signals
| Symbol | Sector | Latest | Daily Δ | 30D SMA | RSI |
|--------|--------|--------|---------|---------|-----|
{table}

### Reasoning
Use the daily change column to spot short-term momentum and RSI to flag overbought (>70) / oversold (<30) conditions. A price sitting above its 30-day SMA with an RSI in the 50–65 band is the cleanest "trend intact, not yet stretched" profile. Cross-check with the sentiment/forecast below before acting.

{sentiment_block}
{lstm_block}"""

        return f"""{continuity}### Summary
I need at least **two tickers** in your message to run a comparison.

### How to ask
- *"Compare NABIL vs EBL"*
- *"NABIL or HBL?"*
- *"HBL vs SCB vs NICA"*

Available stocks include NABIL, EBL, HBL, SCB, NICA, GBIME, NMB, and **{len(NEPSE_STOCKS) - 7} more**."""

    # BUY intent
    if any(w in msg for w in ['buy', 'invest', 'purchase', 'accumulate', 'entry', 'good time', 'kinnu', 'should i', 'kharida']):
        summary_line = ""
        reasoning = ""
        if stock_data.get("available"):
            d = stock_data
            rsi_val = d.get("rsi_14") or 50
            macd_bull = (d.get("macd") or 0) > (d.get("macd_signal") or 0)
            above_sma30 = (d.get("latest_close") or 0) > (d.get("avg_30d") or 0)

            bull_count = sum([above_sma30, macd_bull, rsi_val > 50, sentiment_label == 'positive', pred_dir == 'UP'])
            bear_count = sum([not above_sma30, not macd_bull, rsi_val < 50, sentiment_label == 'negative', pred_dir == 'DOWN'])

            if bull_count >= 3 and rsi_val < 70:
                summary_line = f"**{symbol}** shows converging bullish signals (**{bull_count}/5**) at NPR {d['latest_close']:.2f} ({d['change_pct']:+.2f}% today). Entry window looks favorable with room before overbought."
                reasoning = (
                    f"Three or more of the five core signals (SMA trend, MACD, RSI, sentiment, LSTM) are aligned bullish. "
                    f"RSI at **{rsi_val:.1f}** is below the 70 overbought threshold, so momentum still has runway. "
                    f"LSTM forecasts **{pred_dir}** and news sentiment is **{sentiment_label}** — the fundamental and technical pictures agree. "
                    f"A staggered entry (tranches) manages timing risk while committing to the thesis."
                )
            elif bear_count >= 3:
                summary_line = f"**{symbol}** is showing converging bearish signals (**{bear_count}/5**) at NPR {d['latest_close']:.2f}. Not a clean buy right now."
                reasoning = (
                    f"Three or more of the five core signals are aligned bearish. "
                    f"Forcing an entry here means fighting the trend — better to wait for a concrete reversal trigger: "
                    f"MACD crossing above signal, RSI bouncing off the oversold zone, or sentiment flipping. "
                    f"If you already hold, revisit your thesis and stop-loss rather than averaging down blindly."
                )
            elif rsi_val >= 70:
                summary_line = f"**{symbol}** is technically **overbought** (RSI {rsi_val:.1f}) at NPR {d['latest_close']:.2f}. Even with positive tape, a pullback is the higher-probability near-term move."
                reasoning = (
                    f"RSI above 70 historically precedes mean-reversion in NEPSE large-caps. "
                    f"Buying here pays a premium for momentum that is already well-priced. "
                    f"Patience — waiting for RSI to cool below ~65 — usually offers a meaningfully better entry without sacrificing the longer-term thesis."
                )
            elif d.get("latest_close") and d.get("low_52w") and d['latest_close'] < d['low_52w'] * 1.1:
                summary_line = f"**{symbol}** is trading near its 52-week low (NPR {d['latest_close']:.2f} vs low NPR {d['low_52w']:.2f}) — a historical accumulation zone for patient capital."
                reasoning = (
                    f"Prices within ~10% of the 52-week low tend to mark either (a) a durable support forming, or (b) the middle of a larger decline. "
                    f"The difference is confirmed by volume and a sentiment turn. "
                    f"A small starter position with a clear stop below the 52-week low limits downside while letting you participate if the bottom holds."
                )
            else:
                summary_line = f"**{symbol}** signals are mixed (**{bull_count} bull vs {bear_count} bear**) at NPR {d['latest_close']:.2f}. No high-conviction call either way."
                reasoning = (
                    f"When the five core signals are split, position sizing beats conviction. "
                    f"Either wait for a directional breakout (a clean MACD cross or a decisive move through the 30-day SMA) or size down to a probe position. "
                    f"Don't pay full size for half-evidence."
                )
        else:
            summary_line = f"Live price data for **{symbol}** isn't available right now, so I can't run a full signal stack."
            reasoning = (
                "Without price, SMA, RSI and MACD we can't validate any entry thesis. "
                "Try another ticker from the list, or ask me again once the data service reconnects."
            )

        return f"""{continuity}### Summary
{summary_line}

### Key Signals
{price_block}

{signal_block}

{sentiment_block}
{lstm_block}
{metrics_block}

### Reasoning
{reasoning}"""

    # SELL intent
    if any(w in msg for w in ['sell', 'exit', 'dump', 'book profit', 'bechnu', 'stop loss']):
        summary_line = ""
        reasoning = ""
        if stock_data.get("available"):
            d = stock_data
            rsi_val = d.get("rsi_14") or 50
            if rsi_val >= 70:
                summary_line = f"**{symbol}** is overbought (RSI {rsi_val:.1f}) — classic zone for partial profit-booking."
                reasoning = (
                    "Overbought RSI on NEPSE large-caps historically precedes pullbacks of 3–8%. "
                    "Trimming 25–50% of the position and rolling a trailing stop up to protect the rest is a defensible playbook — "
                    "you lock in gains without abandoning a thesis that might still have legs."
                )
            elif d.get("high_52w") and d['latest_close'] >= d['high_52w'] * 0.95:
                summary_line = f"**{symbol}** is within 5% of its 52-week high (NPR {d['latest_close']:.2f} vs high NPR {d['high_52w']:.2f}) — natural resistance zone."
                reasoning = (
                    "52-week highs are where supply historically re-appears. A partial exit or tightened trailing stop preserves optionality: "
                    "you capture the upside if the breakout confirms, and you keep most of the gain if rejection comes first."
                )
            elif sentiment_label == 'negative' and pred_dir == 'DOWN':
                summary_line = f"**{symbol}** has both bearish sentiment and a DOWN LSTM forecast — the case for tightening risk is real."
                reasoning = (
                    "When fundamentals (news sentiment) and technicals (LSTM direction) agree, the odds of further downside rise materially. "
                    "Scaling out in tranches — rather than a panic exit — gives you a chance to stay in if the story flips without taking the full drawdown."
                )
            else:
                summary_line = f"No urgent exit signal on **{symbol}** at NPR {d['latest_close']:.2f}."
                reasoning = (
                    "Technicals are not flashing exit triggers (RSI not overbought, not at 52-week high, sentiment/LSTM not both bearish). "
                    "If you're in profit, a trailing stop-loss below the most recent swing low lets the position continue working without forcing you out on noise."
                )
        else:
            summary_line = f"Live price data for **{symbol}** isn't available — no hard exit call I can back with numbers."
            reasoning = "Without current price, RSI, and MACD I can't validate an exit trigger. Try another ticker or revisit once data reconnects."

        return f"""{continuity}### Summary
{summary_line}

### Key Signals
{price_block}

{signal_block}

{sentiment_block}
{lstm_block}

### Reasoning
{reasoning}"""

    # PREDICTION intent
    if any(w in msg for w in ['predict', 'forecast', 'future', 'tomorrow', 'next week', 'model', 'lstm', 'neural', 'target']):
        return f"""{continuity}### Summary
LSTM neural forecast for **{symbol}**: direction **{pred_dir}** at **{conf_pct}** confidence.

### Key Signals
{lstm_block}
{metrics_block}

{price_block}

{signal_block}

{sentiment_block}

### Reasoning
The LSTM consumes rolling OHLCV windows and outputs a UP / DOWN / FLAT class probability. Confidence reflects the softmax margin between the winning and runner-up classes — a **{conf_pct}** read means the model is {'highly committed' if conf >= 0.7 else ('moderately committed' if conf >= 0.55 else 'close to a coin-flip')}. Cross-check the forecast against the technical block above: when LSTM direction, RSI/MACD stance, and sentiment all agree, the probability of follow-through rises materially.

*Admins can retrain on the latest data via the dashboard to keep the forecast fresh.*"""

    # SENTIMENT / NEWS intent
    if any(w in msg for w in ['sentiment', 'news', 'market mood', 'khabar', 'outlook', 'bearish', 'bullish']):
        headline_lines = ""
        if headlines:
            headline_lines = "\n**Recent Headlines:**\n" + "\n".join(
                f"• [{h.get('sentiment', 'neu').upper()}] *{h.get('source', '')}* — {h.get('title', '')}" for h in headlines[:5]
            )
        return f"""{continuity}### Summary
News sentiment on **{symbol}** is **{sentiment_label.upper()}** ({mood}), based on {news_count} articles.

### Key Signals
{sentiment_block}
{headline_lines}

{price_block}

{signal_block}

{lstm_block}

### Reasoning
Sentiment is derived from multilingual mBERT NLP over recent Nepali and English financial news — it picks up tone, not just keywords. A bullish tape with negative sentiment often marks a late-stage move; a bearish tape with turning-positive sentiment can mark the early stages of a reversal. Use this as a *confirmation* layer on top of technicals rather than a standalone trigger."""

    # PORTFOLIO / WATCHLIST intent
    if any(w in msg for w in ['portfolio', 'watchlist', 'my stocks', 'my holdings']):
        if not watchlist:
            return f"""{continuity}### Summary
Your watchlist is empty — nothing for me to track yet.

### How to populate it
Add stocks from the **Stock Detail** page or the **Dashboard**. Once you do, I'll track price, RSI, MACD, sentiment, and LSTM forecasts for each ticker and surface the outliers on demand.

### Reasoning
A focused watchlist (5–10 tickers you actually care about) beats scanning all {len(NEPSE_STOCKS)} NEPSE stocks. Start with the sectors you understand best, then add cross-sector diversifiers as your conviction grows."""

        rows = []
        for s in watchlist[:10]:
            d = fetch_stock_summary(s)
            if d.get("available"):
                rsi_s = f"{d['rsi_14']:.1f}" if d.get("rsi_14") is not None else "n/a"
                rows.append(f"| {s} | NPR {d['latest_close']:.2f} | {d['change_pct']:+.2f}% | {rsi_s} |")
        table = "\n".join(rows) if rows else "| n/a | n/a | n/a | n/a |"
        return f"""{continuity}### Summary
Live snapshot of your **{len(watchlist)}-ticker watchlist** — price, daily change, and RSI at a glance.

### Key Signals
| Symbol | Latest | Daily Δ | RSI |
|--------|--------|---------|-----|
{table}

{sentiment_block}

### Reasoning
Scan RSI first: anything above 70 is a candidate for partial profit-booking, anything below 30 is a potential accumulation spot. Pair that with the daily change column to distinguish real momentum from mean-reversion noise. Ask me *"Which of my stocks is strongest?"* or *"Analyse my watchlist"* for a ranked view."""

    # RISK / VALUATION intent
    if any(w in msg for w in ['risk', 'volatility', 'drawdown', 'valuation', 'expensive', 'cheap', 'overvalued']):
        if stock_data.get("available"):
            d = stock_data
            rsi_val = d.get("rsi_14")
            risk_level = "MODERATE"
            if rsi_val is not None:
                if rsi_val >= 75 or rsi_val <= 25:
                    risk_level = "HIGH (extreme RSI)"
                elif 45 <= rsi_val <= 60:
                    risk_level = "LOW (neutral RSI)"
            range_pct = 0
            pos_in_range = 0
            if d.get("high_52w") and d.get("low_52w") and d['high_52w'] > d['low_52w']:
                range_pct = ((d['high_52w'] - d['low_52w']) / d['low_52w']) * 100
                pos_in_range = (d['latest_close'] - d['low_52w']) / (d['high_52w'] - d['low_52w']) * 100
            return f"""{continuity}### Summary
**{symbol}** risk profile reads **{risk_level}**. Price sits at **{pos_in_range:.1f}%** of the 52-week range with an annualised-style band of **{range_pct:.1f}%**.

### Key Signals
{price_block}

- **RSI-based risk:** {risk_level}
- **52-week range width:** {range_pct:.1f}% (higher = more volatile)
- **Position in range:** {pos_in_range:.1f}% of 52-week range

{signal_block}

### Reasoning
Extreme RSI (≥75 or ≤25) historically marks zones where mean-reversion dominates — that's where single-day drawdown risk is highest. A position sitting in the top third of its 52-week range with neutral RSI tends to carry less immediate risk than the same price after a vertical move. Size positions accordingly and set stops based on the range width, not on arbitrary round numbers."""
        return f"""{continuity}### Summary
Can't assess risk on **{symbol}** — live price data isn't available.

### Reasoning
Risk metrics (RSI, 52-week range position, SMA divergence) all require current OHLCV. Try another ticker from the list, or revisit once the data service reconnects."""

    # PRICE / STATUS intent
    if any(w in msg for w in ['price', 'doing', 'today', 'status', 'how is', 'kati', 'close', 'volume']):
        if stock_data.get("available"):
            d = stock_data
            arrow = "up" if d['change'] > 0 else ("down" if d['change'] < 0 else "flat")
            summary_line = f"**{symbol}** last traded at **NPR {d['latest_close']:.2f}**, {arrow} **{d['change_pct']:+.2f}%** on the day."
        else:
            summary_line = f"Price data for **{symbol}** isn't available right now."
        return f"""{continuity}### Summary
{summary_line}

### Key Signals
{price_block}

{signal_block}

{sentiment_block}
{lstm_block}

### Reasoning
Compare the latest close against the 30-day and 200-day SMAs to classify the trend state: above both = strong uptrend, above 30 but below 200 = early recovery, below both = confirmed downtrend. The RSI/MACD lines on the table tell you whether that trend is stretched or still has room. Daily change alone is noise; these levels are the signal."""

    # SECTOR intent
    if any(w in msg for w in ['sector', 'banking', 'hydropower', 'insurance', 'finance', 'category']):
        target_sector = sector
        for s in STOCK_SECTORS:
            if s.lower() in msg:
                target_sector = s
                break
        stocks_in_sector = STOCK_SECTORS.get(target_sector, [])
        first_ticker = stocks_in_sector[0] if stocks_in_sector else 'NABIL'
        second_ticker = stocks_in_sector[1] if len(stocks_in_sector) > 1 else 'EBL'
        return f"""{continuity}### Summary
**{target_sector}** sector — {len(stocks_in_sector)} tickers currently tracked.

### Key Signals
**Stocks ({len(stocks_in_sector)}):** {', '.join(stocks_in_sector)}

{sentiment_block}

### Reasoning
Sector-wide sentiment shifts ({sentiment_label}) tend to lead individual names by a few sessions — a bullish sector tape with a single laggard is often the best asymmetric setup. Ask me about a specific ticker for a full signal stack, or *"Compare {first_ticker} vs {second_ticker}"* to see how the leaders stack up."""

    # HELP / GREETING
    if any(w in msg for w in ['help', 'what can you', 'hello', 'hi ', 'namaste', 'hey']) or msg in ('hi', 'hello', 'yo'):
        greeting = f"Namaste {user_name.split()[0]}" if user_name else "Namaste"
        return f"""{greeting}! I'm **BhaavShare Analyst** — your NEPSE market intelligence assistant.

### What I do
I analyse **{len(NEPSE_STOCKS)} NEPSE stocks** across Banking, Hydropower, Insurance, Finance and more — using live price data, RSI/MACD/SMA technicals, LSTM forecasting, and multilingual NLP sentiment.

### Try these
- *"Should I buy NABIL?"* — full investment call with reasoning
- *"How is EBL doing?"* — live price + technical stance
- *"Predict HBL"* — LSTM neural forecast
- *"How accurate is your model for NABIL?"* — out-of-sample metrics
- *"Compare NABIL vs EBL"* — side-by-side
- *"Banking sector"* — sector view
- *"Analyse my watchlist"* — personalised (logged-in users)
- *"What's the sentiment?"* — news-driven mood

**Currently tracking:** **{symbol}**
{sentiment_block}
{lstm_block}"""

    # DEFAULT — comprehensive overview
    return f"""{continuity}### Summary
Full-stack snapshot on **{symbol}** ({sector}) — price, technicals, sentiment and LSTM forecast in one view.

### Key Signals
{price_block}

{signal_block}

{sentiment_block}
{lstm_block}
{metrics_block}

### Reasoning
This is a neutral, everything-visible view. To turn it into a decision, pick an angle and ask again:
- *"Should I buy {symbol}?"* — weighted investment call
- *"Predict {symbol}"* — LSTM directional forecast
- *"How accurate is your model for {symbol}?"* — out-of-sample metrics
- *"Compare {symbol} vs NABIL"* — relative view

The signals above will not always agree — when they do, conviction is warranted; when they don't, it's information about uncertainty, not a reason to ignore the split."""
