"""
BhaavShare LSTM directional forecaster.

Architecture: single-layer LSTM → 3-class classifier (DOWN / FLAT / UP)
Features: 30-day window of [close, volume, sentiment_proxy] (normalised)
Target: next-day return with ±1% threshold

Trained per-symbol on the Aabishkar2/nepse-data GitHub dataset. Evaluation uses
a CHRONOLOGICAL 70/15/15 train/val/test split (no shuffling across time) and
reports real accuracy, macro-F1, per-class precision/recall, and a confusion
matrix — all persisted to disk alongside the model weights so the API and UI
can surface them without re-running training.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
def _resolve_model_dir() -> Path:
    env = os.getenv("MODEL_DIR")
    if env:
        return Path(env)
    docker_path = Path("/app/data/models")
    if docker_path.is_dir() and any(docker_path.glob("*.pth")):
        return docker_path
    return Path(__file__).resolve().parents[3] / "data" / "models"


MODEL_DIR = _resolve_model_dir()
MODEL_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_SIZE = 30
CLASSES = ["DOWN", "FLAT", "UP"]
NUM_CLASSES = 3
FLAT_BAND = 0.01  # ±1 % is a "flat" day


def _model_path(symbol: str) -> Path:
    return MODEL_DIR / f"{symbol.upper()}.pth"


def _metrics_path(symbol: str) -> Path:
    return MODEL_DIR / f"{symbol.upper()}_metrics.json"


def _norm_path(symbol: str) -> Path:
    return MODEL_DIR / f"{symbol.upper()}_norm.json"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class StockLSTM(nn.Module):
    """Two-layer LSTM with dropout → FC → 3-class output."""

    def __init__(self, input_size: int = 3, hidden: int = 64,
                 num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(hidden),
            nn.Dropout(dropout),
            nn.Linear(hidden, NUM_CLASSES),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
class WindowDataset(Dataset):
    def __init__(self, features: np.ndarray, raw_close: np.ndarray,
                 window: int = WINDOW_SIZE):
        self.x: List[np.ndarray] = []
        self.y: List[int] = []
        for i in range(len(features) - window - 1):
            win = features[i : i + window]
            now = raw_close[i + window - 1]
            nxt = raw_close[i + window]
            ret = (nxt - now) / now if now else 0.0
            if ret > FLAT_BAND:
                label = 2  # UP
            elif ret < -FLAT_BAND:
                label = 0  # DOWN
            else:
                label = 1  # FLAT
            self.x.append(win)
            self.y.append(label)

    def __len__(self) -> int:
        return len(self.x)

    def __getitem__(self, idx: int):
        return (
            torch.tensor(self.x[idx], dtype=torch.float32),
            torch.tensor(self.y[idx], dtype=torch.long),
        )


# ---------------------------------------------------------------------------
# Data loading + feature engineering
# ---------------------------------------------------------------------------
def _fetch_history(symbol: str) -> pd.DataFrame:
    url = f"https://raw.githubusercontent.com/Aabishkar2/nepse-data/main/data/company-wise/{symbol}.csv"
    df = pd.read_csv(url)
    lower = {c.lower(): c for c in df.columns}

    def pick(*names) -> Optional[str]:
        for n in names:
            if n in lower:
                return lower[n]
        return None

    c_close = pick("close", "ltp")
    c_vol = pick("volume", "qty", "traded_quantity")
    c_date = pick("date", "published_date", "businessdate")
    if not c_close:
        raise ValueError(f"{symbol} CSV has no close column")

    out = pd.DataFrame({
        "date": pd.to_datetime(df[c_date], errors="coerce") if c_date else pd.NaT,
        "close": pd.to_numeric(df[c_close], errors="coerce"),
        "volume": pd.to_numeric(df[c_vol], errors="coerce") if c_vol else 0.0,
    }).dropna(subset=["close"])

    out["volume"] = out["volume"].fillna(0.0)
    if out["date"].notna().any():
        out = out.sort_values("date").reset_index(drop=True)
    if len(out) < WINDOW_SIZE * 4:
        raise ValueError(
            f"{symbol}: only {len(out)} rows — need at least {WINDOW_SIZE * 4} for training"
        )
    return out


def _engineer_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Return (normalised_feature_matrix, raw_close_array, normalisation_stats)."""
    close = df["close"].to_numpy(dtype=np.float64)
    vol = df["volume"].to_numpy(dtype=np.float64)

    # Sentiment proxy = normalised 5-day return (NOT random). This is a real,
    # data-driven momentum feature — not noise.
    returns = np.zeros_like(close)
    for i in range(5, len(close)):
        prev = close[i - 5]
        returns[i] = (close[i] - prev) / prev if prev else 0.0
    # Clip extreme moves before scaling
    returns = np.clip(returns, -0.15, 0.15)

    stats = {
        "close_min": float(close.min()),
        "close_max": float(close.max()),
        "vol_min": float(vol.min()),
        "vol_max": float(vol.max()),
        "ret_min": float(returns.min()),
        "ret_max": float(returns.max()),
    }
    eps = 1e-8
    close_n = (close - stats["close_min"]) / (stats["close_max"] - stats["close_min"] + eps)
    vol_n = (vol - stats["vol_min"]) / (stats["vol_max"] - stats["vol_min"] + eps)
    ret_n = (returns - stats["ret_min"]) / (stats["ret_max"] - stats["ret_min"] + eps)

    features = np.column_stack([close_n, vol_n, ret_n]).astype(np.float32)
    return features, close, stats


def _chronological_split(ds: WindowDataset, ratios=(0.7, 0.15, 0.15)):
    """Split dataset chronologically — CRITICAL for time series to avoid leakage."""
    n = len(ds)
    tr = int(n * ratios[0])
    va = int(n * (ratios[0] + ratios[1]))
    train = torch.utils.data.Subset(ds, range(0, tr))
    val = torch.utils.data.Subset(ds, range(tr, va))
    test = torch.utils.data.Subset(ds, range(va, n))
    return train, val, test


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def _evaluate(model: nn.Module, loader: DataLoader) -> Tuple[List[int], List[int]]:
    model.eval()
    y_true, y_pred = [], []
    with torch.no_grad():
        for x, y in loader:
            logits = model(x)
            preds = logits.argmax(dim=1).tolist()
            y_pred.extend(preds)
            y_true.extend(y.tolist())
    return y_true, y_pred


def _compute_metrics(y_true: List[int], y_pred: List[int]) -> Dict:
    if not y_true:
        return {}
    acc = accuracy_score(y_true, y_pred)
    f1_macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
    f1_weighted = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    p, r, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2], zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist()

    # Baseline: always predict the most common class (majority class)
    majority = max(set(y_true), key=y_true.count)
    baseline_acc = sum(1 for t in y_true if t == majority) / len(y_true)

    return {
        "accuracy": round(float(acc), 4),
        "f1_macro": round(float(f1_macro), 4),
        "f1_weighted": round(float(f1_weighted), 4),
        "per_class": {
            CLASSES[i]: {
                "precision": round(float(p[i]), 4),
                "recall": round(float(r[i]), 4),
                "f1": round(float(f1[i]), 4),
                "support": int(support[i]),
            }
            for i in range(NUM_CLASSES)
        },
        "confusion_matrix": cm,
        "class_labels": CLASSES,
        "baseline_majority_acc": round(float(baseline_acc), 4),
        "samples": len(y_true),
    }


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train_model(symbol: str = "NABIL", epochs: int = 25) -> Dict:
    symbol = symbol.upper()
    logger.info(f"[LSTM] Training {symbol} for {epochs} epochs…")

    df = _fetch_history(symbol)
    features, raw_close, stats = _engineer_features(df)

    ds = WindowDataset(features, raw_close, window=WINDOW_SIZE)
    if len(ds) < 50:
        raise ValueError(f"{symbol}: only {len(ds)} windows — not enough to train")

    train_ds, val_ds, test_ds = _chronological_split(ds)
    logger.info(
        f"[LSTM] {symbol} windows — train={len(train_ds)} val={len(val_ds)} test={len(test_ds)}"
    )

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False)

    # Class-balanced loss weights from training distribution
    train_labels = [train_ds.dataset.y[i] for i in train_ds.indices]
    counts = np.bincount(train_labels, minlength=NUM_CLASSES).astype(np.float64)
    weights = counts.sum() / (NUM_CLASSES * np.maximum(counts, 1.0))
    class_weights = torch.tensor(weights, dtype=torch.float32)
    logger.info(f"[LSTM] {symbol} class weights: {weights.round(3).tolist()}")

    model = StockLSTM()
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-3, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    best_val_f1 = -1.0
    best_state = None
    history = []

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        for x, y in train_loader:
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item()
        scheduler.step()
        avg_loss = epoch_loss / max(1, len(train_loader))

        val_true, val_pred = _evaluate(model, val_loader)
        val_metrics = _compute_metrics(val_true, val_pred)
        history.append({
            "epoch": epoch + 1,
            "loss": round(avg_loss, 4),
            "val_acc": val_metrics.get("accuracy", 0.0),
            "val_f1": val_metrics.get("f1_macro", 0.0),
        })
        logger.info(
            f"[LSTM] {symbol} epoch {epoch+1}/{epochs} — "
            f"loss={avg_loss:.4f} val_acc={val_metrics.get('accuracy',0):.3f} "
            f"val_f1={val_metrics.get('f1_macro',0):.3f}"
        )

        if val_metrics.get("f1_macro", 0.0) > best_val_f1:
            best_val_f1 = val_metrics["f1_macro"]
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

    # Restore best model and evaluate on held-out test set
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    test_true, test_pred = _evaluate(model, test_loader)
    test_metrics = _compute_metrics(test_true, test_pred)
    val_true, val_pred = _evaluate(model, val_loader)
    val_metrics = _compute_metrics(val_true, val_pred)

    # Persist model + stats + metrics
    torch.save(model.state_dict(), _model_path(symbol))
    with open(_norm_path(symbol), "w") as f:
        json.dump(stats, f)

    full_metrics = {
        "symbol": symbol,
        "epochs": epochs,
        "window": WINDOW_SIZE,
        "train_size": len(train_ds),
        "val_size": len(val_ds),
        "test_size": len(test_ds),
        "total_rows": int(len(df)),
        "trained_at": pd.Timestamp.utcnow().isoformat(),
        "history": history,
        "val": val_metrics,
        "test": test_metrics,
    }
    with open(_metrics_path(symbol), "w") as f:
        json.dump(full_metrics, f, indent=2)

    # Refresh cache
    _MODEL_CACHE[symbol] = model
    _STATS_CACHE[symbol] = stats

    logger.info(
        f"[LSTM] {symbol} done — test acc={test_metrics.get('accuracy',0):.3f} "
        f"f1={test_metrics.get('f1_macro',0):.3f} "
        f"(baseline {test_metrics.get('baseline_majority_acc',0):.3f})"
    )

    return {
        "message": "Training complete",
        "symbol": symbol,
        "epochs": epochs,
        "train_size": len(train_ds),
        "val_size": len(val_ds),
        "test_size": len(test_ds),
        "test_accuracy": test_metrics.get("accuracy"),
        "test_f1_macro": test_metrics.get("f1_macro"),
        "baseline_accuracy": test_metrics.get("baseline_majority_acc"),
        "test_metrics": test_metrics,
        "val_metrics": val_metrics,
        "final_loss": history[-1]["loss"] if history else None,
    }


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
_MODEL_CACHE: Dict[str, nn.Module] = {}
_STATS_CACHE: Dict[str, Dict] = {}


def _load_model(symbol: str) -> Optional[nn.Module]:
    symbol = symbol.upper()
    if symbol in _MODEL_CACHE:
        return _MODEL_CACHE[symbol]
    path = _model_path(symbol)
    if not path.exists():
        return None
    try:
        model = StockLSTM()
        model.load_state_dict(torch.load(path, map_location="cpu"))
        model.eval()
        _MODEL_CACHE[symbol] = model
        return model
    except Exception as e:
        logger.error(f"[LSTM] load weights failed for {symbol}: {e}")
        return None


def _load_stats(symbol: str) -> Optional[Dict]:
    symbol = symbol.upper()
    if symbol in _STATS_CACHE:
        return _STATS_CACHE[symbol]
    path = _norm_path(symbol)
    if not path.exists():
        return None
    try:
        with open(path) as f:
            stats = json.load(f)
        _STATS_CACHE[symbol] = stats
        return stats
    except Exception:
        return None


def get_metrics(symbol: str) -> Optional[Dict]:
    path = _metrics_path(symbol.upper())
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def predict_direction(symbol: str) -> Dict:
    """Directional forecast using REAL recent OHLCV from GitHub.

    Falls back to a simple momentum heuristic if no trained weights exist yet,
    so the API never 500s — but the response tells the caller whether the
    prediction is from a trained model or the heuristic.
    """
    symbol = symbol.upper()
    try:
        df = _fetch_history(symbol)
    except Exception as e:
        logger.warning(f"[LSTM] predict({symbol}) no data: {e}")
        return {
            "symbol": symbol,
            "predicted_direction": "FLAT",
            "confidence": 0.34,
            "source": "no_data",
        }

    features, raw_close, current_stats = _engineer_features(df)
    window = features[-WINDOW_SIZE:]
    if window.shape[0] < WINDOW_SIZE:
        return {
            "symbol": symbol,
            "predicted_direction": "FLAT",
            "confidence": 0.34,
            "source": "insufficient_history",
        }

    model = _load_model(symbol)
    if model is None:
        # Heuristic: 5-day momentum sign
        last5_ret = (raw_close[-1] - raw_close[-6]) / raw_close[-6] if len(raw_close) >= 6 else 0.0
        if last5_ret > FLAT_BAND:
            direction, conf = "UP", min(0.55 + abs(last5_ret) * 2, 0.80)
        elif last5_ret < -FLAT_BAND:
            direction, conf = "DOWN", min(0.55 + abs(last5_ret) * 2, 0.80)
        else:
            direction, conf = "FLAT", 0.50
        return {
            "symbol": symbol,
            "predicted_direction": direction,
            "confidence": round(float(conf), 3),
            "source": "heuristic_momentum_5d",
            "latest_close": float(raw_close[-1]),
        }

    # Real LSTM forward pass
    tensor = torch.from_numpy(window).unsqueeze(0)  # (1, 30, 3)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1).squeeze(0).numpy()
    idx = int(np.argmax(probs))
    return {
        "symbol": symbol,
        "predicted_direction": CLASSES[idx],
        "confidence": round(float(probs[idx]), 3),
        "probabilities": {
            CLASSES[i]: round(float(probs[i]), 3) for i in range(NUM_CLASSES)
        },
        "latest_close": float(raw_close[-1]),
        "source": "lstm",
    }
