#!/usr/bin/env python3
"""Publish the daily ARCSTUDIO91 carousel through Meta's supported Graph API."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "current"
STATE_PATH = ROOT / "data" / "publish_state.json"
GRAPH_VERSION = os.getenv("META_GRAPH_API_VERSION", "v26.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
TIMEOUT = 45


class MetaError(RuntimeError):
    """A known API or configuration error."""


class UncertainPublish(MetaError):
    """Meta may have accepted the final publish request; do not blindly retry."""


def request_json(method: str, path: str, *, token: str, data: dict[str, Any] | None = None,
                 params: dict[str, Any] | None = None, uncertain: bool = False) -> dict[str, Any]:
    url = f"{GRAPH}/{path.lstrip('/')}"
    form = dict(data or {})
    query = dict(params or {})
    if method.upper() == "GET":
        query["access_token"] = token
    else:
        form["access_token"] = token
    try:
        response = requests.request(method, url, data=form if method.upper() != "GET" else None,
                                    params=query, timeout=TIMEOUT)
    except requests.RequestException as exc:
        if uncertain:
            raise UncertainPublish("Final publish request lost its connection; inspect the platform before retrying.") from exc
        raise MetaError("Meta API network request failed.") from exc
    if uncertain and response.status_code >= 500:
        raise UncertainPublish(f"Final publish returned HTTP {response.status_code}; inspect the platform before retrying.")
    try:
        payload = response.json()
    except ValueError as exc:
        if uncertain:
            raise UncertainPublish("Final publish returned an unreadable response; inspect the platform before retrying.") from exc
        raise MetaError(f"Meta API returned HTTP {response.status_code} with a non-JSON response.") from exc
    if response.status_code >= 400 or payload.get("error"):
        error = payload.get("error", {})
        message = error.get("message", "Meta API request failed")
        raise MetaError(f"Meta API HTTP {response.status_code}: {str(message)[:240]}")
    return payload


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            result = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            return result if isinstance(result, dict) else {}
        except (ValueError, OSError):
            pass
    return {}


def persist_state(state: dict[str, Any], day: str, platform: str, status: str,
                  *, post_id: str | None = None, permalink: str | None = None,
                  error: str | None = None) -> None:
    record = state.setdefault(day, {})
    record[platform] = {
        "status": status, "post_id": post_id, "permalink": permalink,
        "error": error[:240] if error else None,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    # Commit a state change after each platform transition so later reruns see it.
    subprocess.run(["git", "add", str(STATE_PATH.relative_to(ROOT))], cwd=ROOT, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m", f"Record ARCSTUDIO91 {platform} state {day}"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if commit.returncode == 0:
        push = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT,
                              capture_output=True, text=True, check=False)
        if push.returncode != 0:
            print("Warning: state commit could not be pushed; inspect the workflow log.", file=sys.stderr)
            print((push.stderr or "")[-500:], file=sys.stderr)
    else:
        message = (commit.stdout or "") + (commit.stderr or "")
        if "nothing to commit" not in message.lower() and "no changes added" not in message.lower():
            print("Warning: state commit failed; inspect the workflow log.", file=sys.stderr)
            print(message[-500:], file=sys.stderr)


def check_expected_accounts(ig_user_id: str, page_id: str, token: str) -> None:
    """Fail closed unless the configured Instagram user is @arcstudio91 and linked to this Page."""
    ig = request_json("GET", ig_user_id, token=token, params={"fields": "id,username"})
    username = str(ig.get("username", "")).lstrip("@").casefold()
    if username != "arcstudio91":
        raise MetaError(f"Configured Instagram ID resolves to @{username or 'unknown'}, not @arcstudio91; publishing blocked.")
    page = request_json("GET", page_id, token=token, params={"fields": "id,name,instagram_business_account"})
    linked_ig = str((page.get("instagram_business_account") or {}).get("id", ""))
    if str(page.get("id", "")) != page_id:
        raise MetaError("Meta returned a different Facebook Page ID; publishing blocked.")
    if linked_ig and linked_ig != ig_user_id:
        raise MetaError("The selected Facebook Page is linked to a different Instagram account; publishing blocked.")
    if not linked_ig:
        raise MetaError("The selected Facebook Page did not return a linked instagram_business_account. Connect the correct Instagram Professional account first.")


def wait_container(container_id: str, token: str) -> None:
    for _ in range(30):
        result = request_json("GET", container_id, token=token, params={"fields": "status_code,status"})
        status = result.get("status_code")
        if status == "FINISHED":
            return
        if status in {"ERROR", "EXPIRED"}:
            raise MetaError(f"Instagram container processing failed: {result.get('status') or status}")
        time.sleep(2)
    raise MetaError(f"Timed out waiting for Instagram media container {container_id}.")


def public_media_urls() -> list[str]:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("ASSET_COMMIT_SHA", "")
    if not repo or not sha:
        raise MetaError("Missing GitHub repository or asset commit; cannot build public image URLs.")
    urls = [f"https://raw.githubusercontent.com/{repo}/{sha}/output/current/slide_{i:02d}.jpg" for i in range(1, 5)]
    # Verify that each public URL is available before asking Meta to fetch it.
    for url in urls:
        try:
            response = requests.get(url, stream=True, timeout=20)
            response.raise_for_status()
            if not response.headers.get("Content-Type", "").lower().startswith("image/"):
                raise MetaError(f"Public asset URL did not return an image: {url}")
            response.close()
        except requests.RequestException as exc:
            raise MetaError("Generated photo URLs are not publicly reachable yet; no post was attempted.") from exc
    return urls


def publish_instagram(state: dict[str, Any], day: str, urls: list[str], caption: str,
                      ig_user_id: str, token: str) -> None:
    existing = state.get(day, {}).get("instagram", {})
    if existing.get("status") == "published" and existing.get("post_id"):
        print(f"Instagram already published for {day}: {existing.get('permalink') or existing['post_id']}")
        return
    if existing.get("status") in {"needs_review", "publishing"}:
        raise MetaError("Instagram state is ambiguous; inspect the profile before retrying. Duplicate retry is blocked.")
    child_ids: list[str] = []
    try:
        for url in urls:
            child = request_json("POST", f"{ig_user_id}/media", token=token,
                                 data={"image_url": url, "is_carousel_item": "true"})
            container_id = child.get("id")
            if not container_id:
                raise MetaError("Meta returned no Instagram carousel child ID.")
            wait_container(str(container_id), token)
            child_ids.append(str(container_id))
        parent = request_json("POST", f"{ig_user_id}/media", token=token,
                              data={"media_type": "CAROUSEL", "children": ",".join(child_ids), "caption": caption})
        parent_id = parent.get("id")
        if not parent_id:
            raise MetaError("Meta returned no Instagram carousel container ID.")
        wait_container(str(parent_id), token)
    except MetaError as exc:
        persist_state(state, day, "instagram", "failed", error=str(exc))
        raise

    # Save the parent ID before the final publish call. Ambiguous responses are never retried automatically.
    persist_state(state, day, "instagram", "publishing", post_id=str(parent_id))
    try:
        published = request_json("POST", f"{ig_user_id}/media_publish", token=token,
                                 data={"creation_id": str(parent_id)}, uncertain=True)
    except UncertainPublish as exc:
        persist_state(state, day, "instagram", "needs_review", post_id=str(parent_id), error=str(exc))
        raise
    except MetaError as exc:
        persist_state(state, day, "instagram", "failed", post_id=str(parent_id), error=str(exc))
        raise
    media_id = published.get("id")
    if not media_id:
        msg = "Meta returned no media ID after publish; verify Instagram before retrying."
        persist_state(state, day, "instagram", "needs_review", post_id=str(parent_id), error=msg)
        raise UncertainPublish(msg)
    permalink = None
    try:
        detail = request_json("GET", str(media_id), token=token, params={"fields": "id,permalink"})
        permalink = detail.get("permalink")
    except MetaError:
        pass
    persist_state(state, day, "instagram", "published", post_id=str(media_id), permalink=permalink)
    print(f"Instagram published: {permalink or media_id}")


def publish_facebook(state: dict[str, Any], day: str, urls: list[str], caption: str,
                     page_id: str, token: str) -> None:
    existing = state.get(day, {}).get("facebook", {})
    if existing.get("status") == "published" and existing.get("post_id"):
        print(f"Facebook Page already published for {day}: {existing.get('permalink') or existing['post_id']}")
        return
    if existing.get("status") in {"needs_review", "publishing"}:
        raise MetaError("Facebook Page state is ambiguous; inspect the Page before retrying. Duplicate retry is blocked.")
    photo_ids: list[str] = []
    try:
        for url in urls:
            result = request_json("POST", f"{page_id}/photos", token=token,
                                  data={"url": url, "published": "false"})
            photo_id = result.get("id")
            if not photo_id:
                raise MetaError("Meta returned no Facebook photo ID.")
            photo_ids.append(str(photo_id))
    except MetaError as exc:
        persist_state(state, day, "facebook", "failed", error=str(exc))
        raise
    attached = {f"attached_media[{i}]": json.dumps({"media_fbid": photo_id})
                for i, photo_id in enumerate(photo_ids)}
    attached.update({"message": caption, "published": "true"})
    persist_state(state, day, "facebook", "publishing")
    try:
        result = request_json("POST", f"{page_id}/feed", token=token, data=attached, uncertain=True)
    except UncertainPublish as exc:
        persist_state(state, day, "facebook", "needs_review", error=str(exc))
        raise
    except MetaError as exc:
        persist_state(state, day, "facebook", "failed", error=str(exc))
        raise
    post_id = result.get("id")
    if not post_id:
        msg = "Meta returned no Page post ID; verify Facebook before retrying."
        persist_state(state, day, "facebook", "needs_review", error=msg)
        raise UncertainPublish(msg)
    permalink = f"https://www.facebook.com/{post_id}"
    try:
        details = request_json("GET", post_id, token=token, params={"fields": "id,permalink_url"})
        permalink = details.get("permalink_url") or permalink
    except MetaError:
        pass
    persist_state(state, day, "facebook", "published", post_id=str(post_id), permalink=permalink)
    print(f"Facebook Page published: {permalink}")


def main() -> int:
    day = date.today().isoformat()
    if os.getenv("AUTO_PUBLISH_ENABLED", "").strip().upper() != "YES":
        print("Publishing switch is OFF. Daily carousel generated and stored; no social post was created.")
        return 0
    ig_user_id = os.getenv("IG_USER_ID", "").strip()
    page_id = os.getenv("META_PAGE_ID", "").strip()
    token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    if not (ig_user_id.isdigit() and page_id.isdigit() and token):
        print("Publishing is enabled, but IG_USER_ID, META_PAGE_ID or META_PAGE_ACCESS_TOKEN is missing.", file=sys.stderr)
        return 2
    caption_file = OUT / "caption.txt"
    if not caption_file.is_file():
        print("No caption exists; generation must complete before publishing.", file=sys.stderr)
        return 2
    urls = public_media_urls()
    caption = caption_file.read_text(encoding="utf-8").strip()
    try:
        check_expected_accounts(ig_user_id, page_id, token)
    except MetaError as exc:
        print(f"Account verification failed; no social post was attempted: {exc}", file=sys.stderr)
        return 2
    state = load_state()
    issues: list[str] = []
    try:
        publish_instagram(state, day, urls, caption, ig_user_id, token)
    except (MetaError, requests.RequestException) as exc:
        issues.append(f"Instagram: {exc}")
    # Continue to the Page even if Instagram failed; each destination has its own state record.
    try:
        publish_facebook(state, day, urls, caption, page_id, token)
    except (MetaError, requests.RequestException) as exc:
        issues.append(f"Facebook: {exc}")
    if issues:
        print("One or more destinations need attention:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
