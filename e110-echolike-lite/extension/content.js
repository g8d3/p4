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
  const CONTENT_API = 8;

  const KINDS = { like: "like", unlike: "unlike", bookmark: "bookmark", removeBookmark: "unbookmark" };

  function actionButton(target) {
    let el = target && target.closest ? target.closest("[data-testid]") : null;
    while (el && !KINDS[el.getAttribute("data-testid")]) {
      el = el.parentElement ? el.parentElement.closest("[data-testid]") : null;
    }
    return el;
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

  const countOf = (art, testid) => {
    const el = art.querySelector('[data-testid="' + testid + '"]');
    if (!el) return null;
    return num(el.getAttribute("aria-label")) ?? num(el.innerText || el.textContent);
  };

  const viewsOf = (art) => {
    const el = art.querySelector('a[href*="/analytics"]');
    if (!el) return null;
    return num(el.getAttribute("aria-label")) ?? num(el.innerText || el.textContent);
  };

  const mediaOf = (art) => {
    const imgs = art.querySelectorAll('[data-testid="tweetPhoto"]').length;
    const vids = art.querySelectorAll('[data-testid="videoPlayer"], [data-testid="videoComponent"]').length;
    return { media: imgs + vids, photos: imgs, videos: vids, card: !!art.querySelector('[data-testid="card.wrapper"]') };
  };

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
    const name = art.querySelector('[data-testid="User-Name"]');
    const quoted = art.querySelector('div[role="link"] a[href*="/status/"]');
    const qm = quoted && quoted.getAttribute("href").match(/\/status\/(\d+)/);
    const social = art.querySelector('[data-testid="socialContext"]');
    const media = mediaOf(art);
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
      published_at: time ? time.getAttribute("datetime") : null,
      tweet_time: time ? time.getAttribute("datetime") : null, // kept for older inboxes
      counts: {
        replies: countOf(art, "reply"),
        reposts: countOf(art, "retweet"),
        likes: countOf(art, "like"),
        bookmarks: countOf(art, "bookmark"),
        views: viewsOf(art),
      },
      quotes: qm ? qm[1] : null,
      is_repost: social ? /reposted|retweeted|repostó|retuiteó/i.test(social.innerText || "") : false,
      ad,
      ...media,
      // when, and from where: the two dates that cannot be recovered later
      captured_at: new Date().toISOString(),
      clicked_at: new Date().toISOString(),
      source: kind === "bookmark" ? "bookmark" : "like",
      page: location.pathname,
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
      t.style.cssText = "position:fixed;bottom:16px;left:50%;transform:translateX(-50%);padding:8px 14px;border-radius:8px;font:13px system-ui;color:#fff;z-index:99999;transition:opacity .4s";
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
