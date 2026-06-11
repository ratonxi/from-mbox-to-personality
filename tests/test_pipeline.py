import csv
import json
from pathlib import Path

from mbox_to_persona.ingest import scan_mbox
from mbox_to_persona.graphs import generate_graphs
from mbox_to_persona.persona import generate_persona
from mbox_to_persona.psych_profile import generate_profile


FIXTURE = Path(__file__).parent / "fixtures" / "sample.mbox"


def test_scan_classifies_and_redacts(tmp_path):
    report = scan_mbox(FIXTURE, tmp_path, ["andres@example.com"])
    assert report["messages_indexed"] == 3
    assert report["sent_by_target"] == 2
    assert report["received_by_target"] == 1

    rows = list(csv.DictReader((tmp_path / "index.csv").open(encoding="utf-8")))
    assert {r["classification"] for r in rows} == {"sent_by_target", "received_by_target"}
    assert all("+34 600" not in r["redacted_excerpt"] for r in rows)
    assert (tmp_path / "sent_corpus" / "sent_redacted.jsonl").exists()


def test_persona_and_profile_outputs(tmp_path):
    scan_mbox(FIXTURE, tmp_path, ["andres@example.com"])
    persona = generate_persona(tmp_path / "index.csv", tmp_path / "persona")
    profile = generate_profile(tmp_path / "index.csv", tmp_path / "profile")

    assert persona["message_count"] == 2
    assert (tmp_path / "persona" / "style_prompt.md").exists()
    assert profile["sent_count"] == 2
    assert (tmp_path / "profile" / "psychological_profile.md").exists()
    loaded = json.loads((tmp_path / "persona" / "persona.json").read_text(encoding="utf-8"))
    assert loaded["safety_note"]


def test_graph_outputs_include_social_cards(tmp_path):
    scan_mbox(FIXTURE, tmp_path, ["andres@example.com"])
    generate_persona(tmp_path / "index.csv", tmp_path / "persona")
    generate_graphs(tmp_path / "index.csv", tmp_path / "graphs", tmp_path / "persona" / "persona.json")

    assert (tmp_path / "graphs" / "communication_radar.svg").exists()
    assert (tmp_path / "graphs" / "communication_social_card.svg").exists()
    assert (tmp_path / "graphs" / "broad_behavior_radar.svg").exists()
    assert (tmp_path / "graphs" / "broad_behavior_social_card.svg").exists()
