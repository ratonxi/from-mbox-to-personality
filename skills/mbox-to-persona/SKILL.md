---
name: mbox-to-persona
description: Analyze a Gmail MBOX export to create a consented writing persona, style prompt, communication fingerprint, and non-clinical behavioral profile from email patterns. Use when asked to turn Gmail, Takeout, MBOX, sent mail, or received emails into a persona or psychological/psychographic communication profile.
---

# MBOX to Persona

Use this skill when a user wants to analyze a Gmail/Takeout `.mbox` to generate a writing persona, text-style prompt, communication profile, or non-clinical psychological/psychographic profile.

Primary rule: sent emails are the target person's voice. Received emails are not voice data.

## Safety Boundary

- Confirm the user has rights/consent to analyze the mailbox.
- Use sent emails for writing style imitation and "who I am / how I write" persona extraction.
- Use received emails only as context around relationships, obligations, topics, and external pressures.
- Do not produce medical, psychiatric, or diagnostic claims.
- Do not infer protected traits.
- Redact private identifiers by default.
- If the target is a third party without consent, narrow the task to aggregate metadata or refuse invasive profiling.

## Workflow

1. Identify the target person.
   - Prefer explicit `--target-email`.
   - If not provided, infer from the most frequent sender and state that assumption.
2. Run the local CLI against the `.mbox`.
3. Generate persona outputs from `index.csv`.
4. Generate the non-clinical communication profile from `index.csv`.
5. Present only summary paths and key counts unless the user asks for details.

## Commands

From the repo root:

```bash
python -m mbox_to_persona.cli scan --mbox path/to/mail.mbox --out output --target-email user@example.com
python -m mbox_to_persona.cli persona --input output/index.csv --out output/persona
python -m mbox_to_persona.cli profile --input output/index.csv --out output/profile
python -m mbox_to_persona.cli export-prompt --persona output/persona/persona.json --out output/persona/style_prompt_export.md
```

Or use the bundled wrapper:

```bash
python skills/mbox-to-persona/scripts/run_mbox_to_persona.py --mbox path/to/mail.mbox --out output --target-email user@example.com
```

## Output Reading

- `persona/me_style_prompt.md`: the main reusable prompt for future AI text in the target person's style.
- `persona/persona.json`: structured style fingerprint.
- `persona/who_i_am_from_sent_email.md`: self-presentation summary from sent mail only.
- `persona/do_not_copy.md`: boundaries for safe use.
- `profile/psychological_profile.md`: non-clinical behavioral communication profile.
- `profile/evidence_table.csv`: redacted evidence references.
- `redaction_report.json`: counts, inferred target, and redaction status.
