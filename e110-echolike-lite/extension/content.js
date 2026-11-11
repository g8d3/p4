// EchoLike Lite — content script. One capture-phase click listener, nothing else.
// No observers, no timers, no DOM polling: zero cost until you click like/bookmark.
(function () {
  if (window.__echolikeLite) return;
  window.__echolikeLite = true;

  // ---- Ads: one stylesheet, no observers, no timers. ----
  // A promoted post is rendered inside [data-testid="placementTracking"] (the marker
  // Control Panel for Twitter uses too); pro moted trends carry that arrow icon.
  // Hiding the whole cell removes the empty gap the ad would leave behind.
  const ADS_CSS =
    '[data-testid="placementTracking"]{display:none !important}' +
    '[data-testid="cellInnerDiv"]:has([data-testid="placementTracking"]){display:none !important}' +
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

  function capture(btn) {
    const art = btn.closest("article");
    if (!art) return null;
    // Liking an ad is still a like: never silently drop it, but mark it for the inbox.
    const ad = !!art.closest('[data-testid="placementTracking"]');
    const a = art.querySelector('a[href*="/status/"]');
    const m = a && a.getAttribute("href").match(/\/([A-Za-z0-9_]{1,15})\/status\/(\d+)/);
    if (!m) return null;
    const txt = art.querySelector('[data-testid="tweetText"]');
    const time = a.querySelector("time");
    return {
      kind: KINDS[btn.getAttribute("data-testid")],
      id: m[2],
      handle: m[1],
      url: "https://x.com/" + m[1] + "/status/" + m[2],
      text: txt ? (txt.innerText || txt.textContent || "").slice(0, 2000) : "",
      tweet_time: time ? time.getAttribute("datetime") : null,
      ad,
      clicked_at: new Date().toISOString(),
    };
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
