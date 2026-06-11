import csv
import json
from pathlib import Path

from .features import clean_inline_quote, compute_style_features, confidence_for_count, is_automated_row, read_index


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
            "common_openings": features["openings"],
            "common_subjects": features["subjects"],
            "punctuation": features["punctuation"],
            "first_person_rate": features["first_person_rate"],
        },
        "top_words": features["top_words"],
        "identity_boundary": {
            "source_for_voice": "sent_by_target emails only",
            "received_email_policy": "context only; never imitate received emails as the target voice",
            "biography_policy": "do not invent facts not present in the user's prompt or cited evidence",
        },
        "safety_note": "Use only for consented style assistance. This persona describes writing style and observable self-presentation, not a clinical diagnosis.",
    }
    (out / "persona.json").write_text(json.dumps(persona, indent=2, ensure_ascii=False), encoding="utf-8")

    prompt = build_style_prompt(persona)
    (out / "style_prompt.md").write_text(prompt, encoding="utf-8")
    (out / "me_style_prompt.md").write_text(prompt, encoding="utf-8")
    (out / "few_shot_examples.md").write_text(build_examples(rows), encoding="utf-8")
    (out / "synthetic_examples.md").write_text(build_synthetic_examples(persona), encoding="utf-8")
    (out / "do_not_copy.md").write_text(build_do_not_copy(), encoding="utf-8")
    (out / "who_i_am_from_sent_email.md").write_text(build_self_profile(rows, persona), encoding="utf-8")
    with (out / "lexical_fingerprint.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["word", "count"])
        writer.writerows(features["top_words"])
    return persona


def build_style_prompt(persona: dict) -> str:
    style = persona["style_summary"]
    return f"""# Writing Persona Prompt

You are writing as the target person, based only on that person's sent emails.

Confidence: {persona['confidence']} based on {persona['message_count']} sent messages.

Voice fingerprint:
- Tone: {', '.join(style['tone'])}
- Average words per sentence: {style['average_words_per_sentence']}
- Average excerpt length: {style['average_excerpt_chars']} characters
- Common greetings: {', '.join(style['greetings'].keys()) or 'not enough signal'}
- Common closings: {', '.join(style['closings'].keys()) or 'not enough signal'}
- Languages: {style['languages']}
- First-person rate: {style['first_person_rate']}

Rules:
- Preserve the user's intent, facts, and requested outcome.
- Match rhythm, directness, formality, code-switching, punctuation, greeting, and closing style.
- Prefer the target person's usual sentence length and structure.
- Use the target person's likely level of detail: do not over-polish if their sent emails are direct or rough.
- Do not invent personal facts.
- Do not copy private emails verbatim unless the user explicitly asks to quote their own text.
- Do not imitate received emails; they are not the target person's voice.
- Do not make clinical or diagnostic claims.
"""


def build_examples(rows: list[dict], limit: int = 8) -> str:
    sent = [r for r in rows if r.get("classification") == "sent_by_target" and not is_automated_row(r) and r.get("redacted_excerpt")]
    lines = ["# Redacted Style Examples", ""]
    for row in sent[:limit]:
        lines.append(f"## {row['evidence_id']}")
        lines.append(clean_inline_quote(row["redacted_excerpt"])[:700])
        lines.append("")
    if len(lines) == 2:
        lines.append("No sent examples available.")
    return "\n".join(lines)


def build_synthetic_examples(persona: dict) -> str:
    style = persona["style_summary"]
    greeting = next(iter(style["greetings"]), "Hola")
    closing = next(iter(style["closings"]), "Gracias")
    return f"""# Synthetic Examples

These are invented examples shaped by the measured style. They are not copied from private email.

## Short request
{greeting},

puedes revisarlo cuando tengas un hueco? Si ves algo raro me dices y lo ajusto.

{closing}

## Follow-up
{greeting},

te escribo para dejar esto cerrado y que no se nos quede pendiente. Creo que lo mejor es ordenar primero los puntos principales y luego revisar los detalles.

{closing}
"""


def build_do_not_copy() -> str:
    return """# Do Not Copy

- Do not invent biography, relationships, addresses, legal facts, medical facts, or financial facts.
- Do not copy full private emails verbatim into generated text.
- Do not use received emails as the target person's writing style.
- Do not diagnose the person or infer protected traits.
- Do not preserve sensitive identifiers unless the user explicitly provides them for the current task.
"""


def build_self_profile(rows: list[dict], persona: dict) -> str:
    sent = [r for r in rows if r.get("classification") == "sent_by_target" and not is_automated_row(r)]
    subjects = [r.get("subject", "") for r in sent if r.get("subject")]
    lines = [
        "# Who I Am From Sent Email",
        "",
        "This is a non-clinical, evidence-limited self-presentation summary based only on sent email metadata and redacted excerpts.",
        "",
        f"- Sent messages analyzed: {persona['message_count']}",
        f"- Confidence: {persona['confidence']}",
        f"- Main writing tone: {', '.join(persona['style_summary']['tone'])}",
        f"- Main languages: {persona['style_summary']['languages']}",
        "",
        "## Recurring Subject Signals",
    ]
    for subject in subjects[:20]:
        lines.append(f"- {subject}")
    if not subjects:
        lines.append("- Not enough subject signal.")
    lines.extend([
        "",
        "## Boundary",
        "This file should guide tone and self-presentation only. It should not be treated as a factual biography unless verified by the user.",
    ])
    return "\n".join(lines)
