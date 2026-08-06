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
        raise RuntimeError("ffprobe is not on PATH")
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries",
        "format=duration,size:stream=index,codec_type,codec_name,pix_fmt,width,height,r_frame_rate,sample_rate,channels:stream_tags=alpha_mode",
        "-of", "json",
        str(path),
    ]
    return json.loads(subprocess.check_output(cmd, text=True, encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Check duration, streams, dimensions, and alpha metadata")
    ap.add_argument("video", type=Path)
    ap.add_argument("--min-duration", type=float, default=0.0)
    ap.add_argument("--max-duration", type=float)
    ap.add_argument("--expected-duration", type=float)
    ap.add_argument("--duration-tolerance", type=float, default=0.15)
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--require-audio", action="store_true")
    ap.add_argument("--require-alpha", action="store_true")
    args = ap.parse_args()

    if not args.video.is_file():
        sys.exit(f"file not found: {args.video}")

    data = probe(args.video)
    streams = data.get("streams", [])
    duration = float((data.get("format") or {}).get("duration") or 0)
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    has_alpha = bool(video and str((video.get("tags") or {}).get("alpha_mode")) == "1")

    result = {
        "duration": duration,
        "has_audio": has_audio,
        "has_alpha_metadata": has_alpha,
        "video": video,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    failures = []
    if not video:
        failures.append("no video stream")
    if duration < args.min_duration:
        failures.append(f"duration {duration:.3f}s is below {args.min_duration:.3f}s")
    if args.max_duration is not None and duration > args.max_duration:
        failures.append(f"duration {duration:.3f}s is above {args.max_duration:.3f}s")
    if args.expected_duration is not None:
        allowed = args.expected_duration * args.duration_tolerance
        if abs(duration - args.expected_duration) > allowed:
            failures.append(
                f"duration {duration:.3f}s differs from {args.expected_duration:.3f}s by more than {args.duration_tolerance:.1%}"
            )
    if video and args.width is not None and video.get("width") != args.width:
        failures.append(f"width {video.get('width')} does not equal {args.width}")
    if video and args.height is not None and video.get("height") != args.height:
        failures.append(f"height {video.get('height')} does not equal {args.height}")
    if args.require_audio and not has_audio:
        failures.append("audio stream required")
    if args.require_alpha and not has_alpha:
        failures.append("alpha_mode=1 required")
    if failures:
        sys.exit("; ".join(failures))


if __name__ == "__main__":
    main()
