"use strict";
/* OSS Token Launchpad skeleton — vanilla, no deps.
   API-aware: uses /api/* when served behind a backend (e087-style),
   otherwise falls back to a localStorage demo store so file:// works. */
const $ = (id) => document.getElementById(id);
const LS_KEY = "oss-launchpad-v1";
let apiMode = false;

/* ---------- store ---------- */
function demoLoad() {
  try {
    const d = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
    return { tokens: d.tokens || [], payments: d.payments || [] };
  } catch { return { tokens: [], payments: [] }; }
}
function demoSave(d) { localStorage.setItem(LS_KEY, JSON.stringify(d)); }
const uid = (p) => `${p}_${Date.now().toString(36)}${Math.floor(Math.random() * 1e4)}`;

/* ---------- repos ---------- */
function normalizeRepo(s) {
  s = (s || "").trim().replace(/\/+$/, "").replace(/\.git$/i, "");
  const m = s.match(/github\.com[/:]([^/]+\/[^/]+)/i);
  if (m) s = m[1];
  s = s.split("/").slice(0, 2).join("/");
  return /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(s) ? s : null;
}
function collectRepos() {
  const seen = new Set(), out = [], bad = [];
  document.querySelectorAll(".repo").forEach((el) => {
    const v = el.value.trim();
    if (!v) return;
    const n = normalizeRepo(v);
    if (!n || seen.has(n.toLowerCase())) { if (!n) bad.push(v); return; }
    seen.add(n.toLowerCase()); out.push(n);
  });
  return { repos: out.slice(0, 4), bad };
}

/* ---------- api with demo fallback ---------- */
async function api(method, url, body) {
  const r = await fetch(url, {
    method, headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `request failed (${r.status})`);
  return data;
}
async function probeApi() {
  try { await api("GET", "/api/tokens"); apiMode = true; }
  catch { apiMode = false; }
  $("mode-badge").textContent = apiMode ? "api" : "demo store";
}
async function getTokens() {
  if (apiMode) return (await api("GET", "/api/tokens")).tokens || [];
  return demoLoad().tokens;
}
async function getPayments() {
  if (apiMode) return (await api("GET", "/api/payments")).payments || [];
  return demoLoad().payments;
}
async function createToken(name, repos) {
  if (apiMode) return (await api("POST", "/api/tokens", { name, repos })).token;
  const d = demoLoad();
  const tok = { id: uid("tok"), name, repos, created_at: Date.now() / 1000 | 0 };
  d.tokens.push(tok); demoSave(d); return tok;
}
async function createPayment(method, amount, token, repos) {
  if (apiMode) return (await api("POST", "/api/pay", { method, amount, token, repos })).payment;
  const d = demoLoad();
  const splits = splitAmount(amount, repos);
  const pay = {
    id: uid("pay"), method, amount, token, repos, splits,
    splits_original: { ...splits }, refunded: false,
    stub: { note: "demo record, no real rails" }, created_at: Date.now() / 1000 | 0,
  };
  d.payments.push(pay); demoSave(d); return pay;
}
async function refundPayment(id) {
  if (apiMode) return (await api("POST", "/api/refund", { payment_id: id })).payment;
  const d = demoLoad();
  const p = d.payments.find((x) => x.id === id);
  if (p && !p.refunded) {
    p.splits_original = { ...p.splits }; p.splits = Object.fromEntries(p.repos.map((r) => [r, 0]));
    p.refunded = true; demoSave(d);
    ledgerRefund(p.betaId); // mirror into BetaPay guarantee flow (approved => zeroes shareable revenue)
  }
  return p;
}
function splitAmount(amount, repos) {
  const splits = {}; let acc = 0;
  const share = Math.round((amount / repos.length) * 100) / 100;
  repos.slice(0, -1).forEach((r) => { splits[r] = share; acc += share; });
  splits[repos[repos.length - 1]] = Math.round((amount - acc) * 100) / 100;
  return splits;
}

/* ---------- BetaPay ledger truth (single revenue-share rule) ----------
 * Demo store persists tokens/payments for the Projects table; BetaPay is the
 * revenue truth: ONLY live settled non-refunded payments count. Test settles
 * as settled-test worth $0. Per-payment repos are configured equal-weight so
 * the ledger split matches the demo equal-split preview. */
function ledgerRepos(repos) {
  const w = repos.length ? 1 / repos.length : 0;
  return repos.map((r) => ({ repo: r, weight: w }));
}
function ledgerRecord(method, amountCents, repos, live) {
  if (!window.BetaPay) return null;
  BetaPay.configure({ repos: ledgerRepos(repos) });
  let p;
  if (method === "crypto") {
    p = BetaPay.cryptoInvoice(amountCents);
    p.live = !!live; // stub defaults live; honor the test toggle
    BetaPay.cryptoSubmitTx(p.id, "TX-PLACEHOLDER");
    BetaPay.cryptoConfirm(p.id);
    if (!live) p.status = "settled-test";
  } else {
    p = BetaPay.fiatCheckout(amountCents, { live: !!live });
    BetaPay.fiatConfirm(p.id);
  }
  return p;
}
function ledgerRefund(betaId) {
  if (!window.BetaPay || !betaId) return;
  const r = BetaPay.requestRefund(betaId, "guarantee");
  if (r) BetaPay.decideRefund(r.id, true);
}
function renderLedger() {
  const n = $("ledger-out");
  if (!n) return;
  if (!window.BetaPay) { n.textContent = "ledger: beta-payments.js not loaded."; return; }
  const s = BetaPay.snapshot();
  const lines = s.payouts.payouts.map((x) => `${x.repo} \u2190 $${(x.cents / 100).toFixed(2)}`).join(" \u00b7 ") || "(no repos configured)";
  n.textContent = `ledger truth: revenue $${(s.revenueCents / 100).toFixed(2)} from ${s.payments} payment(s), ${s.refunds} refund(s) \u00b7 payouts: ${lines} \u00b7 rule: live+settled+non-refunded only, test = $0.`;
}

/* ---------- projects aggregation (mirrors server logic) ---------- */
function aggregate(tokens, payments) {
  const repos = {};
  const cell = (r) => (repos[r] ??= { repo: r, earned: 0, due: 0, refunded: 0, tokens: [] });
  tokens.forEach((t) => (t.repos || []).forEach((r) => {
    if (!cell(r).tokens.includes(t.name)) cell(r).tokens.push(t.name);
  }));
  payments.forEach((p) => {
    if (p.refunded) {
      Object.entries(p.splits_original || {}).forEach(([r, v]) => { cell(r).refunded = round2(cell(r).refunded + v); });
    } else {
      Object.entries(p.splits || {}).forEach(([r, v]) => { cell(r).earned = round2(cell(r).earned + v); });
    }
  });
  Object.values(repos).forEach((r) => { r.due = r.earned; });
  return Object.values(repos).sort((a, b) => a.repo.localeCompare(b.repo));
}
const round2 = (n) => Math.round((Number(n) + Number.EPSILON) * 100) / 100;
const money = (n) => round2(n).toFixed(2);

/* ---------- safe DOM helpers (no innerHTML with user data) ---------- */
function el(tag, text, attrs = {}) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
  return n;
}
function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }

/* ---------- render ---------- */
let cache = { tokens: [], payments: [] };
async function refresh() {
  try {
    cache.tokens = await getTokens();
    cache.payments = await getPayments();
  } catch (e) { $("pay-out").textContent = "Error: " + e.message; return; }
  renderTokens(); renderProjects(); renderPay(); renderLedger();
}
function renderTokens() {
  $("token-count").textContent = cache.tokens.length ? `(${cache.tokens.length})` : "";
  const ul = $("token-list"); clear(ul);
  if (!cache.tokens.length) { ul.append(el("li", "No tokens yet — launch one above.", { class: "muted" })); }
  cache.tokens.forEach((t) => {
    const li = el("li");
    li.append(el("strong", t.name), el("span", " → " + (t.repos || []).join(", ")));
    ul.append(li);
  });
  const sel = $("pay-token"); clear(sel);
  if (!cache.tokens.length) sel.append(el("option", "— launch first —", { value: "" }));
  cache.tokens.forEach((t) => {
    const o = el("option", `${t.name} (${(t.repos || []).length} repos)`);
    o.value = t.name; o.dataset.repos = JSON.stringify(t.repos || []);
    sel.append(o);
  });
  updateSplitPreview();
}
function renderProjects() {
  const q = ($("project-filter").value || "").toLowerCase();
  const rows = aggregate(cache.tokens, cache.payments).filter((p) => p.repo.toLowerCase().includes(q));
  const tb = $("projects-body"); clear(tb);
  if (!rows.length) {
    const tr = el("tr"), td = el("td", "No repos yet — launch a token, then pay it.");
    td.colSpan = 5; tr.append(td); tb.append(tr);
  }
  let e = 0, d = 0, r = 0;
  rows.forEach((p) => {
    e += p.earned; d += p.due; r += p.refunded;
    const tr = el("tr");
    tr.append(el("td", p.repo), el("td", money(p.earned)), el("td", money(p.due)),
      el("td", money(p.refunded)), el("td", p.tokens.join(", ")));
    tb.append(tr);
  });
  $("tot-earned").textContent = money(e);
  $("tot-due").textContent = money(d);
  $("tot-ref").textContent = money(r);
}
function renderPay() {
  const tb = $("payments-body"); clear(tb);
  const pays = [...cache.payments].reverse();
  if (!pays.length) {
    const tr = el("tr"), td = el("td", "No payments yet.");
    td.colSpan = 6; tr.append(td); tb.append(tr); return;
  }
  pays.forEach((p) => {
    const tr = el("tr");
    tr.append(el("td", p.id), el("td", p.method), el("td", String(p.amount)),
      el("td", p.token || ""), el("td", p.refunded ? "refunded" : "active"));
    const td = el("td");
    if (!p.refunded) {
      const b = el("button", "Refund", { type: "button", class: "ghost" });
      b.onclick = async () => { await refundPayment(p.id); $("pay-out").textContent = `Refunded ${p.id}.`; refresh(); };
      td.append(b);
    }
    tr.append(td); tb.append(tr);
  });
}
function updateSplitPreview() {
  const opt = $("pay-token").selectedOptions[0];
  const amt = parseFloat($("pay-amount").value);
  if (!opt || !opt.dataset.repos || !(amt > 0)) { $("split-preview").textContent = "Pick a token to preview the split."; return; }
  const repos = JSON.parse(opt.dataset.repos);
  const s = splitAmount(amt, repos);
  $("split-preview").textContent = "Split: " + Object.entries(s).map(([r, v]) => `${r} ← $${money(v)}`).join(" · ");
}

/* ---------- events ---------- */
document.querySelectorAll(".tabs button").forEach((b) => b.onclick = () => {
  document.querySelectorAll(".tabs button").forEach((x) => { x.classList.remove("active"); x.setAttribute("aria-selected", "false"); });
  document.querySelectorAll(".tab").forEach((s) => s.classList.remove("active"));
  b.classList.add("active"); b.setAttribute("aria-selected", "true");
  $(b.dataset.tab).classList.add("active");
});
$("launch-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const name = $("token-name").value.trim();
  const { repos, bad } = collectRepos();
  if (!name) { $("launch-hint").textContent = "Token name is required."; return; }
  if (!repos.length) { $("launch-hint").textContent = "Enter at least 1 valid repo (owner/repo)." + (bad.length ? ` Rejected: ${bad.join(", ")}` : ""); return; }
  try {
    const t = await createToken(name, repos);
    $("launch-hint").textContent = `Created “${t.name}” → ${t.repos.join(", ")}.`;
    $("launch-form").reset(); refresh();
  } catch (e) { $("launch-hint").textContent = "Error: " + e.message; }
});
async function pay(method) {
  const sel = $("pay-token"), opt = sel.selectedOptions[0];
  if (!opt || !opt.value) { $("pay-out").textContent = "Launch a token first."; return; }
  const amt = parseFloat($("pay-amount").value);
  if (!(amt > 0)) { $("pay-out").textContent = "Amount must be > 0."; return; }
  const live = !!($("pay-live") && $("pay-live").checked);
  const repos = JSON.parse(opt.dataset.repos);
  const cents = Math.round(amt * 100);
  try {
    const p = await createPayment(method, Math.round(amt * 100) / 100, sel.value, repos);
    const lp = ledgerRecord(method, cents, repos, live); // single ledger rule
    if (lp && !apiMode) { // remember mapping so Refund mirrors into the ledger
      const d = demoLoad();
      const hit = d.payments.find((x) => x.id === p.id);
      if (hit) { hit.betaId = lp.id; hit.live = live; demoSave(d); }
    }
    $("pay-out").textContent = `Paid $${money(p.amount)} via ${p.method} \u2192 ${p.id} (${live ? "LIVE, counts" : "TEST, $0"})\n` + JSON.stringify(p.splits, null, 2);
    refresh();
  } catch (e) { $("pay-out").textContent = "Error: " + e.message; }
}
$("pay-fiat").onclick = () => pay("fiat");
$("pay-crypto").onclick = () => pay("crypto");
$("pay-token").onchange = updateSplitPreview;
$("pay-amount").oninput = updateSplitPreview;
$("reload-projects").onclick = refresh;
$("reload-payments").onclick = refresh;
$("project-filter").oninput = renderProjects;

probeApi().then(refresh);
