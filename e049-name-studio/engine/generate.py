"""Core name generation engine. Pure python, deterministic + optional LLM."""
from __future__ import annotations
import random
import re
import os
import hashlib
import time
from typing import List, Dict, Any, Tuple

# Phonetic building blocks
SIMPLE_SYLLABLES = ["lu","ma","fo","ca","vi","na","zo","ra","li","si","no","pa","te","bo","mi","la","so","re","ki","mo"]
REBUSCADO_SYLLABLES = ["foc","aur","vel","lum","cor","nex","ori","ae","alis","ora","iva","eus","aris","enta","elio","uvia","oria"]
PREFIXES = ["get","try","my","go","use","hey","neo","re","co","hyper","open"]
SUFFIXES = ["ly","io","os","us","ia","ora","alis","is","a","o","ero","ivo","ico","ar","en"]
LATIN_ROOTS = ["focal","lumin","veloc","oralis","coral","novus","clarus","vivus","aurum","verus","solus","caelum"]
EN_ROOTS = ["focus","lens","frame","clip","light","view","pixel","story","shot","scene","vibe","flow","cast","nova","pulse","forge","craft"]

NUM_SUFFIXES = ["7","301","99","01","42","8","365","24"]

def _clean(s: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", "", s.lower())
    return s.strip()

def _keywords_from_input(keywords: str) -> List[str]:
    if not keywords:
        return []
    parts = re.findall(r"[a-z0-9]+", keywords.lower())
    return [p for p in parts if len(p) >= 2][:8]

def _syllable_count(word: str) -> int:
    return max(1, len(re.findall(r"[aeiou]+", word.lower())))

def _filter_by_params(names: List[str], params: Dict[str, Any]) -> List[str]:
    lmin = params.get("length_min", 4)
    lmax = params.get("length_max", 12)
    syl = params.get("syllables")
    filtered = []
    for n in names:
        pure = n.replace(" ", "").replace("-", "")
        if not (lmin <= len(pure) <= lmax):
            continue
        if syl and abs(_syllable_count(pure) - syl) > 1:
            continue
        filtered.append(n)
    return filtered

def _gen_invented(params: Dict[str, Any], keywords: List[str], n: int, rng: random.Random) -> List[str]:
    simplicity = params.get("simplicity", 50)
    language = params.get("language", "auto")
    roots = []
    if keywords:
        for k in keywords:
            roots.append(k[:5])
            roots.append(k)
    if language == "latin" or (language == "auto" and simplicity < 40):
        roots += LATIN_ROOTS
        syllables = REBUSCADO_SYLLABLES if simplicity < 50 else SIMPLE_SYLLABLES + REBUSCADO_SYLLABLES[:4]
        suffixes = ["alis","alis","ora","iva","eus","is","ia","ora","us"]
    else:
        roots += EN_ROOTS
        syllables = SIMPLE_SYLLABLES if simplicity > 60 else SIMPLE_SYLLABLES + REBUSCADO_SYLLABLES[:3]
        suffixes = SUFFIXES
    out = []
    for _ in range(n):
        if rng.random() < 0.3:
            syl_count = 2 if simplicity > 60 else 3
            name = "".join(rng.choice(syllables) for _ in range(syl_count))
        else:
            root = rng.choice(roots)
            if len(root) > 6 and rng.random() < 0.5:
                root = root[: rng.randint(3,5)]
            suf = rng.choice(suffixes)
            name = root + suf
            if len(name) > params.get("length_max", 12):
                name = name[: params.get("length_max", 12)]
        name = re.sub(r"[^a-z0-9]", "", name.lower())
        if len(name) >= 3:
            out.append(name)
    return out

def _gen_mash(params: Dict[str, Any], keywords: List[str], n: int, rng: random.Random) -> List[str]:
    pools = keywords + EN_ROOTS + LATIN_ROOTS[:4]
    if len(pools) < 2:
        pools = EN_ROOTS
    out = []
    for _ in range(n):
        a, b = rng.sample(pools, 2)
        cut_a = rng.randint(2, max(2, len(a)-1))
        cut_b = rng.randint(1, max(1, len(b)-1))
        name = a[:cut_a] + b[cut_b:]
        name = re.sub(r"[^a-z0-9]", "", name.lower())
        out.append(name)
    return out

def _gen_two_words(params: Dict[str, Any], keywords: List[str], n: int, rng: random.Random) -> List[str]:
    pools = keywords if len(keywords) >= 2 else keywords + EN_ROOTS
    if len(pools) < 2:
        pools = EN_ROOTS
    out = []
    for _ in range(n):
        a, b = rng.sample(pools, 2)
        if rng.random() < 0.5:
            b = rng.choice(["studio","labs","works","hub","flow","cast","forge","craft","house","space","grid","field"])
        name = f"{a} {b}"
        out.append(name.lower())
    return out

def _gen_affix(params: Dict[str, Any], base_names: List[str], n: int, rng: random.Random) -> List[str]:
    out = []
    for _ in range(n):
        base = rng.choice(base_names) if base_names else rng.choice(EN_ROOTS)
        base = base.replace(" ", "")
        if rng.random() < 0.5:
            pre = rng.choice(PREFIXES)
            name = pre + base
        else:
            suf = rng.choice(SUFFIXES)
            name = base + suf
        out.append(re.sub(r"[^a-z0-9]", "", name.lower()))
    return out

def _gen_numbers(params: Dict[str, Any], base_names: List[str], n: int, rng: random.Random) -> List[str]:
    out = []
    for _ in range(n):
        base = rng.choice(base_names) if base_names else rng.choice(EN_ROOTS)
        base = base.replace(" ", "")
        suf = rng.choice(NUM_SUFFIXES)
        name = base + suf
        out.append(name.lower())
    return out

def _gen_latin(params: Dict[str, Any], keywords: List[str], n: int, rng: random.Random) -> List[str]:
    out = []
    for _ in range(n):
        root = rng.choice(LATIN_ROOTS + (keywords if keywords else []))
        suf = rng.choice(["alis","alis","ora","iva","us","is","aris","entia","or","ium"])
        name = (root[:5] if len(root) > 6 else root) + suf
        out.append(re.sub(r"[^a-z0-9]", "", name.lower()))
    return out

async def _gen_llm(params: Dict[str, Any], keywords: List[str], n: int, user_key: str = "", user_base: str = "", user_model: str = "") -> Tuple[List[str], float, bool]:
    """Returns (names, elapsed_ms, used)"""
    start = time.time()
    # priority: user_key > admin config (with env interpolation) > direct env
    from engine.config import load_resolved_config, resolve_value
    cfg = load_resolved_config()
    api_key = user_key or resolve_value(cfg.get("ai_api_key")) or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENCODE_API_KEY") or ""
    base_url = user_base or resolve_value(cfg.get("ai_base_url")) or os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENCODE_GO_BASE_URL") or "https://api.openai.com/v1"
    model = user_model or resolve_value(cfg.get("ai_model")) or os.environ.get("OPENAI_MODEL") or os.environ.get("OPENCODE_GO_MODEL") or "gpt-4o-mini"
    # Expand in case still contains ${VAR}
    api_key = resolve_value(api_key) if api_key else api_key
    base_url = resolve_value(base_url) if base_url else base_url
    model = resolve_value(model) if model else model
    if not api_key:
        return [], 0, False
    try:
        import httpx
        style = params.get("style_brandable", 50)
        simp = params.get("simplicity", 50)
        lang = params.get("language", "auto")
        lmax = params.get("length_max", 8)
        try:
            _s = params.get("strategies")
            if not _s:
                _s = []
            strat = ",".join(_s) if isinstance(_s, list) else str(_s)
        except Exception as e:
            try:
                with open('/tmp/llm_debug.log','a') as f:
                    f.write(f"  strat join outer failed {e}\n")
            except: pass
            strat = ""
        prompt = f"""Generate {n} brand name candidates.
Keywords: {', '.join(keywords) or 'general tech'}
Params: brandable={style}/100 (100=invented like focalis, 0=descriptive), simplicity={simp}/100 (100=simple like luma, 0=rebuscado like veliora), max_len={lmax}, strategies={strat}, language={lang}
Rules:
- Each name lowercase, no spaces unless strategy is two_words
- Length {params.get('length_min',4)}-{lmax} chars (without space)
- If brandable>70, invent 1-word names, latin-style allowed. If <30, descriptive 1-2 words.
- Return ONLY a JSON array of strings, no markdown, e.g. ["focalis","luma","focus lens"]"""

        # Fallback models if primary fails (Muse is currently 500 on opencode)
        models_to_try = [model]
        if model == "muse-spark-1.2-contributor":
            models_to_try += ["deepseek-v4-flash", "glm-5", "qwen3.7-max"]
        # also add generic fallback if model not in list
        elif model not in ["deepseek-v4-flash", "glm-5", "qwen3.7-max"]:
            models_to_try += ["deepseek-v4-flash"]
        last_elapsed = 0
        last_status = None
        for m in models_to_try:
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.post(
                        f"{base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={
                            "model": m,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.9,
                            "max_tokens": 800,
                        },
                    )
                    elapsed = (time.time() - start) * 1000
                    last_elapsed = elapsed
                    last_status = resp.status_code
                    if resp.status_code != 200:
                        # try next model on 5xx/4xx
                        if m != models_to_try[-1]:
                            continue
                        return [], elapsed, True
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    import json as js
                    mm = re.search(r"\[.*\]", text, re.S)
                    if not mm:
                        if m != models_to_try[-1]: continue
                        return [], elapsed, True
                    arr = js.loads(mm.group(0))
                    cleaned = []
                    for x in arr:
                        if isinstance(x, str):
                            x = x.lower().strip()
                            x = re.sub(r"[^a-z0-9 ]", "", x)[:20].strip()
                            if 3 <= len(x.replace(" ","")) <= 14:
                                cleaned.append(x)
                    if not cleaned and m != models_to_try[-1]:
                        continue
                    return cleaned[:n], elapsed, True
            except Exception as e:
                last_elapsed = (time.time()-start)*1000
                if m == models_to_try[-1]:
                    return [], last_elapsed, True
                continue
        return [], last_elapsed, True
    except Exception:
        return [], (time.time()-start)*1000, True

def _dedupe(names: List[str]) -> List[str]:
    seen = set()
    out = []
    for n in names:
        key = n.lower().replace(" ", "").replace("-", "")
        if key not in seen and 3 <= len(key) <= 14:
            seen.add(key)
            out.append(n.lower().strip())
    return out

def generate_sync(keywords: str, params: Dict[str, Any], count: int = 40, seed: int | None = None) -> List[str]:
    kw_list = _keywords_from_input(keywords)
    if seed is None:
        # Use fresh randomness each call (variety on repeated clicks) — hash only as fallback if caller wants reproducibility
        import secrets
        seed = secrets.randbits(31) ^ int(time.time() * 1000) & 0x7fffffff
    rng = random.Random(seed)
    strategies = params.get("strategies", ["invented","mash","affix"])
    if isinstance(strategies, str):
        strategies = [strategies]
    per = max(5, count // max(1, len(strategies)))
    all_names: List[str] = []
    base_pool = kw_list + EN_ROOTS[:4]
    for strat in strategies:
        if strat == "invented":
            all_names += _gen_invented(params, kw_list, per, rng)
        elif strat == "mash":
            all_names += _gen_mash(params, kw_list, per, rng)
        elif strat == "two_words":
            all_names += _gen_two_words(params, kw_list, per, rng)
        elif strat == "affix":
            all_names += _gen_affix(params, base_pool, per, rng)
        elif strat == "numbers":
            all_names += _gen_numbers(params, base_pool, per, rng)
        elif strat == "latin":
            all_names += _gen_latin(params, kw_list, per, rng)
    while len(all_names) < count:
        all_names += _gen_invented(params, kw_list, 10, rng)
    all_names = _dedupe(all_names)
    filtered = _filter_by_params(all_names, params)
    if len(filtered) < count * 0.6:
        filtered = all_names
    rng.shuffle(filtered)
    return filtered[:count]

async def generate(keywords: str, params: Dict[str, Any], count: int = 40, seed: int | None = None, use_llm: bool = True, user_key: str = "", user_base: str = "", user_model: str = "", ai_ratio: int | None = None, ai_count: int | None = None) -> Tuple[List[str], Dict[str, Any]]:
    """Returns (names, stats) where stats has timing + breakdown.
    ai_ratio: 0-100 % of LLM vs algo. If None, auto 50% when use_llm and count>20 else count.
    ai_count: explicit LLM count (overrides ratio if given).
    """
    stats: Dict[str, Any] = {}
    t0 = time.time()
    # Determine target LLM count before generating algo pool (algo pool is always full count for blending flexibility)
    if not use_llm:
        target_llm = 0
    elif ai_count is not None:
        target_llm = max(0, min(count, int(ai_count)))
    elif ai_ratio is not None:
        target_llm = max(0, min(count, round(count * int(ai_ratio) / 100)))
    else:
        # default: 50% when has key, else 0 handled by _gen_llm
        target_llm = count // 2 if count > 20 else count
    # Also allow params to carry ai_ratio/ai_count
    if ai_ratio is None and "ai_ratio" in params:
        try:
            target_llm = max(0, min(count, round(count * int(params["ai_ratio"]) / 100)))
        except: pass
    if ai_count is None and "ai_count" in params:
        try:
            target_llm = max(0, min(count, int(params["ai_count"])))
        except: pass
    stats["target_llm"] = target_llm
    stats["target_algo"] = count - target_llm
    stats["ai_ratio"] = round(target_llm / count * 100) if count else 0
    algo_start = time.time()
    algo = generate_sync(keywords, params, count=count, seed=seed)
    algo_ms = (time.time() - algo_start) * 1000
    stats["algo_ms"] = round(algo_ms, 1)
    stats["algo_count"] = len(algo)
    llm_names: List[str] = []
    llm_ms = 0
    llm_used = False
    if use_llm and target_llm > 0:
        llm_names, llm_ms, llm_used = await _gen_llm(params, _keywords_from_input(keywords), target_llm, user_key, user_base, user_model)
        stats["llm_ms"] = round(llm_ms, 1)
        stats["llm_used"] = llm_used
        stats["llm_count"] = len(llm_names)
        stats["llm_model"] = (user_model or "auto")
    else:
        stats["llm_used"] = False
        stats["llm_count"] = 0
        stats["llm_ms"] = 0
    if llm_names:
        blended: List[str] = []
        i = j = 0
        while len(blended) < count and (i < len(llm_names) or j < len(algo)):
            if i < len(llm_names) and (len(blended) % 2 == 0 or j >= len(algo)):
                blended.append(llm_names[i]); i += 1
            elif j < len(algo):
                blended.append(algo[j]); j += 1
        blended = _dedupe(blended)
        if len(blended) < count:
            blended += [x for x in algo if x not in blended]
        result = blended[:count]
        stats["blend"] = "algo+llm"
    else:
        result = algo
        stats["blend"] = "algo-only" if not llm_used else "algo (llm failed)"
    stats["total_gen_ms"] = round((time.time() - t0)*1000, 1)
    stats["total_count"] = len(result)
    return result, stats
