# -*- coding: utf-8 -*-
"""System monitoring — detect Collector/API/Verification/Execution failures."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from commerce_ai.stability.errors import ERROR_PATH, recent_errors

HISTORY = Path(__file__).resolve().parent.parent / "commerce_history"


@dataclass
class MonitorFinding:
    severity: str  # info|warn|critical
    component: str
    message: str
    count: int = 1


@dataclass
class SystemHealth:
    ok: bool
    findings: list[MonitorFinding] = field(default_factory=list)
    error_count_24h: int = 0
    components: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "error_count_24h": self.error_count_24h,
            "components": self.components,
            "findings": [
                {
                    "severity": f.severity,
                    "component": f.component,
                    "message": f.message,
                    "count": f.count,
                }
                for f in self.findings
            ],
        }


class SystemMonitor:
    COMPONENTS = (
        "collector",
        "api",
        "verification",
        "execution",
        "dashboard",
        "analyzer",
        "memory",
        "learning",
    )

    def health(self, *, hours: int = 24) -> SystemHealth:
        cutoff = datetime.now() - timedelta(hours=hours)
        errors = recent_errors(limit=500)
        recent: list[dict] = []
        for e in errors:
            try:
                ts = datetime.fromisoformat(e.get("ts", ""))
            except ValueError:
                continue
            if ts >= cutoff:
                recent.append(e)

        by_comp = Counter(e.get("component", "unknown") for e in recent)
        findings: list[MonitorFinding] = []
        components: dict[str, str] = {c: "ok" for c in self.COMPONENTS}

        for comp, n in by_comp.items():
            key = self._normalize(comp)
            if n >= 5:
                sev = "critical"
                components[key] = "critical"
            elif n >= 2:
                sev = "warn"
                components[key] = "degraded"
            else:
                sev = "info"
                if components.get(key) == "ok":
                    components[key] = "degraded"
            findings.append(
                MonitorFinding(
                    severity=sev,
                    component=key,
                    message=f"{comp} errors in last {hours}h",
                    count=n,
                )
            )

        # file integrity probes
        for name, path in (
            ("memory", HISTORY / "commerce_memory.jsonl"),
            ("verification", HISTORY / "verifications.jsonl"),
        ):
            if path.exists():
                try:
                    # last line parse check
                    lines = [
                        ln
                        for ln in path.read_text(encoding="utf-8").splitlines()
                        if ln.strip()
                    ]
                    if lines:
                        json.loads(lines[-1])
                except Exception:
                    findings.append(
                        MonitorFinding(
                            "critical",
                            name,
                            f"corrupt jsonl: {path.name}",
                        )
                    )
                    components[name] = "critical"

        ok = not any(f.severity == "critical" for f in findings)
        return SystemHealth(
            ok=ok,
            findings=findings,
            error_count_24h=len(recent),
            components=components,
        )

    def _normalize(self, component: str) -> str:
        c = component.lower()
        for name in self.COMPONENTS:
            if name in c:
                return name
        return c.split(".")[0] if c else "unknown"

    def format_text(self) -> str:
        h = self.health()
        lines = [
            "STIX Commerce AI — System Monitor",
            f"Status: {'OK' if h.ok else 'DEGRADED'} | errors(24h): {h.error_count_24h}",
            "",
            "[Components]",
        ]
        for k, v in sorted(h.components.items()):
            lines.append(f"  {k}: {v}")
        if h.findings:
            lines.append("")
            lines.append("[Findings]")
            for f in h.findings[:20]:
                lines.append(
                    f"  [{f.severity}] {f.component} x{f.count}: {f.message}"
                )
        else:
            lines.append("")
            lines.append("[Findings] none")
        if ERROR_PATH.exists():
            lines.append(f"\nerror log: {ERROR_PATH}")
        return "\n".join(lines)
