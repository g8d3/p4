import json
from datetime import datetime
from pathlib import Path

DEFAULTS = {
    "host": "127.0.0.1",
    "port": 8177,
    "data_dir": "data",
    "max_concurrent_jobs": 1,
    "max_entries_per_url": 50,
    "detection": {"browser": True, "browser_timeout_s": 30},
    "resource": {"cpu_percent": 50, "nice": 10, "download_speed_limit_kbps": 0},
    "time_windows": [],
    "allow_origins": [],
}


def _merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.data = dict(DEFAULTS)
        self.reload()

    def reload(self):
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            self.data = _merge(DEFAULTS, raw)
        self.data_dir = (self.path.parent / self.data["data_dir"]).resolve()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2))

    def get(self, key, default=None):
        val = self.data
        for part in key.split("."):
            if not isinstance(val, dict) or part not in val:
                return default
            val = val[part]
        return val

    def set(self, key, value):
        parts = key.split(".")
        target = self.data
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value

    def window_open(self, now: datetime | None = None) -> bool:
        windows = self.data.get("time_windows") or []
        if not windows:
            return True
        now = now or datetime.now()
        weekday = now.weekday()
        minutes = now.hour * 60 + now.minute
        for w in windows:
            days = w.get("days", "all")
            if days != "all" and weekday not in days:
                continue
            start = _to_minutes(w["start"])
            end = _to_minutes(w["end"])
            if start <= end:
                if start <= minutes < end:
                    return True
            else:
                if minutes >= start or minutes < end:
                    return True
        return False


def _to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)
