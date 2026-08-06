from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable


def load_api_key() -> str:
    key = os.environ.get("HEYGEN_API_KEY", "").strip()
    if not key and os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as registry_key:
                key = str(winreg.QueryValueEx(registry_key, "HEYGEN_API_KEY")[0]).strip()
        except (FileNotFoundError, OSError):
            key = ""
    if not key:
        raise RuntimeError(
            "HEYGEN_API_KEY is not configured. Run scripts/configure_heygen_key.ps1."
        )
    return key


class HeyGenError(RuntimeError):
    pass


class HeyGenClient:
    def __init__(
        self,
        base_url: str,
        endpoints: dict[str, str],
        api_key: str | None = None,
        timeout: float = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoints = endpoints
        self.api_key = api_key or load_api_key()
        self.timeout = timeout

    def _url(self, endpoint_name: str, **values: str) -> str:
        try:
            path = self.endpoints[endpoint_name].format(**values)
        except KeyError as exc:
            raise HeyGenError(f"Missing endpoint configuration: {endpoint_name}") from exc
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        endpoint_name: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        retries: int = 3,
        retry_unsafe: bool = False,
        path_values: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self._url(endpoint_name, **(path_values or {}))
        if query:
            clean_query = {key: value for key, value in query.items() if value not in (None, "")}
            url = f"{url}?{urllib.parse.urlencode(clean_query)}"
        payload = None
        if body is not None:
            payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            method=method.upper(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
                "X-Api-Key": self.api_key,
                "User-Agent": "codex-digital-human-skill/1",
            },
        )
        attempts = retries if method.upper() in {"GET", "HEAD"} or retry_unsafe else 1
        for attempt in range(attempts):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                value = json.loads(raw.decode("utf-8")) if raw else {}
                if not isinstance(value, dict):
                    raise HeyGenError("Provider response was not a JSON object")
                return value
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
                if exc.code not in {408, 429, 500, 502, 503, 504} or attempt + 1 >= attempts:
                    raise HeyGenError(f"HeyGen HTTP {exc.code}: {detail}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt + 1 >= attempts:
                    raise HeyGenError(f"HeyGen request failed: {exc}") from exc
            delay = min(15.0, (2**attempt) + random.random())
            time.sleep(delay)
        raise AssertionError("unreachable")

    def me(self) -> dict[str, Any]:
        return self.request("GET", "me")

    def list_avatars(self, token: str | None = None) -> dict[str, Any]:
        return self.request("GET", "avatars", query={"token": token})

    def list_voices(self, voice_id: str | None = None) -> dict[str, Any]:
        endpoint = "voice" if voice_id and "voice" in self.endpoints else "voices"
        path_values = {"voice_id": voice_id} if voice_id else None
        return self.request("GET", endpoint, path_values=path_values)

    def tts(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "tts", body=payload)

    def create_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "videos", body=payload)

    def get_video(self, video_id: str) -> dict[str, Any]:
        return self.request(
            "GET", "video_status", path_values={"video_id": urllib.parse.quote(video_id, safe="")}
        )

    def poll_video(
        self,
        video_id: str,
        *,
        interval: float = 5,
        timeout: float = 1800,
        on_update: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            last = self.get_video(video_id)
            if on_update:
                on_update(last)
            status = find_first(last, ("status", "state"))
            normalized = str(status or "").lower()
            if normalized in {"completed", "complete", "succeeded", "success", "done"}:
                return last
            if normalized in {"failed", "error", "cancelled", "canceled"}:
                raise HeyGenError(f"Video job ended with status {status!r}")
            time.sleep(interval)
        raise HeyGenError(f"Timed out polling video {video_id}; last response preserved")


def find_first(value: Any, names: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        for name in names:
            if name in value and value[name] not in (None, ""):
                return value[name]
        for child in value.values():
            found = find_first(child, names)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_first(child, names)
            if found not in (None, ""):
                return found
    return None
