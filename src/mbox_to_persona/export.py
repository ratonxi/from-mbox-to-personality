import json
from pathlib import Path

from .persona import build_style_prompt


def export_prompt(persona_path: Path, out_path: Path) -> None:
    persona = json.loads(persona_path.read_text(encoding="utf-8"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_style_prompt(persona), encoding="utf-8")

