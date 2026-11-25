#!/usr/bin/env python3
"""Read an `ads.report` fingerprint: which word is that 8-hex hash?

The page never sends the disclosure word — it sends `h=<8 hex>` of any short text in
a post's header (see `adsReport` in `extension/content.js`), so a word this product has
not learned yet can still be identified from the owner's phone without shipping text,
a handle or a post.

    python3 bin/ads_hash.py d3f1a2b4 1a2b3c4d ...
    python3 bin/ads_hash.py --sql "articles=8 marked=0 ..."   # takes the detail string

Exit code 2 when a hash matches nothing: that word is not in the dictionary yet, and
adding it (with the fixture of its shape) is the fix.
"""
import re
import sys

# Every disclosure word this product has seen, plus the decorated forms the apps
# print around them. Normalized the same way the content script normalizes: decoration
# stripped, letters kept. `Ad` first: it is what a phone prints.
WORDS = """
Ad Advert Advertisement Sponsored Promoted Promotion
Anuncio Anuncios Publicidad Promocionado Patrocinado Promocionada
Anzeige Werbung Gesponsert Beworben
Annonce Publicité Sponsorisé Sponsorisée Promu
Annuncio Pubblicità Sponsorizzato Promosso
Anúncio Publicidade Patrocinado Promovido
Sponsorlu Tanıtım Promosyon
Реклама Продвигается Спонсор
Spodstwuowany Reklama Promowane
推广 广告 赞助 廣告
プロモーション 広告 プロモ
홍보 광고 스폰서
إعلان مُموَّل
מודעה ממומן
διαφήμιση χορηγούμενο
Hirdetés Szponzorált
Reklama Sponzorirano
Mainos Sponsoroitu
Annonse Sponset
Reklam Annons Sponsrad
"""


def norm(t):
    """Mirror `adNorm` in content.js: strip decoration, keep letters."""
    out = re.sub(r"[\u00b7\u2022\u2023\u2027\u25cf\u2026|•·:;\-–—.,!?()\[\]{}\"'«»]", " ", t)
    return re.sub(r"\s+", " ", out).strip()


def h8(s):
    """Mirror `h8` in content.js: FNV-1a 32-bit, 8 lowercase hex chars."""
    h = 0x811C9DC5
    for ch in s:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return "%08x" % h


def dictionary():
    d = {}
    for w in WORDS.split():
        d.setdefault(h8(norm(w)), []).append(w)
    # "Promoted by <advertiser>" and "Ad ·": the page hashes the text it sees, and
    # any short vendor name changes the hash — say so instead of pretending to know.
    return d


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    sql = None
    if argv[0] == "--sql":
        sql = argv[1]
        hashes = re.findall(r"h=([0-9a-f]{8})", sql)
    else:
        hashes = [a.lower() for a in argv]
    if not hashes:
        print("no h= fingerprints in that string")
        return 0
    d = dictionary()
    rc = 0
    for h in hashes:
        hit = d.get(h)
        if hit:
            print("%s  %s" % (h, " / ".join(hit)))
        else:
            rc = 2
            print("%s  (not in the dictionary: a new word, a vendor name, or a phrase)" % h)
    if sql:
        print()
        print("detail: %s" % sql)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
