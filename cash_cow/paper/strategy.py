"""Frozen prospective ORB30/VWAP experiment, not a backtest winner.

One long entry attempt per session, on completed five-minute boundaries after
10:00 NY: close above the first 30-minute high and cumulative HLC3 VWAP.
Exit on a completed close below opening-range low or VWAP; runner risk/time
exits also apply. Missing minute bars invalidate signals, never forward-filled.
"""
import math
from datetime import timedelta

from .client import timestamp


def signal(bars, session_open, now, max_age=120):
    completed = []
    for row in bars:
        t = timestamp(row["t"])
        if not session_open <= t or t + timedelta(minutes=1) > now:
            raise ValueError("Bar outside completed current-session interval")
        values = [row[k] for k in ("o", "h", "l", "c", "v")]
        if not all(math.isfinite(v) and v > 0 for v in values):
            raise ValueError("Invalid OHLCV")
        if row["h"] < max(row["o"], row["l"], row["c"]) or row["l"] > min(row["o"], row["c"]):
            raise ValueError("Invalid OHLC bounds")
        if t != session_open + timedelta(minutes=len(completed)):
            raise ValueError("Missing, duplicate or unordered minute bars")
        completed.append(row)
    if len(completed) < 35:
        return {"ready": False, "reason": "opening_range_warmup"}
    age = (now - timestamp(completed[-1]["t"]) - timedelta(minutes=1)).total_seconds()
    if age > max_age:
        raise ValueError("Stale completed bars")
    # Latest fully completed five-minute interval; never use the in-progress one.
    n = len(completed) // 5 * 5
    used = completed[:n]
    latest = used[-1]
    high = max(r["h"] for r in used[:30])
    low = min(r["l"] for r in used[:30])
    vwap = sum((r["h"] + r["l"] + r["c"]) / 3 * r["v"] for r in used) / sum(r["v"] for r in used)
    return {"ready": True, "bar": latest["t"], "close": latest["c"],
            "range_high": high, "range_low": low, "vwap_proxy": vwap,
            "enter": latest["c"] > max(high, vwap), "exit": latest["c"] < max(low, vwap)}
