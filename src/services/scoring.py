import re

from src.utils.text import (
    norm, PAY_WORD_RE, UPI_RE, URL_RE,
    OTP_REQ_RE, PIN_REQ_RE, OTP_WARN_RE, PIN_WARN_RE,
    CLICK_LINK_RE, PHONE_RE,
)

# ============================================================
# SCAM SCORE (used only for confidence + fallback decisions)
# ============================================================

def looks_like_payment_targeted(text: str) -> bool:
    t = text or ""
    tl = norm(t)
    if not PAY_WORD_RE.search(t):
        return False
    if UPI_RE.search(t) or URL_RE.search(t) or re.search(r"(?<!\d)\d{9,18}(?!\d)", t):
        return True
    if re.search(r"\bto\s+(?:upi|account|a/c|bank)\b", tl):
        return True
    return False

def calculate_scam_score(text: str) -> int:
    t = text or ""
    tl = norm(t)
    score = 0

    if OTP_REQ_RE.search(t) and not OTP_WARN_RE.search(t):
        score += 6
    if PIN_REQ_RE.search(t) and not PIN_WARN_RE.search(t):
        score += 6
    if CLICK_LINK_RE.search(t):
        score += 3
    if looks_like_payment_targeted(t):
        score += 3

    for w in ["urgent", "immediately", "asap", "final warning", "within", "blocked", "suspended", "disconnect", "penalty", "frozen"]:
        if w in tl:
            score += 1

    if URL_RE.search(t):
        score += 2
    if PHONE_RE.search(t):
        score += 1
    if UPI_RE.search(t):
        score += 2
    if re.search(r"(?<!\d)\d{9,18}(?!\d)", t):
        score += 1

    if OTP_WARN_RE.search(t):
        score -= 4
    if PIN_WARN_RE.search(t):
        score -= 4

    return max(score, 0)
