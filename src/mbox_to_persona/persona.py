import csv
import json
from pathlib import Path

from .features import compute_style_features, confidence_for_count, read_index


def infer_tone(features: dict) -> list[str]:
    tones = []
    if features["avg_words_per_sentence"] >= 22:
        tones.append("expansive and explanatory")
    else:
        tones.append("concise and direct")
    if features["question_rate"] >= 0.4:
        tones.append("question-driven")
    if features["exclamation_rate"] >= 0.3:
        tones.append("energetic")
    if features["closings"].get("gracias") or features["closings"].get("thanks"):
        tones.append("polite")
    return tones or ["neutral"]


def generate_persona(index_path: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    rows = read_index(index_path)
    features = compute_style_features(rows)
    confidence = confidence_for_count(features["message_count"])
    persona = {
        "name": "MBOX-derived writing persona",
        "source": str(index_path),
        "message_count": features["message_count"],
        "confidence": confidence,
        "style_summary": {
            "tone": infer_tone(features),
            "average_words_per_sentence": features["avg_words_per_sentence"],
            "average_excerpt_chars": features["avg_excerpt_chars"],
            "languages": features["languages"],
            "greetings": features["greetings"],
            "closings": features["closings"],
            "punctuation": features["punctuation"],
        },
        "top_words": features["top_words"],
        "safety_note": "Use only for consented style assistance. This persona describes writing style, not identity or beliefs.",
    }
    (out / "persona.json").write_text(json.dumps(persona, indent=2, ensure_ascii=False), encoding="utf-8")

    prompt = build_style_prompt(persona)
    (out / "style_prompt.md").write_text(prompt, encoding="utf-8")
    (out / "few_shot_examples.md").write_text(build_examples(rows), encoding="utf-8")
    with (out / "lexical_fingerprint.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["word", "count"])
        writer.writerows(features["top_words"])
    return persona


def build_style_prompt(persona: dict) -> str:
    style = persona["style_summary"]
    return f"""# Writing Persona Prompt

Write in a style similar to the target author's sent emails.

Confidence: {persona['confidence']} based on {persona['message_count']} sent messages.

Style traits:
- Tone: {', '.join(style['tone'])}
- Average words per sentence: {style['average_words_per_sentence']}
- Common greetings: {', '.join(style['greetings'].keys()) or 'not enough signal'}
- Common closings: {', '.join(style['closings'].keys()) or 'not enough signal'}
- Languages: {style['languages']}

Rules:
- Preserve the user's intent and facts.
- Match rhythm, directness, formality, and closing style.
- Do not invent personal facts.
- Do not imitate private third-party content.
"""


def build_examples(rows: list[dict], limit: int = 8) -> str:
    sent = [r for r in rows if r.get("classification") == "sent_by_target" and r.get("redacted_excerpt")]
    lines = ["# Redacted Style Examples", ""]
    for row in sent[:limit]:
        lines.append(f"## {row['evidence_id']}")
        lines.append(row["redacted_excerpt"][:700])
        lines.append("")
    if len(lines) == 2:
        lines.append("No sent examples available.")
    return "\n".join(lines)

