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

  // Bump when the walk changes. The background refuses to start an import on a tab
  // whose script speaks an older api, and reloads it instead — a stale tab is the
  // difference between 7 rows and a thousand, and it is invisible otherwise.
  const CONTENT_API = 6;

  const KINDS = { like: "like", unlike: "unlike", bookmark: "bookmark", removeBookmark: "unbookmark" };

  function actionButton(target) {
    let el = target && target.closest ? target.closest("[data-testid]") : null;
    while (el && !KINDS[el.getAttribute("data-testid")]) {
      el = el.parentElement ? el.parentElement.closest("[data-testid]") : null;
    }
    return el;
  }

  // The post's own link: any /status/ anchor that is NOT inside the quoted tweet,
  // the media container, or the tweet text. Taking the first anchor made a row with a
  // quote resolve to the *quoted* post, so many rows collapsed into one id.
  function ownStatusLink(art) {
    const anchors = Array.from(art.querySelectorAll('a[href*="/status/"]'));
    const isQuoted = (a) => {
      const q = a.closest('div[role="link"]');
      if (q && q !== art && art.contains(q)) return true;
      const t = a.closest('[data-testid="tweetText"]');
      return !!(t && t !== art);
    };
    const own = anchors.filter((a) => !isQuoted(a) && /\/status\/\d+/.test(a.getAttribute("href")));
    // the timestamp link is the canonical one when there are several
    return own.find((a) => a.querySelector("time")) || own[0] || null;
  }

  // One extraction, shared by the click path and the import walk.
  function extract(art, kind) {
    if (!art) return null;
    const ad = !!art.closest('[data-testid="placementTracking"]');
    const a = ownStatusLink(art);
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
            " rowsWhileHidden=" + rowsWhileHidden + " reason=" + reason + " rows=" + document.querySelectorAll('article, [data-testid="tweet"]').length +
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
      const rows = document.querySelectorAll('article, [data-testid="tweet"]');
      seenRows = Math.max(seenRows, rows.length);
      for (const art of rows) {
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
        rowsAtHide = document.querySelectorAll('article, [data-testid="tweet"]').length;
        clearTimeout(quiet);
        if (observer) observer.disconnect();
        tel("import.paused", {
          ok: true,
          detail: "collected=" + collected.size + " rows=" + rowsAtHide + " rounds=" + rounds,
        });
      } else if (pausedAt) {
        pausedMs += Date.now() - pausedAt;
        rowsWhileHidden =
          document.querySelectorAll('article, [data-testid="tweet"]').length - rowsAtHide;
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

  chrome.runtime.onMessage.addListener((m, _s, reply) => {
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
