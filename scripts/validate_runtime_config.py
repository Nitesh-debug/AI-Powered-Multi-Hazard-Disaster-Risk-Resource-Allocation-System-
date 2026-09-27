from __future__ import annotations

import sys
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".yml", ".yaml", ".toml", ".md"}
SECRET_PATTERNS = (
    re.compile(r"(?i)(?:SUPABASE_SERVICE_ROLE_KEY|SUPABASE_KEY|TWILIO_AUTH_TOKEN|OPENWEATHER_API_KEY|TOMORROW_API_KEY|EMAIL_PASSWORD)\s*[:=]\s*[\"']?[^\s\"']{16,}"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

from api.config import (  # noqa: E402
    CORS_ORIGINS,
    MAX_REQUEST_BODY_BYTES,
    SUPABASE_CONFIG_STATE,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
    WEATHER_TIMEOUT_SECONDS,
)


def main() -> None:
    if MAX_REQUEST_BODY_BYTES <= 0 or WEATHER_TIMEOUT_SECONDS <= 0:
        raise SystemExit("Request-size and weather-timeout settings must be positive")
    if not CORS_ORIGINS or "*" in CORS_ORIGINS:
        raise SystemExit("CORS origins must be explicitly configured; wildcard is rejected")
    if SUPABASE_CONFIG_STATE == "configured":
        parsed = urlsplit(SUPABASE_URL)
        local_development = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if not parsed.hostname or (parsed.scheme != "https" and not local_development):
            raise SystemExit("Remote Supabase configuration must use HTTPS")
        if not SUPABASE_SERVICE_ROLE_KEY:
            raise SystemExit("Supabase is marked configured without a service-role key")
    for source in (ROOT / "frontend/src").rglob("*"):
        if source.is_file() and source.suffix in {".ts", ".tsx", ".js", ".jsx"}:
            contents = source.read_text(encoding="utf-8", errors="ignore")
            if "SUPABASE_SERVICE_ROLE_KEY" in contents:
                raise SystemExit(f"Service-role key reference found in browser source: {source.relative_to(ROOT)}")
    scan_roots = ("api", "agents", "scripts", "storage", "ui", "tests", "frontend/src", "db", ".github")
    for root_name in scan_roots:
        for source in (ROOT / root_name).rglob("*"):
            if not source.is_file() or source.suffix.lower() not in SOURCE_SUFFIXES or source.name == ".env":
                continue
            contents = source.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(contents) for pattern in SECRET_PATTERNS):
                raise SystemExit(f"Credential-like literal found in source file: {source.relative_to(ROOT)}")
    print(
        "Runtime configuration validated; "
        f"CORS origins={len(CORS_ORIGINS)}, request limit={MAX_REQUEST_BODY_BYTES} bytes, "
        f"Supabase={SUPABASE_CONFIG_STATE} (credential value not displayed)."
    )


if __name__ == "__main__":
    main()
