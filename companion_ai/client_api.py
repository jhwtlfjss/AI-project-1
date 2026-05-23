from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class CompanionClient:
    base_url: str
    token: str = ""
    timeout: int = 120
    verify_tls: bool = True
    client_id: str = ""

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/")

    def status(self) -> dict:
        return self._request("GET", "/api/status")

    def chat(self, message: str, web_search: dict | None = None) -> str:
        body = {"message": message}
        if web_search is not None:
            body["web_search"] = web_search
        payload = self._request("POST", "/api/chat", body)
        return str(payload.get("reply", ""))

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = None
        headers = {"Accept": "application/json"}
        if self.token:
            headers["X-Companion-Token"] = self.token
        if self.client_id:
            headers["X-Companion-Client"] = self.client_id
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            context = None if self.verify_tls else ssl._create_unverified_context()
            with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {details}") from exc
