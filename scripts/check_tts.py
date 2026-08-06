from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from heygen_client import find_first
from project_io import load_config


HAN_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def audio_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is not available on PATH")
    result = subprocess.check_output(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
        encoding="utf-8",
    ).strip()
    return float(result)


def metadata_text(metadata: dict[str, Any]) -> str:
    value = find_first(metadata, ("transcript", "text", "script"))
    if isinstance(value, str):
        return value
    words = find_first(metadata, ("words",))
    if isinstance(words, list):
        return "".join(
            str(item.get("word") or item.get("text") or "")
            for item in words
            if isinstance(item, dict)
        )
    return ""


def metadata_duration(metadata: dict[str, Any]) -> float | None:
    value = find_first(metadata, ("duration", "duration_seconds", "audio_duration"))
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def evaluate(
    script: str,
    duration: float,
    *,
    target_duration: float = 0,
    transcript: str = "",
    min_chars_per_second: float = 3.0,
    max_chars_per_second: float = 7.0,
) -> dict[str, Any]:
    han_count = len(HAN_PATTERN.findall(script))
    failures: list[str] = []
    warnings: list[str] = []
    if not script.strip():
        failures.append("script is empty")
    if "?" in script or "\ufffd" in script:
        failures.append("script contains question marks or replacement characters")
    if duration <= 0:
        failures.append("duration is not positive")
    if han_count >= 40 and duration <= 10:
        failures.append("long Chinese script produced only 1-10 seconds of audio")
    characters_per_second = han_count / duration if duration > 0 else 0
    if han_count and duration > 0:
        if characters_per_second < min_chars_per_second:
            warnings.append("speech is unusually slow for the Chinese character count")
        if characters_per_second > max_chars_per_second:
            failures.append("speech is implausibly fast for the Chinese character count")
    if target_duration > 0 and duration > 0:
        lower = target_duration * 0.65
        upper = target_duration * 1.35
        if not lower <= duration <= upper:
            failures.append(
                f"duration {duration:.3f}s is outside target window {lower:.3f}-{upper:.3f}s"
            )
    if transcript:
        transcript_han = len(HAN_PATTERN.findall(transcript))
        visible = sum(not char.isspace() for char in transcript)
        ratio = transcript_han / visible if visible else 0
        if "?" in transcript or "\ufffd" in transcript:
            failures.append("provider transcript contains encoding replacement characters")
        if han_count and ratio < 0.5:
            failures.append("provider transcript does not contain a plausible Chinese ratio")
    else:
        warnings.append("provider supplied no transcript; spoken content cannot be mechanically verified")
    return {
        "duration_seconds": duration,
        "han_character_count": han_count,
        "characters_per_second": characters_per_second,
        "transcript_available": bool(transcript),
        "failures": failures,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate TTS text encoding and duration")
    parser.add_argument("project", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--min-cps", type=float, default=3.0)
    parser.add_argument("--max-cps", type=float, default=7.0)
    args = parser.parse_args()

    try:
        config = load_config(args.project)
        metadata: dict[str, Any] = {}
        if args.metadata:
            metadata = json.loads(args.metadata.read_text(encoding="utf-8-sig"))
        duration = args.duration
        if duration is None and args.audio:
            duration = audio_duration(args.audio)
        if duration is None:
            duration = metadata_duration(metadata)
        if duration is None:
            raise ValueError("Provide --duration, --audio, or metadata containing duration")
        result = evaluate(
            str(config["script"]["text"]),
            float(duration),
            target_duration=float(config["script"].get("target_duration_seconds") or 0),
            transcript=metadata_text(metadata),
            min_chars_per_second=args.min_cps,
            max_chars_per_second=args.max_cps,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        sys.exit(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["failures"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
