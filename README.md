# ARCSTUDIO91 Daily Open-Weight AI Content System

This project creates a daily Marathi-first Instagram Reel and a four-slide architecture carousel for @arcstudio91 using strictly free tools and locally run open-weight AI models. The final media workflow does not call paid image-generation services, paid hosted inference endpoints, or generation-credit APIs.

## Daily schedule

- **08:07 IST:** GitHub Actions chooses an original concept, updates the concept history, and uploads a small concept-seed artifact. This is not a finished post.
- **08:35 IST:** a Windows Task Scheduler task on your own PC downloads that seed, runs the local AI model, creates the carousel and Reel, validates them, and saves the final pack to `Documents\ARCSTUDIO91\DailyPacks\YYYY-MM-DD`.
- If the local PC is off or not connected, the task can run when Windows makes it available again. The GitHub seed artifact is retained for 30 days.
- Final local outputs are **not auto-published**. The workflow deliberately separates generation from posting and never claims a post went live without confirmation.
- After local AI/video QA passes, Windows saves both the complete dated folder and a single ZIP named `ARCSTUDIO91_Daily_AI_Pack_YYYY-MM-DD.zip` in the `Documents\\ARCSTUDIO91\\DailyPacks` directory.

## The free AI model

- **Default still-image model:** [Black Forest Labs FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell), an open-weight text-to-image model with an Apache-2.0 licence and 1–4-step generation documented by the model publisher.
- The model runs locally through Diffusers on a compatible CUDA GPU. Model weights are downloaded once and cached on the PC. Rendering uses no per-image charge or hosted inference API.
- The model has 12 billion parameters; hardware and memory requirements matter. See the official model card for current details. This workflow does not promise that every PC can run it.
- The final carousel uses four independently generated image backgrounds with precise text overlay via Python/Pillow. Each slide is a separate 1080×1350 JPG and PNG—not a combined collage.
- The Reel uses those same-day AI-generated visuals as its scenes, with restrained motion and transitions, Marathi on-screen copy, SRT subtitles, a Marathi narration script, and a gentle locally generated ambient music bed. It does **not** pretend the script is a voiceover; no synthetic spoken narration is inserted unless a natural free model is separately vetted.
- AI visuals are clearly labelled as concept artwork, not completed ARCSTUDIO91 projects. The caption and source notes identify the model and provenance.

## Strict zero-credit policy

1. **No paid generation services:** do not use image_gen, paid APIs, paid hosted inference endpoints, credits, subscriptions, or anything that asks for a payment card for this workflow.
2. **No hosted-free-tier dependency for final imagery:** small trial credits, public demo Spaces, and provider quotas are not considered reliable daily production infrastructure.
3. **Local open weights only for final visual creation:** use FLUX.1-schnell by default. If it cannot run, stop the final-pack build and report the hardware/setup blocker. Do not silently replace AI images with stock photos, screenshots, generated collages, or hand-drawn placeholders.
4. Python/Pillow and FFmpeg may be used for typography, layout, motion, sound mixing and export QA. They do not substitute for the required AI-generated visual assets.
5. The workflow must not mark anything ready to post until AI model provenance, slide dimensions, MP4 format, duration, soundtrack, captions and package manifest pass validation.

## One-time setup on Windows

### 1. Clone the repository

Install [GitHub CLI](https://cli.github.com/) and Python 3.11 or 3.12, then open PowerShell:

```powershell
gh auth login
gh repo clone artclass11/ARCSTUDIO
cd ARCSTUDIO
```

### 2. Configure the local AI environment

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_local_ai_environment.ps1
```

The script creates `.venv-ai` and installs the base tools. It then pauses so you can install a CUDA-enabled PyTorch build matching your GPU/driver. Use the official selector at [pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/) and run the generated command with `.venv-ai\Scripts\python.exe` as the Python executable. Return to the setup script and confirm CUDA works; it will then install `requirements-ai.txt`.

**Hardware note:** FLUX.1-schnell is a large model. The first local render downloads a large model (allow tens of gigabytes of disk space, depending on the model files/cache). Ensure sufficient GPU VRAM, system RAM and disk space. This repository will not switch to a paid API or lower-quality non-AI fallback if the machine cannot run the model.

### 3. Install the daily download-and-render task

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_daily_download_task.ps1
```

The task is scheduled daily for **08:35 Windows local time** (08:35 IST when Windows is set to India time). Make sure the machine is powered on, connected to the internet and the Windows user is signed in. The script pulls the latest workflow code, finds the latest completed concept seed, checks seed hashes, runs local AI generation, validates the MP4 and slides, and only then moves the completed pack into the dated local folder.

For today's first build, the concept workflow needs one successful run after this change: open [GitHub Actions](https://github.com/artclass11/ARCSTUDIO/actions/workflows/daily-publish.yml), select **Run workflow**, and wait for the concept-seed run to complete. Then run the local downloader below. The scheduled 08:07/08:35 sequence handles later daily runs automatically after setup.

To test immediately:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_latest_pack.ps1
```

Task logs are saved in `Documents\ARCSTUDIO91\logs\daily-pack-download.log`. If AI generation fails, no final folder is marked ready to post. Check the log, model cache, CUDA setup and GitHub Actions status.

## Daily content pack contents

- `reel.mp4`: 1080×1920 H.264 MP4, 30 fps, approximately 25 seconds, with original ambient audio.
- `reel_cover.jpg`, `reel_caption.txt`, `reel_subtitles_mr.srt`, `reel_script_marathi.txt`.
- Exactly four separately exported 1080×1350 carousel JPGs and four PNG masters.
- `preview_contact_sheet.jpg`: review only—never upload this as a carousel slide.
- `ai_generation_manifest.json`: model identifier, prompts, seeds and output hashes.
- `sources.json`, `research_notes.md`, `concept.json`, `package_manifest.json`, `POSTING_README.txt`.

## Content quality and brand safety

- Rotate typologies and editorial pillars; avoid repeated concepts, headlines, images and sentence structures with a 30-concept history where prior runs are available.
- Brand philosophy: minimal but functional, low maintenance, practical security/safety, climate-responsive and sustainable. A 100-year life is an aspiration, not a guarantee.
- Copy and on-screen text are Marathi-first where possible. Slides 1–3 must not display contact details; slide 4 carries +91 9921894495 at the top. The account handle appears at the top of all slides.
- Keep all slide images separate. The contact sheet is preview-only.
- Research informs ideas but may never be copied. Label concepts as concepts, verify claims, and treat structural, safety, waterproofing, cost and code guidance as educational—not site-specific construction advice.
- Use one clear idea per slide and one story arc per Reel. Keep the visuals naturally photographic, minimal, modern, and uncluttered.

## Useful project files

- [Daily concept workflow](.github/workflows/daily-publish.yml)
- [Content quality skill](SKILL.md)
- [Daily concept selector](scripts/create_daily_concept.py)
- [Local open-weight AI renderer](scripts/generate_free_ai_pack.py)
- [Reel renderer](scripts/generate_reel.py)
- [Pack QA and manifest](scripts/package_daily.py)
- [Local downloader](scripts/download_latest_pack.ps1)
- [AI setup helper](scripts/setup_local_ai_environment.ps1)

**Publishing remains manual and explicit.** Only upload the final dated local pack after reviewing it. This project does not report content as posted unless Instagram itself confirms publication.
