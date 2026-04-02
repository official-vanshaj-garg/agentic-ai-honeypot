import re
from typing import List, Dict, Set

from src.config import client, GROQ_MODEL
from src.schemas import MessageItem
from src.session_state import SESSION_ASKED
from src.services.scoring import looks_like_payment_targeted
from src.utils.text import norm, BANNED_WORDS, QUESTION_TURNS

# ============================================================
# LLM REPLY (LLM-FIRST EVERY TURN) + RUBRIC GUARDRAILS
# ============================================================

def _count_features(text: str) -> Dict[str, int]:
    tl = (text or "").lower()
    return {
        "q": 1 if "?" in (text or "") else 0,
        "inv": 1 if any(w in tl for w in ["verify", "official", "confirm", "reference", "ticket", "case"]) else 0,
        "rf": 1 if any(w in tl for w in ["urgent", "otp", "blocked", "link", "transfer", "upi", "fee", "suspended", "frozen", "disconnect"]) else 0,
        "eli": 1 if any(w in tl for w in ["account", "number", "email", "upi", "link", "send", "share", "id", "phone", "call"]) else 0,
    }

def _sanitize_reply(reply: str) -> str:
    r = (reply or "").strip()
    if not r:
        return ""

    # Remove banned words (don't accuse, don't mention AI/bot/honeypot)
    rl = r.lower()
    for bw in BANNED_WORDS:
        if bw in rl:
            r = re.sub(bw, "", r, flags=re.IGNORECASE).strip()
            rl = r.lower()

    # Ensure only 1 question max (rubric says avoid multiple questions)
    if r.count("?") > 1:
        first = r.find("?")
        # keep up to first question mark, convert rest to statements
        r = r[: first + 1] + re.sub(r"\?", ".", r[first + 1 :])

    # Keep short-ish
    if len(r) > 200:
        r = r[:195].rstrip() + "\u2026"

    return r.strip()

def _next_hint(session_id: str, incoming_text: str, preview: Dict[str, List[str]]) -> str:
    """
    Give the LLM a 'preferred next question topic' so it asks for missing intel naturally.
    """
    asked = SESSION_ASKED.get(session_id, set())
    tl = norm(incoming_text)

    want_order = [
        ("reference", "reference/ticket number", "referenceIds"),
        ("link", "verification link", "phishingLinks"),
        ("email", "official email address", "emailAddresses"),
        ("phone", "official phone number", "phoneNumbers"),
        ("upi", "UPI ID", "upiIds"),
        ("account", "bank account number", "bankAccounts"),
    ]

    # prioritize based on context
    if "kyc" in tl or "verify" in tl or "link" in tl:
        want_order = [
            ("link", "verification link", "phishingLinks"),
            ("email", "official email address", "emailAddresses"),
            ("reference", "reference/ticket number", "referenceIds"),
            ("phone", "official phone number", "phoneNumbers"),
            ("upi", "UPI ID", "upiIds"),
            ("account", "bank account number", "bankAccounts"),
        ]
    if "upi" in tl or looks_like_payment_targeted(incoming_text):
        want_order = [
            ("upi", "UPI ID", "upiIds"),
            ("account", "bank account number", "bankAccounts"),
            ("reference", "reference/ticket number", "referenceIds"),
            ("phone", "official phone number", "phoneNumbers"),
            ("email", "official email address", "emailAddresses"),
            ("link", "verification link", "phishingLinks"),
        ]

    for key, label, field in want_order:
        if key in asked:
            continue
        if len(preview.get(field, []) or []) == 0:
            SESSION_ASKED.setdefault(session_id, set()).add(key)
            return label

    # fallback
    return "how to proceed"

def _llm_generate_reply(incoming_text: str, history: List[MessageItem], hint: str, turn: int, counts: Dict[str, int]) -> str:
    """
    LLM-first reply, guided by:
    - hint topic
    - rubric targets so far (questions, investigative, red flags, elicitation)
    """
    # Guidance to help LLM naturally hit rubric thresholds by turn 8
    need_q = counts.get("q", 0) < 5 and turn <= 8
    need_inv = counts.get("inv", 0) < 3 and turn <= 8
    need_rf = counts.get("rf", 0) < 5 and turn <= 8
    need_eli = counts.get("eli", 0) < 4 and turn <= 8

    system_prompt = f"""
You are a normal middle-class person chatting naturally in English.

STRICT RULES:
- Never share OTP/PIN/CVV/password.
- Never accuse or say the words: scam, fraud, AI, bot, honeypot.
- 1\u20132 short sentences.
- Ask at most ONE question.

GOAL:
- Keep the conversation going naturally.
- Sound slightly worried/confused but cooperative.
- Gradually get details.

PREFERRED QUESTION TOPIC (use if relevant): {hint}

RUBRIC TARGETS (by turn ~8):
- total questions >= 5 (still needed now: {str(need_q)})
- investigative/verification wording >= 3 (still needed now: {str(need_inv)})
- mention red-flag words sometimes (urgent/OTP/link/transfer/blocked) (still needed now: {str(need_rf)})
- ask for details (account/email/phone/link/upi/reference) (still needed now: {str(need_eli)})

Important: Do NOT ask multiple questions. Do NOT end the conversation.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]

    for msg in history[-8:]:
        if not msg.text:
            continue
        # scammer -> user; honeypot -> assistant
        role = "user" if (msg.sender or "").lower() == "scammer" else "assistant"
        messages.append({"role": role, "content": msg.text})

    messages.append({"role": "user", "content": incoming_text})

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.8,     # more variation / human feel
        max_tokens=90
    )

    out = completion.choices[0].message.content.strip()
    return out

def _enforce_minimums(turn: int, reply: str, counts: Dict[str, int]) -> str:
    """
    Minimal, non-robotic guardrail:
    If we are behind rubric targets on QUESTION_TURNS, add a single short question.
    """
    r = reply.strip()
    if turn in QUESTION_TURNS:
        if counts.get("q", 0) < 5 and "?" not in r:
            r = r.rstrip(".") + ". What's the reference/ticket number?"
        if counts.get("inv", 0) < 3 and not any(w in r.lower() for w in ["verify", "official", "confirm"]):
            # replace the question part to be investigative
            if "?" in r:
                r = "I'm trying to verify this officially\u2014what's the reference/ticket number?"
            else:
                r = r.rstrip(".") + " I'm trying to verify this officially."
    return _sanitize_reply(r)
