# -*- coding: utf-8
"""Cloudflare quick tunnel for external mobile access."""
from __future__ import annotations

import re
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools"
CF_BIN = TOOLS / "cloudflared.exe"
PUBLIC_URL_FILE = ROOT / "public_url.txt"
CF_RELEASE = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"


def _find_cloudflared() -> Path | None:
    if CF_BIN.exists():
        return CF_BIN
    found = shutil.which("cloudflared")
    if found:
        return Path(found)
    return None


def ensure_cloudflared() -> Path:
    existing = _find_cloudflared()
    if existing:
        return existing
    TOOLS.mkdir(parents=True, exist_ok=True)
    print(f"Downloading cloudflared -> {CF_BIN}")
    urllib.request.urlretrieve(CF_RELEASE, CF_BIN)
    return CF_BIN


def read_public_url() -> str | None:
    if not PUBLIC_URL_FILE.exists():
        return None
    url = PUBLIC_URL_FILE.read_text(encoding="utf-8").strip()
    return url or None


def _extract_url(line: str) -> str | None:
    m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
    return m.group(0) if m else None


class TunnelProcess:
    def __init__(self, local_port: int) -> None:
        self.local_port = local_port
        self.proc: subprocess.Popen[str] | None = None
        self.public_url: str | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> str | None:
        bin_path = ensure_cloudflared()
        cmd = [
            str(bin_path),
            "tunnel",
            "--no-autoupdate",
            "--url",
            f"http://127.0.0.1:{self.local_port}",
        ]
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self._thread = threading.Thread(target=self._read_output, daemon=True)
        self._thread.start()
        for _ in range(60):
            if self.public_url:
                PUBLIC_URL_FILE.write_text(self.public_url + "\n", encoding="utf-8")
                return self.public_url
            time.sleep(0.5)
        return self.public_url

    def _read_output(self) -> None:
        if not self.proc or not self.proc.stdout:
            return
        for line in self.proc.stdout:
            url = _extract_url(line)
            if url:
                self.public_url = url
                PUBLIC_URL_FILE.write_text(url + "\n", encoding="utf-8")
                print(f"Public URL: {url}")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
