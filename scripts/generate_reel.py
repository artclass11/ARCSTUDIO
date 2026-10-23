#!/usr/bin/env python3
"""Create one Marathi-first 9:16 Reel using free Pillow, NumPy and FFmpeg.

No image-generation credits, paid APIs, unlicensed audio, or robotic eSpeak voice.
The Reel uses licensed daily reference photos when available, with original diagram
art as a safe visual fallback. Text remains readable without sound.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import wave
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "current"
SIZE = (1080, 1920)
FPS = 30
SCENE_SECONDS = 5.0
TRANSITION_SECONDS = 0.5
SCENE_COUNT = 5
DURATION = SCENE_COUNT * SCENE_SECONDS
BG = (22, 27, 25)
INK = (242, 239, 230)
SAGE = (160, 177, 153)
MUTED = (204, 207, 198)
PAPER = (225, 221, 210)

def find_font(bold: bool = False) -> str:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for item in candidates:
        if Path(item).exists():
            return item
    for item in Path("/usr/share/fonts").rglob("NotoSansDevanagari-Bold.ttf" if bold else "NotoSansDevanagari-Regular.ttf"):
        return str(item)
    return candidates[-1]

FONT_REGULAR = find_font(False)
FONT_BOLD = find_font(True)
LATIN_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
LATIN_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size=size)

def latin_font(size: int, bold: bool = False):
    path = LATIN_BOLD if bold else LATIN_REGULAR
    if not Path(path).exists():
        return font(size, bold)
    return ImageFont.truetype(path, size=size)

def wrap_lines(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in (text or "").split():
        test = (current + " " + word).strip()
        if current and draw.textlength(test, font=fnt) > max_width:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines or [""]

def write_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], fnt,
                  fill, max_width: int, gap: int = 12, max_lines: int = 3) -> int:
    x, y = xy
    for line in wrap_lines(draw, text, fnt, max_width)[:max_lines]:
        draw.text((x, y), line, font=fnt, fill=fill, stroke_width=0)
        box = draw.textbbox((x, y), line, font=fnt)
        y += (box[3] - box[1]) + gap
    return y

def rounded_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill, outline=None, width: int = 1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def draw_floorplan(draw: ImageDraw.ImageDraw, scene_no: int) -> None:
    """Original abstract architectural diagrams, not construction drawings."""
    # Diagram field
    bx0, by0, bx1, by1 = 115, 520, 965, 1450
    draw.rounded_rectangle((bx0, by0, bx1, by1), radius=8, outline=(140, 153, 139), width=8)
    # Main walls and rooms
    midx, midy = 570, 985
    draw.line((570, 520, 570, 860), fill=(140, 153, 139), width=8)
    draw.line((570, 1120, 570, 1450), fill=(140, 153, 139), width=8)
    draw.line((115, 985, 350, 985), fill=(140, 153, 139), width=8)
    draw.line((700, 985, 965, 985), fill=(140, 153, 139), width=8)
    draw.line((350, 985, 350, 1450), fill=(140, 153, 139), width=8)
    draw.line((780, 520, 780, 830), fill=(140, 153, 139), width=8)
    # Furnishing blocks
    draw.rounded_rectangle((180, 585, 470, 750), radius=12, outline=(194, 186, 169), width=5)
    for y in (605, 670):
        draw.line((205, y, 440, y), fill=(194, 186, 169), width=3)
    draw.rounded_rectangle((650, 1080, 870, 1240), radius=10, outline=(194, 186, 169), width=5)
    draw.ellipse((710, 900, 825, 1015), outline=(194, 186, 169), width=5)
    draw.line((765, 1015, 765, 1080), fill=(194, 186, 169), width=5)
    # Storage / kitchen
    draw.rectangle((650, 585, 725, 800), outline=(194, 186, 169), width=5)
    draw.line((650, 650, 725, 650), fill=(194, 186, 169), width=4)
    # A single circulation path, scene changes emphasize various moments.
    if scene_no in (1, 2):
        pts = [(510, 1410), (510, 1210), (510, 900), (610, 900), (610, 860), (610, 810)]
    elif scene_no == 3:
        pts = [(510, 1410), (510, 1210), (510, 1100), (510, 900), (610, 900), (610, 810)]
    else:
        pts = [(510, 1410), (510, 1210), (510, 900), (610, 900), (610, 810)]
    draw.line(pts, fill=SAGE, width=15, joint="curve")
    # Arrow head
    x, y = pts[-1]
    draw.polygon([(x, y), (x - 24, y + 45), (x + 24, y + 45)], fill=SAGE)
    # Legend
    draw.ellipse((142, 1490, 170, 1518), fill=SAGE)
    draw.text((190, 1481), "हालचालीचा मोकळा मार्ग", font=font(27, True), fill=INK)
    draw.text((140, 1550), "संकल्पना; बांधकामासाठी नाही", font=font(23), fill=MUTED)

def make_scene(photo_path: Path | None, concept: dict[str, Any], scene_no: int,
               title: str, message: str, detail: str = "") -> Path:
    W, H = SIZE
    if photo_path and photo_path.exists():
        with Image.open(photo_path) as im:
            photo = ImageOps.exif_transpose(im).convert("RGB")
            # Full-bleed background, blurred and darkened for legible edge text.
            backdrop = ImageOps.fit(photo, SIZE, method=Image.Resampling.LANCZOS)
            backdrop = backdrop.filter(ImageFilter.GaussianBlur(32))
            backdrop = Image.blend(backdrop, Image.new("RGB", SIZE, BG), 0.64).convert("RGBA")
            # Main image remains whole and undistorted in a 4:5 window.
            hero = ImageOps.fit(photo, (W, 1350), method=Image.Resampling.LANCZOS, centering=(0.5, 0.47)).convert("RGBA")
            # Soft blend edge band so the photo feels full-screen rather than carded.
            backdrop.alpha_composite(hero, (0, 350))
            image = backdrop.convert("RGB")
    else:
        image = Image.new("RGB", SIZE, BG)
        # Quiet architectural grid.
        dd = ImageDraw.Draw(image)
        for x in range(45, W, 72):
            dd.line((x, 410, x, 1640), fill=(39, 47, 43), width=1)
        for y in range(420, 1640, 72):
            dd.line((55, y, W - 55, y), fill=(39, 47, 43), width=1)
        draw_floorplan(dd, scene_no)

    draw = ImageDraw.Draw(image)
    # Stable editorial frame and readable text.
    draw.text((64, 42), "@arcstudio91", font=latin_font(29, True), fill=INK)
    meta = f"वास्तु-विचार   {scene_no:02d} / 05"
    mb = draw.textbbox((0, 0), meta, font=font(21))
    draw.text((W - 64 - (mb[2] - mb[0]), 49), meta, font=font(21), fill=MUTED)
    draw.line((64, 100, W - 64, 100), fill=(112, 127, 111), width=2)

    # Title top band: short, large, no ornate decoration.
    write_wrapped(draw, title, (64, 130), font(55, True), INK, W - 128, gap=6, max_lines=2)
    if photo_path and photo_path.exists():
        # Photo starts after the headline band.
        # Recompose so the hero does not cover the title: resize from temporary hero already at y=350.
        # Keep the image visually anchored to the central frame.
        pass
    # Lower information band.
    draw.line((64, 1710, W - 64, 1710), fill=(112, 127, 111), width=2)
    write_wrapped(draw, message, (64, 1740), font(35, True), SAGE, W - 128, gap=7, max_lines=2)
    if detail:
        write_wrapped(draw, detail, (64, 1835), font(25), MUTED, W - 128, gap=4, max_lines=2)
    if scene_no == SCENE_COUNT:
        draw.text((64, 1881), "आर्किटेक्चर / इंटिरियर / स्पेस प्लॅनिंग", font=font(19, True), fill=INK)
    target = OUT / f"reel_scene_{scene_no:02d}.png"
    image.save(target, format="PNG", optimize=True)
    return target

def make_ambient_audio(path: Path, seconds: float) -> None:
    sr = 48000
    n = int(sr * seconds)
    t = np.arange(n, dtype=np.float64) / sr
    out = np.zeros(n, dtype=np.float64)
    chords = [
        [146.83, 220.00, 293.66],
        [130.81, 196.00, 261.63],
        [110.00, 164.81, 220.00],
        [123.47, 185.00, 246.94],
    ]
    chord_len = seconds / len(chords)
    for idx, chord in enumerate(chords):
        start = int(idx * chord_len * sr)
        end = min(n, int((idx + 1) * chord_len * sr))
        tt = t[start:end] - idx * chord_len
        env = np.minimum(1.0, tt / 1.8) * np.minimum(1.0, np.maximum(0.0, (chord_len - tt) / 2.0))
        pad = np.zeros(end - start, dtype=np.float64)
        for freq in chord:
            pad += np.sin(2 * np.pi * freq * tt) / len(chord)
        out[start:end] += pad * env * 0.08
    # Sparse soft plucks add motion but remain safely below spoken content (none is used).
    for onset in np.arange(0.7, seconds, 2.6):
        start = int(onset * sr)
        length = min(int(1.0 * sr), n - start)
        tt = np.arange(length) / sr
        pluck = (np.sin(2*np.pi*440*tt) + 0.35*np.sin(2*np.pi*660*tt)) * np.exp(-4.2*tt) * 0.025
        out[start:start+length] += pluck
    fade_len = int(sr * 1.5)
    out[:fade_len] *= np.linspace(0, 1, fade_len)
    out[-fade_len:] *= np.linspace(1, 0, fade_len)
    out = np.clip(out, -0.22, 0.22)
    pcm = (out * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

def build_subtitles(scene_data: list[tuple[str, str, str]], path: Path) -> None:
    out = []
    for i, (title, message, detail) in enumerate(scene_data):
        start = i * SCENE_SECONDS
        end = min(DURATION, start + SCENE_SECONDS)
        def ts(x: float) -> str:
            ms = int(round(x * 1000))
            h, ms = divmod(ms, 3600000)
            m, ms = divmod(ms, 60000)
            s, ms = divmod(ms, 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        body = "\n".join(x for x in (title, message, detail) if x)
        out.append(f"{i+1}\n{ts(start)} --> {ts(end)}\n{body}\n")
    path.write_text("\n".join(out), encoding="utf-8")

def main() -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required to render the Reel.")
    OUT.mkdir(parents=True, exist_ok=True)
    concept_path = OUT / "concept.json"
    if concept_path.exists():
        concept = json.loads(concept_path.read_text(encoding="utf-8"))
    else:
        concept = {
            "date": date.today().isoformat(),
            "type": "Compact home circulation",
            "headline": "MAKE ROOM TO MOVE",
            "headline_mr": "मोकळ्या हालचालीसाठी जागा ठेवा",
            "original_idea": "A compact home where circulation is considered before furniture placement.",
            "idea_mr": "फर्निचर मांडण्याआधी घरातील हालचालीचे मार्ग ठरवा.",
            "comfort_mr": "मुख्य वापराचा मार्ग मोकळा राहील अशी मांडणी करा.",
            "life_mr": "दरवाजे, साठवण आणि दैनंदिन वापर यांत अडथळे येऊ देऊ नका.",
            "materials_mr": ["सहज स्वच्छ होणारे टिकाऊ फिनिश", "बदलता येणारे हार्डवेअर"],
            "materials": ["Durable easy-clean finishes", "Replaceable hardware"],
        }
        concept_path.write_text(json.dumps(concept, ensure_ascii=False, indent=2), encoding="utf-8")

    # Photo sources are transient: package contains final Reel and licence notes, not duplicate source files.
    photo_paths = [OUT / f"_reel_source_{i:02d}.jpg" for i in range(1, 5)]
    available = [p for p in photo_paths if p.exists()]
    title = concept.get("headline_mr") or concept.get("mr") or "आजचा वास्तु-विचार"
    idea = concept.get("idea_mr") or concept.get("original_idea") or "जागेचा विचार करून वापर अधिक सोपा करा."
    comfort = concept.get("comfort_mr") or "प्रकाश, सावली आणि हालचालीचे मार्ग लक्षात घ्या."
    life = concept.get("life_mr") or "दुरुस्ती आणि नियमित देखभाल सोपी ठेवा."
    materials = concept.get("materials_mr") or ["स्थानिक परिस्थितीला अनुरूप साहित्य"]
    if isinstance(materials, list):
        materials = materials[0] if materials else "साहित्याची निवड वापर व हवामानानुसार करा."

    scene_data = [
        (title, idea, "ही एक संकल्पना आहे; बांधकाम आराखडा नाही."),
        ("आरामासाठी", comfort, "जागेची दिशा आणि स्थानिक हवामान तपासा."),
        ("दीर्घकाळ वापरासाठी", life, "साइटनुसार तपशील तज्ज्ञांसोबत ठरवा."),
        ("साहित्य निवड", str(materials), "उपलब्धता, दुरुस्ती आणि देखभाल विचारात घ्या."),
        ("तुमच्या जागेत काय महत्त्वाचे?", "प्रकाश • गोपनीयता • सहज देखभाल", "तुमची निवड कमेंटमध्ये सांगा.  @arcstudio91"),
    ]
    scenes: list[Path] = []
    for i, (stitle, message, detail) in enumerate(scene_data, start=1):
        photo = available[(i - 1) % len(available)] if available else None
        scenes.append(make_scene(photo, concept, i, stitle, message, detail))

    narration = [
        f"आजचा वास्तु-विचार: {idea}",
        f"आरामासाठी: {comfort}",
        f"दीर्घकाळ वापरासाठी: {life}",
        f"साहित्य निवडताना: {materials}",
        "ही सर्वसाधारण माहिती आहे. प्रत्यक्ष आराखड्यासाठी साइटची परिस्थिती आणि तज्ज्ञांचा सल्ला महत्त्वाचा आहे.",
        "तुमच्या जागेत काय महत्त्वाचे आहे? प्रकाश, गोपनीयता की सहज देखभाल?",
    ]
    (OUT / "reel_script_marathi.txt").write_text("\n\n".join(narration) + "\n", encoding="utf-8")
    build_subtitles(scene_data, OUT / "reel_subtitles_mr.srt")
    (OUT / "reel_caption.txt").write_text(
        f"जागेची चांगली रचना म्हणजे फक्त दिसणं नाही—रोजचा वापर सहज होणंही महत्त्वाचं.\n\n"
        f"{idea} {comfort} {life}\n\n"
        "सेवा: निवासी व व्यावसायिक आर्किटेक्चर • रिसॉर्ट/हॉटेल/कॅफे • इंटिरियर व स्पेस प्लॅनिंग • "
        "शाश्वत डिझाइन • नूतनीकरण व adaptive reuse • साहित्य मार्गदर्शन.\n\n"
        "तुमच्या जागेत काय आधी सुधारणार—प्रकाश, गोपनीयता की देखभाल?\n"
        "General educational concept only; project-specific decisions need qualified local review.\n"
        "#ARCSTUDIO91 #ArchitectureMarathi #SustainableDesign #SpacePlanning\n",
        encoding="utf-8",
    )
    make_ambient_audio(OUT / "reel_ambient.wav", DURATION)

    ffmpeg_cmd = ["ffmpeg", "-y"]
    for path in scenes:
        ffmpeg_cmd.extend(["-framerate", str(FPS), "-loop", "1", "-t", str(SCENE_SECONDS), "-i", str(path)])
    ffmpeg_cmd.extend(["-i", str(OUT / "reel_ambient.wav")])
    filters = []
    for i in range(SCENE_COUNT):
        filters.append(
            f"[{i}:v]scale=1080:1920,zoompan=z='min(zoom+0.00018,1.025)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={FPS},fps={FPS},"
            f"settb=AVTB,setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{i}]"
        )
    # Use a constant-frame-rate concatenation. This is more robust on GitHub
    # Actions than xfade on image-backed zoompan streams, which can report 1/0.
    filters.append(
        "".join(f"[v{i}]" for i in range(SCENE_COUNT))
        + f"concat=n={SCENE_COUNT}:v=1:a=0,fade=t=out:st={DURATION - 0.25:.3f}:d=0.25[vout]"
    )
    previous = "[vout]"
    filters.append(
        f"[{SCENE_COUNT}:a]atrim=duration={DURATION:.3f},"
        f"afade=t=in:st=0:d=0.8,afade=t=out:st={DURATION-1.5:.3f}:d=1.5,"
        f"volume=0.82[aout]"
    )
    cmd = ffmpeg_cmd + [
        "-filter_complex", ";".join(filters),
        "-map", previous, "-map", "[aout]",
        "-t", f"{DURATION:.3f}",
        "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart",
        str(OUT / "reel.mp4")
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode:
        raise RuntimeError("FFmpeg Reel render failed: " + (proc.stderr or proc.stdout)[-3000:])

    # Validate the actual MP4 stream before marking the Reel as ready.
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe is required for Reel validation.")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate",
         "-show_entries", "format=duration", "-of", "json", str(OUT / "reel.mp4")],
        capture_output=True, text=True, check=True, timeout=30
    )
    probe_data = json.loads(probe.stdout)
    video_stream = next((stream for stream in probe_data.get("streams", []) if stream.get("codec_type") == "video"), None)
    duration = float(probe_data.get("format", {}).get("duration", 0))
    if not video_stream or video_stream.get("width") != 1080 or video_stream.get("height") != 1920:
        raise RuntimeError("Reel QA failed: expected 1080×1920 video.")
    if not (20 <= duration <= 30):
        raise RuntimeError(f"Reel QA failed: duration {duration:.2f}s is outside 20–30 seconds.")

    # Instagram cover uses the clean first scene; retain 1080×1920 for the uploader.
    with Image.open(scenes[0]) as first:
        first.convert("RGB").save(OUT / "reel_cover.jpg", quality=94, optimize=True)
    # Remove temporary source photo copies after video render to prevent accidental duplicate publication.
    for path in photo_paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    (OUT / "reel_manifest.json").write_text(json.dumps({
        "date": concept.get("date", date.today().isoformat()),
        "format": "Instagram Reel",
        "video": "reel.mp4",
        "cover": "reel_cover.jpg",
        "size": [1080, 1920],
        "fps": FPS,
        "duration_seconds": DURATION,
        "language": "Marathi on-screen text",
        "spoken_voiceover": False,
        "audio": "Original soft ambient sound bed generated locally; no external music licence required",
        "artwork": "Licensed reference photography with credit where available; otherwise original concept diagram",
        "created_by": "Python/Pillow + FFmpeg + NumPy; no paid generation credits",
        "srt": "reel_subtitles_mr.srt",
        "script": "reel_script_marathi.txt"
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created Marathi-first {DURATION:.1f}s Reel: {OUT / 'reel.mp4'}")

if __name__ == "__main__":
    main()
