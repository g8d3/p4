"""Simple scoring helpers."""
import re

def pronounceable_score(name: str) -> int:
    """0-100, higher = easier to pronounce. Penalize consonant clusters, numbers."""
    n = name.lower().replace(" ","")
    if any(c.isdigit() for c in n):
        return 60
    # consonant clusters >3
    clusters = re.findall(r"[^aeiou]{4,}", n)
    if clusters:
        return 50
    # alternation
    vowels = sum(1 for c in n if c in "aeiou")
    ratio = vowels / max(1, len(n))
    if 0.35 < ratio < 0.55:
        return 90
    if 0.25 < ratio < 0.65:
        return 75
    return 60

def memorability_score(name: str) -> int:
    # short + pronounceable = memorable
    l = len(name.replace(" ",""))
    base = 90 if 4 <= l <= 7 else 70 if l <= 9 else 55
    p = pronounceable_score(name)
    return int(base * 0.5 + p * 0.5)
