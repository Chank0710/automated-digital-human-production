from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from check_tts import evaluate, metadata_duration, metadata_text
from heygen_client import HeyGenClient, HeyGenError, find_first
from prepare_audio import prepare
from project_io import atomic_write_json, create_project, load_config, load_state, project_paths, request_fingerprint, save_state, validate_config


def client_from_config(config: dict[str, Any]) -> HeyGenClient:
    api = config.get("api") or {}
    return HeyGenClient(str(api.get("base_url") or "https://api.heygen.com"), dict(api.get("endpoints") or {}))


def fail_if_invalid(config: dict[str, Any], stage: str) -> None:
    result = validate_config(config, stage=stage)
    if result["missing"] or result["errors"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(2)


def store_response(project: Path, name: str, response: dict[str, Any]) -> Path:
    path = project / "artifacts" / name
    atomic_write_json(path, response)
    return path


def tts_payload(config: dict[str, Any]) -> dict[str, Any]:
    return {"text": config["script"]["text"], "voice_id": config["voice"]["voice_id"], "language": config["script"].get("language") or "zh-CN"}


def video_payload(config: dict[str, Any], audio_url: str) -> dict[str, Any]:
    return {
        "type": "avatar",
        "avatar_id": config["person"]["avatar_id"],
        "audio_url": audio_url,
        "output_format": config["output"].get("output_format") or "webm",
        "dimension": {"width": config["output"]["width"], "height": config["output"]["height"]},
    }


def command_init(args: argparse.Namespace) -> None:
    config_path, state_path = create_project(args.project, overwrite=args.overwrite)
    print(json.dumps({"config": str(config_path), "state": str(state_path)}, indent=2))


def command_validate(args: argparse.Namespace) -> None:
    result = validate_config(load_config(args.project), stage=args.stage)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["missing"] or result["errors"]:
        raise SystemExit(2)


def command_auth(args: argparse.Namespace) -> None:
    config = load_config(args.project)
    response = client_from_config(config).me()
    store_response(args.project, "auth_response.json", response)
    state = load_state(args.project)
    state["step"] = "authenticated"
    state["auth"] = {"verified": True}
    save_state(args.project, state)
    print(json.dumps({"authenticated": True}, indent=2))


def command_avatars(args: argparse.Namespace) -> None:
    config = load_config(args.project)
    path = store_response(args.project, "avatars_response.json", client_from_config(config).list_avatars(args.token))
    print(json.dumps({"saved": str(path)}, indent=2))


def command_voices(args: argparse.Namespace) -> None:
    config = load_config(args.project)
    path = store_response(args.project, "voices_response.json", client_from_config(config).list_voices(args.voice_id))
    print(json.dumps({"saved": str(path)}, indent=2))


def command_prepare_audio(args: argparse.Namespace) -> None:
    config = load_config(args.project)
    source_value = config.get("voice", {}).get("audio_path")
    if not source_value:
        raise RuntimeError("config voice.audio_path is empty")
    source = Path(source_value)
    if not source.is_absolute():
        source = args.project / source
    output = args.project / "artifacts" / "voice.wav"
    result = prepare(source, output)
    config["voice"]["audio_path"] = str(output)
    config_path, _ = project_paths(args.project)
    atomic_write_json(config_path, config)
    state = load_state(args.project)
    state["step"] = "audio_prepared"
    state["audio"] = {"path": str(output), "probe": result["output"]}
    save_state(args.project, state)
    print(json.dumps({"path": str(output), **result}, ensure_ascii=False, indent=2))


def command_tts(args: argparse.Namespace) -> None:
    config = load_config(args.project)
    fail_if_invalid(config, "generate")
    if not config["voice"].get("voice_id"):
        raise RuntimeError("voice.voice_id is required for provider TTS")
    payload = tts_payload(config)
    fingerprint = request_fingerprint("tts", payload)
    state = load_state(args.project)
    existing = state.get("tts") or {}
    if existing.get("request_fingerprint") == fingerprint and existing.get("audio_url"):
        print(json.dumps({"reused": True, "audio_url": existing["audio_url"]}, indent=2))
        return
    response = client_from_config(config).tts(payload)
    response_path = store_response(args.project, "tts_response.json", response)
    audio_url = find_first(response, ("audio_url", "url"))
    duration = metadata_duration(response)
    if not audio_url or duration is None:
        raise RuntimeError(f"TTS response lacks audio URL or duration; inspect {response_path}")
    check = evaluate(str(config["script"]["text"]), duration, target_duration=float(config["script"].get("target_duration_seconds") or 0), transcript=metadata_text(response))
    state["tts"] = {"request_fingerprint": fingerprint, "response_path": str(response_path), "check": check}
    if check["failures"]:
        state["step"] = "tts_rejected"
        save_state(args.project, state)
        print(json.dumps(check, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    state["step"] = "tts_validated"
    state["tts"].update({"audio_url": audio_url, "duration_seconds": duration})
    save_state(args.project, state)
    print(json.dumps(state["tts"], ensure_ascii=False, indent=2))


def command_create(args: argparse.Namespace) -> None:
    config = load_config(args.project)
    fail_if_invalid(config, "generate")
    state = load_state(args.project)
    audio_url = config["voice"].get("audio_url") or (state.get("tts") or {}).get("audio_url")
    if not audio_url:
        raise RuntimeError("No validated audio URL. Run tts or set voice.audio_url.")
    payload = video_payload(config, audio_url)
    fingerprint = request_fingerprint("create_video", payload)
    existing = state.get("video") or {}
    if existing.get("request_fingerprint") == fingerprint and existing.get("job_id"):
        print(json.dumps({"reused": True, "job_id": existing["job_id"]}, indent=2))
        return
    response = client_from_config(config).create_video(payload)
    response_path = store_response(args.project, "video_create_response.json", response)
    job_id = find_first(response, ("video_id", "job_id", "id"))
    if not job_id:
        raise RuntimeError(f"Create response has no job ID; inspect {response_path}")
    state["step"] = "video_submitted"
    state["video"] = {"request_fingerprint": fingerprint, "job_id": str(job_id), "response_path": str(response_path), "status": "submitted"}
    save_state(args.project, state)
    print(json.dumps(state["video"], ensure_ascii=False, indent=2))


def command_poll(args: argparse.Namespace) -> None:
    config = load_config(args.project)
    state = load_state(args.project)
    job_id = (state.get("video") or {}).get("job_id")
    if not job_id:
        raise RuntimeError("state.json has no video job ID")

    def checkpoint(response: dict[str, Any]) -> None:
        current = load_state(args.project)
        current["step"] = "video_polling"
        current_video = current.setdefault("video", {})
        current_video["job_id"] = job_id
        current_video["status"] = str(find_first(response, ("status", "state")) or "unknown")
        store_response(args.project, "video_poll_response.json", response)
        save_state(args.project, current)

    response = client_from_config(config).poll_video(str(job_id), interval=args.interval, timeout=args.timeout, on_update=checkpoint)
    response_path = store_response(args.project, "video_complete_response.json", response)
    output_url = find_first(response, ("video_url", "output_url", "url"))
    state = load_state(args.project)
    state["step"] = "video_completed"
    state["video"].update({"status": "completed", "output_url": output_url, "response_path": str(response_path)})
    save_state(args.project, state)
    print(json.dumps(state["video"], ensure_ascii=False, indent=2))


def command_status(args: argparse.Namespace) -> None:
    print(json.dumps(load_state(args.project), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic HeyGen project workflow")
    subs = parser.add_subparsers(dest="command", required=True)
    init = subs.add_parser("init"); init.add_argument("project", type=Path); init.add_argument("--overwrite", action="store_true"); init.set_defaults(handler=command_init)
    validate = subs.add_parser("validate"); validate.add_argument("project", type=Path); validate.add_argument("--stage", choices=("intake", "generate"), default="intake"); validate.set_defaults(handler=command_validate)
    auth = subs.add_parser("auth"); auth.add_argument("project", type=Path); auth.set_defaults(handler=command_auth)
    avatars = subs.add_parser("avatars"); avatars.add_argument("project", type=Path); avatars.add_argument("--token"); avatars.set_defaults(handler=command_avatars)
    voices = subs.add_parser("voices"); voices.add_argument("project", type=Path); voices.add_argument("--voice-id"); voices.set_defaults(handler=command_voices)
    prepare_audio = subs.add_parser("prepare-audio"); prepare_audio.add_argument("project", type=Path); prepare_audio.set_defaults(handler=command_prepare_audio)
    tts = subs.add_parser("tts"); tts.add_argument("project", type=Path); tts.set_defaults(handler=command_tts)
    create = subs.add_parser("create"); create.add_argument("project", type=Path); create.set_defaults(handler=command_create)
    poll = subs.add_parser("poll"); poll.add_argument("project", type=Path); poll.add_argument("--interval", type=float, default=5); poll.add_argument("--timeout", type=float, default=1800); poll.set_defaults(handler=command_poll)
    status = subs.add_parser("status"); status.add_argument("project", type=Path); status.set_defaults(handler=command_status)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except (ValueError, RuntimeError, HeyGenError, OSError, KeyError) as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
