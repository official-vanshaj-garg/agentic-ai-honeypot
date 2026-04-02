import re
from typing import List, Dict, Set

from src.schemas import MessageItem
from src.utils.text import (
    URL_RE, EMAIL_RE, PHONE_RE, UPI_RE,
    REF_TOKEN_RE, REF_ONLY_RE,
    _clean_url, _normalize_phone, _has_digit,
)

# ============================================================
# EXTRACTION (clean + robust)
# ============================================================

def _extract_reference_ids(text: str) -> List[str]:
    t = text or ""
    ids: Set[str] = set()

    for m in REF_TOKEN_RE.findall(t):
        s = m.strip().upper()
        s = re.sub(r"[\s:#]+", "-", s)
        s = re.sub(r"-{2,}", "-", s).strip("-")
        if _has_digit(s):
            ids.add(s)

    for m in REF_ONLY_RE.findall(t):
        s = m.strip().upper()
        s = re.sub(r"[\s:#]+", "-", s)
        s = re.sub(r"-{2,}", "-", s).strip("-")
        ids.add(s)

    return sorted(ids)

def _split_ids(ids: List[str]) -> Dict[str, List[str]]:
    case_ids, policy_nums, order_nums = set(), set(), set()
    for s in ids:
        u = s.upper()
        if u.startswith(("REF", "REFERENCE", "TICKET", "CASE", "COMPLAINT")):
            case_ids.add(u)
        if u.startswith("POLICY"):
            policy_nums.add(u)
        if u.startswith(("ORDER", "ORD", "AWB", "APP", "BILL", "KYC", "TXN", "TRANSACTION")):
            order_nums.add(u)
    return {
        "caseIds": sorted(case_ids),
        "policyNumbers": sorted(policy_nums),
        "orderNumbers": sorted(order_nums),
    }

def extract_intelligence(history: List[MessageItem], latest_text: str) -> Dict[str, List[str]]:
    full_text = " ".join([m.text for m in history if m.text] + [latest_text or ""])

    links = {_clean_url(u) for u in URL_RE.findall(full_text)}
    emails = set(EMAIL_RE.findall(full_text))

    phones_raw = set(PHONE_RE.findall(full_text))
    phones = {_normalize_phone(p) for p in phones_raw}
    phone_last10 = {re.sub(r"\D", "", p)[-10:] for p in phones if re.sub(r"\D", "", p)}

    # UPI IDs: exclude emails + exclude PSP with dots (likely email domain)
    upi_raw = set(UPI_RE.findall(full_text))
    upis: Set[str] = set()
    for u in upi_raw:
        if EMAIL_RE.fullmatch(u):
            continue
        domain = u.split("@", 1)[-1]
        if "." in domain:
            continue
        # also avoid truncated email local part like "support@fakebank" if "support@fakebank.com" exists
        if any(e.lower().startswith((u + ".").lower()) for e in emails):
            continue
        upis.add(u)

    accounts_raw = set(re.findall(r"(?<!\d)\d{9,18}(?!\d)", full_text))
    accounts: Set[str] = set()
    for a in accounts_raw:
        if a[-10:] in phone_last10:
            continue
        # filter epoch-like timestamps
        if len(a) == 13:
            try:
                v = int(a)
                if 1_000_000_000_000 <= v <= 2_200_000_000_000:
                    continue
            except Exception:
                pass
        accounts.add(a)

    ref_ids = _extract_reference_ids(full_text)
    split_ids = _split_ids(ref_ids)

    return {
        "phoneNumbers": sorted(phones),
        "bankAccounts": sorted(accounts),
        "upiIds": sorted(upis),
        "phishingLinks": sorted(links),
        "emailAddresses": sorted(emails),
        "caseIds": split_ids["caseIds"],
        "policyNumbers": split_ids["policyNumbers"],
        "orderNumbers": split_ids["orderNumbers"],
        "referenceIds": ref_ids,
    }

def high_value_count(extracted: Dict[str, List[str]]) -> int:
    return sum(
        1 for k in ["phishingLinks", "emailAddresses", "upiIds", "bankAccounts", "phoneNumbers"]
        if len(extracted.get(k, []) or []) > 0
    )
