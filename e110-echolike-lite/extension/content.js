// EchoLike Lite — content script. One capture-phase click listener, nothing else.
// No timers, no DOM polling: zero cost until you click like/bookmark. The only
// observer is the one that marks promoted posts while the ads switch is on.
(function () {
  if (window.__echolikeLite) return;
  window.__echolikeLite = true;

  // Bump when the walk changes. The background refuses to start an import on a tab
  // whose script speaks an older api, and reloads it instead — a stale tab is the
  // difference between 7 rows and a thousand, and it is invisible otherwise.
  // (Declared first: ping("hello") below reads it, and a later const is in its dead
  // zone at that moment — the throw was swallowed and hello never reached the
  // background, so an X tab loading did not retry the queue, silently.)
  const CONTENT_API = 10;

  // The post container, and the only structural assumption capture makes. Both of
  // X's apps wrap a post in <article>; role=article and the old data-testid row are
  // kept as fallbacks so a tag rename alone does not stop a like from being read.
  const POST_IN = 'article, [role="article"], [data-testid="tweet"]';
  const postOf = (el) => (el && el.closest ? el.closest(POST_IN) : null);

  // ---- Ads ----
  // Old app (rweb): a promoted post is a real tweet inside
  // [data-testid="placementTracking"] (the marker Control Panel for Twitter uses
  // too); promoted trends carry that arrow icon. Hiding the whole cell removes the
  // empty gap the ad would leave behind. X puts OTHER inserted modules in the same
  // wrapper — Grok answers, above all — so a placement only counts as an ad when it
  // holds a tweet and shows no Grok marker: Grok testids, a /grok author link, or an
  // aria-label naming Grok.
  const NOT_GROK =
    ':not(:has([data-testid*="Grok"],[data-testid*="grok"],a[href*="/grok"],' +
    '[aria-label*="Grok"],[aria-label*="grok"]))';
  // x-web (2026) prints the disclosure as text and keeps no marker, so CSS alone
  // cannot see it. The label is the marker: a short span that reads as a disclosure
  // and sits before the post's own text; the JS below sets data-echolike-ad on the
  // cell, and the last rule here hides it.
  const ADS_CSS =
    '[data-testid="placementTracking"]:has([data-testid="tweet"])' + NOT_GROK + '{display:none !important}' +
    '[data-testid="cellInnerDiv"]:has([data-testid="placementTracking"] [data-testid="tweet"])' +
    NOT_GROK +
    '{display:none !important}' +
    '[data-testid="trend"]:has(path[d^="M19.498 3h-15"]){display:none !important}' +
    '[data-echolike-ad]{display:none !important}';
  // The disclosure X prints above a promoted post. Desktop rweb says "Promoted";
  // the phone says "Ad", which is why 1.20.1's list (Promoted, Promocionado, …)
  // missed every ad on a phone. The rest are the same word in the languages this
  // product has actually been installed in, plus the "Promoted by <advertiser>"
  // form. The whole element's text has to be exactly one of them, after decoration
  // is stripped (see `adNorm`).
  // "Ad from explee.com" is the form the phone actually prints (the first mark that
  // came back with its words said exactly that), so `from` belongs in the same list as
  // `by`. A domain or a brand name after it is what the trailing group is for.
  const AD_LABEL =
    /^(Ad|Anuncio|Anzeige|Advert|Werbung|Promoted|Promocionado|Patrocinado|Publicidad|Sponsored|Publicité|Sponsorisé|Sponsorisée|Promu|Sponsorizzato|Promosso|Promowane|Sponsorlu|Реклама|Reklama|推广|广告|プロモーション|広告|홍보)(\s+(by|from|por|de|del|von|par|da|di|door|aus|fra|van|tarafından)\s+.{1,60})?$/i;

  // The phone decorates the word — "Ad ·", "Ad.", "Ad |" — and one stray character
  // used to defeat the whole match. Decoration is stripped, letters never are, so a
  // real word cannot be turned into a disclosure word by this.
  const adNorm = (t) =>
    String(t)
      .replace(/[\u00b7\u2022\u2023\u2027\u25cf\u2026|•·:;\-–—.,!?()[\]{}"'«»]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  // Words the owner taught by marking an ad on the page. Stored as fingerprints of
  // the short header texts, never as the words themselves, so a disclosure in any
  // language can be learned from a tap and applied to every later post.
  let learned = new Set();
  let pendingWords = [];
  // Some ads carry no disclosure word at all (the first field mark proved it: all four
  // short texts of that card were words this product had never seen, and none was a
  // disclosure). For those the learnable thing is the card's SHAPE.
  let learnedSkel = new Set();
  let pendingSkel = "";
  // How much a report carries, chosen by its owner: shapes → labels → everything. The
  // default is the richest, because a report exists to be enough to fix the thing, and
  // a phone has no devtools; the setting is the honest way to walk that back.
  let reportLevel = "full";
  try {
    chrome.storage.local.get({ report_level: "full" }, (s) => {
      reportLevel = String(s.report_level || "full");
    });
    chrome.storage.onChanged.addListener((ch) => {
      if (ch.report_level) reportLevel = String(ch.report_level.newValue || "full");
    });
  } catch (e) {
    /* no storage, no setting: the default stands */
  }
  const readSoon = (s) => {
    if (s.ads_learned) learned = new Set((s.ads_learned || []).filter((h) => typeof h === "string"));
    if (s.ads_pending) pendingWords = (s.ads_pending || []).filter((h) => typeof h === "string");
    if (s.ads_skel) learnedSkel = new Set((s.ads_skel || []).filter((h) => typeof h === "string"));
    if (s.ads_skel_pending !== undefined) pendingSkel = String(s.ads_skel_pending || "");
  };
  try {
    chrome.storage.local.get({ ads_learned: [], ads_pending: [], ads_skel: [], ads_skel_pending: "" }, readSoon);
    chrome.storage.onChanged.addListener((ch) => {
      if (ch.ads_learned) readSoon({ ads_learned: ch.ads_learned.newValue || [] });
      if (ch.ads_pending) readSoon({ ads_pending: ch.ads_pending.newValue || [] });
      if (ch.ads_skel) readSoon({ ads_skel: ch.ads_skel.newValue || [] });
      if (ch.ads_skel_pending) readSoon({ ads_skel_pending: ch.ads_skel_pending.newValue || "" });
    });
  } catch (e) {
    /* a page without storage still captures likes */
  }

  const looksLabel = (t) => {
    const n = adNorm(t);
    if (!n || n.length > 64) return false;
    return AD_LABEL.test(n) || learned.has(h8(n));
  };

  // A stable 8-hex fingerprint of a short UI string. It lets this page report "there
  // is a word here I do not recognise" without sending the word itself: it can be
  // looked up in a dictionary of disclosure words, and it is not a capture, a handle
  // or a post. Diagnostics only — never used on the capture path.
  const h8 = (str) => {
    let h = 0x811c9dc5;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h.toString(16).padStart(8, "0");
  };

  // The post's own words: the longest [dir=auto][lang] container in the article
  // (its body, media alt text aside). Hiding a label must never hide this, and a
  // real post whose whole text is "Ad" or "Promoted" is exactly this container.
  function bodyOf(art) {
    let best = null;
    for (const t of art.querySelectorAll('[dir="auto"][lang]')) {
      if (t.closest(POST_IN) !== art) continue; // a quoted post's body is not ours
      if (!best || (t.textContent || "").length > (best.textContent || "").length) best = t;
    }
    return best;
  }

  // The cell, not the article: hiding the article leaves its padding behind. In
  // priority order, and never by one `closest()` over a selector list — that returns
  // the NEAREST match, so a `div[role=link]` inside the list cell would be hidden
  // instead of the cell, and the empty cell still takes its box in the timeline.
  const cellOf = (art) =>
    art.closest('[data-testid="cellInnerDiv"]') || art.closest("li") || art.closest('[role="link"]') || art;

  // X paints the disclosure in its regular weight and an author name in bold: a
  // person called "Ad" (or a brand called "Publicidad") is a name, not an ad, and
  // hiding their posts would be a worse bug than the one this fixes.
  const bold = (s) => Number(getComputedStyle(s).fontWeight) >= 600;

  // A card's shape with every word removed: tags, roles, testids, dir/lang and child
  // counts, bounded. Two ads of the same kind share it; a real post usually does not.
  // This is what gets learned when there is no disclosure word to learn.
  function skeleton(root) {
    const parts = [];
    const walk = (el, d) => {
      if (parts.length > 48 || d > 4) return;
      parts.push(
        el.tagName + "|" + (el.getAttribute("data-testid") || "") + "|" + (el.getAttribute("role") || "") +
          "|" + (el.getAttribute("dir") || "") + "|" + el.children.length,
      );
      for (const c of el.children) walk(c, d + 1);
    };
    walk(root, 0);
    return h8(parts.join(";"));
  }

  // The label, not the post. Any element whose whole (normalized) text is a
  // disclosure word counts: `div` or `span`, inside the advertiser's link or not,
  // before or after the post's text, and with icon wrappers inside it (the phone
  // renders `Ad<svg></svg><span></span>` — one word, two children — which the
  // leaf-only rule of 1.21.0 skipped every time). A container that wraps the post's
  // own text is excluded (the body check); a container of real UI text is too long
  // or has too many words.
  function looksPromoted(art, body) {
    const own = body === undefined ? bodyOf(art) : body;
    const scan = (root, ours) => {
      for (const s of root.querySelectorAll("span,div")) {
        if (ours && s.closest(POST_IN) !== art) continue; // a quoted post's header
        if (!ours && s.closest(POST_IN) && s.closest(POST_IN) !== art) continue; // another post
        if (own && (s === own || own.contains(s) || s.contains(own))) continue; // the post itself
        const t = (s.textContent || "").trim();
        if (!t || t.length > 64 || !looksLabel(t) || bold(s)) continue;
        return true;
      }
      return false;
    };
    if (scan(art, true)) return true;
    // A shape the owner taught by marking two ads of the same kind: no word needed.
    if (learnedSkel.size && learnedSkel.has(skeleton(art))) return true;
    // Sponsored modules put the disclosure BESIDE the post (or beside a card that is
    // not a post at all), still inside the same cell: look there too, skipping any
    // words that belong to another post.
    const cell = cellOf(art);
    return cell !== art && scan(cell, false);
  }

  // Hiding the card is not enough: X wraps it in padded rows and the gap stays — the
  // owner reported exactly that ("ads were hidden, but blank space remained"). Climb
  // while the ancestor is chrome only: same text, no other content-bearing child.
  function rowOf(cell) {
    let el = cell;
    for (let i = 0; i < 3; i++) {
      const p = el.parentElement;
      if (!p || p === document.body || p === document.documentElement) break;
      if ((p.textContent || "") !== (el.textContent || "")) break; // shows something of its own
      const other = [...p.children].some((c) => c !== el && (c.textContent || "").trim());
      if (other) break;
      el = p;
    }
    return el;
  }

  // X's timeline is a virtualized list: a row is `li[data-index]` positioned absolutely
  // with an inline `transform: translateY(<px>)`. Hiding such a row removes its box but
  // not its slot — the rows after it keep their offsets, and that is the blank space the
  // owner kept seeing. So the row's offset and height are recorded before hiding, and
  // `collapse()` pulls every later row of the same list up by the heights of the hidden
  // rows above it. It recomputes from the recorded bases, so it is safe to re-run and it
  // undoes itself when a row stops being an ad.
  const tfY = (el) => {
    const m = /translateY\((-?[\d.]+)px\)/.exec((el.style && el.style.transform) || "");
    return m ? parseFloat(m[1]) : null;
  };

  const collapsed = new Set(); // lists we have moved rows in, so unmarking can undo it

  function collapse() {
    const parents = new Set(collapsed);
    for (const el of document.querySelectorAll("[data-echolike-ad]")) {
      if (el.parentElement) parents.add(el.parentElement);
    }
    if (!parents.size) return;
    for (const parent of parents) {
      const hidden = [];
      for (const el of parent.children) {
        if (!el.hasAttribute("data-echolike-ad")) continue;
        const base = Number(el.dataset.echBase);
        const h = Number(el.dataset.echH);
        if (Number.isFinite(base) && Number.isFinite(h)) hidden.push({ base, h });
      }
      let moved = 0;
      for (const row of parent.children) {
        if (row.hasAttribute("data-echolike-ad")) continue;
        const cur = tfY(row);
        if (cur == null) continue; // not a virtualized row: normal flow closes itself
        let base = Number(row.dataset.echBase);
        const applied = Number(row.dataset.echApplied);
        // X rewrote the offset (it re-measures on scroll): that new value is the base.
        if (!Number.isFinite(base) || (Number.isFinite(applied) && Math.abs(cur - applied) > 0.5)) base = cur;
        let shift = 0;
        for (const h of hidden) if (h.base < base) shift += h.h;
        const target = Math.max(0, base - shift);
        if (Math.abs(cur - target) > 0.5) row.style.transform = "translateY(" + target + "px)";
        if (target !== base) {
          row.dataset.echBase = String(base);
          row.dataset.echApplied = String(target);
          moved++;
        } else {
          delete row.dataset.echBase;
          delete row.dataset.echApplied;
        }
      }
      if (hidden.length || moved) collapsed.add(parent);
      else collapsed.delete(parent);
    }
  }

  function markCell(cell, on) {
    for (const el of new Set([cell, rowOf(cell)])) {
      if (on) {
        const h = el.getBoundingClientRect().height;
        const t = tfY(el);
        if (h > 0 && t != null && el.dataset.echBase == null) {
          el.dataset.echBase = String(t);
          el.dataset.echH = String(h);
        }
        el.setAttribute("data-echolike-ad", "1");
      } else {
        el.removeAttribute("data-echolike-ad");
        const base = el.dataset.echBase;
        if (base != null) el.style.transform = "translateY(" + base + "px)";
        delete el.dataset.echBase;
        delete el.dataset.echH;
        delete el.dataset.echApplied;
      }
    }
    collapse();
  }

  function markAds(node) {
    // A label painted as text (X swaps a header's textContent, so the mutation is a
    // Text node, not an element) still has to mark its post.
    if (node && node.nodeType === 3) node = node.parentElement;
    if (!node || node.nodeType !== 1) return;
    const arts = new Set();
    if (node.matches && node.matches(POST_IN)) arts.add(node);
    if (node.querySelectorAll) for (const a of node.querySelectorAll(POST_IN)) arts.add(a);
    // A label that arrives after its post (X paints the disclosure in a second
    // pass) is inserted INSIDE the article, so the added node is the label and no
    // article is found by the two rules above: walk up, or every such ad is missed.
    // Only for a short insertion — a label is a leaf — so a busy timeline does not
    // re-scan a whole post on every node React swaps in.
    const up = node.closest && node.closest(POST_IN);
    if (up && (node.textContent || "").length <= 96) arts.add(up);
    for (const art of arts) markCell(cellOf(art), looksPromoted(art));
  }

  // A cell that is not a post at all — a sponsored module, a promoted trend, a card
  // with "Sponsored" and a button — has no article to hang the label on, so the cell
  // itself is the unit. Only the timeline (never a nav/header/aside), only while the
  // ads switch is on, and only for a short element whose whole text is a disclosure.
  function markModules(root) {
    if (!root || root.nodeType !== 1) return;
    for (const cell of root.querySelectorAll('li,[data-testid="cellInnerDiv"]')) {
      if (cell.querySelector(POST_IN)) continue; // an ad post: the article path owns it
      if (cell.closest("nav,header,aside")) continue;
      let hit = learnedSkel.size > 0 && learnedSkel.has(skeleton(cell));
      if (!hit) {
        for (const s of cell.querySelectorAll("span,div")) {
          const t = (s.textContent || "").trim();
          if (!t || t.length > 64 || !looksLabel(t) || bold(s)) continue;
          hit = true;
          break;
        }
      }
      markCell(cell, hit);
    }
  }

  // The words that are unique to this card's header: short, regular weight, and not
  // found in any other post on screen. A disclosure appears only on its ad; an author
  // name belongs to its own post and a date shows up everywhere, so neither survives
  // that filter for long.
  function headerWords(card, art) {
    const body = art ? bodyOf(art) : null;
    // How many OTHER posts carry each short text. Two is "everywhere" (a UI word like
    // "Follow"); one is another ad with the same disclosure, which must not stop it
    // from being learned. Cards already known to be ads are not evidence at all.
    const others = new Map();
    for (const a of document.querySelectorAll(POST_IN)) {
      if (a === art || cellOf(a).getAttribute("data-echolike-ad") === "1") continue;
      const seen = new Set();
      for (const s of a.querySelectorAll("span,div")) {
        const t = (s.textContent || "").trim();
        if (!t || t.length > 24) continue;
        const h = h8(adNorm(t));
        if (seen.has(h)) continue;
        seen.add(h);
        others.set(h, (others.get(h) || 0) + 1);
      }
    }
    const out = [];
    for (const s of card.querySelectorAll("span,div")) {
      if (art && s.closest(POST_IN) && s.closest(POST_IN) !== art) continue;
      if (body && (s === body || body.contains(s) || s.contains(body))) continue;
      const t = (s.textContent || "").trim();
      if (!t || t.length > 24 || t.split(/\s+/).length > 3 || bold(s)) continue;
      if (!/^\D*$/.test(t) || !/\p{L}{2,}/u.test(t)) continue; // "·", "2h", "Nov 24" teach nothing
      const h = h8(adNorm(t));
      if ((others.get(h) || 0) >= 2 || out.some((c) => c.h === h)) continue;
      out.push({ h, t });
      if (out.length >= 4) break;
    }
    return out;
  }

  // "Mark this as an ad": the owner taps the card. It goes away on the spot, its shape
  // is sent (so the rule is written from what their phone renders, not from a guess),
  // and the words unique to it are kept as candidates. A SECOND mark of the same kind
  // teaches the word — one mark cannot tell "Ad" from an advertiser's own name.
  function markAsAd(target, done) {
    const art = postOf(target);
    const card = (art && cellOf(art)) || target.closest('li,[data-testid="cellInnerDiv"]') || target;
    markCell(card, true);
    const cands = headerWords(card, art);
    const words = cands.map((c) => c.h);
    const taught = words.filter((h) => pendingWords.includes(h));
    const next = [...new Set([...learned, ...taught])];
    const pending = taught.length ? [] : words;
    learned = new Set(next);
    pendingWords = pending;

    // The shape: an ad with no disclosure word has nothing else to learn. Two marks of
    // the same shape teach it, unless that shape is everywhere on the page already —
    // then it is the timeline's own row, not an ad.
    const skRoot = art || card;
    const sk = skeleton(skRoot);
    const skCommon = [...document.querySelectorAll(POST_IN)].filter(
      (a) => a !== art && cellOf(a).getAttribute("data-echolike-ad") !== "1" && skeleton(a) === sk,
    ).length;
    const teachSkel = !!pendingSkel && pendingSkel === sk && skCommon < 2;
    const nextSkel = teachSkel ? [...new Set([...learnedSkel, sk])] : [...learnedSkel];
    const nextPendingSkel = teachSkel || skCommon >= 2 ? "" : sk;
    learnedSkel = new Set(nextSkel);
    pendingSkel = nextPendingSkel;
    const skReal = (() => {
      for (const a of document.querySelectorAll(POST_IN)) {
        if (a !== art && cellOf(a).getAttribute("data-echolike-ad") !== "1") return skeleton(a);
      }
      return "-";
    })();
    try {
      chrome.storage.local.set({
        ads_learned: next,
        ads_pending: pending,
        ads_skel: nextSkel,
        ads_skel_pending: nextPendingSkel,
      });
    } catch (e) {
      /* the mark still hides this card */
    }
    const links = [...card.querySelectorAll("a[href]")];
    const ext = links.filter((a) => /^https?:/.test(a.getAttribute("href")) && !/x\.com|twitter\.com/.test(a.getAttribute("href"))).length;
    const detail = (
      "v=" + VER + " post=" + (art ? 1 : 0) +
      " len=" + (card.textContent || "").length +
      " cell=" + card.tagName + ":" + (card.getAttribute("data-testid") || "-") +
      " a=" + links.length + " ext=" + ext + " btn=" + card.querySelectorAll("button,[role=button]").length +
      " body=" + (art && bodyOf(art) ? bodyOf(art).textContent.length : 0) +
      " words=[" + words.map((h) => "h=" + h).join(",") + "]" +
      " taught=" + taught.length + " pending=" + pending.length + " known=" + learned.size +
      " sk=" + sk + " skreal=" + skReal + " skcommon=" + skCommon +
      " sktaught=" + (teachSkel ? 1 : 0) + " skknown=" + learnedSkel.size
    );
    tel("ads.mark", { ok: true, host: location.host, detail: detail.slice(0, 1200) });
    // The rich report goes with the mark: at `labels` and above it carries the words as
    // they are, at `full` it carries the card's own markup too. That is the difference
    // between "a shape changed" and a selector that can be written tonight.
    const post = [...card.querySelectorAll("a[href]")].map((a) => a.getAttribute("href") || "")
      .find((h) => /\/status\/\d+/.test(h)) || "";
    const rich = {
      kind: "mark",
      version: VER,
      post_url: post,
      detail: (detail + " level=" + reportLevel).slice(0, 2000),
      words: reportLevel === "shapes" ? "" : cands.map((c) => c.t).join(" | ").slice(0, 1000),
      html: reportLevel === "full" ? (card.outerHTML || "").slice(0, 96000) : "",
    };
    try {
      chrome.runtime.sendMessage({ type: "adreport", report: rich }, () => {});
    } catch (e) {
      /* the mark still hides this card */
    }
    if (done) done(teachSkel || taught.length ? "taught" : words.length || nextPendingSkel ? "pending" : "none");
  }

  // One tap to point at the ad, one to be done. Window capture runs before the like
  // handler on document, so a mark never captures the post as a like.
  let pickOff = null;
  function startPick() {
    if (pickOff) return pickOff();
    const stop = () => {
      window.removeEventListener("click", pick, true);
      window.removeEventListener("keydown", onKey, true);
      document.documentElement.style.cursor = "";
      pickOff = null;
    };
    const onKey = (e) => {
      if (e.key === "Escape") {
        stop();
        toast("cancelled", true);
      }
    };
    const pick = (e) => {
      const t = e.target instanceof Element ? e.target : null;
      if (!t) return;
      if (t.closest("#echolike-lite-fab")) return; // the circle is not a post
      if (!postOf(t) && !t.closest('li,[data-testid="cellInnerDiv"]')) {
        toast("Tap the post you want gone", false);
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      stop();
      markAsAd(t, (state) => {
        toast(
          state === "taught"
            ? "Marked. Learned: ads like this hide by themselves now"
            : state === "pending"
              ? "Marked. Mark one more ad like it and it is learned"
              : "Marked as an ad. Its shape was sent",
          true,
        );
      });
    };
    pickOff = stop;
    window.addEventListener("click", pick, true);
    window.addEventListener("keydown", onKey, true);
    document.documentElement.style.cursor = "crosshair";
    toast("Tap the ad you want gone", true);
    return stop;
  }

  // Why an ad is still showing. Structure and short fingerprints only — no post
  // text, no handle, no link — because the phone this runs on has no devtools and
  // the next DOM change has to be read, not guessed. One tap in Settings sends it.
  //
  //   A[...]  a post-shaped cell: its length, whether it is marked, its cell, and up
  //           to two short texts in it as `h=<fingerprint>,l=length,w=words,f=weight,
  //           k=children,b=isBody,a=inLink,t=tag`
  //   M[...]  a cell that is NOT a post (sponsored module, trend, "who to follow"):
  //           length, words, links, external links, buttons, and its short texts.
  function adsReport() {
    const arts = [...document.querySelectorAll(POST_IN)];
    // One per hidden ad, not per marked element: a card and the padded row around it
    // both carry the mark.
    const marked = [...document.querySelectorAll("[data-echolike-ad]")].filter(
      (el) => !(el.parentElement && el.parentElement.closest("[data-echolike-ad]")),
    ).length;
    const shorts = (root, art, body) => {
      const out = [];
      for (const s of root.querySelectorAll("span,div")) {
        if (art && s.closest(POST_IN) !== art) continue;
        if (!art && s.closest(POST_IN)) continue;
        const t = (s.textContent || "").trim();
        if (!t || t.length > 40 || t.split(/\s+/).length > 3) continue;
        out.push(
          "h=" + h8(adNorm(t)) +
            ",l=" + t.length +
            ",w=" + t.split(/\s+/).length +
            ",f=" + getComputedStyle(s).fontWeight +
            ",k=" + s.children.length +
            ",b=" + (body && (s === body || body.contains(s) || s.contains(body)) ? 1 : 0) +
            ",a=" + (s.closest("a") ? 1 : 0) +
            ",t=" + s.tagName.charAt(0),
        );
        if (out.length >= 2) break;
      }
      return out;
    };
    const rows = [];
    for (const art of arts.slice(0, 6)) {
      const body = bodyOf(art);
      const cell = cellOf(art);
      rows.push(
        "A[len=" + (art.textContent || "").length +
          ",m=" + (cell.getAttribute("data-echolike-ad") === "1" ? 1 : 0) +
          ",cell=" + cell.tagName + ":" + (cell.getAttribute("data-testid") || "-") +
          "|" + (shorts(art, art, body).join("|") || "-") + "]",
      );
    }
    const mods = [];
    for (const cell of document.querySelectorAll('li,[data-testid="cellInnerDiv"]')) {
      if (cell.querySelector(POST_IN)) continue;
      const text = (cell.textContent || "").trim();
      if (!text) continue;
      const links = [...cell.querySelectorAll("a[href]")];
      const ext = links.filter((a) => /^https?:/.test(a.getAttribute("href")) && !/x\.com|twitter\.com/.test(a.getAttribute("href"))).length;
      mods.push(
        "M[len=" + text.length + ",w=" + text.split(/\s+/).length + ",a=" + links.length +
          ",ext=" + ext + ",btn=" + cell.querySelectorAll("button,[role=button]").length +
          "|" + (shorts(cell, null, null).join("|") || "-") + "]",
      );
      if (mods.length >= 3) break;
    }
    const out = {
      layout: document.querySelector("[data-testid]") ? "rweb" : "x-web",
      articles: arts.length,
      marked,
      learned: learned.size,
      pending: pendingWords.length,
      learnedSkel: learnedSkel.size,
      pendingSkel: pendingSkel ? 1 : 0,
      rows,
      mods,
    };
    // The rich half, shaped by the owner's privacy level: `shapes` sends none of it,
    // `labels` adds the short words as they are, `full` adds the column's markup. This
    // is the payload that makes a DOM change fixable without a devtools on a phone.
    const main = document.querySelector("main");
    const col = main && main.querySelectorAll(POST_IN).length >= 3 ? main : document.body;
    out.line = (
      "v=" + VER + " articles=" + out.articles + " marked=" + marked + " layout=" + out.layout +
      " learned=" + out.learned + " pending=" + out.pending +
      " skel=" + out.learnedSkel + "/" + out.pendingSkel +
      " | " + rows.join(" ") + (mods.length ? " | modules: " + mods.join(" ") : " | no modules")
    ).slice(0, 2000);
    out.rich = {
      kind: "report",
      version: VER,
      post_url: "",
      detail: out.line,
      words: reportLevel === "shapes" ? "" : [...new Set([
        ...[...col.querySelectorAll("span,div")].map((e) => (e.textContent || "").trim()),
      ])].filter((t) => t && t.length <= 24 && t.split(/\s+/).length <= 3).slice(0, 60).join(" | ").slice(0, 1000),
      html: reportLevel === "full" ? (col.outerHTML || "").slice(0, 96000) : "",
    };
    return out;
  }

  chrome.runtime.onMessage.addListener((m, _s, reply) => {
    if (m && m.type === "ads-report") reply(adsReport());
  });

  let adObserver = null;

  function watchAds(on) {
    if (adObserver) {
      adObserver.disconnect();
      adObserver = null;
    }
    if (!on) {
      // Off means back exactly as X had it: the hidden rows return to their own offsets
      // and the rows we pulled up return to theirs.
      for (const el of document.querySelectorAll("[data-echolike-ad]")) {
        el.removeAttribute("data-echolike-ad");
        if (el.dataset.echBase != null) el.style.transform = "translateY(" + el.dataset.echBase + "px)";
        delete el.dataset.echBase;
        delete el.dataset.echH;
        delete el.dataset.echApplied;
      }
      collapse();
      return;
    }
    markAds(document.body);
    markModules(document.body);
    // Ads arrive as the timeline grows: one observer marks them on insertion (and
    // clears a cell that a virtualized list reused for a real post). It watches the
    // body, not `main`: x-web's feed is not always inside <main>, and an observer on
    // a container the app replaces dies with it.
    adObserver = new MutationObserver((muts) => {
      for (const m of muts) for (const n of m.addedNodes) {
        markAds(n);
        markModules(n);
      }
      collapse(); // a re-render puts the rows back at X's offsets: pull them up again
    });
    adObserver.observe(document.body, { childList: true, subtree: true });
  }

  function applyAds(hide) {
    const cur = document.getElementById("echolike-lite-ads");
    if (!hide) {
      if (cur) cur.remove();
      watchAds(false);
      return;
    }
    if (!cur) {
      const style = document.createElement("style");
      style.id = "echolike-lite-ads";
      style.textContent = ADS_CSS;
      (document.head || document.documentElement).appendChild(style);
    }
    watchAds(true);
  }

  // Two events, no timers: an X tab finishing loading is the cheapest honest moment
  // to retry a queue, and the browser's own "online" is when a queue is worth sending.
  const ping = (type) => {
    try {
      const p = chrome.runtime.sendMessage({ type, api: CONTENT_API });
      if (p && p.catch) p.catch(() => {});
    } catch (e) {
      /* a page that cannot talk to the extension still captures likes */
    }
  };
  ping("hello");
  window.addEventListener("online", () => ping("net-online"));

  chrome.storage.local.get({ hide_ads: true }, (s) => applyAds(s.hide_ads));
  chrome.storage.onChanged.addListener((ch) => {
    if (ch.hide_ads) applyAds(ch.hide_ads.newValue);
  });

  const KINDS = { like: "like", unlike: "unlike", bookmark: "bookmark", removeBookmark: "unbookmark" };

  // Two X web apps are in the wild at once (the 2026 rewrite rolls out country by
  // country): the old rweb, where every control carries data-testid, and x-web,
  // where data-testid is gone. x-web still marks an engagement button the way a
  // native toggle would — the icon inside it (icon-heart / icon-bookmark) and
  // aria-pressed for the state — so one script can read either app.
  function iconName(el) {
    const u = el.querySelector("use");
    const href = u && (u.getAttribute("href") || u.getAttribute("xlink:href"));
    const d = el.querySelector("[data-icon]");
    return String(href || "") + " " + String(d ? d.getAttribute("data-icon") : "");
  }

  function newKind(el) {
    if (!el || el.tagName !== "BUTTON") return null;
    const icon = iconName(el);
    const pressed = el.getAttribute("aria-pressed") === "true";
    if (/icon-heart/.test(icon)) return pressed ? "unlike" : "like";
    if (/icon-bookmark/.test(icon)) return pressed ? "unbookmark" : "bookmark";
    return null;
  }

  // The last resort: the accessible name. Icon names and testids have both been
  // renamed under us, the words have not. Covers the languages this product is used
  // in; a new locale still captures through the icon path above.
  const LIKE_WORDS = /\b(likes?|unlike|me gusta|ya no me gusta)\b/i;
  const MARK_WORDS = /\b(bookmarks?|unbookmark|remove bookmark|guardar|guardado|eliminar)\b/i;
  const UNDO_WORDS = /\b(unlike|remove like|unbookmark|remove bookmark|ya no me gusta|quitar|remove)\b/i;

  function labeledKind(el) {
    if (!el || (el.tagName !== "BUTTON" && el.getAttribute("role") !== "button")) return null;
    const label = (el.getAttribute("aria-label") || el.getAttribute("title") || "").trim();
    if (!label) return null;
    const pressed = el.getAttribute("aria-pressed") === "true";
    if (MARK_WORDS.test(label)) return pressed || UNDO_WORDS.test(label) ? "unbookmark" : "bookmark";
    if (LIKE_WORDS.test(label)) return pressed || UNDO_WORDS.test(label) ? "unlike" : "like";
    return null;
  }

  // Returns {el, kind}: the element is what a click travelled through, the kind is
  // read before X flips it (the listener runs in the capture phase).
  function actionButton(target) {
    let el = target && target.closest ? target.closest('[data-testid],button,[role="button"]') : null;
    while (el) {
      const t = el.getAttribute("data-testid");
      // Only inside a post: a "Bookmarks" nav button is not a capture, and must not
      // turn a normal page click into "could not read this post".
      if (t && KINDS[t] && postOf(el)) return { el, kind: KINDS[t] };
      const k = newKind(el) || labeledKind(el);
      if (k && postOf(el)) return { el, kind: k };
      el = el.parentElement ? el.parentElement.closest('[data-testid],button,[role="button"]') : null;
    }
    return null;
  }

  // Counts arrive localized: "1.234 respuestas", "1,234 replies", "1,2 mil", "3.4K".
  // Separators are guessed by position (3 digits after = thousands), suffixes known.
  function num(value) {
    if (value == null) return null;
    const raw = String(value).replace(/\u00a0/g, " ").trim();
    const m = raw.match(/(\d+(?:[.,\s]\d+)*)/);
    if (!m) return null;
    const token = m[1];
    const after = raw.slice(m.index + token.length);
    const suf = (after.match(/^\s*(mil|mn|kk|k|m|b)\b/i) || [])[1] || "";
    const suffix = suf.toLowerCase();
    let n = token;
    const both = n.includes(",") && n.includes(".");
    if (both) {
      const lastComma = n.lastIndexOf(",") > n.lastIndexOf(".");
      n = lastComma ? n.replace(/\./g, "").replace(",", ".") : n.replace(/,/g, "");
    } else if (n.includes(",")) {
      n = /,\d{3}(\D|$)/.test(n) && !suffix ? n.replace(/,/g, "") : n.replace(",", ".");
    } else if (n.includes(".")) {
      n = /\.\d{3}(\D|$)/.test(n) && !suffix ? n.replace(/\./g, "") : n;
    }
    let v = parseFloat(n.replace(/\s/g, ""));
    if (!isFinite(v)) return null;
    if (suffix === "mil" || suffix === "k" || suffix === "kk") v *= 1e3;
    if (suffix === "mn" || suffix === "m") v *= 1e6;
    if (suffix === "b") v *= 1e9;
    return Math.round(v);
  }

  // A post's own content only: never the quoted post, which sits inside it as a
  // nested <article> in x-web (and inside a role=link div in the old app). Rows are
  // normally <article>, but the old app also renders some as div[data-testid=tweet].
  function own(art, el) {
    if (!el || !art.contains(el)) return false;
    if (el.closest(POST_IN) !== art) return false;
    const q = el.closest('div[role="link"]');
    return !(q && q !== art && art.contains(q));
  }

  function firstOwn(art, sel) {
    for (const el of art.querySelectorAll(sel)) if (own(art, el)) return el;
    return null;
  }

  const countOf = (art, testid) => {
    const el = art.querySelector('[data-testid="' + testid + '"]');
    if (!el || !own(art, el)) return null;
    return num(el.getAttribute("aria-label")) ?? num(el.innerText || el.textContent);
  };

  // x-web has no testids, but the same number rides in the engagement button's
  // aria-label ("12 Likes. Like") or its text ("5.4M" for views).
  const countByIcon = (art, icon) => {
    for (const el of art.querySelectorAll("button")) {
      if (!own(art, el) || iconName(el).indexOf(icon) < 0) continue;
      return num(el.getAttribute("aria-label")) ?? num(el.innerText || el.textContent);
    }
    return null;
  };

  const viewsOf = (art) => {
    const el = art.querySelector('a[href*="/analytics"]');
    if (el && own(art, el)) return num(el.getAttribute("aria-label")) ?? num(el.innerText || el.textContent);
    return countByIcon(art, "icon-bar-chart");
  };

  const mediaOf = (art) => {
    // One element per media item: a tweetPhoto holds an <img> too, and a
    // videoPlayer holds a <video>, so the inner node must not count twice.
    const photos = [...art.querySelectorAll('[data-testid="tweetPhoto"], img[src*="/media/"]')].filter(
      (el) => own(art, el) && !(el.tagName === "IMG" && el.closest('[data-testid="tweetPhoto"]')),
    ).length;
    const videos = [...art.querySelectorAll('[data-testid="videoPlayer"], [data-testid="videoComponent"], video')]
      .filter(
        (el) =>
          own(art, el) &&
          !(el.tagName === "VIDEO" && el.closest('[data-testid="videoPlayer"], [data-testid="videoComponent"]')),
      ).length;
    return {
      media: photos + videos,
      photos,
      videos,
      card: !!firstOwn(art, '[data-testid="card.wrapper"], a[href^="https://t.co/"]'),
    };
  };

  // The post's own link: any /status/ anchor that is NOT inside the quoted tweet,
  // the media container, or the tweet text. Taking the first anchor made a row with a
  // quote resolve to the *quoted* post, so many rows collapsed into one id.
  function ownStatusLink(art) {
    const anchors = Array.from(art.querySelectorAll('a[href*="/status/"]')).filter(
      (a) => own(art, a) && /\/status\/\d+/.test(a.getAttribute("href")),
    );
    // the timestamp link is the canonical one when there are several
    return anchors.find((a) => a.querySelector("time")) || anchors[0] || null;
  }

  // The quoted post, if there is one: a nested <article> in x-web, a role=link div
  // in the old app. Its id is kept so the inbox can show the context.
  function quotedLink(art) {
    const nested = [...art.querySelectorAll(POST_IN)].find(
      (el) => el.parentElement && el.parentElement.closest(POST_IN) === art,
    );
    return nested ? ownStatusLink(nested) : art.querySelector('div[role="link"] a[href*="/status/"]');
  }

  // One extraction, shared by the click path and the import walk.
  function extract(art, kind) {
    if (!art) return null;
    const head = (art.innerText || "").slice(0, 200);
    const ad =
      !!art.closest('[data-testid="placementTracking"]') ||
      /(^|\n)\s*(Promoted|Ad|Anzeige|Promocionado|Publicidad|Sponsorisé)\s*($|\n)/i.test(head);
    const a = ownStatusLink(art);
    const m = a && a.getAttribute("href").match(/\/([A-Za-z0-9_]{1,15})\/status\/(\d+)/);
    if (!m) return null;
    const txt = firstOwn(art, '[data-testid="tweetText"], [lang][dir="auto"]');
    const time = a.querySelector("time");
    const name = firstOwn(art, '[data-testid="User-Name"], div.font-bold[dir="auto"], span.font-bold[dir="auto"]');
    const quoted = quotedLink(art);
    const qm = quoted && quoted.getAttribute("href").match(/\/status\/(\d+)/);
    const media = mediaOf(art);
    // x-web labels the date the way X shows it: an absolute one on the post page
    // ("5:44 AM · Nov 24, 2026") and a relative one in the list ("5h"). Only the
    // absolute form is worth keeping: "5h" is a fact about the click, not the post.
    const stamp = time ? null : (a.innerText || a.textContent || "").trim().slice(0, 40) || null;
    return {
      kind,
      id: m[2],
      handle: m[1],
      url: "https://x.com/" + m[1] + "/status/" + m[2],
      text: txt ? (txt.innerText || txt.textContent || "").slice(0, 2000) : "",
      lang: txt ? txt.getAttribute("lang") || null : null,
      author_name: name
        ? ((name.querySelector("span") || name).innerText || name.textContent || "").split("\n")[0].trim().slice(0, 80) ||
          null
        : null,
      // x-web prints the date as X itself shows it ("Nov 23") and ships no <time>:
      // an exact instant would be a guess, so published_at stays null and the
      // display string travels separately.
      published_at: time ? time.getAttribute("datetime") : null,
      tweet_time: time ? time.getAttribute("datetime") : null, // kept for older inboxes
      published_text: stamp && /[A-Za-z\u00c0-\u00fa]{3}|\d{4}/.test(stamp) ? stamp : null,
      counts: {
        replies: countOf(art, "reply") ?? countByIcon(art, "icon-reply"),
        reposts: countOf(art, "retweet") ?? countByIcon(art, "icon-repost"),
        likes: countOf(art, "like") ?? countByIcon(art, "icon-heart"),
        bookmarks: countOf(art, "bookmark") ?? countByIcon(art, "icon-bookmark"),
        views: viewsOf(art),
      },
      quotes: qm ? qm[1] : null,
      is_repost: /reposted|retweeted|repostó|retuiteó/i.test(head),
      ad,
      ...media,
      // when, and from where: the two dates that cannot be recovered later
      captured_at: new Date().toISOString(),
      clicked_at: new Date().toISOString(),
      source: kind === "bookmark" ? "bookmark" : "like",
      page: location.pathname,
    };
  }

  const tel = (action, info) => {
    try {
      const p = chrome.runtime.sendMessage({ type: "tel", action, info: Object.assign({ host: location.host }, info || {}) });
      if (p && p.catch) p.catch(() => {});
    } catch (e) {
      /* the walk must not die because a diagnostic could not be sent */
    }
  };

  // Which X app this tab is running, in one line. X replaced its web app in 2026
  // (data-testid gone), and the only visible symptom was "the button does nothing":
  // these counts answer it from the field instead of from a guess. Sent with the
  // first capture of the page and with any capture that fails.
  function domDetail() {
    const testids = document.querySelectorAll("[data-testid]").length;
    return (
      "layout=" + (testids ? "rweb" : "x-web") +
      " articles=" + document.querySelectorAll("article").length +
      " testids=" + testids +
      " hearts=" + document.querySelectorAll('use[href="#icon-heart"], [data-icon*="heart"]').length +
      " marks=" + document.querySelectorAll('use[href="#icon-bookmark"], [data-icon*="bookmark"]').length +
      " pressed=" + document.querySelectorAll("[aria-pressed]").length
    );
  }

  let domReported = false;
  function reportDom() {
    if (domReported) return;
    domReported = true;
    tel("dom", { ok: true, detail: domDetail() });
  }

  // ---- Import: walk a list that X builds as you scroll ----------------------
  // Only runs when the user starts it from the Import tab. It stops by itself at the
  // requested count, when the list stops growing, or after ten minutes. Growth is
  // detected with a MutationObserver: the only timer is the "nothing new arrived"
  // guard, and it exists only while an import is running.
  const IMPORT_QUIET_MS = 3500; // one quiet tick is not the end of the world
  const IMPORT_QUIET_ROUNDS = 3; // ... three in a row, with nothing loading, is
  const IMPORT_MAX_MS = 10 * 60 * 1000;
  const IMPORT_BATCH = 25;
  let importRun = null;

  const importProgress = (patch) =>
    chrome.storage.local.set({ import_progress: Object.assign({ at: new Date().toISOString() }, patch) });

  // The scroll container is whatever ancestor of a tweet actually scrolls: X moves
  // it between layouts, and guessing by testid breaks on every redesign.
  function xScroller() {
    const scrolls = (el) => {
      if (!el || el.scrollHeight <= el.clientHeight + 100) return false;
      const oy = getComputedStyle(el).overflowY;
      return oy === "auto" || oy === "scroll" || el === document.scrollingElement;
    };
    const art = document.querySelector("article");
    let el = art && art.parentElement;
    while (el && el !== document.documentElement) {
      if (scrolls(el)) return el;
      el = el.parentElement;
    }
    const inner = document.querySelector('div[data-testid="primaryColumn"] div[style*="overflow"]');
    if (scrolls(inner)) return inner;
    return document.scrollingElement || document.documentElement;
  }

  // X appends in bursts, sometimes seconds apart. Scrolling one element and hoping is
  // how the first attempt "finished" with 2 of 100.
  // One viewport at a time. Jumping to scrollHeight makes a virtualized list render
  // its tail and throw away the middle: that is how a 1k list yielded 6 tweets.
  function nudgeStep() {
    const sc = xScroller() || document.scrollingElement;
    try {
      const step = Math.max(400, Math.floor((window.innerHeight || 900) * 0.8));
      // The window, the resolved container, and a wheel hint: X's list reacts to
      // different ones depending on the layout it shipped this week.
      window.scrollBy(0, step);
      if (sc && sc !== document.scrollingElement) {
        sc.scrollTop = Math.min(sc.scrollHeight, sc.scrollTop + step);
        sc.dispatchEvent(new Event("scroll", { bubbles: true }));
      }
      window.dispatchEvent(new Event("scroll"));
      try {
        window.dispatchEvent(new WheelEvent("wheel", { deltaY: step, bubbles: true }));
      } catch (e) {
        /* no WheelEvent in this engine: the scrolls above still happened */
      }
    } catch (e) {
      /* a page that refuses to scroll is a page we report, not crash on */
    }
    return sc;
  }

  const stillLoading = () =>
    !!document.querySelector('[role="progressbar"], [data-testid="ProgressBar"]') ||
    !!document.querySelector('div[role="progressbar"]');

  function startImport(mode, limit) {
    if (importRun) return { ok: false, error: "an import is already running" };
    const kind = mode === "bookmarks" ? "bookmark" : "like";
    const wanted = Math.max(1, Math.min(20000, Number(limit) || 300));
    const startedAt = Date.now();
    const collected = new Map(); // post id -> item, for this run
    const queue = []; // harvested, not yet handed to the background
    let observer = null;
    let quiet = null;
    let done = false;
    let sent = 0;

    const report = (state, reason) =>
      importProgress({ state, mode, of: wanted, collected: collected.size, sent, reason: reason || null });

    const drain = (final, after) => {
      if (!queue.length) {
        if (final) {
          report("done");
          if (after) after();
        }
        return;
      }
      const batch = queue.splice(0, final ? queue.length : IMPORT_BATCH);
      chrome.runtime.sendMessage({ type: "capture-batch", items: batch, source: "import" }, (r) => {
        const err = chrome.runtime.lastError && chrome.runtime.lastError.message;
        if (err) tel("import.sendfail", { ok: false, error: err, detail: "batch=" + batch.length });
        else if (!r || r.ok === false) tel("import.sendfail", { ok: false, error: (r && r.error) || "no answer", detail: "batch=" + batch.length });
        else sent += r.added || 0;
        report(final ? "done" : "running");
        if (final && queue.length) drain(true, after);
        else if (final && after) after();
      });
    };

    const finish = (reason) => {
      if (done) return;
      done = true;
      if (observer) observer.disconnect();
      clearTimeout(quiet);
      cleanupVisibility();
      importRun = null;
      report(reason === "cancelled" ? "cancelled" : "done", reason);
      // The end row is written once the last batch answered, so the numbers in the
      // log are the numbers on screen (they disagreed before: sent=0 vs "5 sent").
      const writeEnd = () => {
        const sc = xScroller();
        tel(reason === "end" || reason === "timeout" ? "import.stall" : "import.end", {
          ok: reason !== "timeout",
          error: reason,
          detail:
            "collected=" + collected.size + " sent=" + sent + " skipped=" + Math.max(0, collected.size - sent) +
            " queued=" + queue.length + " rounds=" + rounds + " quiet=" + quietRounds +
            " atBottom=" + atBottom() + " stuck=" + stuckRounds + " hiddenMs=" + Math.round(pausedMs / 1000) +
            " rowsWhileHidden=" + rowsWhileHidden + " reason=" + reason + " rows=" + document.querySelectorAll(POST_IN).length +
            " seenRows=" + seenRows + " noId=" + noId +
            " scroller=" + (sc ? sc.tagName + ":" + (getComputedStyle(sc).overflowY || "?") : "none") +
            " scrollTop=" + (sc ? Math.round(sc.scrollTop) : -1) +
            " scrollable=" + (sc ? sc.scrollHeight - sc.clientHeight : -1),
        });
      };
      drain(true, writeEnd);
    };

    let rounds = 0;
    // Counters, so "the tab has more than 6" can be answered with numbers instead of
    // a guess: how many rows the DOM had, how many we could read, how many had no id.
    let seenRows = 0;
    let noId = 0;
    const harvest = () => {
      const rows = document.querySelectorAll(POST_IN);
      seenRows = Math.max(seenRows, rows.length);
      for (const art of rows) {
        // A quoted post is an <article> inside another one in x-web: it belongs to
        // the post above, not to the list as a capture of its own.
        if (art.parentElement && art.parentElement.closest(POST_IN)) continue;
        if (collected.size >= wanted) return; // the number asked for is the number sent
        const it = extract(art, kind);
        if (!it) {
          noId++;
          continue;
        }
        if (collected.has(it.id)) continue;
        collected.set(it.id, it);
        queue.push(it);
      }
    };

    let quietRounds = 0;
    let stuckRounds = 0;
    let pausedMs = 0;
    let pausedAt = 0;
    let rowsWhileHidden = 0;
    let rowsAtHide = 0;

    const onVisibility = () => {
      if (done) return;
      if (document.visibilityState === "hidden") {
        pausedAt = Date.now();
        rowsAtHide = document.querySelectorAll(POST_IN).length;
        clearTimeout(quiet);
        if (observer) observer.disconnect();
        tel("import.paused", {
          ok: true,
          detail: "collected=" + collected.size + " rows=" + rowsAtHide + " rounds=" + rounds,
        });
      } else if (pausedAt) {
        pausedMs += Date.now() - pausedAt;
        rowsWhileHidden =
          document.querySelectorAll(POST_IN).length - rowsAtHide;
        tel("import.resumed", {
          ok: true,
          detail:
            "hiddenFor=" + Math.round((Date.now() - pausedAt) / 1000) + "s rowsDelta=" + rowsWhileHidden +
            " collected=" + collected.size,
        });
        pausedAt = 0;
        step();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    const cleanupVisibility = () => document.removeEventListener("visibilitychange", onVisibility);
    const atBottom = () => {
      const sc = xScroller() || document.scrollingElement || document.documentElement;
      return sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 200;
    };
    const waitForGrowth = () => {
      if (observer) observer.disconnect();
      clearTimeout(quiet);
      observer = new MutationObserver(() => {
        clearTimeout(quiet);
        quietRounds = 0;
        quiet = setTimeout(() => {
          if (observer) observer.disconnect();
          step();
        }, 250);
      });
      observer.observe(document.body, { childList: true, subtree: true });
      quiet = setTimeout(() => {
        if (stillLoading()) {
          // X is fetching more: wait another tick instead of pretending it ended.
          quietRounds = 0;
          step();
          return;
        }
        quietRounds++;
        // A background tab does not render, and a mid-list page has more below: only
        // call it finished when we are actually at the bottom.
        const grew = collected.size > lastCount;
        lastCount = collected.size;
        if (!grew) stuckRounds++;
        else stuckRounds = 0;
        if (!atBottom() && stuckRounds < 8) {
          step();
          return;
        }
        if (quietRounds < IMPORT_QUIET_ROUNDS) step();
        else finish(atBottom() ? "end" : "stuck");
      }, IMPORT_QUIET_MS);
    };

    let lastCount = 0;
    function step() {
      if (done) return;
      rounds++;
      harvest();
      report("running");
      if (collected.size >= wanted) return finish("limit");
      // Time spent hidden does not count against the ten-minute guard.
      if (Date.now() - startedAt - pausedMs > IMPORT_MAX_MS) return finish("timeout");
      if (queue.length >= IMPORT_BATCH) drain(false);
      const sc = nudgeStep();
      // Never conclude on the first tick, however few we have: X's list loads in
      // bursts and a lesson learned at 2 of 100.
      if (rounds < 2) {
        clearTimeout(quiet);
        quiet = setTimeout(() => step(), 800);
        return;
      }
      waitForGrowth();
    }

    importRun = { cancel: () => finish("cancelled") };
    const firstScroller = xScroller();
    tel("import.begin", {
      ok: true,
      detail:
        "path=" + location.pathname + " mode=" + mode + " want=" + wanted +
        " articles=" + document.querySelectorAll("article").length +
        " scroller=" + ((firstScroller && firstScroller.tagName) || "none") +
        " scrollable=" + (firstScroller ? firstScroller.scrollHeight - firstScroller.clientHeight : -1),
    });
    report("running");
    step();
    return { ok: true, mode, limit: wanted };
  }

  try {
    chrome.runtime.onMessage.addListener(importMessage);
  } catch (e) {
    /* a page without the message API still captures likes */
  }

  function importMessage(m, _s, reply) {
    if (!m) return false;
    if (m.type === "import-start") {
      const r = startImport(m.mode, m.limit);
      reply(Object.assign({ api: CONTENT_API }, r || {}));
      return true;
    }
    if (m.type === "import-cancel") {
      if (importRun) importRun.cancel();
      reply({ ok: true });
      return true;
    }
    return false;
  }

  function toast(msg, ok) {
    let t = document.getElementById("echolike-lite-toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "echolike-lite-toast";
      t.style.cssText = "position:fixed;bottom:16px;left:50%;transform:translateX(-50%);padding:8px 14px;border-radius:8px;font:13px system-ui;color:#fff;z-index:99999;transition:opacity .4s;pointer-events:none";
      document.body.appendChild(t);
    }
    t.style.background = ok ? "#00875a" : "#d0021b";
    t.textContent = msg;
    t.style.opacity = "1";
    clearTimeout(t._h);
    t._h = setTimeout(() => (t.style.opacity = "0"), 2500);
  }

  // ---- The circle on x.com: the extension in one press --------------------
  // A small draggable button that carries the version and, on press, the things a
  // user actually wants from a page they are already on: open the inbox, open the
  // settings, export likes or bookmarks. It lives in a shadow root, so X's CSS can
  // never restyle it and ours can never leak into X. Position and on/off switch come
  // from storage; no timers, no observers, nothing running while nobody presses it.
  const VER = (() => {
    try {
      return chrome.runtime.getManifest().version;
    } catch (e) {
      return "?";
    }
  })();

  const FAB_CSS = `
    :host{all:initial}
    *{box-sizing:border-box;font:13px/1.4 system-ui,-apple-system,sans-serif;color:#111}
    .dot{position:fixed;width:42px;height:42px;border-radius:50%;background:#fff;
      border:1px solid #d8d8d8;box-shadow:0 2px 10px rgba(0,0,0,.18);cursor:grab;
      display:flex;align-items:center;justify-content:center;touch-action:none;
      -webkit-user-select:none;user-select:none;z-index:1}
    .dot:hover{border-color:#111}
    .dot:active{cursor:grabbing}
    .dot img{width:24px;height:24px;pointer-events:none;display:block}
    .dot b{position:absolute;top:-4px;right:-4px;min-width:17px;height:17px;border-radius:9px;
      background:#d0021b;color:#fff;font-size:10px;font-weight:700;line-height:17px;
      text-align:center;padding:0 4px;display:none}
    .dot[data-pending] b{display:block}
    .panel{position:fixed;width:290px;background:#fff;border:1px solid #e2e2e2;border-radius:12px;
      box-shadow:0 8px 30px rgba(0,0,0,.18);padding:12px;display:none;z-index:2}
    .panel.on{display:block}
    .head{display:flex;align-items:baseline;gap:6px;margin:0 0 10px}
    .head b{font-size:14px;font-weight:650}
    .head small{color:#888;font-size:11px;font-variant-numeric:tabular-nums}
    .head i.code{margin-left:auto;font:10px/1.6 ui-monospace,Menlo,monospace;font-style:normal;letter-spacing:.09em;color:#b3b3b3}
    .row{display:flex;gap:8px;margin:0 0 8px}
    button{font:inherit;flex:1;padding:8px 10px;border:1px solid #ddd;border-radius:9px;background:#fff;
      cursor:pointer;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    button:hover{border-color:#111}
    button.primary{background:#111;color:#fff;border-color:#111}
    .note{color:#777;font-size:11px;line-height:1.45;margin:10px 0 0}
    .foot{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:10px 0 0;
      border-top:1px solid #eee;padding-top:8px}
    .link{background:none;border:none;padding:0;color:#888;font-size:11px;cursor:pointer;flex:0;
      white-space:nowrap}
    .link:hover{color:#111;text-decoration:underline}
    .status{font-size:11px;color:#00875a;min-height:14px}
  `;

  const FAB_ON = { fab_on: true };
  let fab = null;

  function mountFab() {
    if (fab || window.top !== window) return; // one circle, and not inside an embed
    const host = document.createElement("div");
    host.id = "echolike-lite-fab";
    host.style.cssText = "position:fixed;inset:0;width:0;height:0;z-index:2147483000";
    const root = host.attachShadow({ mode: "open" });
    const icon = (() => {
      try {
        return chrome.runtime.getURL("icons/icon48.png");
      } catch (e) {
        return "";
      }
    })();
    root.innerHTML =
      "<style>" + FAB_CSS + "</style>" +
      '<div class="dot" part="dot" role="button" tabindex="0" title="EchoLike Lite v' + VER + ' — press for actions">' +
      (icon ? '<img src="' + icon + '" alt="EchoLike">' : "<b style=\"position:static\">E</b>") +
      "<b>0</b></div>" +
      '<div class="panel" role="dialog" aria-label="EchoLike Lite">' +
      '<div class="head"><b>EchoLike Lite</b><small>v' + VER + '</small><i class="code">X1</i></div>' +
      '<div class="row"><button data-act="open" data-page="inbox" class="primary">My inbox</button>' +
      '<button data-act="open" data-page="settings">Settings</button></div>' +
      '<div class="row"><button data-act="export" data-pick="likes">Export likes</button></div>' +
      '<div class="row"><button data-act="export" data-pick="bookmarks">Export bookmarks</button></div>' +
      '<div class="row"><button data-act="export" data-pick="all">Export everything</button></div>' +
      '<div class="row"><button data-act="markad">Mark an ad…</button></div>' +
      '<div class="status"></div>' +
      '<p class="note">Next on this button: AI on the post you are reading, profile edits, writing posts with images and video, and comments.</p>' +
      '<div class="foot"><span class="link" data-act="hide">Hide this button</span>' +
      '<span class="link">v' + VER + "</span></div></div>";
    // documentElement, not body: X re-renders the app root, and this must outlive it.
    // The icon comes from the package; if the browser cannot load it, the letter
    // stands in. (An inline onerror attribute would be blocked by X's CSP.)
    const img = root.querySelector(".dot img");
    if (img) {
      img.addEventListener("error", () => {
        const mark = document.createElement("span");
        mark.textContent = "E";
        mark.style.cssText = "font:700 15px system-ui;letter-spacing:.5px;pointer-events:none";
        img.replaceWith(mark);
      });
    }
    document.documentElement.appendChild(host);

    const dot = root.querySelector(".dot");
    const panel = root.querySelector(".panel");
    const badge = dot.querySelector("b");
    fab = { host, root, dot, panel, x: 0, y: 0, open: false };

    const place = (x, y) => {
      fab.x = Math.max(4, Math.min(window.innerWidth - 50, x));
      fab.y = Math.max(4, Math.min(window.innerHeight - 50, y));
      dot.style.left = fab.x + "px";
      dot.style.top = fab.y + "px";
      if (fab.open) placePanel();
    };
    const placePanel = () => {
      const w = panel.offsetWidth || 280;
      const h = panel.offsetHeight || 260;
      const left = Math.max(8, Math.min(window.innerWidth - w - 8, fab.x + 21 - w / 2));
      // Above the circle when there is room, below it otherwise — measured from the
      // circle's own edges, so the panel never lands on top of the button.
      const above = fab.y - h - 10;
      const top = above > 8 ? above : Math.min(window.innerHeight - h - 8, fab.y + 52);
      panel.style.left = left + "px";
      panel.style.top = Math.max(8, top) + "px";
    };

    // Pending captures get a count on the circle: the one number a user wants to see
    // without opening anything.
    const paintPending = (n) => {
      if (n > 0) {
        badge.textContent = n > 9 ? "9+" : String(n);
        dot.setAttribute("data-pending", "1");
        dot.title = "EchoLike Lite v" + VER + " — " + n + " waiting to send";
      } else {
        dot.removeAttribute("data-pending");
        dot.title = "EchoLike Lite v" + VER + " — press for actions";
      }
    };
    const readPending = () => {
      try {
        chrome.storage.local.get({ outbox: [] }, (s) => paintPending((s.outbox || []).length));
      } catch (e) {
        /* no storage, no badge: the circle still works */
      }
    };

    const say = (msg) => {
      const st = root.querySelector(".status");
      st.textContent = msg;
      clearTimeout(say._h);
      say._h = setTimeout(() => (st.textContent = ""), 3000);
    };

    // Export is local and immediate: the mirror in this browser is the user's own
    // data, so a press gives a file without asking a server for anything.
    function download(items, pick) {
      const blob = new Blob([JSON.stringify(items, null, 1)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "echolike-" + pick + "-" + new Date().toISOString().slice(0, 10) + ".json";
      a.style.display = "none";
      document.documentElement.appendChild(a);
      a.click();
      setTimeout(() => {
        URL.revokeObjectURL(a.href);
        a.remove();
      }, 4000);
      return items.length;
    }

    const counts = () => {
      try {
        chrome.storage.local.get({ items: [] }, (s) => {
          const items = s.items || [];
          const likes = items.filter((i) => i.kind === "like" || i.kind === "unlike").length;
          const bookmarks = items.filter((i) => i.kind === "bookmark" || i.kind === "unbookmark").length;
          const label = (pick, n) => {
            const b = root.querySelector('button[data-act="export"][data-pick="' + pick + '"]');
            if (b) b.textContent = (pick === "likes" ? "Export likes" : pick === "bookmarks" ? "Export bookmarks" : "Export everything") + (n ? " (" + n + ")" : "");
          };
          label("likes", likes);
          label("bookmarks", bookmarks);
          label("all", items.length);
        });
      } catch (e) {
        /* counts are decoration; the buttons work without them */
      }
    };

    const close = () => {
      fab.open = false;
      panel.classList.remove("on");
    };
    const open = () => {
      fab.open = true;
      panel.classList.add("on");
      counts();
      placePanel();
    };

    // Drag or press: 5 px of travel means the user is moving the button, not opening it.
    let drag = null;
    dot.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      drag = { dx: e.clientX - fab.x, dy: e.clientY - fab.y, moved: false };
      dot.setPointerCapture(e.pointerId);
    });
    dot.addEventListener("pointermove", (e) => {
      if (!drag) return;
      e.stopPropagation();
      const x = e.clientX - drag.dx;
      const y = e.clientY - drag.dy;
      if (Math.abs(x - fab.x) + Math.abs(y - fab.y) > 5) drag.moved = true;
      place(x, y);
    });
    dot.addEventListener("pointerup", (e) => {
      e.stopPropagation();
      const d = drag;
      drag = null;
      if (!d) return;
      if (d.moved) {
        try {
          chrome.storage.local.set({ fab_x: fab.x, fab_y: fab.y });
        } catch (err) {
          /* a page that cannot save still keeps it for this session */
        }
        return;
      }
      if (fab.open) close();
      else open();
    });
    dot.addEventListener("pointercancel", () => (drag = null));
    // The same button for a keyboard: Enter or Space, no mouse needed.
    dot.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      e.stopPropagation();
      if (fab.open) close();
      else open();
    });

    root.addEventListener("click", (e) => {
      const t = e.target instanceof Element ? e.target.closest("[data-act]") : null;
      if (!t) return;
      e.stopPropagation();
      const act = t.getAttribute("data-act");
      if (act === "hide") {
        try {
          chrome.storage.local.set({ fab_on: false });
        } catch (err) {
          /* ignore */
        }
        unmountFab();
        return;
      }
      if (act === "open") {
        try {
          chrome.runtime.sendMessage({ type: "open", page: t.getAttribute("data-page") }, () => {
            if (chrome.runtime.lastError) say("the extension page is not reachable");
            else say("opening…");
          });
        } catch (err) {
          say("the extension page is not reachable");
        }
        return;
      }
      if (act === "markad") {
        close();
        say("tap the ad you want gone");
        startPick();
        return;
      }
      if (act === "export") {
        const pick = t.getAttribute("data-pick") || "all";
        try {
          chrome.runtime.sendMessage({ type: "export", pick }, (r) => {
            const items = (r && r.items) || [];
            const n = download(items, pick);
            say(n ? "downloaded " + n + " " + (pick === "all" ? "captures" : pick) : "nothing to export yet");
          });
        } catch (err) {
          say("the extension is not reachable");
        }
      }
    });

    // Press anywhere else, or Escape: the panel closes. No polling, no focus trap.
    window.addEventListener(
      "pointerdown",
      (e) => {
        if (!fab || !fab.open) return;
        if (e.composedPath().indexOf(host) >= 0) return;
        close();
      },
      true
    );
    window.addEventListener("keydown", (e) => {
      if (fab && fab.open && e.key === "Escape") close();
    });
    window.addEventListener("resize", () => place(fab.x, fab.y));

    try {
      chrome.storage.local.get({ fab_x: window.innerWidth - 58, fab_y: window.innerHeight - 118 }, (s) =>
        place(Number(s.fab_x), Number(s.fab_y)),
      );
    } catch (e) {
      place(window.innerWidth - 58, window.innerHeight - 118);
    }
    readPending();
  }

  function unmountFab() {
    if (!fab) return;
    fab.host.remove();
    fab = null;
  }

  function applyFab(on) {
    if (on) mountFab();
    else unmountFab();
  }

  chrome.storage.local.get(FAB_ON, (s) => applyFab(s.fab_on !== false));
  chrome.storage.onChanged.addListener((ch) => {
    if (ch.fab_on) applyFab(ch.fab_on.newValue !== false);
    if (fab && (ch.outbox || ch.items)) {
      if (ch.outbox && fab.dot) {
        const n = (ch.outbox.newValue || []).length;
        const badge = fab.dot.querySelector("b");
        if (n > 0) {
          badge.textContent = n > 9 ? "9+" : String(n);
          fab.dot.setAttribute("data-pending", "1");
        } else fab.dot.removeAttribute("data-pending");
      }
    }
    if (ch.fab_x || ch.fab_y) {
      // "Put it back" in Settings: the position was cleared.
      if (fab && ch.fab_x && ch.fab_x.newValue == null) placeDefault();
    }
  });
  function placeDefault() {
    if (!fab) return;
    fab.x = window.innerWidth - 58;
    fab.y = window.innerHeight - 118;
    fab.dot.style.left = fab.x + "px";
    fab.dot.style.top = fab.y + "px";
  }

  // Capture phase: read the button's testid BEFORE X flips it. On x-web there is
  // no testid; the icon and aria-pressed are read instead, in the same phase.
  let unmatchedReported = false;
  document.addEventListener(
    "click",
    (e) => {
      try {
        const btn = actionButton(e.target);
        if (!btn) {
          // A like/bookmark-shaped button we cannot name is the failure that looks
          // like "EchoLike does nothing". Record the label, once per page.
          const b = e.target instanceof Element ? e.target.closest('button,[role="button"]') : null;
          const label = (b && b.getAttribute("aria-label")) || "";
          if (b && !unmatchedReported && /like|heart|bookmark|guardar|me gusta/i.test(label)) {
            unmatchedReported = true;
            tel("capture.unmatched", { ok: false, error: label.slice(0, 60), detail: domDetail() });
          }
          return;
        }
        reportDom();
        const item = extract(postOf(btn.el), btn.kind);
        if (!item) {
          tel("capture.noitem", { ok: false, error: "no post link on a " + btn.kind + " button", detail: domDetail() });
          return toast("EchoLike: could not read this post", false);
        }
        tel("capture", { ok: true, detail: "kind=" + btn.kind + " " + domDetail() });
        chrome.runtime.sendMessage({ type: "capture", item }, (r) => {
          if (chrome.runtime.lastError || !r) return toast("EchoLike: saved here, inbox not reached", false);
          toast(r.sent ? "EchoLike ✓ sent" : r.saved ? "EchoLike ✓ saved (no inbox yet)" : "EchoLike ✗ " + (r.error || "error"), !!(r.sent || r.saved));
        });
      } catch (err) {
        console.warn("EchoLike Lite", err);
      }
    },
    true
  );
})();
