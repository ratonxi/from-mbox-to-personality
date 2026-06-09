import csv
from collections import Counter
from pathlib import Path

from .features import confidence_for_count, read_index


THEMES = {
    "planning": ["plan", "agenda", "calendar", "deadline", "fecha", "plazo", "organizar", "organización"],
    "finance_admin": ["factura", "invoice", "pago", "renta", "tax", "banco", "recibo"],
    "work": ["meeting", "reunión", "proyecto", "informe", "trabajo", "cliente", "equipo"],
    "housing": ["piso", "vivienda", "alquiler", "obra", "reforma", "contrato", "inquilino"],
    "care_social": ["familia", "gracias", "ayuda", "favor", "cuidar", "sorry", "perdona"],
    "conflict_resolution": ["problema", "issue", "reclamar", "queja", "error", "solución", "resolver"],
}


def score_themes(rows: list[dict]) -> tuple[Counter, dict[str, list[str]]]:
    counts = Counter()
    evidence = {k: [] for k in THEMES}
    for row in rows:
        text = (row.get("subject", "") + " " + row.get("redacted_excerpt", "")).lower()
        for theme, terms in THEMES.items():
            if any(term in text for term in terms):
                counts[theme] += 1
                if len(evidence[theme]) < 8:
                    evidence[theme].append(row["evidence_id"])
    return counts, evidence


def generate_profile(index_path: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    rows = read_index(index_path)
    sent = [r for r in rows if r.get("classification") == "sent_by_target"]
    received = [r for r in rows if r.get("classification") == "received_by_target"]
    theme_counts, evidence = score_themes(rows)
    confidence = confidence_for_count(len(sent))

    evidence_rows = []
    for row in rows:
        if row.get("classification") in {"sent_by_target", "received_by_target"}:
            evidence_rows.append({
                "evidence_id": row["evidence_id"],
                "classification": row["classification"],
                "date": row["date"],
                "subject": row["subject"],
                "excerpt": row["redacted_excerpt"][:500],
            })

    with (out / "evidence_table.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["evidence_id", "classification", "date", "subject", "excerpt"])
        writer.writeheader()
        writer.writerows(evidence_rows)

    md = build_profile_markdown(sent, received, theme_counts, evidence, confidence)
    (out / "psychological_profile.md").write_text(md, encoding="utf-8")
    (out / "limitations.md").write_text(LIMITATIONS, encoding="utf-8")
    return {
        "sent_count": len(sent),
        "received_count": len(received),
        "confidence": confidence,
        "themes": dict(theme_counts),
    }


def build_profile_markdown(sent, received, theme_counts, evidence, confidence) -> str:
    lines = [
        "# Non-Clinical Communication Profile",
        "",
        f"Overall confidence: **{confidence}**. Based on {len(sent)} sent messages and {len(received)} received/context messages.",
        "",
        "This profile describes observable communication behavior. It is not a medical, psychiatric, or diagnostic assessment.",
        "",
        "## Behavioral Signals",
    ]
    if not theme_counts:
        lines.append("- Low signal: no repeated themes were detected.")
    for theme, count in theme_counts.most_common():
        conf = "high" if count >= 50 else "medium" if count >= 10 else "low"
        refs = ", ".join(evidence.get(theme, [])[:6])
        label = theme.replace("_", " ")
        lines.append(f"- **{label}**: {count} references, confidence {conf}. Evidence: {refs or 'n/a'}.")
    lines.extend([
        "",
        "## Interpretation Guardrails",
        "- Treat repeated topics as priorities or obligations, not as personality certainty.",
        "- Use sent emails for communication style; received emails only indicate context around the person.",
        "- Do not infer diagnoses or protected traits from this output.",
    ])
    return "\n".join(lines)


LIMITATIONS = """# Limitations

- This is not a clinical or diagnostic report.
- Email data is incomplete and context-dependent.
- Received emails may describe other people's behavior, not the target person's traits.
- Confidence depends on the amount, diversity, and recency of sent messages.
- Redaction can remove context needed for perfect interpretation.
"""

