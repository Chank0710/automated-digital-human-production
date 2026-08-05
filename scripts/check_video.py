from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def ffprobe(path: Path) -> dict:
    command = shutil.which("ffprobe")
    if not command:
        raise RuntimeError("没有在 PATH 中找到 ffprobe")
    args = [
        command,
        "-v", "error",
        "-show_entries",
        "format=duration,size:stream=index,codec_type,codec_name,pix_fmt,width,height:stream_tags=alpha_mode",
        "-of", "json",
        str(path),
    ]
    return json.loads(subprocess.check_output(args, text=True, encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="检查视频时长、音频、尺寸和透明通道元数据")
    parser.add_argument("video", type=Path, help="需要检查的视频文件")
    parser.add_argument("--min-duration", type=float, default=0.0, help="允许的最短时长，单位为秒")
    parser.add_argument("--require-audio", action="store_true", help="要求视频必须包含音频")
    parser.add_argument("--require-alpha", action="store_true", help="要求视频必须包含 alpha_mode=1")
    args = parser.parse_args()

    if not args.video.is_file():
        sys.exit(f"文件不存在：{args.video}")

    data = ffprobe(args.video)
    streams = data.get("streams", [])
    duration = float((data.get("format") or {}).get("duration") or 0)
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    has_audio = any(item.get("codec_type") == "audio" for item in streams)
    has_alpha = bool(video and str((video.get("tags") or {}).get("alpha_mode")) == "1")

    result = {
        "时长_秒": duration,
        "包含音频": has_audio,
        "包含透明通道元数据": has_alpha,
        "视频流": video,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    failures = []
    if not video:
        failures.append("没有视频流")
    if duration < args.min_duration:
        failures.append(f"视频时长 {duration:.3f} 秒，低于要求的 {args.min_duration:.3f} 秒")
    if args.require_audio and not has_audio:
        failures.append("缺少音频流")
    if args.require_alpha and not has_alpha:
        failures.append("缺少 alpha_mode=1")
    if failures:
        sys.exit("；".join(failures))


if __name__ == "__main__":
    main()
