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
from typing import Dict, Any, Optional, List
import pandas as pd
import logging

logger = logging.getLogger(__name__)

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
    detected = detect_symbol(user_message)
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

    # --- Try Gemini first with RICH context ---
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "YOUR_API_KEY_HERE":
        try:
            from google import genai
            stock_data = fetch_stock_summary(symbol)

            # Build each context block
            price_context = ""
            tech_context = ""
            if stock_data.get("available"):
                price_context = (
                    f"\n[Live Price — {symbol}]\n"
                    f"- Latest Close: NPR {stock_data['latest_close']:.2f}\n"
                    f"- Previous Close: NPR {stock_data['prev_close']:.2f}\n"
                    f"- Daily Change: {stock_data['change']:+.2f} ({stock_data['change_pct']:+.2f}%)\n"
                    f"- 52-Week High/Low: NPR {stock_data['high_52w']:.2f} / {stock_data['low_52w']:.2f}\n"
                    f"- 30-Day SMA: NPR {(stock_data.get('avg_30d') or 0):.2f}\n"
                )
                if stock_data.get("sma_200") is not None:
                    price_context += f"- 200-Day SMA: NPR {stock_data['sma_200']:.2f}\n"

                tech_lines = _tech_signals(stock_data)
                if tech_lines:
                    tech_context = "\n[Technical Indicators]\n" + "\n".join(f"- {s}" for s in tech_lines) + "\n"

            # LSTM metrics block — so the bot can honestly cite model accuracy
            metrics = _fetch_model_metrics(symbol)
            lstm_metrics_block = ""
            if metrics and metrics.get("test"):
                t = metrics["test"]
                baseline = metrics.get("baseline_majority_acc", 0)
                lstm_metrics_block = (
                    f"\n[LSTM Model Performance for {symbol}]\n"
                    f"- Test accuracy: {t.get('accuracy', 0) * 100:.2f}%\n"
                    f"- Test F1 (macro): {t.get('f1_macro', 0):.3f}\n"
                    f"- Test F1 (weighted): {t.get('f1_weighted', 0):.3f}\n"
                    f"- Majority-class baseline: {baseline * 100:.2f}%\n"
                    f"- Trained on {metrics.get('n_train', '?')} windows, "
                    f"tested on {metrics.get('n_test', '?')}\n"
                )

            market_block = ""
            if top_gainers or top_losers:
                market_block = (
                    f"\n[Today's Market Movers]\n"
                    f"- Top Gainers: {', '.join(top_gainers) or 'n/a'}\n"
                    f"- Top Losers: {', '.join(top_losers) or 'n/a'}\n"
                )

            news_block = ""
            if headlines:
                lines = [f"  · [{h.get('sentiment', 'neutral')}] {h.get('source', '')}: {h.get('title', '')}" for h in headlines[:6]]
                news_block = "\n[Recent Headlines (NLP-scored)]\n" + "\n".join(lines) + "\n"

            user_block = ""
            if user_name:
                user_block = f"\n[User]\n- Name: {user_name}"
                if watchlist:
                    user_block += f"\n- Watchlist: {', '.join(watchlist)}"
                user_block += "\n"

            system_instruction = f"""You are **BhaavShare AI**, Nepal's most advanced NEPSE market intelligence assistant. You are built on:
- PyTorch LSTM directional forecasting (2-layer, class-balanced training, chronological split)
- Multilingual mBERT sentiment analysis on Nepali + English financial news
- Live OHLCV data from the Aabishkar2/nepse-data GitHub mirror
- Classical technicals: RSI-14, MACD, SMA-30, SMA-200, Bollinger Bands

## Your personality
- Confident, warm, professional — speak like a senior buy-side analyst, not a generic AI.
- Format with markdown: **bold**, tables, bullets, clear headers.
- Switch languages naturally: if the user writes in Nepali / Romanised Nepali, reply in the same register.
- Be specific: cite actual numbers from the data block below. Never hand-wave.
- Explain the *reasoning*, not just the conclusion. Mention what indicators agree or disagree.
- Always end investment-advice answers with: "⚠️ Not financial advice — do your own research."

## Current focus
Symbol: **{symbol}** ({sector})
NLP news sentiment: **{sentiment_label.upper()}** ({news_count} articles analysed)
LSTM forecast: **{pred_dir}** at {conf_pct} confidence
{price_context}{tech_context}{lstm_metrics_block}{market_block}{news_block}{user_block}

## Rules
- If the user asks "how accurate is your model", cite the LSTM metrics block verbatim — never invent numbers.
- If metrics are missing, say so honestly and suggest retraining.
- If technical indicators disagree (e.g. RSI overbought but MACD bullish), call it out explicitly as a mixed signal.
- If the user is logged in and has a watchlist, weave in personalised insight ("NABIL on your watchlist is …").
- Keep responses under 400 words unless the user explicitly asks for depth.
- Never recommend leverage, margin, or derivatives without a risk warning.

## Required output format — every answer MUST end with this exact block
End every response with a horizontal rule followed by two lines, using this literal markdown:

---
**Final Recommendation: <BUY|HOLD|SELL>**
Reason: <one crisp sentence citing the strongest signal(s) from sentiment + LSTM forecast + technicals>

Pick exactly one of BUY, HOLD, or SELL. Do not add any text after the Reason line.
"""

            client = genai.Client(api_key=api_key)

            # Multi-turn: build a contents list with history + current message
            contents: List[Any] = []
            for turn in history[-6:]:  # last 3 exchanges
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

            response = client.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=contents if contents else user_message,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.45,
                ),
            )
            if response and response.text:
                return response.text
        except Exception as e:
            logger.warning(f"Gemini call failed, falling back to local engine: {e}")

    # --- Local Intelligence Engine (fallback when Gemini is unavailable) ---
    msg = user_message.lower().strip()

    stock_data = fetch_stock_summary(symbol)
    signals = _tech_signals(stock_data)

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
            return f"""**LSTM Model Evaluation — {symbol}**

| Metric | Validation | Test |
|--------|-----------|------|
| Accuracy | {v.get('accuracy', 0) * 100:.2f}% | {t.get('accuracy', 0) * 100:.2f}% |
| F1 (macro) | {v.get('f1_macro', 0):.3f} | {t.get('f1_macro', 0):.3f} |
| F1 (weighted) | {v.get('f1_weighted', 0):.3f} | {t.get('f1_weighted', 0):.3f} |

**Majority-class baseline:** {baseline * 100:.2f}% — the LSTM {'beats' if t.get('accuracy', 0) > baseline else 'does not yet beat'} this.
**Training set:** {metrics.get('n_train', '?')} windows · **Test set:** {metrics.get('n_test', '?')} windows.

Architecture: 2-layer LSTM (hidden=64), dropout=0.2, LayerNorm head, class-balanced CE loss, chronological 70/15/15 split.

⚠️ *These are out-of-sample metrics — the model never saw the test window during training.*"""
        else:
            return f"""**No saved metrics for {symbol} yet.**

The LSTM model has not been trained on this symbol, or the metrics file is missing. An admin can train it from the admin dashboard, which will generate:
- Accuracy, F1-macro, F1-weighted
- Per-class precision/recall
- Confusion matrix
- Baseline comparison

{lstm_block}"""

    # LIST / BROWSE stocks
    if any(w in msg for w in ['list all', 'all stocks', 'which stocks', 'show stocks', 'symbols', 'how many stocks']):
        sector_list = "\n".join(f"**{s}:** {', '.join(stocks[:8])}{'...' if len(stocks) > 8 else ''}" for s, stocks in STOCK_SECTORS.items())
        return f"""**Available NEPSE Stocks ({len(NEPSE_STOCKS)} total)**

{sector_list}

**Try asking:** "Should I buy NABIL?", "Predict EBL", "How is HBL doing?"

All data is sourced from live GitHub historical records updated daily."""

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
                return f"""**Stock Comparison**

| Symbol | Sector | Latest | Daily Δ | 30D SMA | RSI |
|--------|--------|--------|---------|---------|-----|
{table}

{sentiment_block}
{lstm_block}

⚠️ *AI-generated analysis. Not financial advice.*"""

        return f"""Please mention two or more stock symbols to compare.
**Example:** "Compare NABIL vs EBL" or "NABIL or HBL?"

Available stocks include: NABIL, EBL, HBL, SCB, NICA, GBIME, NMB, and {len(NEPSE_STOCKS) - 7} more."""

    # BUY intent
    if any(w in msg for w in ['buy', 'invest', 'purchase', 'accumulate', 'entry', 'good time', 'kinnu', 'should i', 'kharida']):
        recommendation = ""
        if stock_data.get("available"):
            d = stock_data
            rsi_val = d.get("rsi_14") or 50
            macd_bull = (d.get("macd") or 0) > (d.get("macd_signal") or 0)
            above_sma30 = (d.get("latest_close") or 0) > (d.get("avg_30d") or 0)

            bull_count = sum([above_sma30, macd_bull, rsi_val > 50, sentiment_label == 'positive', pred_dir == 'UP'])
            bear_count = sum([not above_sma30, not macd_bull, rsi_val < 50, sentiment_label == 'negative', pred_dir == 'DOWN'])

            if bull_count >= 3 and rsi_val < 70:
                recommendation = f"""**Outlook: FAVORABLE** ({bull_count}/5 bullish signals)
{symbol} shows converging positive signals. LSTM predicts {pred_dir}, sentiment is {sentiment_label}, and technicals confirm uptrend. RSI at {rsi_val:.1f} still has room before overbought."""
            elif bear_count >= 3:
                recommendation = f"""**Outlook: CAUTION** ({bear_count}/5 bearish signals)
{symbol} shows converging negative signals. Waiting for a clear reversal (MACD crossover, RSI oversold bounce, sentiment flip) is prudent."""
            elif rsi_val >= 70:
                recommendation = f"""**Outlook: OVERBOUGHT**
RSI at {rsi_val:.1f} — {symbol} is overbought. Even if other signals are positive, a short-term pullback is likely. Better to wait for RSI to cool below 65."""
            elif d.get("latest_close") and d.get("low_52w") and d['latest_close'] < d['low_52w'] * 1.1:
                recommendation = f"""**Outlook: VALUE ZONE**
{symbol} is near its 52-week low — historically an accumulation zone for long-term investors. Confirm with volume and a sentiment turn before committing."""
            else:
                recommendation = f"""**Outlook: MIXED** ({bull_count} bull vs {bear_count} bear signals)
Signals are not aligned. Consider a smaller position size or wait for a clearer directional breakout."""
        else:
            recommendation = f"Insufficient data for detailed analysis of {symbol}."

        return f"""**Investment Analysis: {symbol}** ({sector})

{price_block}

**Technical Signals:**
{signal_block}

{sentiment_block}
{lstm_block}
{metrics_block}

---
{recommendation}

⚠️ *AI-generated analysis based on historical data. Not financial advice. Always DYOR.*"""

    # SELL intent
    if any(w in msg for w in ['sell', 'exit', 'dump', 'book profit', 'bechnu', 'stop loss']):
        exit_advice = ""
        if stock_data.get("available"):
            d = stock_data
            rsi_val = d.get("rsi_14") or 50
            if rsi_val >= 70:
                exit_advice = f"RSI at {rsi_val:.1f} is in overbought territory — historically a good zone for partial profit-booking."
            elif d.get("high_52w") and d['latest_close'] >= d['high_52w'] * 0.95:
                exit_advice = "Near 52-week high — natural resistance zone. Consider partial exits or tightening a trailing stop-loss."
            elif sentiment_label == 'negative' and pred_dir == 'DOWN':
                exit_advice = "Both sentiment and LSTM are bearish. Tightening stop-losses or scaling out is defensible."
            else:
                exit_advice = "No urgent sell signal. If you're in profit, a trailing stop-loss preserves gains without forcing a full exit."

        return f"""**Exit Strategy Analysis: {symbol}** ({sector})

{price_block}

**Technical Signals:**
{signal_block}

{sentiment_block}
{lstm_block}

**Recommendation:** {exit_advice}

⚠️ *AI-generated analysis. Not financial advice.*"""

    # PREDICTION intent
    if any(w in msg for w in ['predict', 'forecast', 'future', 'tomorrow', 'next week', 'model', 'lstm', 'neural', 'target']):
        return f"""**LSTM Neural Network Forecast: {symbol}** ({sector})

{lstm_block}
{metrics_block}

{price_block}

**Technical Signals:**
{signal_block}

{sentiment_block}

*Click "Retrain Real-Time AI" (admin only) to update the LSTM on {symbol}'s latest data.*

⚠️ *Neural predictions are probabilistic estimates, not guarantees.*"""

    # SENTIMENT / NEWS intent
    if any(w in msg for w in ['sentiment', 'news', 'market mood', 'khabar', 'outlook', 'bearish', 'bullish']):
        headline_lines = ""
        if headlines:
            headline_lines = "\n**Recent Headlines:**\n" + "\n".join(
                f"• [{h.get('sentiment', 'neu').upper()}] *{h.get('source', '')}* — {h.get('title', '')}" for h in headlines[:5]
            )
        return f"""**Market Sentiment Report: {symbol}** ({sector})

{sentiment_block}
{headline_lines}

{price_block}

**Technical Signals:**
{signal_block}

{lstm_block}

*Sentiment is derived from {news_count} articles via multilingual mBERT NLP analysis.*"""

    # PORTFOLIO / WATCHLIST intent
    if any(w in msg for w in ['portfolio', 'watchlist', 'my stocks', 'my holdings']):
        if not watchlist:
            return """**Your watchlist is empty.**

Add stocks from the Stock Detail page or the Dashboard, and I'll track sentiment, technicals, and LSTM forecasts for each of them.

Try: "Add NABIL to watchlist" (use the UI button)."""

        rows = []
        for s in watchlist[:10]:
            d = fetch_stock_summary(s)
            if d.get("available"):
                rsi_s = f"{d['rsi_14']:.1f}" if d.get("rsi_14") is not None else "n/a"
                rows.append(f"| {s} | NPR {d['latest_close']:.2f} | {d['change_pct']:+.2f}% | {rsi_s} |")
        table = "\n".join(rows) if rows else "| n/a | n/a | n/a | n/a |"
        return f"""**Your Watchlist — Live Snapshot**

| Symbol | Latest | Daily Δ | RSI |
|--------|--------|---------|-----|
{table}

{sentiment_block}

Ask me "Analyse my watchlist" or "Which of my stocks is strongest?" for deeper insight."""

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
            if d.get("high_52w") and d.get("low_52w"):
                range_pct = ((d['high_52w'] - d['low_52w']) / d['low_52w']) * 100
            return f"""**Risk Assessment: {symbol}** ({sector})

{price_block}

**Risk Indicators:**
• RSI-based risk: **{risk_level}**
• 52-week range: {range_pct:.1f}% (higher = more volatile)
• Position in range: {((d['latest_close'] - d['low_52w']) / (d['high_52w'] - d['low_52w']) * 100):.1f}% of 52W range

**Technical Signals:**
{signal_block}

⚠️ *Historical volatility is not a guarantee of future risk.*"""
        return f"Unable to assess risk for {symbol} without price data."

    # PRICE / STATUS intent
    if any(w in msg for w in ['price', 'doing', 'today', 'status', 'how is', 'kati', 'close', 'volume']):
        return f"""**Market Status: {symbol}** ({sector})

{price_block}

**Technical Signals:**
{signal_block}

{sentiment_block}
{lstm_block}

⚠️ *Data sourced from GitHub historical records.*"""

    # SECTOR intent
    if any(w in msg for w in ['sector', 'banking', 'hydropower', 'insurance', 'finance', 'category']):
        target_sector = sector
        for s in STOCK_SECTORS:
            if s.lower() in msg:
                target_sector = s
                break
        stocks_in_sector = STOCK_SECTORS.get(target_sector, [])
        return f"""**{target_sector} Sector Overview**

**Stocks ({len(stocks_in_sector)}):** {', '.join(stocks_in_sector)}

{sentiment_block}

**Try:** "Should I buy {stocks_in_sector[0] if stocks_in_sector else 'NABIL'}?" or "Compare {stocks_in_sector[0] if stocks_in_sector else 'NABIL'} vs {stocks_in_sector[1] if len(stocks_in_sector) > 1 else 'EBL'}" """

    # HELP / GREETING
    if any(w in msg for w in ['help', 'what can you', 'hello', 'hi ', 'namaste', 'hey']) or msg in ('hi', 'hello', 'yo'):
        return f"""**Namaste! I'm BhaavShare AI** — your NEPSE market intelligence assistant.

I analyze **{len(NEPSE_STOCKS)} stocks** across Banking, Hydropower, Insurance, Finance & more — using live price data, RSI/MACD/SMA technicals, LSTM forecasting, and multilingual NLP sentiment.

**Try these:**
• "Should I buy NABIL?" — full investment analysis
• "How is EBL doing?" — live price + technicals
• "Predict HBL" — LSTM forecast
• "How accurate is your model for NABIL?" — training metrics
• "Compare NABIL vs EBL" — side-by-side
• "Banking sector" — sector view
• "Analyse my watchlist" — personalised (logged-in users)
• "What's the sentiment?" — news sentiment

**Currently tracking:** {symbol}
{sentiment_block}
{lstm_block}"""

    # DEFAULT — comprehensive overview
    return f"""**BhaavShare AI — {symbol} Analysis** ({sector})

{price_block}

**Technical Signals:**
{signal_block}

{sentiment_block}
{lstm_block}
{metrics_block}

---
**Quick actions:**
• "Should I buy {symbol}?" — investment guidance
• "Predict {symbol}" — LSTM forecast
• "How accurate is your model for {symbol}?" — model metrics
• "Compare {symbol} vs NABIL" — comparison
• "List all stocks" — browse {len(NEPSE_STOCKS)} NEPSE stocks

⚠️ *AI-generated analysis. Not financial advice.*"""
