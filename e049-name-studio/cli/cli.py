from __future__ import annotations
import typer
from typing import Optional, List
import asyncio
import json
import random
import re

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

    async def _clean():
        params2 = {}
        if preset and preset in PRESETS:
            params2.update(PRESETS[preset]["params"])
            typer.echo(f"Preset {preset}: {PRESETS[preset]['label']}")
        if prompt:
            tuned = await ai_tune(prompt)
            for k,v in tuned.items():
                if k=="keywords_hint":
                    if not keywords:
                        tuned_keywords = v  # will use below
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
        names, stats = await gen_async(kw, params2, count=count, use_llm=use_llm)
        typer.echo(f"\nGenerated {len(names)} names for '{kw}' {params2}:")
        for n in names: typer.echo(f"  {n}")
        typer.echo(f"  stats: {stats}")
        if check:
            doms=await check_domains(names, tld_list)
            avail=[d for d in doms if d["status"]=="available"]
            typer.echo(f"\n=== AVAILABLE ({len(avail)}/{len(doms)}) ===")
            for d in avail: typer.echo(f"  ✅ {d['domain']} {d['price']} {d['detail']}")
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

# ── NEW: shortest / hunt — find the shortest available domain ──

def _brute_short_names(length: int, count: int, rng: random.Random) -> List[str]:
    """Generate pronounceable short candidates for brute mode.
    Uses CVC patterns + vowel/consonant alternation to maximize pronounceability,
    avoiding pure random like 'qxw' which will never be brandable."""
    vowels = "aeiou"
    consonants = "bdfghklmnpstrvwz"
    # common short pronounceable pools
    out = set()
    attempts = 0
    while len(out) < count and attempts < count * 10:
        attempts += 1
        if length == 3:
            # patterns: CVC, VCV, CVV
            pat = rng.choice(["CVC", "VCV", "CVV", "CVC"])
            name = ""
            for ch in pat:
                if ch == "C":
                    name += rng.choice(consonants)
                else:
                    name += rng.choice(vowels)
        elif length == 4:
            pat = rng.choice(["CVCV", "VCVC", "CVVC", "CVCV", "CVCC"])
            name = ""
            for ch in pat:
                if ch == "C":
                    name += rng.choice(consonants)
                else:
                    name += rng.choice(vowels)
        elif length == 5:
            pat = rng.choice(["CVCVC", "VCVCV", "CVVCV"])
            name = ""
            for ch in pat:
                if ch == "C":
                    name += rng.choice(consonants)
                else:
                    name += rng.choice(vowels)
        else:
            # fallback: random but vowel-balanced
            name = "".join(rng.choice(vowels + consonants) for _ in range(length))
        # avoid double same letter at start, no 'q' without 'u', etc.
        if len(name) != length:
            continue
        if re.search(r"(.)\1\1", name):
            continue
        out.add(name)
    # also inject some pure engine-style syllable combos for variety
    syllables = ["lu","ma","fo","ca","vi","na","zo","ra","li","si","no","pa","te","bo","mi","la","so","re","ki","mo"]
    while len(out) < count:
        syl_count = 2 if length <= 4 else 3
        name = "".join(rng.choice(syllables) for _ in range(syl_count))
        name = name[:length]
        if len(name) == length:
            out.add(name)
    return list(out)[:count]

@app.command(name="hunt")
def hunt(
    keywords: str = typer.Argument("", help="Keywords / idea e.g. 'app studio' (optional, for context)"),
    min_length: int = typer.Option(3, "--min", help="Min name length (3-6)"),
    max_length: int = typer.Option(5, "--max", help="Max name length (3-8)"),
    tlds: str = typer.Option("cc,com,co,xyz,site,online,app,dev,net,org,me", help="Comma TLDs (default = cheap ≤$15 only; add io/ai manually if you accept premium)"),
    per_length: int = typer.Option(30, help="Candidates per length (total = per_length * lengths)"),
    brute: bool = typer.Option(False, help="Brute-force pronounceable enumeration for 3-4 chars instead of engine"),
    use_llm: bool = typer.Option(False, help="Use LLM to generate (adds brandable variety, slower)"),
    prompt: Optional[str] = typer.Option(None, help="Natural language prompt to tune generation"),
    lang: str = typer.Option("auto", help="Language bias for engine"),
    top: int = typer.Option(15, help="Show top N shortest available"),
    max_price: int = typer.Option(15, "--max-price", help="Max renewal price USD (filters TLDs, e.g. 15 = standard only, 70 = include io/ai)"),
    cheap_only: bool = typer.Option(True, "--cheap/--no-cheap", help="Only show ≤max-price TLDs (default cheap)"),
):
    """Hunt the shortest available domain — ideal for an umbrella domain for many apps.

    Searches incrementally by length (min→max) and ranks by total domain length (name+TLD).
    Example:
      ./bin/cli.sh hunt --min 3 --max 5 --tlds cc,io,ai --per-length 30
      ./bin/cli.sh hunt \"mi estudio\" --brute --tlds cc,io
    """
    from engine.presets import ai_tune
    from engine.generate import generate as gen_async
    from engine.domain import check_domains
    from engine.scoring import pronounceable_score, memorability_score

    # filter TLDs by max_price if cheap_only
    raw_tlds = [t.strip().lstrip(".") for t in tlds.split(",") if t.strip()]
    if not raw_tlds:
        typer.echo("No TLDs given", err=True)
        raise typer.Exit(1)
    if cheap_only:
        from engine.domain import TLD_PRICE_NUM
        filtered = []
        skipped = []
        for t in raw_tlds:
            price = TLD_PRICE_NUM.get(t)
            if price is None:
                filtered.append(t)  # unknown price, keep but warn
            elif price <= max_price:
                filtered.append(t)
            else:
                skipped.append(f"{t}(${price})")
        if skipped:
            typer.echo(f"  💰 filtro ≤${max_price}: excluidos {', '.join(skipped)} — usa --no-cheap o --max-price 70 para incluirlos")
        tld_list = filtered if filtered else raw_tlds
        if not tld_list:
            typer.echo("All TLDs filtered by price — use --no-cheap", err=True)
            raise typer.Exit(1)
    else:
        tld_list = raw_tlds
    if min_length < 2: min_length = 2
    if max_length < min_length: max_length = min_length
    if max_length > 12: max_length = 12

    async def _run():
        rng = random.Random()
        # tuning from prompt if given
        tuned_params = {}
        kw = keywords or prompt or "app"
        if prompt:
            tuned = await ai_tune(prompt)
            if tuned:
                typer.echo(f"AI tuned: {tuned}")
                for k,v in tuned.items():
                    if k == "keywords_hint":
                        if not keywords:
                            kw = v
                        continue
                    tuned_params[k]=v

        typer.echo(f"\n🎯 HUNT shortest domain {min_length}–{max_length} chars | TLDs: {tld_list} | per_length={per_length} | brute={brute} | keywords='{kw}'")
        typer.echo(f"   Total candidates ~ {(max_length-min_length+1)*per_length} names × {len(tld_list)} TLDs = ~{(max_length-min_length+1)*per_length*len(tld_list)} checks\n")

        all_names: List[str] = []
        per_len_names = {}
        for length in range(min_length, max_length+1):
            if brute and length <= 4:
                names = _brute_short_names(length, per_length, rng)
                typer.echo(f"  length {length}: brute {len(names)} → {names[:8]} ...")
            else:
                params = {
                    "style_brandable": tuned_params.get("style_brandable", 85),
                    "simplicity": tuned_params.get("simplicity", 85),
                    "length_min": length,
                    "length_max": length,
                    "syllables": 2 if length <= 5 else 3,
                    "strategies": tuned_params.get("strategies", ["invented"]),
                    "language": tuned_params.get("language", lang),
                }
                # keep length strict
                # generate_sync would shuffle, use async generate
                names_list, stats = await gen_async(kw, params, count=per_length, use_llm=use_llm)
                # filter strictly to exact length (engine may deviate slightly)
                names = [n for n in names_list if len(n.replace(" ","").replace("-","")) == length]
                # if not enough, top up with brute
                if len(names) < per_length * 0.6:
                    extra = _brute_short_names(length, per_length - len(names), rng)
                    names += extra
                names = names[:per_length]
                typer.echo(f"  length {length}: engine {len(names)} → {names[:8]} ...  {stats.get('blend','')}")
            per_len_names[length] = names
            all_names.extend(names)

        # dedupe
        seen = set()
        uniq = []
        for n in all_names:
            k = n.lower().replace(" ","").replace("-","")
            if k not in seen:
                seen.add(k)
                uniq.append(k)
        all_names = uniq
        typer.echo(f"\nChecking {len(all_names)} names × {len(tld_list)} TLDs ... (RDAP + DNS, cached 24h)\n")

        domains = await check_domains(all_names, tld_list)

        # score and sort by total length (name + tld + dot)
        for d in domains:
            name = d["name"]
            total = len(name) + 1 + len(d["tld"])
            d["total_len"] = total
            d["pronounceable"] = pronounceable_score(name)
            d["memorable"] = memorability_score(name)

        # sort available first by total_len, then pronounceable desc, then name
        available = [d for d in domains if d["status"] == "available"]
        taken = [d for d in domains if d["status"] == "taken"]
        unknown = [d for d in domains if d["status"] == "unknown"]

        available_sorted = sorted(available, key=lambda x: (x["total_len"], -x["pronounceable"], x["domain"]))
        taken_sorted = sorted(taken, key=lambda x: (x["total_len"], x["domain"]))
        unknown_sorted = sorted(unknown, key=lambda x: (x["total_len"], x["domain"]))

        typer.echo(f"=== ✅ AVAILABLE ({len(available_sorted)}/{len(domains)}) — shortest first ===")
        if not available_sorted:
            typer.echo("  (none found — try larger --max or different --tlds, or --brute)")
        else:
            for d in available_sorted[:top]:
                typer.echo(f"  ✅ {d['domain']:18}  total={d['total_len']:2}  ({len(d['name'])}+{len(d['tld'])})  pron={d['pronounceable']:2}  mem={d['memorable']:2}  {d['price']:4}  {d['detail']}")
            if len(available_sorted) > top:
                typer.echo(f"  ... +{len(available_sorted)-top} more available (use --top {len(available_sorted)} to see all)")

            # umbrella recommendation: shortest + most pronounceable
            best = available_sorted[0]
            typer.echo(f"\n🏆 SHORTEST UMBRELLA PICK: {best['domain']}  (total {best['total_len']} chars, name {len(best['name'])} + TLD {best['tld']})")
            typer.echo(f"   → ideal for subdomains:  app1.{best['domain']}, app2.{best['domain']}  or  {best['domain']}/app1")
            # also show best per TLD
            typer.echo(f"\n📌 Best per TLD (shortest available):")
            seen_tld = set()
            for d in available_sorted:
                if d["tld"] not in seen_tld:
                    typer.echo(f"   .{d['tld']:6} → {d['domain']:18}  total {d['total_len']}  pron {d['pronounceable']}")
                    seen_tld.add(d["tld"])
                if len(seen_tld) >= len(tld_list):
                    break

        if taken_sorted:
            typer.echo(f"\n=== ❌ TAKEN sample ({len(taken_sorted)}) shortest ===")
            for d in taken_sorted[:6]:
                typer.echo(f"  ❌ {d['domain']:18} total={d['total_len']}")

        if unknown_sorted:
            typer.echo(f"\n=== ? UNKNOWN ({len(unknown_sorted)}) ===")
            for d in unknown_sorted[:6]:
                typer.echo(f"  ? {d['domain']:18} {d['detail']}")

        # summary stats
        typer.echo(f"\n📊 Summary: checked {len(domains)} | available {len(available)} | taken {len(taken)} | unknown {len(unknown)}")
        # hint for next step
        if available_sorted:
            example = available_sorted[0]["domain"]
            typer.echo(f"\n💡 Next: ./bin/cli.sh check {example}  — or open https://porkbun.com/checkout/search?q={example}")

    asyncio.run(_run())

@app.command(name="shortest")
def shortest(
    keywords: str = typer.Argument("", help="Keywords"),
    min_length: int = typer.Option(3, "--min"),
    max_length: int = typer.Option(5, "--max"),
    tlds: str = typer.Option("cc,com,co,xyz,site,online,app,dev,net,org,me", help="TLDs"),
    per_length: int = typer.Option(30, help="Per length"),
    brute: bool = typer.Option(False, help="Brute"),
    use_llm: bool = typer.Option(False, help="Use LLM"),
    prompt: Optional[str] = typer.Option(None),
    lang: str = typer.Option("auto"),
    top: int = typer.Option(15),
    max_price: int = typer.Option(15, "--max-price"),
    cheap_only: bool = typer.Option(True, "--cheap/--no-cheap"),
):
    """Alias for hunt."""
    hunt(keywords, min_length, max_length, tlds, per_length, brute, use_llm, prompt, lang, top, max_price, cheap_only)

if __name__=="__main__":
    app()
