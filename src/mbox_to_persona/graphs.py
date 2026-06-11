import csv
import json
import math
import re
from pathlib import Path

from .features import read_index


DIMENSIONS = [
    ("Directness", "Short, practical messages with low ceremony."),
    ("Question Drive", "Uses questions to unblock the next step."),
    ("Politeness", "Greetings, thanks, and soft closings."),
    ("Action Orientation", "Focus on sending, reviewing, fixing, closing, paying, or deciding."),
    ("Planning Mode", "Mentions deadlines, plans, organization, meetings, and next steps."),
    ("Admin Intensity", "Handles invoices, documents, contracts, taxes, payments, housing, or records."),
    ("Context Switching", "Moves across different domains and threads."),
    ("Bilingual Flex", "Switches across languages or handles multilingual communication."),
]


ACTION_TERMS = [
    "send", "review", "fix", "close", "pay", "decide", "check", "appraise",
    "enviar", "revisar", "mirar", "arreglar", "cerrar", "pagar", "decidir",
    "comprobar", "pasar", "organizar", "ajustar",
]

PLANNING_TERMS = [
    "plan", "deadline", "meeting", "calendar", "next step", "schedule",
    "plazo", "fecha", "reunion", "reunión", "organizar", "agenda", "siguiente",
]

ADMIN_TERMS = [
    "invoice", "payment", "contract", "document", "tax", "receipt", "appraisal",
    "factura", "pago", "contrato", "documento", "renta", "recibo", "piso",
    "vivienda", "expediente", "seguro", "abono", "minuta",
]


def clamp(value: float) -> float:
    return max(0.0, min(10.0, value))


def count_terms(text: str, terms: list[str]) -> int:
    low = (text or "").lower()
    return sum(len(re.findall(rf"(?<!\w){re.escape(term)}(?!\w)", low)) for term in terms)


def load_persona(path: Path | None) -> dict:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def score_dimensions(index_path: Path, persona_path: Path | None = None) -> list[dict]:
    rows = read_index(index_path)
    sent = [r for r in rows if r.get("classification") == "sent_by_target"]
    persona = load_persona(persona_path)
    style = persona.get("style_summary", {})
    sent_count = max(1, len(sent))
    text = "\n".join((r.get("subject", "") + " " + r.get("redacted_excerpt", "")) for r in sent)
    subjects = {r.get("subject", "").strip().lower() for r in sent if r.get("subject")}
    languages = {k: v for k, v in style.get("languages", {}).items() if k != "unknown" and v}

    avg_words = float(style.get("average_words_per_sentence") or 16)
    directness = clamp(10 - max(0, avg_words - 8) * 0.45)
    question_drive = clamp((sum((r.get("redacted_excerpt", "") + r.get("subject", "")).count("?") for r in sent) / sent_count) * 4.0)
    closings = sum(style.get("closings", {}).values()) if isinstance(style.get("closings"), dict) else 0
    greetings = sum(style.get("greetings", {}).values()) if isinstance(style.get("greetings"), dict) else 0
    politeness = clamp(((closings + greetings) / sent_count) * 7.0)
    action = clamp((count_terms(text, ACTION_TERMS) / sent_count) * 5.5)
    planning = clamp((count_terms(text, PLANNING_TERMS) / sent_count) * 6.0)
    admin = clamp((count_terms(text, ADMIN_TERMS) / sent_count) * 5.0)
    context_switching = clamp((len(subjects) / sent_count) * 11.0)
    bilingual = clamp((len(languages) / 2) * 10.0 if languages else 0.0)

    scores = {
        "Directness": directness,
        "Question Drive": question_drive,
        "Politeness": politeness,
        "Action Orientation": action,
        "Planning Mode": planning,
        "Admin Intensity": admin,
        "Context Switching": context_switching,
        "Bilingual Flex": bilingual,
    }
    return [
        {
            "dimension": name,
            "score": round(scores[name], 1),
            "description": description,
            "basis": "sent_by_target emails only",
        }
        for name, description in DIMENSIONS
    ]


def write_scores_csv(scores: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["dimension", "score", "description", "basis"])
        writer.writeheader()
        writer.writerows(scores)


def radar_svg(scores: list[dict], title: str = "Communication Personality Radar") -> str:
    size = 900
    cx = cy = size / 2
    radius = 300
    n = len(scores)
    angles = [(-math.pi / 2) + 2 * math.pi * i / n for i in range(n)]

    def point(angle: float, value: float):
        r = radius * value / 10
        return cx + math.cos(angle) * r, cy + math.sin(angle) * r

    rings = []
    for value in [2, 4, 6, 8, 10]:
        pts = " ".join(f"{point(a, value)[0]:.1f},{point(a, value)[1]:.1f}" for a in angles)
        rings.append(f'<polygon points="{pts}" fill="none" stroke="#d7dee8" stroke-width="1"/>')

    axes = []
    labels = []
    for angle, row in zip(angles, scores):
        x, y = point(angle, 10)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#c1cad7" stroke-width="1"/>')
        lx, ly = point(angle, 11.35)
        anchor = "middle"
        if lx > cx + 40:
            anchor = "start"
        elif lx < cx - 40:
            anchor = "end"
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dominant-baseline="middle" '
            f'font-family="Inter, Segoe UI, Arial" font-size="18" fill="#1f2937">{row["dimension"]} ({row["score"]})</text>'
        )

    poly = " ".join(f"{point(angle, row['score'])[0]:.1f},{point(angle, row['score'])[1]:.1f}" for angle, row in zip(angles, scores))
    dots = []
    for angle, row in zip(angles, scores):
        x, y = point(angle, row["score"])
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#0f766e"/>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-label="{title}">
  <rect width="100%" height="100%" fill="#f8fafc"/>
  <text x="{cx}" y="58" text-anchor="middle" font-family="Inter, Segoe UI, Arial" font-size="34" font-weight="700" fill="#0f172a">{title}</text>
  <text x="{cx}" y="92" text-anchor="middle" font-family="Inter, Segoe UI, Arial" font-size="15" fill="#64748b">Scores 0-10 from sent-email communication patterns; not a clinical personality test.</text>
  <g>
    {''.join(rings)}
    {''.join(axes)}
    <polygon points="{poly}" fill="#14b8a6" fill-opacity="0.28" stroke="#0f766e" stroke-width="4"/>
    {''.join(dots)}
    {''.join(labels)}
  </g>
</svg>
"""


def write_summary(scores: list[dict], path: Path) -> None:
    lines = [
        "# Communication Personality Radar",
        "",
        "Scores are 0-10 behavioral communication signals derived from sent emails only.",
        "They are useful for persona prompting, not clinical or psychometric diagnosis.",
        "",
    ]
    for row in scores:
        lines.append(f"- **{row['dimension']}**: {row['score']}/10 - {row['description']}")
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_graphs(index_path: Path, out: Path, persona_path: Path | None = None) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    scores = score_dimensions(index_path, persona_path)
    write_scores_csv(scores, out / "personality_radar_scores.csv")
    (out / "personality_radar.svg").write_text(radar_svg(scores), encoding="utf-8")
    write_summary(scores, out / "personality_radar.md")
    return scores

