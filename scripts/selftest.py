from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from check_tts import evaluate
from heygen_client import HeyGenClient
from project_io import create_project, load_state, save_state, validate_config


class Handler(BaseHTTPRequestHandler):
    received: dict = {}

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        Handler.received = json.loads(self.rfile.read(length).decode("utf-8"))
        payload = json.dumps({"audio_url": "https://example.test/audio.wav", "duration": 20}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


class WorkflowTests(unittest.TestCase):
    def test_project_and_state_are_utf8_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            config_path, _ = create_project(project)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("script", config)
            state = load_state(project)
            state["video"] = {"job_id": "job-123"}
            save_state(project, state)
            self.assertEqual(load_state(project)["video"]["job_id"], "job-123")

    def test_validation_reports_missing_fields(self) -> None:
        self.assertIn("script.text", validate_config({"schema_version": 1})["missing"])

    def test_tts_rejects_encoding_and_short_audio(self) -> None:
        self.assertTrue(evaluate("?" * 50 + "中文", 5)["failures"])

    def test_client_sends_utf8_json(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = HeyGenClient(f"http://127.0.0.1:{server.server_port}", {"tts": "/tts"}, api_key="test-key")
            client.tts({"text": "中文台词", "voice_id": "voice"})
            self.assertEqual(Handler.received["text"], "中文台词")
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    os.environ.pop("HEYGEN_API_KEY", None)
    unittest.main()
