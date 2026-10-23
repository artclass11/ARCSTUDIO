#!/usr/bin/env python3
"""Validate and package the complete daily ARCSTUDIO91 carousel + Reel deliverable."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "current"
PACK_DIR = ROOT / "output"

REQUIRED = [
    "slide_01.jpg", "slide_02.jpg", "slide_03.jpg", "slide_04.jpg",
    "slide_01.png", "slide_02.png", "slide_03.png", "slide_04.png",
    "preview_contact_sheet.jpg", "caption.txt", "sources.json", "concept.json",
    "research_notes.md", "reel.mp4", "reel_cover.jpg", "reel_caption.txt",
    "reel_script_marathi.txt", "reel_subtitles_mr.srt", "reel_manifest.json", "reel_ambient.wav",
    "reel_scene_01.png", "reel_scene_02.png", "reel_scene_03.png", "reel_scene_04.png", "reel_scene_05.png",
]

def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()

def validate_image(path: Path, expected: tuple[int, int]) -> None:
    with Image.open(path) as image:
        if image.size != expected:
            raise RuntimeError(f"Image QA failed for {path.name}: got {image.size}, expected {expected}.")
        image.verify()

def validate_video(path: Path) -> dict:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,r_frame_rate,codec_name",
         "-show_entries", "format=duration,size", "-of", "json", str(path)],
        check=True, capture_output=True, text=True, timeout=30
    )
    data = json.loads(probe.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    duration = float(data.get("format", {}).get("duration", 0))
    if not video or video.get("width") != 1080 or video.get("height") != 1920:
        raise RuntimeError("Reel QA failed: expected a 1080×1920 video stream.")
    if video.get("codec_name") != "h264":
        raise RuntimeError(f"Reel QA failed: expected H.264, got {video.get('codec_name')}.")
    if not audio:
        raise RuntimeError("Reel QA failed: expected the original ambient soundtrack.")
    if not 20 <= duration <= 30:
        raise RuntimeError(f"Reel QA failed: duration {duration:.2f}s is outside 20–30 seconds.")
    return {
        "width": video["width"], "height": video["height"], "fps": video.get("r_frame_rate"),
        "video_codec": video["codec_name"], "audio_codec": audio.get("codec_name"),
        "duration_seconds": round(duration, 2), "size_bytes": int(data.get("format", {}).get("size", 0)),
    }

def main() -> None:
    missing = [name for name in REQUIRED if not (OUT / name).is_file()]
    if missing:
        raise RuntimeError("Daily pack is incomplete; missing: " + ", ".join(missing))

    for i in range(1, 5):
        validate_image(OUT / f"slide_{i:02d}.jpg", (1080, 1350))
        validate_image(OUT / f"slide_{i:02d}.png", (1080, 1350))
    validate_image(OUT / "preview_contact_sheet.jpg", (888, 1090))
    validate_image(OUT / "reel_cover.jpg", (1080, 1920))
    video_meta = validate_video(OUT / "reel.mp4")

    source_data = json.loads((OUT / "sources.json").read_text(encoding="utf-8"))
    concept_data = json.loads((OUT / "concept.json").read_text(encoding="utf-8"))
    reel_data = json.loads((OUT / "reel_manifest.json").read_text(encoding="utf-8"))
    day = source_data["date"]
    if source_data.get("date") != reel_data.get("date"):
        raise RuntimeError("Pack QA failed: carousel and Reel dates do not match.")
    if concept_data.get("type") != source_data.get("concept"):
        raise RuntimeError("Pack QA failed: concept metadata is inconsistent.")

    posting_notes = (
        f"ARCSTUDIO91 DAILY CONTENT PACK — {source_data['date']}\n\n"
        f"Concept: {source_data['concept']}\n"
        f"Headline: {source_data['headline']}\n\n"
        "READY-TO-POST FILES\n"
        "- reel.mp4: vertical 1080×1920 H.264 MP4, approximately 25 seconds.\n"
        "- reel_cover.jpg: Reel cover / cover-picker image.\n"
        "- reel_caption.txt: copy/paste caption for the Reel.\n"
        "- reel_subtitles_mr.srt and reel_script_marathi.txt: accessible Marathi text and optional narration script.\n"
        "- slide_01.jpg through slide_04.jpg: four carousel slides, separately exported.\n"
        "- slide_01.png through slide_04.png: full-size PNG masters.\n"
        "- preview_contact_sheet.jpg: review sheet only; do not post it as a slide.\n\n"
        "AUDIO / LANGUAGE\n"
        "This version uses Marathi on-screen text and an original, low-volume ambient sound bed. It does not contain a synthetic spoken voiceover. The Marathi narration script is included separately; add a human or properly licensed natural voice if spoken narration is required.\n\n"
        "MEDIA / CLAIMS\n"
        "Inspect research_notes.md and sources.json for reference-photo attributions or confirmation that original concept artwork was used. Concept visuals are not completed projects. This pack is general educational content, not construction advice. Do not claim the content was published; verify Instagram after manual upload.\n\n"
        "INSTAGRAM UPLOAD\n"
        "1. Create a Reel and select reel.mp4.\n"
        "2. Choose reel_cover.jpg as the cover and check the crop.\n"
        "3. Paste reel_caption.txt; upload the .srt only if your publishing interface supports it, or use the on-screen Marathi text already embedded in the Reel.\n"
        "4. Review all four separate carousel slides before posting the carousel separately.\n"
    )
    (OUT / "POSTING_README.txt").write_text(posting_notes, encoding="utf-8")

    package_files = [
        p for p in sorted(OUT.iterdir())
        if p.is_file() and not p.name.startswith("_reel_source_")
    ]
    manifest = {
        "date": day,
        "brand": "@arcstudio91",
        "reel": video_meta,
        "files": [
            {"name": p.name, "size_bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in package_files
        ],
        "publish_status": "not published by this packaging step",
    }
    (OUT / "package_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Validated {len(package_files)} content files.")
    print(f"Reel: {video_meta['width']}×{video_meta['height']} / {video_meta['duration_seconds']}s.")
    print(f"Daily pack ready in {OUT}. GitHub Actions will bundle this directory as one download artifact.")

if __name__ == "__main__":
    main()
