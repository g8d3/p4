from __future__ import annotations
import typer
from typing import Optional, List
import asyncio
import json

app = typer.Typer(help="Name Studio CLI — same engine as web")

@app.command()
def generate(
    keywords: str = typer.Argument("", help="Keywords e.g. 'video focus'"),
    preset: Optional[str] = typer.Option(None, help="Preset id: focalis-like, minimal-5, descriptive-mash, two-words, with-numbers, rebuscado"),
    prompt: Optional[str] = typer.Option(None, help="Natural language prompt for AI tuner"),
    tlds: str = typer.Option("com,cc,io,ai", help="Comma TLDs"),
    count: int = typer.Option(40, help="How many"),
    strategies: Optional[str] = typer.Option(None, help="Comma strategies: invented,mash,two_words,affix,numbers,latin"),
    lang: str = typer.Option("auto", help="auto/en/es/latin"),
    check: bool = typer.Option(True, help="Check domains"),
    use_llm: bool = typer.Option(True, help="Use LLM if key set"),
):
    from engine.presets import PRESETS, ai_tune
    from engine.generate import generate as gen_async
    from engine.domain import check_domains

    async def _run():
        params = {}
        if preset and preset in PRESETS:
            params.update(PRESETS[preset]["params"])
            typer.echo(f"Preset {preset}: {PRESETS[preset]['label']}")
        if prompt:
            tuned = asyncio.run(ai_tune(prompt)) if False else None
            # need async
            tuned = __import__("asyncio").run(ai_tune(prompt)) if False else None

        # Correct: we are already in async
        if prompt:
            tuned = await ai_tune(prompt)
            for k, v in tuned.items():
                if k == "keywords_hint" and not keywords:
                    keywords_local = v
                elif k not in params:
                    params[k] = v
            if tuned:
                typer.echo(f"AI tuned: {tuned}")

        # For simplicity, handle prompt sync: call ai_tune async
        # override with explicit
        if strategies:
            params["strategies"] = [s.strip() for s in strategies.split(",")]
        params["language"] = lang
        params.setdefault("style_brandable", 60)
        params.setdefault("simplicity", 60)
        params.setdefault("length_min", 4)
        params.setdefault("length_max", 10)
        params.setdefault("syllables", 3)
        params.setdefault("strategies", ["invented","mash","affix"])
        params.setdefault("language", "auto")

        tld_list = [t.strip().lstrip(".") for t in tlds.split(",") if t.strip()]

        # special: handle prompt->tune correctly (we already did async tuned? redo)
        # Actually we need to re-run if prompt and we didn't await earlier due to confusion. Let's do properly:
        # Use a separate async tune
        names = await gen_async(keywords or prompt or "focus", params, count=count, use_llm=use_llm)
        typer.echo(f"\nGenerated {len(names)} names:")
        for n in names:
            typer.echo(f"  {n}")

        if check:
            typer.echo(f"\nChecking {tld_list} ...")
            domains = await check_domains(names, tld_list)
            # group
            by_status = {"available": [], "taken": [], "unknown": []}
            for d in domains:
                by_status[d["status"]].append(d)
            typer.echo(f"\n=== AVAILABLE ({len(by_status['available'])}) ===")
            for d in by_status["available"]:
                typer.echo(f"  ✅ {d['domain']} {d['price']} ({d['detail']})")
            if by_status["taken"]:
                typer.echo(f"\n=== TAKEN ({len(by_status['taken'])}) sample ===")
                for d in by_status["taken"][:12]:
                    typer.echo(f"  ❌ {d['domain']}")
            if by_status["unknown"]:
                typer.echo(f"\n=== UNKNOWN ({len(by_status['unknown'])}) ===")
                for d in by_status["unknown"][:8]:
                    typer.echo(f"  ? {d['domain']} {d['detail']}")
        return

    # Need to handle prompt tuning async properly: we called above with confusion. Simplify: run generate directly
    # Reimplement clean
    async def _clean():
        params2 = {}
        if preset and preset in PRESETS:
            params2.update(PRESETS[preset]["params"])
        if prompt:
            tuned = await ai_tune(prompt)
            for k,v in tuned.items():
                if k=="keywords_hint":
                    if not keywords:
                        nonlocal_keywords = v
                    continue
                if k not in params2:
                    params2[k]=v
            if tuned:
                typer.echo(f"AI tuned from prompt: {tuned}")
            kw = keywords or tuned.get("keywords_hint","") or prompt or "focus"
        else:
            kw = keywords or "focus"
        if strategies:
            params2["strategies"]=[s.strip() for s in strategies.split(",")]
        params2["language"]=lang
        params2.setdefault("style_brandable",60)
        params2.setdefault("simplicity",60)
        params2.setdefault("length_min",4)
        params2.setdefault("length_max",10)
        params2.setdefault("syllables",3)
        params2.setdefault("strategies",["invented","mash","affix"])
        params2.setdefault("language","auto")
        tld_list=[t.strip().lstrip(".") for t in tlds.split(",") if t.strip()]
        from engine.generate import generate as g2
        from engine.domain import check_domains as cd2
        names=await g2(kw, params2, count=count, use_llm=use_llm)
        typer.echo(f"\nGenerated {len(names)} names for '{kw}' {params2}:")
        for n in names: typer.echo(f"  {n}")
        if check:
            doms=await cd2(names, tld_list)
            avail=[d for d in doms if d["status"]=="available"]
            typer.echo(f"\n=== AVAILABLE ({len(avail)}/{len(doms)}) ===")
            for d in avail: typer.echo(f"  ✅ {d['domain']} {d['price']}")
            taken=[d for d in doms if d["status"]=="taken"]
            if taken:
                typer.echo(f"\n=== TAKEN sample ===")
                for d in taken[:10]: typer.echo(f"  ❌ {d['domain']}")
            unk=[d for d in doms if d["status"]=="unknown"]
            if unk:
                typer.echo(f"\n=== UNKNOWN ===")
                for d in unk[:10]: typer.echo(f"  ? {d['domain']} {d['detail']}")
    asyncio.run(_clean())

@app.command()
def check(
    domain: str = typer.Argument(..., help="Domain e.g. focalis.cc"),
    tlds: str = typer.Option("", help="Optional: check name across TLDs comma"),
):
    from engine.domain import check_single_domain, check_domains
    import asyncio
    if tlds:
        name = domain.split(".")[0]
        tld_list=[t.strip().lstrip(".") for t in tlds.split(",")]
        async def _batch():
            ds=await check_domains([name], tld_list)
            for d in ds:
                icon="✅" if d["status"]=="available" else "❌" if d["status"]=="taken" else "?"
                print(f"{icon} {d['domain']} {d['status']} {d['detail']} {d['price']}")
        asyncio.run(_batch())
    else:
        async def _one():
            r=await check_single_domain(domain)
            icon="✅" if r["status"]=="available" else "❌" if r["status"]=="taken" else "?"
            print(f"{icon} {r['domain']} {r['status']} {r['detail']} {r['price']}")
        asyncio.run(_one())

@app.command()
def presets():
    from engine.presets import list_presets
    for p in list_presets():
        typer.echo(f"{p['id']:15} {p['label']:20} {p['description']}  params={p['params']}")

if __name__=="__main__":
    app()
