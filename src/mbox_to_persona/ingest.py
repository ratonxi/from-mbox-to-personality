import csv
import hashlib
import json
import re
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path

from .identity import classify_message, extract_addresses
from .normalize import detect_language, html_to_text, normalize_text, strip_quoted_reply
from .redact import compact_whitespace, redact_text


FIELDNAMES = [
    "evidence_id", "classification", "date", "year", "from", "to", "cc", "subject",
    "message_id", "thread_hint", "gmail_labels", "language", "body_chars", "redacted_excerpt",
    "attachment_count", "attachment_names", "body_hash",
]


def iter_mbox_messages(path: Path):
    buffer = bytearray()
    with path.open("rb") as fh:
        for line in fh:
            if line.startswith(b"From ") and buffer:
                yield bytes(buffer)
                buffer.clear()
            buffer.extend(line)
        if buffer:
            yield bytes(buffer)


def infer_target_from_headers(mbox: Path, limit: int = 0) -> list[str]:
    parser = BytesParser(policy=policy.default)
    sent_counts: dict[str, int] = {}
    all_counts: dict[str, int] = {}
    for idx, raw in enumerate(iter_mbox_messages(mbox), start=1):
        if limit and idx > limit:
            break
        try:
            message = parser.parsebytes(raw, headersonly=True)
        except Exception:
            continue
        labels = (message.get("x-gmail-labels", "") or "").lower()
        looks_sent = any(term in labels for term in ["sent", "enviado", "enviados"])
        for addr in extract_addresses(message.get("from", "")):
            all_counts[addr] = all_counts.get(addr, 0) + 1
            if looks_sent:
                sent_counts[addr] = sent_counts.get(addr, 0) + 1
    counts = sent_counts or all_counts
    if not counts:
        return []
    return [max(counts.items(), key=lambda item: item[1])[0]]


def parse_date(message):
    raw = message.get("date", "")
    if not raw:
        return "", ""
    try:
        dt = parsedate_to_datetime(raw)
        return dt.isoformat(), str(dt.year)
    except Exception:
        return raw, ""


def message_text(message, max_chars: int = 120_000) -> str:
    chunks = []
    total = 0
    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue
        ctype = part.get_content_type()
        if ctype not in {"text/plain", "text/html"}:
            continue
        try:
            text = part.get_content()
        except Exception:
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")
        if ctype == "text/html":
            text = html_to_text(text)
        chunks.append(text)
        total += len(text)
        if total >= max_chars:
            break
    return strip_quoted_reply(normalize_text("\n".join(chunks)))[:max_chars]


def attachment_names(message) -> list[str]:
    names = []
    for part in message.walk():
        filename = part.get_filename()
        if filename or part.get_content_disposition() == "attachment":
            names.append(filename or "attachment")
    return names


def thread_hint(subject: str) -> str:
    normalized = re.sub(r"(?i)^\s*(re|fw|fwd)\s*:\s*", "", subject or "")
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return hashlib.sha1(normalized.encode("utf-8", errors="ignore")).hexdigest()[:12]


def iter_records(mbox: Path, limit: int = 0):
    parser = BytesParser(policy=policy.default)
    for idx, raw in enumerate(iter_mbox_messages(mbox), start=1):
        if limit and idx > limit:
            break
        try:
            message = parser.parsebytes(raw)
        except Exception:
            continue
        text = message_text(message, max_chars=20_000)
        names = attachment_names(message)
        date, year = parse_date(message)
        subject = message.get("subject", "")
        digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
        yield {
            "seq": idx,
            "date": date,
            "year": year,
            "from": message.get("from", ""),
            "to": message.get("to", ""),
            "cc": message.get("cc", ""),
            "bcc": message.get("bcc", ""),
            "subject": subject,
            "message_id": message.get("message-id", ""),
            "thread_hint": thread_hint(subject),
            "gmail_labels": message.get("x-gmail-labels", ""),
            "language": detect_language(text),
            "body_chars": len(text),
            "body": text,
            "attachment_count": len(names),
            "attachment_names": ";".join(names),
            "body_hash": digest,
        }


def scan_mbox(
    mbox: Path,
    out: Path,
    target_emails: list[str] | None,
    limit: int = 0,
    redact: bool = True,
    progress_every: int = 5000,
) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    sent_dir = out / "sent_corpus"
    received_dir = out / "received_context"
    sent_dir.mkdir(exist_ok=True)
    received_dir.mkdir(exist_ok=True)

    targets = set(addr.lower() for addr in target_emails if addr) if target_emails else set(infer_target_from_headers(mbox, limit=limit))
    seen = set()
    counts = {"messages_indexed": 0, "sent_by_target": 0, "received_by_target": 0, "unknown": 0}
    with (out / "index.csv").open("w", newline="", encoding="utf-8") as fh, \
            (out / "index.jsonl").open("w", encoding="utf-8") as json_fh, \
            (sent_dir / "sent_redacted.jsonl").open("w", encoding="utf-8") as sent_fh, \
            (received_dir / "received_redacted.jsonl").open("w", encoding="utf-8") as received_fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        for n, record in enumerate(iter_records(mbox, limit=limit), start=1):
            dedupe_key = record["message_id"] or f"{record['date']}:{record['body_hash']}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            classification = classify_message(record, targets)
            excerpt = compact_whitespace(record.pop("body", ""))[:1200]
            row = {
                "evidence_id": f"E{n:06d}",
                "classification": classification,
                **{k: record.get(k, "") for k in FIELDNAMES if k not in {"evidence_id", "classification", "redacted_excerpt"}},
                "redacted_excerpt": redact_text(excerpt, enabled=redact),
            }
            writer.writerow(row)
            json_line = json.dumps(row, ensure_ascii=False) + "\n"
            json_fh.write(json_line)
            if classification == "sent_by_target":
                sent_fh.write(json_line)
            elif classification == "received_by_target":
                received_fh.write(json_line)
            counts["messages_indexed"] += 1
            counts[classification] = counts.get(classification, 0) + 1
            if progress_every and counts["messages_indexed"] % progress_every == 0:
                print(
                    f"scanned={n} indexed={counts['messages_indexed']} sent={counts['sent_by_target']} received={counts['received_by_target']}",
                    flush=True,
                )

    report = {
        "mbox": str(mbox),
        "messages_indexed": counts["messages_indexed"],
        "target_addresses": sorted(targets),
        "sent_by_target": counts["sent_by_target"],
        "received_by_target": counts["received_by_target"],
        "unknown": counts["unknown"],
        "redaction_enabled": redact,
    }
    (out / "redaction_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
