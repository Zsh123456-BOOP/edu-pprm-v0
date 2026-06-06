from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from src.data.common import CACHE_DIR, REPORT_DIR, ROOT, append_jsonl, load_json_yaml, write_json
from src.llm.json_repair import parse_json_object


def load_config(path: Path = ROOT / "configs" / "deepseek.yaml") -> dict[str, Any]:
    return load_json_yaml(path)["deepseek"]


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class DeepSeekClient:
    def __init__(self, config: dict[str, Any] | None = None, dry_run: bool = False):
        self.config = config or load_config()
        self.dry_run = dry_run
        self.cache_dir = ROOT / self.config.get("cache_dir", str(CACHE_DIR / "deepseek"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.request_log = self.cache_dir / "label_requests.jsonl"
        self.response_log = self.cache_dir / "label_responses.jsonl"
        self.failed_log = REPORT_DIR / "deepseek_failed_responses.jsonl"

    def build_payload(self, messages: list[dict[str, str]], *, sample_id: str, temperature: float | None = None, max_tokens: int | None = None) -> dict[str, Any]:
        payload = {
            "model": self.config["model"],
            "messages": messages,
            "temperature": self.config["temperature"] if temperature is None else temperature,
            "max_tokens": self.config["max_tokens"] if max_tokens is None else max_tokens,
            "stream": self.config.get("stream", False),
            "response_format": {"type": "json_object"},
        }
        if self.config.get("reasoning_effort") is not None:
            payload["reasoning_effort"] = self.config["reasoning_effort"]
        if self.config.get("thinking") is not None:
            payload["thinking"] = self.config["thinking"]
        payload["_sample_id"] = sample_id
        return payload

    def _cache_path(self, payload: dict[str, Any]) -> Path:
        clean = {k: v for k, v in payload.items() if not k.startswith("_")}
        return self.cache_dir / "responses" / f"{stable_hash(clean)}.json"

    def chat_json(self, messages: list[dict[str, str]], *, sample_id: str, temperature: float | None = None, max_tokens: int | None = None) -> dict[str, Any]:
        payload = self.build_payload(messages, sample_id=sample_id, temperature=temperature, max_tokens=max_tokens)
        cache_path = self._cache_path(payload)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(self.request_log, [{"sample_id": sample_id, "payload_hash": cache_path.stem, "payload": {k: v for k, v in payload.items() if not k.startswith("_")}}])
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            cached["cache_hit"] = True
            return cached
        if self.dry_run:
            return {"sample_id": sample_id, "dry_run": True, "payload": {k: v for k, v in payload.items() if not k.startswith("_")}}
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set")
        request_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
        data = json.dumps(request_payload).encode("utf-8")
        url = self.config["base_url"].rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "edu-pprm-pilot/0.1",
        }
        last_error = None
        for attempt in range(int(self.config.get("max_retries", 3)) + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=int(self.config.get("timeout_seconds", 90))) as response:
                    raw = json.loads(response.read().decode("utf-8"))
                content = raw["choices"][0]["message"]["content"]
                parsed = parse_json_object(content)
                result = {
                    "sample_id": sample_id,
                    "model": raw.get("model", self.config["model"]),
                    "raw": raw,
                    "parsed": parsed,
                    "cache_hit": False,
                }
                write_json(cache_path, result)
                append_jsonl(self.response_log, [{"sample_id": sample_id, "payload_hash": cache_path.stem, "model": result["model"], "parsed": parsed}])
                return result
            except urllib.error.HTTPError as exc:
                last_error = f"HTTP {exc.code}: {exc.reason}"
                if exc.code == 429:
                    time.sleep(10 * (attempt + 1))
                else:
                    time.sleep(2**attempt)
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(2**attempt)
        failure = {"sample_id": sample_id, "error": last_error}
        append_jsonl(self.failed_log, [failure])
        raise RuntimeError(last_error)


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek client dry-run")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    client = DeepSeekClient(dry_run=args.dry_run)
    messages = [
        {"role": "system", "content": "Return JSON only."},
        {"role": "user", "content": "Return {\"ok\": true}."},
    ]
    result = client.chat_json(messages, sample_id="deepseek_client_dryrun")
    write_json(REPORT_DIR / "deepseek_client_dryrun.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
