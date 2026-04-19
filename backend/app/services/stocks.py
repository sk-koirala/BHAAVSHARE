"""
Stock data + technical indicators service.

Sources live OHLCV from the Aabishkar2/nepse-data GitHub dataset and computes
classical technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands.

All heavy results are cached in-memory with a short TTL to avoid hammering
GitHub on every request.
"""
from __future__ import annotations

import time
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---- Stock universe (mirrors chatbot.NEPSE_STOCKS) ----
NEPSE_STOCKS: List[str] = [
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
    "UMRH", "UNHPL", "UPCL", "UPPER",
]

SECTORS: Dict[str, List[str]] = {
    "Banking": ["ADBL", "BOKL", "CBL", "CCBL", "CZBIL", "EBL", "GBIME", "HBL", "JBBL",
                "KBL", "LBBL", "LBL", "MBL", "MEGA", "MNBBL", "NABIL", "NBB", "NBL",
                "NCCB", "NIB", "NICA", "NMB", "PCBL", "PRVU", "SANIMA", "SBI", "SBL",
                "SCB", "SHBL", "SRBL"],
    "Hydropower": ["AHPC", "AKJCL", "AKPL", "API", "BARUN", "BPCL", "CGH", "CHCL", "CHL",
                   "DHPL", "GHL", "GLH", "HDHPC", "HPPL", "HURJA", "KKHC", "KPCL", "LEC",
                   "MEN", "MHNL", "MKJC", "NHPC", "NRN", "NYADI", "PPCL", "RADHI", "RHPC",
                   "RHPL", "RRHP", "RURU", "SAHAS", "SHEL", "SHL", "SHPC", "SJCL", "SPC",
                   "SPDL", "SSHL", "TPC", "UMHL", "UMRH", "UNHPL", "UPCL", "UPPER"],
    "Insurance": ["ALICL", "GLICL", "JLI", "LICN", "NLIC", "NLICL", "PLI", "PLIC", "RLI",
                  "SLICL", "SLI", "ULI"],
    "Finance": ["BFC", "CFCL", "CORBL", "EDBL", "GFCL", "GMFIL", "GRDBL", "GUFL", "ICFC",
                "JFL", "KSBBL", "MFIL", "MLBL", "MPFL", "NFS", "PFL", "PROFL", "RLFL",
                "SADBL", "SAPDBL", "SFCL", "SIFC", "SINDU"],
    "Others": ["CHDC", "CIT", "HIDCL", "JOSHI", "NABBC", "NHDL", "NIFRA", "NGPL", "OHL",
               "SHINE", "TRH"],
}


def get_sector(symbol: str) -> str:
    for s, lst in SECTORS.items():
        if symbol in lst:
            return s
    return "Others"


# ---------------------------------------------------------------
# In-memory TTL cache
# ---------------------------------------------------------------
_CACHE: Dict[str, Tuple[float, object]] = {}
_DEFAULT_TTL = 900  # 15 minutes


def _cache_get(key: str, ttl: int = _DEFAULT_TTL):
    v = _CACHE.get(key)
    if v and time.time() - v[0] < ttl:
        return v[1]
    return None


def _cache_set(key: str, value):
    _CACHE[key] = (time.time(), value)


# ---------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------
def load_history(symbol: str) -> Optional[pd.DataFrame]:
    """Return a DataFrame with columns: date, close, volume, high, low, open."""
    symbol = symbol.upper().strip()
    cached = _cache_get(f"hist:{symbol}")
    if cached is not None:
        return cached

    url = f"https://raw.githubusercontent.com/Aabishkar2/nepse-data/main/data/company-wise/{symbol}.csv"
    try:
        df = pd.read_csv(url)
    except Exception as e:
        logger.warning(f"load_history({symbol}) failed: {e}")
        return None

    # Normalise columns (file varies)
    lower = {c.lower(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n in lower:
                return lower[n]
        return None

    c_close = pick("close", "ltp")
    c_open = pick("open")
    c_high = pick("high", "max")
    c_low = pick("low", "min")
    c_vol = pick("volume", "qty", "traded_quantity")
    c_date = pick("date", "published_date", "businessdate")

    if not c_close:
        return None

    out = pd.DataFrame({
        "date": pd.to_datetime(df[c_date], errors="coerce") if c_date else pd.NaT,
        "close": pd.to_numeric(df[c_close], errors="coerce"),
        "open": pd.to_numeric(df[c_open], errors="coerce") if c_open else np.nan,
        "high": pd.to_numeric(df[c_high], errors="coerce") if c_high else np.nan,
        "low": pd.to_numeric(df[c_low], errors="coerce") if c_low else np.nan,
        "volume": pd.to_numeric(df[c_vol], errors="coerce") if c_vol else 0,
    }).dropna(subset=["close"])

    if "date" in out.columns and out["date"].notna().any():
        out = out.sort_values("date").reset_index(drop=True)

    _cache_set(f"hist:{symbol}", out)
    return out


# ---------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------
def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=1).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1 / period, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = roll_up / (roll_down.replace(0, 1e-9))
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(series: pd.Series, window: int = 20, nstd: float = 2.0):
    ma = series.rolling(window=window, min_periods=1).mean()
    std = series.rolling(window=window, min_periods=1).std().fillna(0)
    upper = ma + nstd * std
    lower = ma - nstd * std
    return upper, ma, lower


# ---------------------------------------------------------------
# Summaries for API
# ---------------------------------------------------------------
def _f(x) -> Optional[float]:
    try:
        if x is None or pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def stock_summary(symbol: str) -> Dict:
    df = load_history(symbol)
    if df is None or df.empty or len(df) < 2:
        return {"symbol": symbol, "available": False}

    close = df["close"]
    latest = _f(close.iloc[-1])
    prev = _f(close.iloc[-2])
    change = (latest - prev) if latest is not None and prev is not None else 0.0
    pct = (change / prev * 100) if prev else 0.0

    high_52w = _f(close.tail(252).max() if len(close) >= 252 else close.max())
    low_52w = _f(close.tail(252).min() if len(close) >= 252 else close.min())
    avg_30 = _f(close.tail(30).mean())
    avg_200 = _f(close.tail(200).mean())

    rsi_val = _f(rsi(close).iloc[-1])
    macd_line, signal_line, _hist = macd(close)
    macd_val = _f(macd_line.iloc[-1])
    macd_sig = _f(signal_line.iloc[-1])

    vol_30 = _f(df["volume"].tail(30).mean()) if "volume" in df else None

    return {
        "symbol": symbol,
        "sector": get_sector(symbol),
        "available": True,
        "latest_close": latest,
        "prev_close": prev,
        "change": round(change, 2),
        "change_pct": round(pct, 2),
        "high_52w": high_52w,
        "low_52w": low_52w,
        "sma_30": avg_30,
        "sma_200": avg_200,
        "rsi_14": round(rsi_val, 2) if rsi_val is not None else None,
        "macd": round(macd_val, 3) if macd_val is not None else None,
        "macd_signal": round(macd_sig, 3) if macd_sig is not None else None,
        "volume_avg_30": vol_30,
        "records": int(len(df)),
    }


def stock_history(symbol: str, days: int = 120) -> Dict:
    df = load_history(symbol)
    if df is None or df.empty:
        return {"symbol": symbol, "available": False, "points": []}

    df = df.tail(days).reset_index(drop=True)
    close = df["close"]
    sma20 = sma(close, 20)
    sma50 = sma(close, 50)
    rsi14 = rsi(close)
    macd_l, sig_l, hist = macd(close)
    bb_u, bb_m, bb_l = bollinger(close)

    points = []
    for i, row in df.iterrows():
        points.append({
            "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row.get("date", None)) else str(i),
            "close": _f(row["close"]),
            "open": _f(row.get("open")),
            "high": _f(row.get("high")),
            "low": _f(row.get("low")),
            "volume": _f(row.get("volume")),
            "sma20": _f(sma20.iloc[i]),
            "sma50": _f(sma50.iloc[i]),
            "rsi": _f(rsi14.iloc[i]),
            "macd": _f(macd_l.iloc[i]),
            "macd_signal": _f(sig_l.iloc[i]),
            "macd_hist": _f(hist.iloc[i]),
            "bb_upper": _f(bb_u.iloc[i]),
            "bb_middle": _f(bb_m.iloc[i]),
            "bb_lower": _f(bb_l.iloc[i]),
        })

    return {
        "symbol": symbol,
        "sector": get_sector(symbol),
        "available": True,
        "points": points,
    }


def market_overview(limit_movers: int = 6) -> Dict:
    """Aggregate latest-day snapshot across a curated subset for the homepage.

    We intentionally poll a subset (~24 popular tickers) to keep this fast;
    callers can request /stocks/all for the full universe.
    """
    cached = _cache_get("market:overview", ttl=600)
    if cached is not None:
        return cached

    curated = [
        "NABIL", "NICA", "GBIME", "EBL", "HBL", "SCB", "NMB", "SANIMA",
        "UPPER", "API", "HIDCL", "NIFRA", "CIT", "NLIC", "NLICL", "ALICL",
        "MBL", "KBL", "PRVU", "SBI", "ADBL", "SBL", "CHCL", "BPCL",
    ]
    rows = []
    for s in curated:
        try:
            r = stock_summary(s)
            if r.get("available"):
                rows.append(r)
        except Exception:
            continue

    if not rows:
        return {"gainers": [], "losers": [], "active": [], "index": None}

    rows_sorted_gain = sorted(rows, key=lambda x: (x.get("change_pct") or 0), reverse=True)
    gainers = rows_sorted_gain[:limit_movers]
    losers = rows_sorted_gain[-limit_movers:][::-1]
    active = sorted(rows, key=lambda x: (x.get("volume_avg_30") or 0), reverse=True)[:limit_movers]

    # Pseudo index = weighted average of latest close
    closes = [r["latest_close"] for r in rows if r.get("latest_close") is not None]
    prev_closes = [r["prev_close"] for r in rows if r.get("prev_close") is not None]
    idx = sum(closes) / len(closes) if closes else None
    prev_idx = sum(prev_closes) / len(prev_closes) if prev_closes else None
    idx_change = (idx - prev_idx) if (idx is not None and prev_idx is not None) else 0
    idx_pct = (idx_change / prev_idx * 100) if prev_idx else 0

    result = {
        "index": {
            "name": "BhaavShare Composite",
            "value": round(idx, 2) if idx else None,
            "change": round(idx_change, 2),
            "change_pct": round(idx_pct, 2),
            "components": len(rows),
        },
        "gainers": gainers,
        "losers": losers,
        "active": active,
        "total_covered": len(rows),
    }
    _cache_set("market:overview", result)
    return result
