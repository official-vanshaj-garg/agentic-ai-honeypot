import re

# ============================================================
# NORMALIZATION + PATTERNS
# ============================================================

def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

URL_RE = re.compile(r"\bhttps?://[^\s<>()]+\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")
# India-focused phone (works for test data); still accepts +91 forms.
PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
# UPI-like: local@psp (no dot in PSP); filter emails separately.
UPI_RE = re.compile(r"\b[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z]{2,64}\b")

OTP_REQ_RE = re.compile(r"\b(?:share|send|tell|provide|enter)\s+otp\b", re.IGNORECASE)
PIN_REQ_RE = re.compile(r"\b(?:share|send|tell|provide|enter)\s+(?:pin|cvv|password)\b", re.IGNORECASE)
OTP_WARN_RE = re.compile(r"\b(?:do\s*not|don't|never)\s+(?:share\s+)?otp\b", re.IGNORECASE)
PIN_WARN_RE = re.compile(r"\b(?:do\s*not|don't|never)\s+(?:share\s+)?(?:pin|cvv|password)\b", re.IGNORECASE)

CLICK_LINK_RE = re.compile(r"\b(?:click|open|login|verify)\s+(?:the\s+)?(?:link|url|website)\b", re.IGNORECASE)
PAY_WORD_RE = re.compile(r"\b(?:pay|transfer|send)\b", re.IGNORECASE)

REF_TOKEN_RE = re.compile(
    r"\b(?:REF|REFERENCE|TICKET|CASE|COMPLAINT|ORDER|ORD|POLICY|AWB|APP|BILL|KYC|TXN|TRANSACTION)"
    r"[-\s:#]*[A-Z0-9][A-Z0-9\-]{3,24}\b",
    re.IGNORECASE
)
REF_ONLY_RE = re.compile(r"\bREF[-\s:#]*\d{4,10}\b", re.IGNORECASE)

BANNED_WORDS = ("honeypot", "bot", "ai", "fraud", "scam")
INV_WORDS = ["verify", "official", "confirm", "reference", "ticket", "case id", "where"]
RED_FLAG_WORDS = ["urgent", "otp", "blocked", "link", "transfer", "upi", "fee", "suspended", "frozen", "disconnect"]
ELICIT_WORDS = ["account", "number", "email", "upi", "link", "send", "share", "id", "phone", "call"]

QUESTION_TURNS = {1, 2, 3, 5, 7}  # ensures >=5 questions by turn 8

def _clean_url(u: str) -> str:
    return u.rstrip(").,;!?:\"'")

def _normalize_phone(p: str) -> str:
    x = re.sub(r"[\s-]+", "", p)
    if x.startswith("+"):
        return x
    if x.startswith("91") and len(x) == 12:
        return "+" + x
    if len(x) == 10:
        return "+91" + x
    return x

def _has_digit(s: str) -> bool:
    return any(ch.isdigit() for ch in s)
