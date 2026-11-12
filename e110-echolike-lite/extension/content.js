// EchoLike Lite — content script. One capture-phase click listener, nothing else.
// No observers, no timers, no DOM polling: zero cost until you click like/bookmark.
(function () {
  if (window.__echolikeLite) return;
  window.__echolikeLite = true;

  // ---- Ads: one stylesheet, no observers, no timers. ----
  // A promoted post is a real tweet inside [data-testid="placementTracking"] (the
  // marker Control Panel for Twitter uses too); promoted trends carry that arrow
  // icon. Hiding the whole cell removes the empty gap the ad would leave behind.
  // X puts OTHER inserted modules in the same wrapper — Grok answers, above all —
  // so a placement only counts as an ad when it holds a tweet and shows no Grok
  // marker: Grok testids, a /grok author link, or an aria-label naming Grok.
  const NOT_GROK =
    ':not(:has([data-testid*="Grok"],[data-testid*="grok"],a[href*="/grok"],' +
    '[aria-label*="Grok"],[aria-label*="grok"]))';
  const ADS_CSS =
    '[data-testid="placementTracking"]:has([data-testid="tweet"])' + NOT_GROK + '{display:none !important}' +
    '[data-testid="cellInnerDiv"]:has([data-testid="placementTracking"] [data-testid="tweet"])' +
    NOT_GROK +
    '{display:none !important}' +
    '[data-testid="trend"]:has(path[d^="M19.498 3h-15"]){display:none !important}';

  function applyAds(hide) {
    const cur = document.getElementById("echolike-lite-ads");
    if (!hide) {
      if (cur) cur.remove();
      return;
    }
    if (cur) return;
    const style = document.createElement("style");
    style.id = "echolike-lite-ads";
    style.textContent = ADS_CSS;
    (document.head || document.documentElement).appendChild(style);
  }

  // Two events, no timers: an X tab finishing loading is the cheapest honest moment
  // to retry a queue, and the browser's own "online" is when a queue is worth sending.
  const ping = (type) => {
    try {
      const p = chrome.runtime.sendMessage({ type });
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

  function actionButton(target) {
    let el = target && target.closest ? target.closest("[data-testid]") : null;
    while (el && !KINDS[el.getAttribute("data-testid")]) {
      el = el.parentElement ? el.parentElement.closest("[data-testid]") : null;
    }
    return el;
  }

  // One extraction, shared by the click path and the import walk.
  function extract(art, kind) {
    if (!art) return null;
    const ad = !!art.closest('[data-testid="placementTracking"]');
    const a = art.querySelector('a[href*="/status/"]');
    const m = a && a.getAttribute("href").match(/\/([A-Za-z0-9_]{1,15})\/status\/(\d+)/);
    if (!m) return null;
    const txt = art.querySelector('[data-testid="tweetText"]');
    const time = a.querySelector("time");
    return {
      kind,
      id: m[2],
      handle: m[1],
      url: "https://x.com/" + m[1] + "/status/" + m[2],
      text: txt ? (txt.innerText || txt.textContent || "").slice(0, 2000) : "",
      tweet_time: time ? time.getAttribute("datetime") : null,
      ad,
      clicked_at: new Date().toISOString(),
    };
  }

  function capture(btn) {
    return extract(btn.closest("article"), KINDS[btn.getAttribute("data-testid")]);
  }

  const tel = (action, info) => {
    try {
      const p = chrome.runtime.sendMessage({ type: "tel", action, info: Object.assign({ host: location.host }, info || {}) });
      if (p && p.catch) p.catch(() => {});
    } catch (e) {
      /* the walk must not die because a diagnostic could not be sent */
    }
  };

  // ---- Import: walk a list that X builds as you scroll ----------------------
  // Only runs when the user starts it from the Import tab. It stops by itself at the
  // requested count, when the list stops growing, or after ten minutes. Growth is
  // detected with a MutationObserver: the only timer is the "nothing new arrived"
  // guard, and it exists only while an import is running.
  const IMPORT_QUIET_MS = 2500;
  const IMPORT_MAX_MS = 10 * 60 * 1000;
  const IMPORT_BATCH = 25;
  let importRun = null;

  const importProgress = (patch) =>
    chrome.storage.local.set({ import_progress: Object.assign({ at: new Date().toISOString() }, patch) });

  // The scroll container is whatever ancestor of a tweet actually scrolls: X moves
  // it between layouts, and guessing by testid breaks on every redesign.
  function xScroller() {
    const art = document.querySelector("article");
    let el = art && art.parentElement;
    while (el && el !== document.body && el !== document.documentElement) {
      if (el.scrollHeight > el.clientHeight + 100) return el;
      el = el.parentElement;
    }
    return document.scrollingElement || document.documentElement;
  }

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

    const drain = (final) => {
      if (!queue.length) {
        if (final) report("done");
        return;
      }
      const batch = queue.splice(0, final ? queue.length : IMPORT_BATCH);
      chrome.runtime.sendMessage({ type: "capture-batch", items: batch, source: "import" }, (r) => {
        if (!chrome.runtime.lastError && r && r.ok) sent += r.added || 0;
        report(final ? "done" : "running");
        if (final && queue.length) drain(true);
      });
    };

    const finish = (reason) => {
      if (done) return;
      done = true;
      if (observer) observer.disconnect();
      clearTimeout(quiet);
      importRun = null;
      drain(true);
      report(reason === "cancelled" ? "cancelled" : "done", reason);
      const sc = xScroller();
      tel(reason === "end" || reason === "timeout" ? "import.stall" : "import.end", {
        ok: reason !== "timeout",
        error: reason,
        detail:
          "collected=" + collected.size + " sent=" + sent + " rounds=" + rounds + " reason=" + reason +
          " articles=" + document.querySelectorAll("article").length +
          " scrollTop=" + (sc ? Math.round(sc.scrollTop) : -1) +
          " scrollable=" + (sc ? sc.scrollHeight - sc.clientHeight : -1),
      });
    };

    let rounds = 0;
    const harvest = () => {
      for (const art of document.querySelectorAll("article")) {
        const it = extract(art, kind);
        if (!it || collected.has(it.id)) continue;
        collected.set(it.id, it);
        queue.push(it);
      }
    };

    const waitForGrowth = () => {
      if (observer) observer.disconnect();
      clearTimeout(quiet);
      observer = new MutationObserver(() => {
        clearTimeout(quiet);
        quiet = setTimeout(() => {
          if (observer) observer.disconnect();
          step();
        }, 200);
      });
      observer.observe(document.body, { childList: true, subtree: true });
      quiet = setTimeout(() => finish("end"), IMPORT_QUIET_MS);
    };

    function step() {
      if (done) return;
      rounds++;
      harvest();
      report("running");
      if (collected.size >= wanted) return finish("limit");
      if (Date.now() - startedAt > IMPORT_MAX_MS) return finish("timeout");
      if (queue.length >= IMPORT_BATCH) drain(false);
      const sc = xScroller();
      if (sc) sc.scrollTop = sc.scrollHeight;
      // A list that has not answered once is not "finished": give X another round
      // before believing the end.
      if (collected.size === 0 && rounds < 4) {
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

  chrome.runtime.onMessage.addListener((m, _s, reply) => {
    if (!m) return false;
    if (m.type === "import-start") {
      reply(startImport(m.mode, m.limit));
      return true;
    }
    if (m.type === "import-cancel") {
      if (importRun) importRun.cancel();
      reply({ ok: true });
      return true;
    }
    return false;
  });

  function toast(msg, ok) {
    let t = document.getElementById("echolike-lite-toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "echolike-lite-toast";
      t.style.cssText = "position:fixed;bottom:16px;left:50%;transform:translateX(-50%);padding:8px 14px;border-radius:8px;font:13px system-ui;color:#fff;z-index:99999;transition:opacity .4s";
      document.body.appendChild(t);
    }
    t.style.background = ok ? "#00875a" : "#d0021b";
    t.textContent = msg;
    t.style.opacity = "1";
    clearTimeout(t._h);
    t._h = setTimeout(() => (t.style.opacity = "0"), 2500);
  }

  // Capture phase: read the button's testid BEFORE X flips it.
  document.addEventListener(
    "click",
    (e) => {
      try {
        const btn = actionButton(e.target);
        if (!btn) return;
        const item = capture(btn);
        if (!item) return;
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
