from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def probe(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is not available on PATH")
    output = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=format_name,duration:stream=codec_type,codec_name,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        encoding="utf-8",
    )
    return json.loads(output)


def is_compatible_wav(data: dict) -> bool:
    format_name = str((data.get("format") or {}).get("format_name") or "")
    audio = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"), None)
    return bool(audio and "wav" in format_name.split(",") and audio.get("codec_name") == "pcm_s16le")


def prepare(input_path: Path, output_path: Path, sample_rate: int = 48000, channels: int = 1) -> dict:
    before = probe(input_path)
    if is_compatible_wav(before) and input_path.resolve() == output_path.resolve():
        after = before
        converted = False
    else:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg is not available on PATH")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [ffmpeg, "-y", "-i", str(input_path), "-vn", "-c:a", "pcm_s16le", "-ar", str(sample_rate), "-ac", str(channels), str(output_path)],
            check=True,
        )
        after = probe(output_path)
        converted = True
    duration = float((after.get("format") or {}).get("duration") or 0)
    if not is_compatible_wav(after) or duration <= 0:
        raise RuntimeError("converted output is not a valid PCM 16-bit WAV")
    return {"converted": converted, "input": before, "output": after}


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect audio and convert it to PCM 16-bit WAV when needed")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--channels", type=int, default=1)
    args = parser.parse_args()
    if not args.input.is_file():
        sys.exit(f"file not found: {args.input}")
    try:
        result = prepare(args.input, args.output, args.sample_rate, args.channels)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        sys.exit(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
