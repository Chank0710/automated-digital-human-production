from __future__ import annotations

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONFIG_NAME = "config.json"
STATE_NAME = "state.json"
SCHEMA_VERSION = 1


CONFIG_TEMPLATE: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "provider": "heygen",
    "api": {
        "base_url": "https://api.heygen.com",
        "endpoints": {
            "me": "/v3/users/me",
            "avatars": "/v3/avatars/looks",
            "voices": "/v3/voices",
            "tts": "/v3/voices/speech",
            "videos": "/v3/videos",
            "video_status": "/v3/videos/{video_id}",
        },
    },
    "person": {
        "avatar_id": "",
        "asset_path": "",
    },
    "background": {
        "asset_path": "",
        "design_allowed": False,
    },
    "script": {
        "text": "",
        "language": "zh-CN",
        "target_duration_seconds": 0,
        "allow_shortening": False,
        "pronunciation_notes": "",
    },
    "voice": {
        "voice_id": "",
        "audio_path": "",
        "audio_url": "",
        "description": "",
    },
    "output": {
        "width": 1920,
        "height": 1080,
        "style": "",
        "brand_elements": "",
        "captions": False,
        "knowledge_panel": False,
        "output_format": "webm",
    },
    "authorization": {
        "likeness_confirmed": False,
        "voice_confirmed": False,
        "media_confirmed": False,
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_paths(project_dir: Path) -> tuple[Path, Path]:
    return project_dir / CONFIG_NAME, project_dir / STATE_NAME


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Missing file: {path}") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid UTF-8 JSON file: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def create_project(project_dir: Path, overwrite: bool = False) -> tuple[Path, Path]:
    config_path, state_path = project_paths(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "artifacts").mkdir(exist_ok=True)
    if config_path.exists() and not overwrite:
        raise ValueError(f"Config already exists: {config_path}")
    atomic_write_json(config_path, deepcopy(CONFIG_TEMPLATE))
    atomic_write_json(
        state_path,
        {
            "schema_version": SCHEMA_VERSION,
            "step": "initialized",
            "updated_at": utc_now(),
            "tts": {},
            "video": {},
            "checks": {},
        },
    )
    return config_path, state_path


def load_config(project_dir: Path) -> dict[str, Any]:
    config_path, _ = project_paths(project_dir)
    config = read_json(config_path)
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported config schema_version: {config.get('schema_version')!r}"
        )
    return config


def load_state(project_dir: Path) -> dict[str, Any]:
    _, state_path = project_paths(project_dir)
    if not state_path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "step": "initialized",
            "updated_at": utc_now(),
            "tts": {},
            "video": {},
            "checks": {},
        }
    return read_json(state_path)


def save_state(project_dir: Path, state: dict[str, Any]) -> Path:
    _, state_path = project_paths(project_dir)
    state["schema_version"] = SCHEMA_VERSION
    state["updated_at"] = utc_now()
    atomic_write_json(state_path, state)
    return state_path


def get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def validate_config(config: dict[str, Any], stage: str = "intake") -> dict[str, list[str]]:
    missing: list[str] = []
    errors: list[str] = []

    required = [
        "provider",
        "script.text",
        "script.target_duration_seconds",
        "output.width",
        "output.height",
        "output.style",
        "authorization.likeness_confirmed",
        "authorization.voice_confirmed",
        "authorization.media_confirmed",
    ]
    for field in required:
        value = get_path(config, field)
        if value in (None, "", 0, False):
            missing.append(field)

    if not any(get_path(config, field) for field in ("person.avatar_id", "person.asset_path")):
        missing.append("person.avatar_id|person.asset_path")
    if not (
        get_path(config, "background.asset_path")
        or get_path(config, "background.design_allowed")
    ):
        missing.append("background.asset_path|background.design_allowed")
    if not any(
        get_path(config, field)
        for field in ("voice.voice_id", "voice.audio_path", "voice.audio_url", "voice.description")
    ):
        missing.append("voice.voice_id|voice.audio_path|voice.audio_url|voice.description")

    width = get_path(config, "output.width")
    height = get_path(config, "output.height")
    duration = get_path(config, "script.target_duration_seconds")
    if width and (not isinstance(width, int) or width <= 0):
        errors.append("output.width must be a positive integer")
    if height and (not isinstance(height, int) or height <= 0):
        errors.append("output.height must be a positive integer")
    if duration and (not isinstance(duration, (int, float)) or duration <= 0):
        errors.append("script.target_duration_seconds must be positive")

    if stage == "generate":
        if not get_path(config, "person.avatar_id"):
            missing.append("person.avatar_id")
        if not (
            get_path(config, "voice.voice_id")
            or get_path(config, "voice.audio_url")
        ):
            missing.append("voice.voice_id|voice.audio_url")

    return {"missing": sorted(set(missing)), "errors": sorted(set(errors))}


def request_fingerprint(operation: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        {"operation": operation, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
