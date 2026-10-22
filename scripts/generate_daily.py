#!/usr/bin/env python3
"""Generate one minimal, original ARCSTUDIO91 four-slide carousel using licensed Commons photos."""

from __future__ import annotations

import html
import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "current"
DATA = ROOT / "data"
HISTORY_PATH = DATA / "image_history.json"
CONCEPT_HISTORY_PATH = DATA / "concept_history.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {
    "User-Agent": "ARCSTUDIO91DailyPublisher/1.0 (https://github.com/artclass11/ARCSTUDIO; architecture inspiration and attribution)"
}
SIZE = (1080, 1350)

# Each entry is an original practical idea. Reference photos illustrate a subject;
# they are not presented as ARCSTUDIO91's built work.
CONCEPTS: list[dict[str, Any]] = [
    {
        "type": "Courtyard home", "headline": "SHADE BEFORE GLASS", "mr": "काचेआधी सावली",
        "idea": "A compact courtyard home where shade makes the outdoor room useful.",
        "idea_mr": "सावलीमुळे अंगण रोजच्या वापरात येईल असे छोटे घर.",
        "comfort": "Plan shade before choosing glass.", "comfort_mr": "काच निवडण्याआधी सावलीचे नियोजन करा.",
        "life": "Keep rain out. Keep repairs simple.", "life_mr": "पाणी साचू देऊ नका. दुरुस्ती सोपी ठेवा.",
        "materials": ["Locally available brick or stone", "Weather-suitable mineral / lime finish", "Accessible, replaceable rainwater details"],
        "materials_mr": ["स्थानिक विटा किंवा दगड", "हवामानाला अनुरूप मिनरल / चुन्याचा फिनिश", "सहज बदलता येणारे पावसाच्या पाण्याचे तपशील"],
        "queries": ["courtyard house architecture", "external shading residential architecture", "residential entrance canopy architecture", "brick stone lime plaster building detail"],
    },
    {
        "type": "Tropical cafe", "headline": "LET AIR DO THE WORK", "mr": "हवेला वाट द्या",
        "idea": "A small cafe arranged around cross-ventilation and a shaded waiting edge.",
        "idea_mr": "नैसर्गिक वायुवीजन आणि सावलीची प्रतीक्षा-जागा असलेले छोटे कॅफे.",
        "comfort": "Place openings to move air across the room.", "comfort_mr": "खोलीतून हवा वाहील अशा ठिकाणी खिडक्या ठेवा.",
        "life": "Use washable finishes where hands and rain reach.", "life_mr": "स्पर्श आणि पावसाचा संपर्क असलेल्या भागात सहज स्वच्छ होणारे फिनिश वापरा.",
        "materials": ["Locally sourced masonry", "Non-slip, easy-clean floor", "Shaded, repairable joinery"],
        "materials_mr": ["स्थानिक बांधकाम साहित्य", "न घसरणारा, सहज स्वच्छ होणारा मजला", "सावलीतील दुरुस्त करता येणारे जॉइनरी तपशील"],
        "queries": ["tropical cafe architecture", "shaded veranda restaurant architecture", "cafe entrance architecture", "brick timber stone architecture detail"],
    },
    {
        "type": "Small office", "headline": "LESS GLASS. MORE COMFORT.", "mr": "काच कमी. आराम अधिक.",
        "idea": "A low-energy office with daylight, controlled glare and a simple service spine.",
        "idea_mr": "नैसर्गिक प्रकाश, कमी झगमगाट आणि सोपी सेवा-रचना असलेले कार्यालय.",
        "comfort": "Let daylight in without inviting glare.", "comfort_mr": "डोळ्यांना झगमगाट न होता नैसर्गिक प्रकाश येऊ द्या.",
        "life": "Keep pipes, wiring and filters reachable.", "life_mr": "पाईप, वायरिंग आणि फिल्टर सहज तपासता येतील असे ठेवा.",
        "materials": ["Durable local wall finish", "Shading suited to the sun path", "Service access panels"],
        "materials_mr": ["टिकाऊ स्थानिक भिंत-फिनिश", "सूर्याच्या दिशेनुसार सावलीची रचना", "सेवा तपासण्यासाठी सहज उघडणारे पॅनेल"],
        "queries": ["courtyard office building architecture", "office external sun shading", "office entrance architecture", "commercial building facade detail"],
    },
    {
        "type": "Compact apartment", "headline": "MAKE SPACE WORK", "mr": "जागेचा योग्य वापर",
        "idea": "A compact apartment plan with clear circulation and flexible shared space.",
        "idea_mr": "मोकळी हालचाल आणि बदलता वापर असलेला कॉम्पॅक्ट अपार्टमेंट आराखडा.",
        "comfort": "Keep circulation clear; make storage part of the plan.", "comfort_mr": "हालचालीची जागा मोकळी ठेवा; साठवण आराखड्यातच ठेवा.",
        "life": "Protect wet areas and keep access panels visible.", "life_mr": "ओलसर भागांचे संरक्षण करा आणि तपासणीची पॅनेल्स सहज दिसतील अशी ठेवा.",
        "materials": ["Robust, replaceable floor finish", "Moisture-rated wet-area system", "Standard-size hardware"],
        "materials_mr": ["टिकाऊ व बदलता येणारा फ्लोअर फिनिश", "ओलाव्याला अनुरूप वेट-एरिया प्रणाली", "सहज मिळणारे स्टँडर्ड हार्डवेअर"],
        "queries": ["apartment courtyard architecture", "apartment balcony shade architecture", "apartment entrance architecture", "durable apartment exterior materials"],
    },
    {
        "type": "Small resort", "headline": "FOLLOW THE LAND", "mr": "जमिनीशी जुळवून घ्या",
        "idea": "A low-rise resort that follows the site instead of over-cutting it.",
        "idea_mr": "जमिनीचा अनावश्यक कटाव टाळणारे कमी उंचीचे रिसॉर्ट.",
        "comfort": "Use shade and planted edges along outdoor routes.", "comfort_mr": "बाहेरील वाटांवर सावली आणि हिरवळ नियोजित करा.",
        "life": "Drain water away from foundations and paths.", "life_mr": "पायाभरणी आणि वाटांपासून पाणी दूर वाहील असे नियोजन करा.",
        "materials": ["Site-appropriate local stone", "Weather-rated exterior finish", "Replaceable walkway components"],
        "materials_mr": ["जागेला अनुरूप स्थानिक दगड", "हवामान सहन करणारा बाह्य फिनिश", "बदलता येणारे पायवाटेचे घटक"],
        "queries": ["low rise eco resort architecture", "shaded resort veranda architecture", "landscape resort walkway", "local stone timber architecture detail"],
    },
    {
        "type": "Neighbourhood clinic", "headline": "MAKE THE ROUTE CLEAR", "mr": "वाट स्पष्ट ठेवा",
        "idea": "A small clinic with an obvious entrance, step-free access and calm waiting space.",
        "idea_mr": "स्पष्ट प्रवेश, अडथळारहित मार्ग आणि शांत प्रतीक्षा-जागा असलेले दवाखाना डिझाइन.",
        "comfort": "Give visitors one clear route from entry to reception.", "comfort_mr": "प्रवेशापासून रिसेप्शनपर्यंत एक स्पष्ट मार्ग ठेवा.",
        "life": "Choose surfaces that can be cleaned and repaired.", "life_mr": "स्वच्छ आणि दुरुस्त करता येतील असे पृष्ठभाग निवडा.",
        "materials": ["Non-slip floor with suitable rating", "Cleanable wall finish", "Protected, accessible service runs"],
        "materials_mr": ["योग्य घसरण-प्रतिरोध असलेला मजला", "सहज स्वच्छ होणारा भिंत-फिनिश", "संरक्षित व सहज पोहोचता येणाऱ्या सेवा-लाईन्स"],
        "queries": ["small clinic architecture entrance", "healthcare daylight waiting room", "clinic accessible entrance building", "easy clean durable building materials"],
    },
    {
        "type": "Adaptive-reuse shop", "headline": "KEEP WHAT STILL WORKS", "mr": "जे उपयोगी आहे ते जपा",
        "idea": "A small shop that reuses sound structure and upgrades only what fails.",
        "idea_mr": "मजबूत रचना जपून आवश्यक भागच सुधारण्याची दुकानाची कल्पना.",
        "comfort": "Reuse the useful shell before adding new area.", "comfort_mr": "नवीन जागा वाढवण्याआधी उपयोगी विद्यमान रचना जपा.",
        "life": "Inspect first; replace only what needs replacement.", "life_mr": "आधी तपासणी करा; आवश्यक तेवढेच बदला.",
        "materials": ["Salvaged materials after inspection", "Compatible repair mortar", "Standard replaceable fittings"],
        "materials_mr": ["तपासणीनंतर वापरलेले पुनर्वापर साहित्य", "जुन्या बांधकामाशी सुसंगत दुरुस्ती मोर्टार", "सहज बदलता येणारे फिटिंग्स"],
        "queries": ["adaptive reuse shop architecture", "renovated commercial building facade", "adaptive reuse entrance architecture", "reclaimed brick timber building detail"],
    },
    {
        "type": "Shaded walkway", "headline": "SHADE THE WALK", "mr": "वाटेला सावली द्या",
        "idea": "A resort or campus route that stays comfortable between buildings.",
        "idea_mr": "इमारतींमधील चालण्याचा मार्ग सावलीत आणि सोयीचा ठेवण्याची कल्पना.",
        "comfort": "Connect useful destinations with a continuous shaded path.", "comfort_mr": "महत्त्वाच्या जागा सलग सावलीच्या मार्गाने जोडा.",
        "life": "Use drainage details that stay visible and serviceable.", "life_mr": "निचऱ्याचे तपशील दिसतील आणि दुरुस्त होतील असे ठेवा.",
        "materials": ["Locally available paving", "Durable shaded canopy", "Replaceable drainage grates"],
        "materials_mr": ["स्थानिक पॅव्हिंग", "टिकाऊ सावलीचे कॅनोपी", "बदलता येणाऱ्या ड्रेनेज जाळ्या"],
        "queries": ["shaded pedestrian walkway architecture", "covered campus walkway", "resort path canopy architecture", "paving drainage detail landscape"],
    },
    {
        "type": "Learning studio", "headline": "LIGHT FROM TWO SIDES", "mr": "दोन बाजूंनी प्रकाश",
        "idea": "A learning studio with balanced daylight and clear sightlines.",
        "idea_mr": "समतोल नैसर्गिक प्रकाश आणि स्पष्ट दृश्यरेषा असलेला अभ्यास-स्टुडिओ.",
        "comfort": "Use daylight from more than one direction where the site allows.", "comfort_mr": "जागेनुसार एकापेक्षा जास्त दिशांनी नैसर्गिक प्रकाश आणा.",
        "life": "Keep finishes robust and fixtures easy to replace.", "life_mr": "फिनिश टिकाऊ आणि फिटिंग्स सहज बदलता येतील असे ठेवा.",
        "materials": ["Durable wall finish", "Low-glare daylight control", "Standard serviceable fittings"],
        "materials_mr": ["टिकाऊ भिंत-फिनिश", "झगमगाट कमी करणारे प्रकाश-नियोजन", "सहज दुरुस्त होणारे स्टँडर्ड फिटिंग्स"],
        "queries": ["school studio architecture daylight", "classroom natural light architecture", "educational building corridor", "durable wall floor material architecture"],
    },
    {
        "type": "Community pavilion", "headline": "ONE ROOF. MANY USES.", "mr": "एक छप्पर. अनेक उपयोग.",
        "idea": "A simple covered pavilion that can host daily activity and community events.",
        "idea_mr": "दैनंदिन वापर आणि सामुदायिक कार्यक्रमांसाठी सोपे आच्छादित मंडप.",
        "comfort": "Prioritise shade, airflow and flexible seating.", "comfort_mr": "सावली, हवा आणि बदलता आसन-वापर यांना प्राधान्य द्या.",
        "life": "Choose a roof system with reachable, replaceable parts.", "life_mr": "सहज पोहोचून बदलता येणारे छताचे घटक निवडा.",
        "materials": ["Locally sourced structure", "Weather-appropriate roof system", "Replaceable fasteners and gutters"],
        "materials_mr": ["स्थानिक संरचनात्मक साहित्य", "हवामानाला अनुरूप छत प्रणाली", "बदलता येणारे फास्टनर्स आणि गटर्स"],
        "queries": ["community pavilion architecture roof", "open pavilion courtyard architecture", "covered public seating architecture", "roof gutter connection construction detail"],
    },
    {
        "type": "Restaurant", "headline": "RAIN SHOULD LEAVE FAST", "mr": "पावसाचे पाणी लगेच वाहू द्या",
        "idea": "A restaurant entry and dining edge designed around monsoon movement.",
        "idea_mr": "पावसाळ्यातील हालचाल लक्षात घेऊन नियोजित रेस्टॉरंट प्रवेश आणि बाहेरील आसन-जागा.",
        "comfort": "Keep entry, seating and service routes dry and legible.", "comfort_mr": "प्रवेश, आसन-जागा आणि सेवा-मार्ग कोरडे व स्पष्ट ठेवा.",
        "life": "Slope surfaces correctly and keep drains accessible.", "life_mr": "पृष्ठभागांना योग्य उतार द्या आणि ड्रेनेज सहज तपासता येईल असे ठेवा.",
        "materials": ["Non-slip exterior paving", "Rain-screen or protected wall detail", "Serviceable roof drainage"],
        "materials_mr": ["न घसरणारे बाह्य पॅव्हिंग", "संरक्षित भिंत-तपशील", "दुरुस्त करता येणारा छताचा निचरा"],
        "queries": ["restaurant entrance monsoon architecture", "covered restaurant outdoor seating", "restaurant veranda building", "exterior non slip paving drainage"],
    },
    {
        "type": "Work-live building", "headline": "GROW WITHOUT REBUILDING", "mr": "पुन्हा न बांधता वाढवा",
        "idea": "A small mixed-use building with a flexible ground floor and serviceable upper levels.",
        "idea_mr": "बदलता तळमजला आणि सोपी देखभाल असलेली मिश्र-वापर इमारत.",
        "comfort": "Plan for change before partitions become permanent.", "comfort_mr": "पार्टिशन्स कायमस्वरूपी करण्याआधी भविष्यातील बदलांचा विचार करा.",
        "life": "Separate service access from everyday circulation.", "life_mr": "सेवा-देखभालीचा मार्ग दैनंदिन हालचालीपासून वेगळा ठेवा.",
        "materials": ["Modular, repairable partitions", "Standard-sized doors and fittings", "Weather-resistant exterior finish"],
        "materials_mr": ["मॉड्युलर व दुरुस्त होणारे पार्टिशन्स", "स्टँडर्ड आकाराचे दरवाजे व फिटिंग्स", "हवामान-प्रतिरोधक बाह्य फिनिश"],
        "queries": ["mixed use building architecture", "flexible retail office ground floor", "mixed use building entrance", "modular partition architecture detail"],
    },
]


# Extra ideas live in a data file so new concepts can be added without rebuilding the renderer.
EXTRA_IDEAS_PATH = DATA / "extra_ideas.json"
if EXTRA_IDEAS_PATH.exists():
    try:
        extra_ideas = json.loads(EXTRA_IDEAS_PATH.read_text(encoding="utf-8"))
        if isinstance(extra_ideas, list):
            CONCEPTS.extend(extra_ideas)
    except (OSError, ValueError) as exc:
        print(f"Could not load extra idea file: {exc}")

GENERIC_QUERIES = [
    "modern architecture building exterior photograph",
    "shaded outdoor architecture building",
    "building entrance canopy architectural photograph",
    "brick stone timber building material detail",
]

def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

def font_path(filename: str) -> str:
    for path in Path("/usr/share/fonts").rglob(filename):
        return str(path)
    try:
        result = subprocess.run(["fc-match", "-f", "%{file}", "Noto Sans Devanagari"],
                                capture_output=True, text=True, check=False, timeout=5)
        if result.stdout.strip() and Path(result.stdout.strip()).is_file():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

REGULAR_FONT = font_path("NotoSansDevanagari-Regular.ttf")
BOLD_FONT = font_path("NotoSansDevanagari-Bold.ttf")

def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(BOLD_FONT if bold else REGULAR_FONT, size=size)
    except OSError:
        return ImageFont.load_default()

def wrap_text(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if current and draw.textlength(trial, font=selected_font) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines

def text_block(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, selected_font: ImageFont.FreeTypeFont,
               max_width: int, fill: tuple[int, int, int, int], spacing: int = 8, max_lines: int = 3) -> int:
    lines = wrap_text(draw, text, selected_font, max_width)[:max_lines]
    ascent, descent = selected_font.getmetrics()
    for line in lines:
        draw.text((x, y), line, font=selected_font, fill=fill)
        y += ascent + descent + spacing
    return y

def darken_photo(source: Image.Image) -> Image.Image:
    base = source.convert("RGBA")
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    start = int(SIZE[1] * 0.35)
    for y in range(SIZE[1]):
        if y < 150:
            alpha = int(120 * (1 - y / 150))
        elif y < start:
            alpha = 0
        else:
            alpha = int(225 * ((y - start) / max(1, SIZE[1] - start)))
        if alpha:
            draw.line((0, y, SIZE[0], y), fill=(0, 0, 0, min(225, alpha)))
    return Image.alpha_composite(base, overlay).convert("RGB")

def commons_candidates(query: str) -> list[dict[str, Any]]:
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6, "gsrlimit": 50,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1800,
    }
    response = requests.get(COMMONS_API, params=params, headers=HEADERS, timeout=35)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    results: list[dict[str, Any]] = []
    for page in pages.values():
        info_list = page.get("imageinfo", [])
        if not info_list:
            continue
        info = info_list[0]
        meta = info.get("extmetadata", {})
        licence = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
        lower = licence.lower()
        reusable = ("public domain" in lower or "cc0" in lower or
                    ("cc by" in lower and "nc" not in lower and "nd" not in lower))
        if not reusable or info.get("mime") not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        url = info.get("thumburl") or info.get("url")
        if not url or not str(url).startswith("https://"):
            continue
        title = page.get("title", "Unknown file").removeprefix("File:")
        artist = (strip_html(meta.get("Artist", {}).get("value", "")) or
                  strip_html(meta.get("Credit", {}).get("value", "")) or "Author not stated")
        source_page = "https://commons.wikimedia.org/wiki/File:" + quote(title.replace(" ", "_"), safe="()_'-,.")
        results.append({
            "title": title, "url": url, "license": licence,
            "license_url": strip_html(meta.get("LicenseUrl", {}).get("value", "")),
            "artist": artist[:130], "source_page": source_page,
        })
    return results

def choose_image(query: str, used_today: set[str], recent_titles: set[str]) -> dict[str, Any]:
    for term in [query] + GENERIC_QUERIES:
        try:
            candidates = commons_candidates(term)
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"Photo search failed for {term!r}: {exc}")
            continue
        for candidate in candidates:
            if candidate["title"] in used_today or candidate["title"] in recent_titles:
                continue
            try:
                response = requests.get(candidate["url"], headers=HEADERS, timeout=40)
                response.raise_for_status()
                if len(response.content) < 20_000:
                    continue
                candidate["bytes"] = response.content
                used_today.add(candidate["title"])
                return candidate
            except requests.RequestException:
                continue
    raise RuntimeError(f"No suitable, non-recent freely reusable photo found for: {query}")

def crop_to_portrait(data: bytes) -> Image.Image:
    import io
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        return ImageOps.fit(image, SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.45))

def header(draw: ImageDraw.ImageDraw, index: int, contact: bool = False) -> None:
    top_font = font(28, True)
    small = font(19)
    draw.text((64, 54), "@arcstudio91", font=top_font, fill=(255, 255, 255, 250))
    if contact:
        label = "+91 9921894495"
    else:
        label = f"DESIGN NOTE / {index:02d}"
    width = draw.textlength(label, font=small)
    draw.text((SIZE[0] - 64 - width, 61), label, font=small, fill=(255, 255, 255, 245))

def render_slide(photo: dict[str, Any], concept: dict[str, Any], index: int) -> Path:
    image = darken_photo(crop_to_portrait(photo["bytes"])).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    header(draw, index, contact=(index == 4))
    x, width = 68, 930
    white = (255, 255, 255, 255)
    muted = (246, 246, 246, 240)
    if index == 1:
        draw.text((x, 710), concept["type"].upper(), font=font(23, True), fill=muted)
        y = text_block(draw, concept["headline"], x, 760, font(74, True), width, white, 5, 2)
        y = text_block(draw, concept["mr"], x, y + 12, font(43, True), width, white, 7, 2)
        text_block(draw, concept["idea"], x, y + 20, font(26), width, muted, 7, 2)
    elif index == 2:
        draw.text((x, 790), "01 / COMFORT", font=font(24, True), fill=muted)
        y = text_block(draw, concept["comfort"], x, 850, font(57, True), width, white, 7, 3)
        text_block(draw, concept["comfort_mr"], x, y + 18, font(38), width, white, 8, 2)
    elif index == 3:
        draw.text((x, 790), "02 / LONG LIFE", font=font(24, True), fill=muted)
        y = text_block(draw, concept["life"], x, 850, font(57, True), width, white, 7, 3)
        text_block(draw, concept["life_mr"], x, y + 18, font(38), width, white, 8, 2)
    else:
        draw.text((x, 715), "MATERIALS, SIMPLIFIED", font=font(25, True), fill=muted)
        y = 775
        for line in concept["materials"]:
            y = text_block(draw, "— " + line, x, y, font(29), width, white, 7, 2) + 9
        y += 14
        draw.text((x, y), "ARCHITECTURE · INTERIORS · HOSPITALITY", font=font(19, True), fill=muted)
        y += 35
        draw.text((x, y), "SUSTAINABLE DESIGN · RENOVATION", font=font(19, True), fill=muted)
        y += 40
        text_block(draw, "Local materials • verified quality • site-specific details", x, y, font(21), width, muted, 6, 2)
        draw.text((x, 1280), "PHOTO SOURCES + LICENCES IN CAPTION", font=font(16), fill=muted)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"slide_{index:02d}.jpg"
    image.convert("RGB").save(path, format="JPEG", quality=92, optimize=True, progressive=True, subsampling=0)
    with Image.open(path) as check:
        if check.size != SIZE or check.format != "JPEG":
            raise RuntimeError(f"Quality gate failed for {path.name}: {check.size}/{check.format}")
    return path

def make_caption(concept: dict[str, Any], photos: list[dict[str, Any]], today: date) -> str:
    text = (
        f"{concept['type']} — an original ARCSTUDIO91 design study.\n\n"
        f"मराठी: {concept['idea_mr']} {concept['comfort_mr']} {concept['life_mr']}\n\n"
        f"English: {concept['idea']} {concept['comfort']} {concept['life']}\n\n"
        "सेवा: घर व व्यावसायिक आर्किटेक्चर • रिसॉर्ट/कॅफे • इंटिरियर • शाश्वत डिझाइन • नूतनीकरण.\n"
        "Services: Residential & commercial architecture • Resorts/hotels/cafés • Interiors • Sustainable design • Renovation/adaptive reuse • Material guidance.\n"
        "हे संदर्भ फोटो आहेत; ARCSTUDIO91 चे पूर्ण झालेले प्रकल्प नाहीत. These licensed photos are references, not completed ARCSTUDIO91 projects.\n\n"
        "Photo credits:\n"
    )
    for i, photo in enumerate(photos, start=1):
        text += f"{i}. {photo['title'][:60]} — {photo['artist'][:60]} ({photo['license']}); {photo['source_page']}\n"
    text += "\n#ARCSTUDIO91 #FunctionalArchitecture #SustainableArchitecture #ClimateResponsiveDesign"
    if len(text) > 2200:
        raise RuntimeError("Caption with photo attributions exceeds Instagram's 2,200-character limit.")
    (OUT / "caption.txt").write_text(text, encoding="utf-8")
    return text

def editorial_pillar(concept: dict[str, Any]) -> str:
    label = (concept.get("type", "") + " " + concept.get("headline", "")).lower()
    if any(k in label for k in ("landscape", "rain garden", "public seating", "pavilion", "courtyard garden")):
        return "Landscape & public space"
    if any(k in label for k in ("clinic", "healthcare", "school", "library", "wayfinding", "accessible", "multi-generation")):
        return "People-first places"
    if any(k in label for k in ("reuse", "heritage", "warehouse")):
        return "Adaptive reuse"
    if any(k in label for k in ("material", "facade", "maintenance", "repair", "durability", "coastal", "flood", "drainage")):
        return "Durability & resilience"
    if any(k in label for k in ("office", "apartment", "home", "house", "villa", "work-live")):
        return "Space planning"
    if any(k in label for k in ("hotel", "restaurant", "cafe", "café", "retail", "market", "guesthouse")):
        return "Hospitality & commercial"
    if any(k in label for k in ("shade", "daylight", "ventilation", "climate", "sun", "rain")):
        return "Climate-wise design"
    return "Original design study"


def main() -> None:
    today = date.today()
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        concept_history_data = json.loads(CONCEPT_HISTORY_PATH.read_text(encoding="utf-8")) if CONCEPT_HISTORY_PATH.exists() else {"concepts": []}
    except (OSError, ValueError):
        concept_history_data = {"concepts": []}
    concept_entries = concept_history_data.get("concepts", [])
    todays_entry = next((entry for entry in reversed(concept_entries) if entry.get("date") == today.isoformat()), None)
    by_type = {item.get("type"): item for item in CONCEPTS}
    if todays_entry and todays_entry.get("type") in by_type:
        concept = by_type[todays_entry["type"]]
    else:
        recent_names = {entry.get("type") for entry in concept_entries[-30:]}
        eligible = [item for item in CONCEPTS if item.get("type") not in recent_names]
        if not eligible:
            eligible = CONCEPTS
        concept = eligible[today.toordinal() % len(eligible)]
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8")) if HISTORY_PATH.exists() else {"images": []}
    recent = history.get("images", [])[-80:]
    recent_titles = {entry.get("title") for entry in recent}
    used_today: set[str] = set()
    photos = [choose_image(query, used_today, recent_titles) for query in concept["queries"]]
    paths = [render_slide(photo, concept, index) for index, photo in enumerate(photos, start=1)]
    caption = make_caption(concept, photos, today)
    metadata = {
        "date": today.isoformat(), "concept": concept["type"], "headline": concept["headline"],
        "photos": [{key: value for key, value in photo.items() if key != "bytes"} for photo in photos],
        "files": [str(path.relative_to(ROOT)) for path in paths], "caption_length": len(caption),
    }
    (OUT / "sources.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "concept.json").write_text(json.dumps({
        "date": today.isoformat(), "type": concept["type"], "headline": concept["headline"],
        "original_idea": concept["idea"], "materials": concept["materials"],
        "materials_mr": concept["materials_mr"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    recent.extend({"date": today.isoformat(), "title": photo["title"]} for photo in photos)
    history["images"] = recent[-80:]
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    if not todays_entry:
        concept_entries.append({
            "date": today.isoformat(),
            "pillar": editorial_pillar(concept),
            "type": concept["type"],
            "headline": concept["headline"],
            "insight": concept.get("comfort", ""),
            "visual_motif": concept.get("queries", [""])[0],
        })
        concept_history_data["concepts"] = concept_entries[-120:]
        CONCEPT_HISTORY_PATH.write_text(json.dumps(concept_history_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated four separate {SIZE[0]}x{SIZE[1]} slides for {today}: {concept['type']} / {concept['headline']}")
    print(f"Caption length: {len(caption)}. Sources are recorded in output/current/sources.json.")

if __name__ == "__main__":
    main()
