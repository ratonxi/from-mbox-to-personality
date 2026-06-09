from mbox_to_persona.redact import redact_text


def test_redact_private_identifiers():
    text = "Email a@b.com tel +34 600 123 456 url https://x.test?a=1"
    redacted = redact_text(text)
    assert "a@b.com" not in redacted
    assert "600 123 456" not in redacted
    assert "https://x.test" not in redacted
    assert "[REDACTED_EMAIL]" in redacted

