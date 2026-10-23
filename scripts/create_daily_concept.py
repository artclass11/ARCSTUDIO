#!/usr/bin/env python3
"""Create the daily concept seed on GitHub Actions; AI visuals are rendered locally."""
from __future__ import annotations
import hashlib
import json
import os
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("ARCSTUDIO_OUTPUT_DIR", str(ROOT / "output" / "current"))).resolve()
DATA = ROOT / "data"
HISTORY = DATA / "concept_history.json"
sys.path.insert(0, str(ROOT / "scripts"))
import generate_daily as gd

def main() -> None:
    today = date.today()
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"concepts": []}
    except (OSError, ValueError):
        state = {"concepts": []}
    entries = state.get("concepts", [])
    today_record = next((entry for entry in reversed(entries) if entry.get("date") == today.isoformat()), None)
    indexed = {item.get("type"): item for item in gd.CONCEPTS}
    if today_record and today_record.get("type") in indexed:
        concept = indexed[today_record["type"]]
    else:
        recent = {entry.get("type") for entry in entries[-30:]}
        eligible = [item for item in gd.CONCEPTS if item.get("type") not in recent]
        if not eligible:
            eligible = gd.CONCEPTS
        concept = eligible[today.toordinal() % len(eligible)]
        entries.append({
            "date": today.isoformat(),
            "pillar": gd.editorial_pillar(concept),
            "type": concept["type"],
            "headline": concept["headline"],
            "insight": concept.get("comfort", ""),
            "visual_motif": concept.get("queries", [""])[0] if concept.get("queries") else "AI-generated architecture visual",
        })
        state["concepts"] = entries[-120:]
        HISTORY.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    concept_out = {
        "date": today.isoformat(),
        "type": concept["type"],
        "headline": concept["headline"],
        "headline_mr": concept.get("mr", ""),
        "original_idea": concept["idea"],
        "idea_mr": concept["idea_mr"],
        "comfort": concept["comfort"],
        "comfort_mr": concept["comfort_mr"],
        "life": concept["life"],
        "life_mr": concept["life_mr"],
        "materials": concept["materials"],
        "materials_mr": concept["materials_mr"],
        "visual_mode": "concept seed only; final visuals must be locally AI-generated",
    }
    (OUT / "concept.json").write_text(json.dumps(concept_out, ensure_ascii=False, indent=2), encoding="utf-8")
    seed_manifest = {
        "date": today.isoformat(),
        "type": concept["type"],
        "headline": concept["headline"],
        "editorial_pillar": gd.editorial_pillar(concept),
        "status": "concept seed only; NOT ready to post",
        "visual_generation_required": "Local inference with black-forest-labs/FLUX.1-schnell (Apache-2.0 model)",
        "paid_services_used": False,
    }
    (OUT / "cloud_source_manifest.json").write_text(json.dumps(seed_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    seed_files = ["concept.json", "cloud_source_manifest.json"]
    (OUT / "package_manifest.json").write_text(json.dumps({
        "date": today.isoformat(),
        "brand": "@arcstudio91",
        "status": "concept seed only; NOT ready to post",
        "files": [
            {
                "name": name,
                "size_bytes": (OUT / name).stat().st_size,
                "sha256": hashlib.sha256((OUT / name).read_bytes()).hexdigest(),
            } for name in seed_files
        ],
        "publish_status": "not published",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created concept seed for {today.isoformat()}: {concept['type']} — {concept['headline']}.")
    print("Final visual generation and ready-to-post QA must run locally through the open-weight AI model.")

if __name__ == "__main__":
    main()
