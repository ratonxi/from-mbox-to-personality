import csv
import html
import json
import math
import re
from pathlib import Path

from .features import is_automated_row, read_index


COMMUNICATION_DIMENSIONS = [
    ("Directness", "Short, practical messages with low ceremony."),
    ("Question Drive", "Uses questions to unblock the next step."),
    ("Politeness", "Greetings, thanks, and soft closings."),
    ("Action Orientation", "Focus on sending, reviewing, fixing, closing, paying, or deciding."),
    ("Planning Mode", "Mentions deadlines, plans, organization, meetings, and next steps."),
    ("Admin Intensity", "Handles invoices, documents, contracts, taxes, payments, housing, or records."),
    ("Context Switching", "Moves across different domains and threads."),
    ("Bilingual Flex", "Switches across languages or handles multilingual communication."),
]

BROAD_BEHAVIOR_DIMENSIONS = [
    ("Systems Builder", "Turns messy information into structures, workflows, and repeatable processes."),
    ("Problem Solver", "Focuses on diagnosing issues and moving blocked situations forward."),
    ("Admin Operator", "Handles documents, invoices, contracts, housing, taxes, and records."),
    ("Explorer Builder", "Experiments with new tools, projects, opportunities, and technical ideas."),
    ("Social Connector", "Maintains practical relationships, coordination, and polite exchanges."),
    ("Conflict Navigator", "Engages with claims, corrections, disputes, errors, and resolution paths."),
    ("Care Load", "Carries responsibility around health, family, housing, or people-dependent tasks."),
    ("Follow Through", "Tracks next steps, reminders, closures, and completion-oriented language."),
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

SYSTEMS_TERMS = [
    "organize", "structure", "workflow", "repo", "script", "folder", "index", "csv",
    "ordenar", "estructura", "carpeta", "índice", "indice", "automatizar", "herramienta",
    "skill", "github", "codex",
]

EXPLORER_TERMS = [
    "test", "try", "idea", "prototype", "experiment", "github", "repo", "tool", "ai",
    "probar", "idea", "experimento", "skill", "publicar", "implementar",
]

SOCIAL_TERMS = [
    "thanks", "thank you", "please", "hello", "hi", "family", "help",
    "gracias", "por favor", "hola", "buenas", "familia", "ayuda", "saludos",
]

CONFLICT_TERMS = [
    "claim", "issue", "problem", "error", "complaint", "dispute", "fix", "resolve",
    "reclamar", "reclamación", "problema", "error", "queja", "disputa", "resolver",
    "solución", "solucion", "multa", "contencioso",
]

CARE_TERMS = [
    "health", "doctor", "medicine", "treatment", "family", "home", "housing",
    "salud", "médico", "medico", "medicación", "medicacion", "tratamiento",
    "familia", "piso", "vivienda", "casa",
]

FOLLOW_THROUGH_TERMS = [
    "next", "pending", "done", "close", "complete", "follow", "reminder",
    "siguiente", "pendiente", "hecho", "cerrar", "completar", "seguimiento",
    "recordatorio", "recibido", "ok",
]


def clamp(value: float) -> float:
    return max(0.0, min(10.0, value))


def count_terms(text: str, terms: list[str]) -> int:
    low = (text or "").lower()
    return sum(len(re.findall(rf"(?<!\w){re.escape(term)}(?!\w)", low)) for term in terms)


def density_score(count: int, denominator: int, factor: float = 10.0) -> float:
    if denominator <= 0 or count <= 0:
        return 0.0
    return clamp(math.sqrt(count / denominator) * factor)


def load_persona(path: Path | None) -> dict:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def score_communication_dimensions(index_path: Path, persona_path: Path | None = None) -> list[dict]:
    rows = read_index(index_path)
    sent = [r for r in rows if r.get("classification") == "sent_by_target" and not is_automated_row(r)]
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
        for name, description in COMMUNICATION_DIMENSIONS
    ]


def score_broad_behavior_dimensions(index_path: Path) -> list[dict]:
    rows = read_index(index_path)
    relevant = [r for r in rows if r.get("classification") in {"sent_by_target", "received_by_target"} and not is_automated_row(r)]
    sent = [r for r in rows if r.get("classification") == "sent_by_target" and not is_automated_row(r)]
    has_received_context = any(r.get("classification") == "received_by_target" for r in relevant)
    basis = (
        "sent emails plus received-email context; aggregate behavioral inference"
        if has_received_context
        else "sent emails only; aggregate behavioral inference"
    )
    base_count = max(1, len(relevant))
    sent_count = max(1, len(sent))
    all_text = "\n".join((r.get("subject", "") + " " + r.get("redacted_excerpt", "")) for r in relevant)
    sent_text = "\n".join((r.get("subject", "") + " " + r.get("redacted_excerpt", "")) for r in sent)
    subjects = {r.get("subject", "").strip().lower() for r in relevant if r.get("subject")}

    systems_count = count_terms(sent_text, SYSTEMS_TERMS)
    action_count = count_terms(all_text, ACTION_TERMS)
    admin_count = count_terms(all_text, ADMIN_TERMS)
    explorer_count = count_terms(sent_text, EXPLORER_TERMS)
    social_count = count_terms(all_text, SOCIAL_TERMS)
    conflict_count = count_terms(all_text, CONFLICT_TERMS)
    care_count = count_terms(all_text, CARE_TERMS)
    follow_count = count_terms(sent_text, FOLLOW_THROUGH_TERMS + PLANNING_TERMS)
    question_count = sum((r.get("redacted_excerpt", "") + r.get("subject", "")).count("?") for r in sent)

    scores = {
        "Systems Builder": density_score(systems_count + follow_count // 2 + admin_count // 4, sent_count, 12.0),
        "Problem Solver": density_score(action_count + conflict_count + question_count, base_count, 11.0),
        "Admin Operator": density_score(admin_count, base_count, 10.0),
        "Explorer Builder": density_score(explorer_count + systems_count, sent_count, 13.0),
        "Social Connector": density_score(social_count, base_count, 9.0),
        "Conflict Navigator": density_score(conflict_count, base_count, 13.0),
        "Care Load": density_score(care_count, base_count, 10.0),
        "Follow Through": density_score(follow_count + action_count // 3, sent_count, 11.0),
    }
    if subjects:
        scores["Systems Builder"] = clamp(scores["Systems Builder"] + min(2.0, len(subjects) / base_count * 8))
        scores["Explorer Builder"] = clamp(scores["Explorer Builder"] + min(1.5, len(subjects) / base_count * 6))

    return [
        {
            "dimension": name,
            "score": round(scores[name], 1),
            "description": description,
            "basis": basis,
        }
        for name, description in BROAD_BEHAVIOR_DIMENSIONS
    ]


def write_scores_csv(scores: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["dimension", "score", "description", "basis"])
        writer.writeheader()
        writer.writerows(scores)


def radar_svg(
    scores: list[dict],
    title: str = "Communication Personality Radar",
    subtitle: str = "Scores 0-10 from sent-email communication patterns; not a clinical personality test.",
) -> str:
    size = 1200
    cx = cy = size / 2
    radius = 340
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
  <text x="{cx}" y="70" text-anchor="middle" font-family="Inter, Segoe UI, Arial" font-size="38" font-weight="700" fill="#0f172a">{title}</text>
  <text x="{cx}" y="108" text-anchor="middle" font-family="Inter, Segoe UI, Arial" font-size="16" fill="#64748b">{subtitle}</text>
  <g>
    {''.join(rings)}
    {''.join(axes)}
    <polygon points="{poly}" fill="#14b8a6" fill-opacity="0.28" stroke="#0f766e" stroke-width="4"/>
    {''.join(dots)}
    {''.join(labels)}
  </g>
</svg>
"""


def social_card_svg(
    scores: list[dict],
    title: str,
    subtitle: str,
    badge: str,
    footer: str,
) -> str:
    width = 1200
    height = 1500
    cx = width / 2
    cy = 590
    radius = 240
    n = len(scores)
    angles = [(-math.pi / 2) + 2 * math.pi * i / n for i in range(n)]

    def point(angle: float, value: float, base_radius: float = radius):
        r = base_radius * value / 10
        return cx + math.cos(angle) * r, cy + math.sin(angle) * r

    rings = []
    for value in [2, 4, 6, 8, 10]:
        pts = " ".join(f"{point(a, value)[0]:.1f},{point(a, value)[1]:.1f}" for a in angles)
        rings.append(f'<polygon points="{pts}" fill="none" stroke="#cbd5e1" stroke-width="2"/>')

    axes = []
    number_badges = []
    for i, angle in enumerate(angles, start=1):
        x, y = point(angle, 10)
        axes.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="#94a3b8" stroke-width="2" stroke-dasharray="7 9"/>'
        )
        nx = cx + math.cos(angle) * 285
        ny = cy + math.sin(angle) * 285
        number_badges.append(
            f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="34" fill="#ffffff" stroke="#99f6e4" stroke-width="3"/>'
            f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="27" fill="#0f172a"/>'
            f'<text x="{nx:.1f}" y="{ny + 1:.1f}" text-anchor="middle" dominant-baseline="middle" '
            f'font-family="Inter, Segoe UI, Arial" font-size="28" font-weight="800" fill="#ffffff">{i}</text>'
        )

    poly = " ".join(f"{point(angle, row['score'])[0]:.1f},{point(angle, row['score'])[1]:.1f}" for angle, row in zip(angles, scores))
    dots = []
    for angle, row in zip(angles, scores):
        x, y = point(angle, row["score"])
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="#0f766e"/>')

    scale_labels = []
    for value, label in [(10, "10"), (7.5, "7.5"), (5, "5"), (2.5, "2.5"), (0, "0")]:
        y = cy - radius * value / 10
        scale_labels.append(
            f'<text x="{cx}" y="{y + 8:.1f}" text-anchor="middle" font-family="Inter, Segoe UI, Arial" '
            f'font-size="25" font-weight="650" fill="#334155">{label}</text>'
        )

    cards = []
    card_w = 510
    card_h = 103
    left_x = 70
    right_x = 620
    top_y = 910
    gap_y = 18
    for i, row in enumerate(scores, start=1):
        col = 0 if i <= 4 else 1
        row_i = i - 1 if i <= 4 else i - 5
        x = left_x if col == 0 else right_x
        y = top_y + row_i * (card_h + gap_y)
        dimension = html.escape(str(row["dimension"]))
        score = html.escape(str(row["score"]))
        cards.append(
            f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="24" fill="#ffffff" stroke="#dbe4ee" stroke-width="2"/>'
            f'<circle cx="{x + 46}" cy="{y + 61}" r="28" fill="#0f172a"/>'
            f'<text x="{x + 46}" y="{y + 62}" text-anchor="middle" dominant-baseline="middle" '
            f'font-family="Inter, Segoe UI, Arial" font-size="28" font-weight="800" fill="#ffffff">{i}</text>'
            f'<text x="{x + 88}" y="{y + 46}" font-family="Inter, Segoe UI, Arial" '
            f'font-size="31" font-weight="750" fill="#0f172a">{dimension}</text>'
            f'<text x="{x + card_w - 42}" y="{y + 74}" text-anchor="end" font-family="Inter, Segoe UI, Arial" '
            f'font-size="58" font-weight="850" fill="#0f766e">{score}</text>'
        )

    escaped_title = html.escape(title)
    escaped_subtitle = html.escape(subtitle)
    escaped_badge = html.escape(badge)
    escaped_footer = html.escape(footer)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escaped_title}">
  <rect width="100%" height="100%" fill="#f8fafc"/>
  <rect x="34" y="34" width="1132" height="1432" rx="42" fill="#ffffff" stroke="#dbe4ee" stroke-width="2"/>
  <text x="{cx}" y="112" text-anchor="middle" font-family="Inter, Segoe UI, Arial" font-size="76" font-weight="900" fill="#0f172a">{escaped_title}</text>
  <line x1="545" y1="148" x2="633" y2="148" stroke="#0f766e" stroke-width="9" stroke-linecap="round"/>
  <circle cx="662" cy="148" r="7" fill="#0f766e"/>
  <text x="{cx}" y="205" text-anchor="middle" font-family="Inter, Segoe UI, Arial" font-size="27" font-weight="850" letter-spacing="10" fill="#0f172a">SCORE OVERVIEW</text>
  <text x="{cx}" y="252" text-anchor="middle" font-family="Inter, Segoe UI, Arial" font-size="29" font-weight="500" fill="#475569">{escaped_subtitle}</text>
  <g>
    {''.join(rings)}
    {''.join(axes)}
    <line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - radius}" stroke="#0f766e" stroke-opacity="0.28" stroke-width="3"/>
    <polygon points="{poly}" fill="#14b8a6" fill-opacity="0.32" stroke="#0f766e" stroke-width="9" stroke-linejoin="round"/>
    {''.join(dots)}
    {''.join(scale_labels)}
    {''.join(number_badges)}
  </g>
  <g>
    {''.join(cards)}
  </g>
  <rect x="82" y="1425" width="1036" height="54" rx="27" fill="#ecfeff" stroke="#d7f7f2" stroke-width="2"/>
  <text x="124" y="1462" text-anchor="middle" font-family="Inter, Segoe UI, Arial" font-size="32" font-weight="850" fill="#f59e0b">*</text>
  <line x1="174" y1="1441" x2="174" y2="1464" stroke="#67e8f9" stroke-width="3"/>
  <text x="206" y="1460" font-family="Inter, Segoe UI, Arial" font-size="22" font-weight="700" fill="#334155">{escaped_badge}</text>
  <text x="1085" y="1460" text-anchor="end" font-family="Inter, Segoe UI, Arial" font-size="18" font-weight="550" fill="#64748b">{escaped_footer}</text>
</svg>
"""


def write_summary(scores: list[dict], path: Path, title: str, scope_note: str) -> None:
    lines = [
        f"# {title}",
        "",
        scope_note,
        "They are useful for persona prompting, not clinical or psychometric diagnosis.",
        "",
    ]
    for row in scores:
        lines.append(f"- **{row['dimension']}**: {row['score']}/10 - {row['description']}")
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_graphs(index_path: Path, out: Path, persona_path: Path | None = None) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    communication_scores = score_communication_dimensions(index_path, persona_path)
    broad_scores = score_broad_behavior_dimensions(index_path)

    write_scores_csv(communication_scores, out / "communication_radar_scores.csv")
    (out / "communication_radar.svg").write_text(
        radar_svg(
            communication_scores,
            title="Communication Personality Radar",
            subtitle="Scores 0-10 from sent-email communication patterns; not a clinical personality test.",
        ),
        encoding="utf-8",
    )
    (out / "communication_social_card.svg").write_text(
        social_card_svg(
            communication_scores,
            title="Communication Radar",
            subtitle="Writing style and communication signals",
            badge="0-10 scores from sent email patterns",
            footer="Local analysis. Non-clinical.",
        ),
        encoding="utf-8",
    )
    write_summary(
        communication_scores,
        out / "communication_radar.md",
        "Communication Personality Radar",
        "Scores are 0-10 behavioral communication signals derived from sent emails only.",
    )

    write_scores_csv(broad_scores, out / "broad_behavior_radar_scores.csv")
    (out / "broad_behavior_radar.svg").write_text(
        radar_svg(
            broad_scores,
            title="Broad Behavioral Radar",
            subtitle="Scores 0-10 from aggregate email traces; broad inference, not diagnosis.",
        ),
        encoding="utf-8",
    )
    (out / "broad_behavior_social_card.svg").write_text(
        social_card_svg(
            broad_scores,
            title="Behavioral Radar",
            subtitle="Broad aggregate signals from email traces",
            badge="0-10 scores from aggregate email traces",
            footer="Local analysis. Broad inference.",
        ),
        encoding="utf-8",
    )
    write_summary(
        broad_scores,
        out / "broad_behavior_radar.md",
        "Broad Behavioral Radar",
        "Scores use sent emails plus received-email context as aggregate behavioral inference.",
    )

    # Backward-compatible aliases for the original graph names.
    write_scores_csv(communication_scores, out / "personality_radar_scores.csv")
    (out / "personality_radar.svg").write_text((out / "communication_radar.svg").read_text(encoding="utf-8"), encoding="utf-8")
    (out / "personality_radar.md").write_text((out / "communication_radar.md").read_text(encoding="utf-8"), encoding="utf-8")

    return [
        {"radar": "communication", "scores": communication_scores},
        {"radar": "broad_behavior", "scores": broad_scores},
    ]
