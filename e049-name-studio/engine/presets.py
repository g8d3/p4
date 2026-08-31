"""Presets + AI param tuner."""
from __future__ import annotations
from typing import Dict, Any

PRESETS: Dict[str, Dict[str, Any]] = {
    "focalis-like": {
        "label": "Focalis-like",
        "description": "Latin premium, invented, 6-8 chars like focalis.cc",
        "params": {
            "style_brandable": 90,
            "simplicity": 45,
            "length_min": 6,
            "length_max": 8,
            "syllables": 3,
            "strategies": ["invented", "latin", "affix"],
            "language": "latin",
        },
    },
    "minimal-5": {
        "label": "Minimal 5",
        "description": "Ultra simple, 4-5 chars, 1-2 syllables — luma, foco",
        "params": {
            "style_brandable": 85,
            "simplicity": 95,
            "length_min": 4,
            "length_max": 5,
            "syllables": 2,
            "strategies": ["invented"],
            "language": "en",
        },
    },
    "descriptive-mash": {
        "label": "Descriptive Mash",
        "description": "Two-word mash, tech vibe (focus+lens = foclens)",
        "params": {
            "style_brandable": 30,
            "simplicity": 70,
            "length_min": 7,
            "length_max": 11,
            "syllables": 3,
            "strategies": ["mash", "two_words"],
            "language": "en",
        },
    },
    "two-words": {
        "label": "Two Words",
        "description": "Clean two words (focus studio)",
        "params": {
            "style_brandable": 10,
            "simplicity": 80,
            "length_min": 8,
            "length_max": 14,
            "syllables": 4,
            "strategies": ["two_words"],
            "language": "en",
        },
    },
    "with-numbers": {
        "label": "With Numbers",
        "description": "Brandeable + number (focalis7, foco301)",
        "params": {
            "style_brandable": 75,
            "simplicity": 85,
            "length_min": 5,
            "length_max": 9,
            "syllables": 2,
            "strategies": ["invented", "numbers", "affix"],
            "language": "en",
        },
    },
    "rebuscado": {
        "label": "Rebuscado Premium",
        "description": "Elegant, less obvious, veliora / aurialis",
        "params": {
            "style_brandable": 95,
            "simplicity": 20,
            "length_min": 7,
            "length_max": 10,
            "syllables": 4,
            "strategies": ["invented", "latin"],
            "language": "latin",
        },
    },
    "startup-tech": {
        "label": "Startup Tech",
        "description": "Short tech, .io/.ai friendly — nova, pulse",
        "params": {
            "style_brandable": 80,
            "simplicity": 75,
            "length_min": 5,
            "length_max": 7,
            "syllables": 2,
            "strategies": ["invented", "affix"],
            "language": "en",
        },
    },
    "playful": {
        "label": "Playful",
        "description": "Friendly, memorable — bubbly, quirky",
        "params": {
            "style_brandable": 85,
            "simplicity": 85,
            "length_min": 5,
            "length_max": 8,
            "syllables": 2,
            "strategies": ["invented", "mash"],
            "language": "en",
        },
    },
    "es-corto": {
        "label": "ES Corto",
        "description": "Español simple — luz, foco, claro",
        "params": {
            "style_brandable": 70,
            "simplicity": 90,
            "length_min": 4,
            "length_max": 7,
            "syllables": 2,
            "strategies": ["invented", "affix"],
            "language": "es",
        },
    },
    "geo-latin": {
        "label": "Geo Latin Pro",
        "description": "Latin pro, 7-9 chars para marca premium",
        "params": {
            "style_brandable": 92,
            "simplicity": 35,
            "length_min": 7,
            "length_max": 9,
            "syllables": 3,
            "strategies": ["latin", "invented"],
            "language": "latin",
        },
    },
}

# Language options
LANGUAGES = [
    {"id": "auto", "label": "Auto"},
    {"id": "en", "label": "EN"},
    {"id": "es", "label": "ES"},
    {"id": "latin", "label": "Latin"},
    {"id": "pt", "label": "PT"},
    {"id": "fr", "label": "FR"},
    {"id": "it", "label": "IT"},
    {"id": "de", "label": "DE"},
]

# TLD presets
TLD_PRESETS = {
    "classic": {"label": "Classic", "tlds": ["com","cc","io","ai"]},
    "startup": {"label": "Startup", "tlds": ["io","ai","co","app"]},
    "all": {"label": "Popular 10", "tlds": ["com","cc","io","ai","co","net","org","app","dev","xyz"]},
    "premium": {"label": "Premium", "tlds": ["com","io","ai","co","studio","tech"]},
    "cheap": {"label": "Barato", "tlds": ["xyz","online","site","cc","com"]},
}

ALL_TLDS = ["com","cc","io","ai","co","net","org","app","dev","studio","xyz","tech","online","site","me","sh","live","pro"]

def list_presets():
    return [{"id": k, **v} for k, v in PRESETS.items()]

def get_preset(pid: str) -> Dict[str, Any] | None:
    return PRESETS.get(pid)

import os, json, re

def heuristic_tune(prompt: str) -> Dict[str, Any]:
    p = prompt.lower()
    out: Dict[str, Any] = {}
    if any(w in p for w in ["simple", "sencill", "corto", "minimal", "facil"]):
        out["simplicity"] = 90
        out["length_max"] = 6
        out["syllables"] = 2
    if any(w in p for w in ["rebuscad", "elegant", "premium", "latin", "sofistic"]):
        out["simplicity"] = 25
        out["language"] = "latin"
        out["style_brandable"] = 90
    if any(w in p for w in ["dos palabras", "two words", "descriptivo"]):
        out["style_brandable"] = 15
        out["strategies"] = ["two_words"]
    if any(w in p for w in ["mash", "unir", "mezclar", "combinar"]):
        out["strategies"] = ["mash"]
        out["style_brandable"] = 40
    if any(w in p for w in ["numero", "number", "con numero"]):
        out["strategies"] = ["invented", "numbers"]
    if any(w in p for w in ["focalis", "como focalis"]):
        out.update(PRESETS["focalis-like"]["params"])
    if "video" in p:
        out["keywords_hint"] = "video, focus, lens, frame, clip"
    return out

async def ai_tune(prompt: str, user_key: str = "", user_base: str = "", user_model: str = "") -> Dict[str, Any]:
    from engine.config import load_resolved_config, resolve_value
    cfg = load_resolved_config()
    api_key = user_key or resolve_value(cfg.get("ai_api_key")) or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENCODE_API_KEY")
    base_url = user_base or resolve_value(cfg.get("ai_base_url")) or os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENCODE_GO_BASE_URL") or "https://api.openai.com/v1"
    model = user_model or resolve_value(cfg.get("ai_model")) or os.environ.get("OPENAI_MODEL") or os.environ.get("OPENCODE_GO_MODEL") or "gpt-4o-mini"
    api_key = resolve_value(api_key) if api_key else api_key
    base_url = resolve_value(base_url) if base_url else base_url
    model = resolve_value(model) if model else model
    if api_key:
        try:
            import httpx
            sys_prompt = """You are a naming param tuner. Given a user description in Spanish or English, output ONLY valid JSON with any of these keys (only include keys you are confident about):
- style_brandable: 0-100 (0=descriptive like 'focus studio', 100=brandable invented like 'focalis')
- simplicity: 0-100 (0=rebuscado/elegant/veliora, 100=simple/minimal/luma)
- length_min: 3-12, length_max: 3-14
- syllables: 1-4
- strategies: array subset of ["invented","mash","two_words","affix","numbers","latin"]
- language: "en"|"es"|"latin"|"pt"|"fr"|"it"|"de"|"auto"
Example: user says "quiero algo simple como focalis pero mas corto para video" -> {"style_brandable":85,"simplicity":80,"length_min":4,"length_max":6,"syllables":2,"strategies":["invented"],"language":"latin"}
Only output JSON, no markdown."""
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 300,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    m = re.search(r"\{.*\}", text, re.S)
                    if m:
                        parsed = json.loads(m.group(0))
                        allowed = {"style_brandable","simplicity","length_min","length_max","syllables","strategies","language"}
                        return {k: v for k, v in parsed.items() if k in allowed}
        except Exception:
            pass
    return heuristic_tune(prompt)
