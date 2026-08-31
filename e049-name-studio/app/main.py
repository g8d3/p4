from __future__ import annotations
from fastapi import FastAPI, Query, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import time
import asyncio
import os

from engine.generate import generate, generate_sync
from engine.domain import check_domains, check_single_domain
from engine.presets import PRESETS, TLD_PRESETS, ALL_TLDS, LANGUAGES, list_presets, get_preset, ai_tune
from engine.scoring import pronounceable_score, memorability_score
from engine.history import add_entry, list_history, get_entry, delete_entry
from engine.config import load_config, save_config, get_public_config, create_admin_token, verify_admin_token, verify_admin_request, resolve_value, load_resolved_config
from engine.referrals import list_registrars, get_registrar, create_share, get_share, list_shares

WEB_DIR = Path(__file__).parent.parent / "web"

class GenerateRequest(BaseModel):
    keywords: str = ""
    prompt: str = ""
    preset: Optional[str] = None
    style_brandable: Optional[int] = None
    simplicity: Optional[int] = None
    length_min: Optional[int] = None
    length_max: Optional[int] = None
    syllables: Optional[int] = None
    strategies: Optional[List[str]] = None
    language: Optional[str] = None
    tlds: Optional[List[str]] = None
    count: int = 40
    check_domains_flag: bool = True
    use_llm: bool = True
    user_ai_key: Optional[str] = None
    user_ai_base: Optional[str] = None
    user_ai_model: Optional[str] = None
    ai_ratio: Optional[int] = None  # 0-100 % LLM vs algo
    ai_count: Optional[int] = None  # explicit LLM count (overrides ratio)

def create_app() -> FastAPI:
    app = FastAPI(title="Name Studio")

    @app.get("/api/presets")
    def presets():
        return list_presets()

    @app.get("/api/tlds")
    def tlds():
        return {"presets": TLD_PRESETS, "all": ALL_TLDS}

    @app.get("/api/languages")
    def langs():
        return LANGUAGES

    @app.get("/api/config")
    def get_config():
        return get_public_config()

    @app.get("/api/config/resolved")
    def get_resolved_config(x_admin_token: str = Header(None), x_admin_password: str = Header(None)):
        # Only admin can see resolved secrets
        if not verify_admin_request(x_admin_password, x_admin_token):
            raise HTTPException(401, "admin auth required")
        from engine.config import load_resolved_config
        cfg = load_resolved_config()
        # mask key
        masked = dict(cfg)
        if masked.get("ai_api_key"):
            k = masked["ai_api_key"]
            masked["ai_api_key"] = k[:8] + "..." + k[-4:] if len(k) > 12 else "***"
        return masked

    @app.post("/api/admin/login")
    def admin_login(body: dict):
        pwd = body.get("password", "")
        cfg = load_config()
        if pwd != cfg.get("admin_password"):
            raise HTTPException(401, "wrong password")
        tok = create_admin_token()
        return {"ok": True, "token": tok, "expires_in": 24*3600}

    @app.get("/api/admin/me")
    def admin_me(x_admin_token: str = Header(None), x_admin_password: str = Header(None)):
        if verify_admin_request(x_admin_password, x_admin_token):
            return {"is_admin": True}
        return {"is_admin": False}

    @app.post("/api/admin/logout")
    def admin_logout(x_admin_token: str = Header(None)):
        # Just client discards token; we clean expired lazily
        return {"ok": True}

    @app.post("/api/config")
    def set_config(body: dict, x_admin_password: str = Header(None), x_admin_token: str = Header(None)):
        if not verify_admin_request(x_admin_password, x_admin_token):
            raise HTTPException(401, "bad admin auth — login first")
        cfg = load_config()
        for k in ["registrar_template","registrar_name","referral_code","ai_provider","ai_base_url","ai_model","ai_api_key","admin_password"]:
            if k in body:
                cfg[k] = body[k]
        save_config(cfg)
        return {"ok": True, "public": get_public_config()}

    @app.get("/api/env")
    def list_env(x_admin_token: str = Header(None), x_admin_password: str = Header(None)):
        if not verify_admin_request(x_admin_password, x_admin_token):
            raise HTTPException(401, "admin only")
        # List OPENCODE and related vars without leaking full keys
        keys = [k for k in os.environ.keys() if k.startswith("OPENCODE") or k.startswith("OPENAI") or k.startswith("PI_")]
        out = {}
        for k in sorted(keys):
            v = os.environ[k]
            # mask keys
            if "KEY" in k or "TOKEN" in k:
                out[k] = v[:6] + "***" + v[-4:] if len(v) > 12 else "***"
            else:
                out[k] = v
        return out

    @app.get("/api/history")
    def history(limit: int = 30):
        return list_history(limit)

    @app.get("/api/history/{hid}")
    def history_one(hid: str):
        e = get_entry(hid)
        if not e:
            raise HTTPException(404, "not found")
        return e

    @app.delete("/api/history/{hid}")
    def history_del(hid: str, x_admin_token: str = Header(None), x_admin_password: str = Header(None)):
        # Anyone can delete own history? For now allow all, but protect if needed
        ok = delete_entry(hid)
        if not ok:
            raise HTTPException(404, "not found")
        return {"ok": True}

    @app.post("/api/tune")
    async def tune(body: dict, x_user_ai_key: str = Header(None), x_user_ai_base: str = Header(None), x_user_ai_model: str = Header(None)):
        prompt = body.get("prompt", "")
        tuned = await ai_tune(prompt, body.get("user_ai_key") or x_user_ai_key or "", body.get("user_ai_base") or x_user_ai_base or "", body.get("user_ai_model") or x_user_ai_model or "")
        return {"tuned": tuned}

    @app.post("/api/generate")
    async def generate_names(req: GenerateRequest, request: Request):
        hdr_key = request.headers.get("x-user-ai-key") or ""
        hdr_base = request.headers.get("x-user-ai-base") or ""
        hdr_model = request.headers.get("x-user-ai-model") or ""
        user_key = req.user_ai_key or hdr_key
        user_base = req.user_ai_base or hdr_base
        user_model = req.user_ai_model or hdr_model

        t_start = time.time()
        params = {}
        if req.preset and req.preset in PRESETS:
            params.update(PRESETS[req.preset]["params"])
        if req.prompt:
            tuned = await ai_tune(req.prompt, user_key, user_base, user_model)
            for k, v in tuned.items():
                if k not in params:
                    if k == "keywords_hint":
                        if not req.keywords:
                            req.keywords = v
                        continue
                    params[k] = v
        for k in ["style_brandable","simplicity","length_min","length_max","syllables","strategies","language"]:
            v = getattr(req, k)
            if v is not None:
                params[k] = v
        tlds = req.tlds or ["com","cc","io","ai"]
        params.setdefault("style_brandable", 60)
        params.setdefault("simplicity", 60)
        params.setdefault("length_min", 4)
        params.setdefault("length_max", 10)
        params.setdefault("syllables", 3)
        params.setdefault("strategies", ["invented","mash","affix"])
        params.setdefault("language", "auto")

        keywords = req.keywords or req.prompt or "focus"
        # Pass ai_ratio / ai_count from request (or from params if tuner set them)
        _ratio = req.ai_ratio if req.ai_ratio is not None else params.get("ai_ratio")
        _acount = req.ai_count if req.ai_count is not None else params.get("ai_count")
        names, gen_stats = await generate(keywords, params, count=req.count, use_llm=req.use_llm, user_key=user_key, user_base=user_base, user_model=user_model, ai_ratio=_ratio, ai_count=_acount)

        scored = []
        for n in names:
            scored.append({
                "name": n,
                "display": n,
                "length": len(n.replace(" ","")),
                "pronounceable": pronounceable_score(n),
                "memorable": memorability_score(n),
            })

        domains = []
        domain_ms = 0
        if req.check_domains_flag:
            d0 = time.time()
            domains = await check_domains(names, tlds)
            domain_ms = round((time.time() - d0)*1000, 1)

        by_name = {}
        for d in domains:
            by_name.setdefault(d["name"], []).append(d)
        for s in scored:
            key = s["name"].replace(" ","").lower()
            ds = by_name.get(key, [])
            s["domains"] = ds
            avail = [x for x in ds if x["status"]=="available"]
            s["has_available"] = len(avail) > 0
            s["available_count"] = len(avail)

        total_ms = round((time.time() - t_start)*1000, 1)
        stats = {
            **gen_stats,
            "domain_ms": domain_ms,
            "total_ms": total_ms,
            "tlds": tlds,
            "domain_checked": len(domains),
            "available_total": sum(1 for d in domains if d["status"]=="available"),
        }

        cfg = load_config()
        registrar_template = cfg.get("registrar_template", "https://porkbun.com/checkout/search?q={domain}")
        entry = add_entry({
            "keywords": keywords,
            "prompt": req.prompt,
            "preset": req.preset,
            "params": params,
            "tlds": tlds,
            "count": req.count,
            "names": scored,
            "stats": stats,
            "registrar_template": registrar_template,
        })

        return {"id": entry["id"], "params": params, "keywords": keywords, "names": scored, "tlds": tlds, "stats": stats, "registrar_template": registrar_template}

    @app.get("/api/check")
    async def check(domain: str = Query(..., description="e.g. focalis.cc")):
        r = await check_single_domain(domain)
        return r

    @app.post("/api/check-batch")
    async def check_batch(body: dict):
        names = body.get("names", [])
        tlds = body.get("tlds", ["com","cc"])
        domains = await check_domains(names, tlds)
        return {"results": domains}

    @app.get("/api/referrals")
    def referrals():
        return {"registrars": list_registrars(), "global": get_public_config(), "shares": list_shares(10)}

    @app.post("/api/referrals/share")
    def referral_share(body: dict):
        # Anyone (admin or normal) can create a share — stores template, returns short code
        template = body.get("template", "").strip()
        name = body.get("registrar_name", "").strip() or "Custom"
        owner = body.get("owner", "anon")[:30]
        if not template or "{domain}" not in template:
            raise HTTPException(400, "template must contain {domain}")
        code = create_share(template, name, owner)
        return {"ok": True, "code": code, "share_url": f"/s/{code}", "full_url": f"{body.get('origin','')}?r={code}"}

    @app.get("/api/referrals/share/{code}")
    def referral_share_get(code: str):
        entry = get_share(code)
        if not entry:
            raise HTTPException(404, "share not found")
        return entry

    @app.get("/s/{code}", response_class=HTMLResponse)
    def share_redirect(code: str):
        entry = get_share(code)
        if not entry:
            return HTMLResponse("<h3>Share no encontrado</h3><a href='/'>Volver</a>", status_code=404)
        # Simple landing: sets localStorage referral and redirects to home with r param
        html = f"""<!doctype html><meta http-equiv="refresh" content="1;url=/?r={code}"><body style="font-family:system-ui;padding:20px;background:#0a0a0c;color:#f2f2f5">
        <h3>🔗 Referido: {entry['registrar_name']}</h3><p>Template: <code>{entry['template']}</code></p><p>Redirigiendo a <a href="/?r={code}" style="color:#7c5cff">name.studio?r={code}</a> ...</p>
        <script>try{{localStorage.setItem('shared_referral_template', `{entry['template']}`); localStorage.setItem('shared_referral_name', `{entry['registrar_name']}`); }}catch(e){{}}; setTimeout(()=> location.href='/?r={code}', 800)</script>
        </body>"""
        return HTMLResponse(html)

    @app.get("/api/health")
    def health():
        return {"ok": True, "public_config": get_public_config()}

    if WEB_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

        @app.get("/", response_class=HTMLResponse)
        def index():
            html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
            return HTMLResponse(html)

        @app.get("/admin", response_class=HTMLResponse)
        def admin():
            p = WEB_DIR / "admin.html"
            if p.exists():
                return HTMLResponse(p.read_text(encoding="utf-8"))
            return HTMLResponse("admin.html missing", status_code=404)

    return app

app = create_app()
