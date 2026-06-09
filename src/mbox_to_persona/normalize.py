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


def strip_quoted_reply(value: str) -> str:
    lines = []
    quote_markers = [
        r"^on .+ wrote:$",
        r"^el .+ escribió:$",
        r"^el .+ escribio:$",
        r"^de:\s",
        r"^from:\s",
        r"^sent:\s",
        r"^enviado:\s",
        r"^to:\s",
        r"^para:\s",
        r"^subject:\s",
        r"^asunto:\s",
        r"^-{2,}\s*forwarded message\s*-{2,}$",
        r"^-{2,}\s*mensaje reenviado\s*-{2,}$",
    ]
    for line in (value or "").splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if stripped.startswith(">"):
            continue
        inline_quote = re.search(r"\s+(?:on|el)\s+.{0,220}(?:wrote|escribi[oó]):", line, flags=re.I)
        if not inline_quote:
            inline_quote = re.search(
                r"\s+(?:el\s+(?:lun|mar|mi[eé]|jue|vie|s[aá]b|dom)|on\s+(?:mon|tue|wed|thu|fri|sat|sun)),",
                line,
                flags=re.I,
            )
        if inline_quote:
            line = line[:inline_quote.start()]
            stripped = line.strip()
            low = stripped.lower()
        if any(re.search(pattern, low) for pattern in quote_markers):
            break
        if stripped:
            lines.append(line)
    return "\n".join(lines).strip()


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
