from dataclasses import dataclass
from typing import Any
import requests

@dataclass
class APIConfig:
    base_api: str
    csrf_token: str = ""
    cookie: str = ""

class DACApiClient:
    def __init__(self, cfg: APIConfig):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Referer": "https://inception.dachain.io/dashboard",
            "Origin": "https://inception.dachain.io",
        })
        if cfg.csrf_token:
            self.session.headers["X-CSRFToken"] = cfg.csrf_token
        if cfg.cookie:
            self.session.headers["Cookie"] = cfg.cookie

    def get(self, endpoint: str) -> dict[str, Any]:
        try:
            r = self.session.get(endpoint, timeout=30)
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    return {"raw": r.text[:200], "status": r.status_code}
            return {"error": f"HTTP {r.status_code}", "body": r.text[:200]}
        except Exception as e:
            return {"error": str(e)}

    def post(self, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            r = self.session.post(endpoint, json=data or {}, timeout=30)
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    return {"raw": r.text[:200], "status": r.status_code}
            return {"error": f"HTTP {r.status_code}", "body": r.text[:200]}
        except Exception as e:
            return {"error": str(e)}
