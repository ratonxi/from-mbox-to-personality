# mbox-to-persona

Local-first tool for turning a Gmail `.mbox` export into a reusable writing persona and a non-clinical behavioral communication profile.

The tool is designed for self-analysis or explicitly consented analysis. Sent emails are used for writing style. Received emails are only used as context.

## Quick Start

```powershell
python -m pip install -e .
mbox-to-persona scan --mbox "All mail Including Spam and Trash.mbox" --out output --target-email you@example.com
mbox-to-persona persona --input output/index.csv --out output/persona
mbox-to-persona profile --input output/index.csv --out output/profile
mbox-to-persona export-prompt --persona output/persona/persona.json --out output/persona/style_prompt_export.md
```

If you omit `--target-email`, the scanner infers likely target sender addresses and uses the most frequent one.

## Outputs

- `index.csv`: message-level metadata, classification, redacted excerpt, scores, evidence ids.
- `index.jsonl`: same records as JSON Lines.
- `sent_corpus/sent_redacted.jsonl`: redacted snippets from target-authored mail.
- `received_context/received_redacted.jsonl`: redacted snippets from received mail.
- `persona/persona.json`: structured style profile.
- `persona/style_prompt.md`: pasteable AI prompt for writing in a similar style.
- `persona/few_shot_examples.md`: short redacted examples.
- `profile/psychological_profile.md`: non-clinical communication/behavior profile.
- `profile/evidence_table.csv`: evidence rows cited by the profile.
- `profile/limitations.md`: scope and safety limitations.

## Safety Boundary

This is not a diagnostic or clinical tool. It does not infer mental health conditions. It produces behavioral observations from communication patterns with confidence levels and evidence references.

