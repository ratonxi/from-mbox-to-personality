import re


REDACTION_PATTERNS = [
    ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("URL", re.compile(r"https?://\S+", re.I)),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.I)),
    ("LONG_NUMBER", re.compile(r"\b\d{8,}\b")),
]


def redact_text(text: str, enabled: bool = True) -> str:
    if not enabled:
        return text or ""
    value = text or ""
    for label, pattern in REDACTION_PATTERNS:
        value = pattern.sub(f"[REDACTED_{label}]", value)
    return value


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

