import html
import re


def html_to_text(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value or "")
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return html.unescape(value)


def normalize_text(value: str) -> str:
    value = html.unescape(value or "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def detect_language(text: str) -> str:
    sample = (text or "").lower()
    spanish_hits = sum(w in sample for w in [" que ", " para ", " gracias", " hola", " pedido", " factura"])
    english_hits = sum(w in sample for w in [" the ", " and ", " thanks", " hello", " order", " invoice"])
    galician_hits = sum(w in sample for w in [" que ", " grazas", " concello", " solicitude"])
    if galician_hits >= 2 and galician_hits >= spanish_hits:
        return "gl"
    if spanish_hits > english_hits:
        return "es"
    if english_hits > 0:
        return "en"
    return "unknown"

