import csv
import re
from collections import Counter
from pathlib import Path


def read_index(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def words(text: str) -> list[str]:
    stop = {"redacted", "email", "url", "phone", "iban", "long", "number", "wrote", "escribió", "escribio", "on", "at"}
    return [w for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ']{2,}", text or "") if w.lower() not in stop]


def clean_inline_quote(text: str) -> str:
    patterns = [
        r"\s+(?:on|el)\s+.{0,220}(?:wrote|escribi[oó]):",
        r"\s+(?:el\s+(?:lun|mar|mi[eé]|jue|vie|s[aá]b|dom)|on\s+(?:mon|tue|wed|thu|fri|sat|sun)),",
    ]
    value = text or ""
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.I)
        if match:
            value = value[:match.start()]
    return value.strip()


def sentence_count(text: str) -> int:
    return max(1, len(re.findall(r"[.!?]+", text or "")))


def compute_style_features(rows: list[dict]) -> dict:
    sent = [r for r in rows if r.get("classification") == "sent_by_target"]
    corpus = "\n".join(r.get("redacted_excerpt", "") for r in sent)
    tokens = words(corpus)
    lower = [t.lower() for t in tokens]
    total_chars = sum(len(r.get("redacted_excerpt", "")) for r in sent)
    total_sentences = sum(sentence_count(r.get("redacted_excerpt", "")) for r in sent)
    punctuation = Counter(ch for ch in corpus if ch in "!?;:,.")
    greetings = Counter()
    closings = Counter()
    openings = Counter()
    subjects = Counter()
    for row in sent:
        text = row.get("redacted_excerpt", "").strip()
        text = clean_inline_quote(text)
        first = text.split(".")[0][:80].lower()
        last = text[-160:].lower()
        if text:
            openings[text[:90]] += 1
        subject = (row.get("subject") or "").strip()
        if subject:
            subjects[subject[:90]] += 1
        for phrase in ["hola", "buenas", "hi", "hello", "querido", "estimado"]:
            if phrase in first:
                greetings[phrase] += 1
        for phrase in ["gracias", "un saludo", "saludos", "abrazo", "best", "thanks"]:
            if phrase in last:
                closings[phrase] += 1
    languages = Counter(r.get("language") or "unknown" for r in sent)
    return {
        "message_count": len(sent),
        "avg_excerpt_chars": round(total_chars / max(1, len(sent)), 1),
        "avg_words_per_sentence": round(len(tokens) / max(1, total_sentences), 1),
        "top_words": Counter(lower).most_common(40),
        "punctuation": dict(punctuation),
        "greetings": dict(greetings.most_common(10)),
        "closings": dict(closings.most_common(10)),
        "openings": dict(openings.most_common(12)),
        "subjects": dict(subjects.most_common(12)),
        "languages": dict(languages),
        "question_rate": round(punctuation.get("?", 0) / max(1, len(sent)), 2),
        "exclamation_rate": round(punctuation.get("!", 0) / max(1, len(sent)), 2),
        "first_person_rate": round(sum(1 for t in lower if t in {"i", "me", "my", "yo", "me", "mi", "mis"}) / max(1, len(tokens)), 3),
    }


def confidence_for_count(count: int) -> str:
    if count >= 200:
        return "high"
    if count >= 40:
        return "medium"
    return "low"
