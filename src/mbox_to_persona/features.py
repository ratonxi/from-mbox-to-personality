import csv
import re
from collections import Counter
from pathlib import Path


def read_index(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ']{2,}", text or "")


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
    for row in sent:
        text = row.get("redacted_excerpt", "").strip()
        first = text.split(".")[0][:80].lower()
        last = text[-160:].lower()
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
        "languages": dict(languages),
        "question_rate": round(punctuation.get("?", 0) / max(1, len(sent)), 2),
        "exclamation_rate": round(punctuation.get("!", 0) / max(1, len(sent)), 2),
    }


def confidence_for_count(count: int) -> str:
    if count >= 200:
        return "high"
    if count >= 40:
        return "medium"
    return "low"

