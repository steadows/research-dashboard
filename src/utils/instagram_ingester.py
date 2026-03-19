"""Instagram video ingestion pipeline.

Downloads Instagram videos via instaloader, transcribes with faster-whisper,
extracts keywords/summary via Claude Haiku, and writes structured markdown
notes to the Obsidian vault.
"""

import json
import logging
import os
import re
import shutil
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import instaloader

from utils import claude_client

logger = logging.getLogger(__name__)

# Input validation patterns — prevent path traversal via external strings
_SAFE_USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
_SAFE_SHORTCODE_RE = re.compile(r"^[A-Za-z0-9_-]{1,30}$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_TERM_CORRECTIONS: dict[str, str] = {
    "CloudCode": "Claude Code",
    "Cloud Code": "Claude Code",
    "Cloud code": "Claude Code",
    "cloud code": "Claude Code",
    "Cloud Agents": "Claude Agents",
    "Cloud Agent": "Claude Agent",
    "Clod": "Claude",
}

_DEFAULT_STATE_FILE = Path.home() / ".research-dashboard" / "instagram_state.json"
_WHISPER_MODEL_NAME = "base"


@lru_cache(maxsize=1)
def _get_whisper_model() -> Any:
    """Lazily initialize and return a cached WhisperModel singleton."""
    from faster_whisper import WhisperModel

    return WhisperModel(_WHISPER_MODEL_NAME, device="cpu", compute_type="int8")


def _load_state(state_file: Path) -> dict[str, Any]:
    """Load ingestion state from JSON file.

    Args:
        state_file: Path to state JSON.

    Returns:
        State dict mapping shortcodes to metadata.
    """
    if not state_file.is_file():
        return {}
    try:
        content = state_file.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Corrupt state file %s, resetting: %s", state_file, exc)
        return {}


def _save_state_atomic(state: dict[str, Any], state_file: Path) -> None:
    """Save state dict atomically using tempfile + os.replace.

    Args:
        state: State dict to persist.
        state_file: Path to state JSON.
    """
    state_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=state_file.parent, suffix=".tmp", prefix=".ig_state_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, state_file)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def fetch_recent_posts(
    username: str,
    days: int = 14,
    state_file: Path = _DEFAULT_STATE_FILE,
) -> list[dict[str, Any]]:
    """Fetch recent video posts from an Instagram account.

    Args:
        username: Instagram username to fetch from.
        days: Only include posts from the last N days.
        state_file: Path to state JSON for dedup.

    Returns:
        List of post dicts with shortcode, url, caption, date, username.
    """
    state = _load_state(state_file)
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

    try:
        loader = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(loader.context, username)
    except instaloader.exceptions.LoginRequiredException:
        logger.error("Instagram login required — set INSTAGRAM_SESSION_FILE env var")
        return []
    except Exception as exc:
        logger.error("Failed to load profile %s: %s", username, exc)
        return []

    posts: list[dict[str, Any]] = []
    _MAX_SCAN = 200  # Cap iteration — Instagram API order is not guaranteed

    for i, post in enumerate(profile.get_posts()):
        if i >= _MAX_SCAN:
            logger.info("Reached scan limit (%d posts), stopping", _MAX_SCAN)
            break

        # Check date cutoff — skip (don't break) since API order isn't reliable
        post_date = post.date_utc
        if not post_date.tzinfo:
            post_date = post_date.replace(tzinfo=timezone.utc)
        if post_date < cutoff:
            continue

        # Skip already-ingested
        if post.shortcode in state:
            continue

        # Skip non-video
        if not post.is_video:
            logger.warning("Skipping non-video post %s", post.shortcode)
            continue

        # Validate shortcode to prevent path traversal (CWE-22)
        if not _SAFE_SHORTCODE_RE.match(post.shortcode):
            logger.warning("Skipping post with invalid shortcode: %s", post.shortcode)
            continue

        date_str = post.date_utc.date().isoformat()
        if not _ISO_DATE_RE.match(date_str):
            logger.warning("Skipping post with invalid date: %s", date_str)
            continue

        posts.append(
            {
                "shortcode": post.shortcode,
                "url": post.video_url,
                "caption": post.caption or "",
                "date": date_str,
                "username": username,
            }
        )

        time.sleep(2)

    return posts


def download_video(
    post: dict[str, Any],
    download_dir: Path,
) -> Path:
    """Download video from URL to local directory.

    Args:
        post: Post dict with 'shortcode' and 'url' keys.
        download_dir: Directory to save the video file.

    Returns:
        Path to the downloaded video file.

    Raises:
        OSError: On download failure (partial file cleaned up).
    """
    target = download_dir / f"{post['shortcode']}.mp4"
    try:
        urllib.request.urlretrieve(post["url"], str(target))
        time.sleep(2)
        return target
    except Exception:
        if target.exists():
            target.unlink()
        raise


def transcribe_video(video_path: Path) -> str:
    """Transcribe video using faster-whisper with term corrections.

    Args:
        video_path: Path to video file (ffmpeg handles format conversion).

    Returns:
        Corrected transcript string.
    """
    model = _get_whisper_model()
    segments, _ = model.transcribe(str(video_path))
    text = "".join(seg.text for seg in segments)

    for wrong, correct in _TERM_CORRECTIONS.items():
        text = text.replace(wrong, correct)

    return text


def extract_keywords_and_summary(
    transcript: str,
    caption: str,
    known_projects: list[str],
) -> dict[str, Any]:
    """Extract title, key points, and keywords from transcript via Haiku.

    Args:
        transcript: Full video transcript.
        caption: Instagram post caption.
        known_projects: List of known project names for wiki-link matching.

    Returns:
        Dict with 'title', 'key_points', 'keywords' keys.
    """
    projects_list = ", ".join(known_projects) if known_projects else "(none)"

    prompt = f"""\
Extract structured information from this Instagram video transcript.

<transcript>
{transcript}
</transcript>

<caption>
{caption}
</caption>

<known_projects>
{projects_list}
</known_projects>

Return a JSON object with exactly these keys:
- "title": A concise title (10 words max) summarizing the video content
- "key_points": An array of 3-5 key takeaway strings
- "keywords": An array of relevant keyword strings. IMPORTANT: if any known project \
name appears verbatim in the transcript or caption, include it as "[[Project Name]]" \
(with wiki-link brackets).

Return ONLY the JSON object, no other text."""

    try:
        response = claude_client.call_haiku_json(prompt)
        # Strip markdown code fences that Haiku sometimes wraps around JSON
        stripped = response.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped
            stripped = stripped.rsplit("```", 1)[0].strip()
        parsed = json.loads(stripped)
        return {
            "title": parsed.get("title", caption[:60] if caption else "Instagram Post"),
            "key_points": parsed.get("key_points", []),
            "keywords": parsed.get("keywords", []),
        }
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse Haiku response: %s", exc)
        return {
            "title": caption[:60] if caption else "Instagram Post",
            "key_points": [],
            "keywords": [],
        }


def write_vault_note(
    post: dict[str, Any],
    transcript: str,
    extracted: dict[str, Any],
    vault_path: Path,
) -> Path:
    """Write a structured markdown note to the Obsidian vault.

    Args:
        post: Post dict with shortcode, username, date, caption, url.
        transcript: Full transcript text.
        extracted: Dict with title, key_points, keywords.
        vault_path: Root path to the Obsidian vault.

    Returns:
        Path to the written markdown file.
    """
    output_dir = vault_path / "Research" / "Instagram" / post["username"]

    # Verify output stays within vault boundary (CWE-22)
    resolved_dir = output_dir.resolve()
    resolved_vault = vault_path.resolve()
    if not resolved_dir.is_relative_to(resolved_vault):
        raise ValueError(
            f"Output path {resolved_dir} escapes vault boundary {resolved_vault}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{post['date']}-{post['shortcode']}.md"

    # Sanitize LLM-generated title for YAML frontmatter (CWE-74)
    safe_title = (
        extracted["title"].replace("\n", " ").replace("\r", " ").replace("'", "''")
    )

    # Build key points section
    kp_lines = "\n".join(f"- {point}" for point in extracted.get("key_points", []))

    # Build keywords line
    kw_line = ", ".join(extracted.get("keywords", []))

    content = f"""\
---
title: '{safe_title}'
tags: []
date: '{post["date"]}'
account: '[[{post["username"]}]]'
shortcode: {post["shortcode"]}
source_url: {post["url"]}
---

## Caption
{post.get("caption", "")}

## Key Points
{kp_lines}

## Keywords
{kw_line}

## Transcript
{transcript}
"""

    # Atomic write: temp file in same dir, then os.replace
    fd, tmp_path = tempfile.mkstemp(dir=output_dir, suffix=".tmp", prefix=".ig_note_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, output_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return output_path


def ensure_account_hub_page(username: str, vault_path: Path) -> Path:
    """Create an Obsidian hub page for an Instagram account if it doesn't exist.

    The hub page lives at Research/Instagram/{username}.md and acts as a
    central node in Obsidian's graph view. All post notes wiki-link to this
    page via ``account: '[[username]]'`` in their frontmatter.

    Args:
        username: Instagram username (already validated by caller).
        vault_path: Root path to the Obsidian vault.

    Returns:
        Path to the account hub page.
    """
    hub_dir = vault_path / "Research" / "Instagram"
    hub_dir.mkdir(parents=True, exist_ok=True)
    hub_path = hub_dir / f"{username}.md"

    if hub_path.exists():
        return hub_path

    today = datetime.now(tz=timezone.utc).date().isoformat()
    content = f"""\
---
tags:
  - instagram
  - account
type: account-hub
account: {username}
created: '{today}'
---

# {username}

Instagram account hub. All ingested video notes for this account link here
via the `account` frontmatter field, making this node the centre of the
account's cluster in Obsidian's graph view.
"""

    fd, tmp_path = tempfile.mkstemp(dir=hub_dir, suffix=".tmp", prefix=".ig_hub_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, hub_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.info("Created account hub page: %s", hub_path)
    return hub_path


def run_ingestion(
    username: str,
    vault_path: Path,
    known_projects: list[str] | None = None,
    days: int = 14,
    state_file: Path = _DEFAULT_STATE_FILE,
) -> list[Path]:
    """Orchestrate the full Instagram ingestion pipeline.

    For each recent video post: download, transcribe, extract, write note,
    update state. Failures are isolated per-post (logged, never propagated).

    Args:
        username: Instagram username to ingest from.
        vault_path: Root path to the Obsidian vault.
        known_projects: List of known project names for wiki-link matching.
        days: Only include posts from the last N days.
        state_file: Path to state JSON for dedup and tracking.

    Returns:
        List of Paths to successfully written vault notes.
    """
    # Validate username to prevent path traversal (CWE-22)
    if not _SAFE_USERNAME_RE.match(username):
        raise ValueError(f"Invalid Instagram username: {username!r}")

    # Ensure the account hub page exists so Obsidian graph shows it as a node
    ensure_account_hub_page(username, vault_path)

    projects = known_projects if known_projects is not None else []
    download_dir = Path(tempfile.mkdtemp(prefix="ig_ingest_"))
    written: list[Path] = []

    try:
        posts = fetch_recent_posts(username, days=days, state_file=state_file)
        state = _load_state(state_file)

        for post in posts:
            video_path: Path | None = None
            try:
                video_path = download_video(post, download_dir)
                transcript = transcribe_video(video_path)
                extracted = extract_keywords_and_summary(
                    transcript, post["caption"], projects
                )
                note_path = write_vault_note(post, transcript, extracted, vault_path)

                # Update state atomically per-post
                new_state = {
                    **state,
                    post["shortcode"]: {
                        "ingested_at": datetime.now(tz=timezone.utc).isoformat(),
                        "note_path": str(note_path),
                    },
                }
                _save_state_atomic(new_state, state_file)
                state = new_state

                written.append(note_path)
                logger.info("Ingested %s → %s", post["shortcode"], note_path)
            except Exception as exc:
                logger.warning("Failed to ingest %s: %s", post["shortcode"], exc)
            finally:
                if video_path is not None and video_path.exists():
                    video_path.unlink()
    finally:
        # Clean up download directory
        shutil.rmtree(download_dir, ignore_errors=True)

    # Post-ingestion: inject wiki-links to connect notes to the knowledge graph
    if written:
        try:
            from utils.knowledge_linker import build_entity_index, link_note

            entities = build_entity_index(vault_path)
            linked = sum(1 for p in written if link_note(p, entities))
            logger.info("Knowledge linker: linked %d / %d new notes", linked, len(written))
        except Exception as exc:
            logger.warning("Knowledge linker failed (non-fatal): %s", exc)

    return written
