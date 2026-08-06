#!/usr/bin/env node
// Fast verification of the playground UI without a browser.
// Loads index.html in jsdom, runs the page JS against the live server
// (Node's global fetch), then checks that key UI elements rendered.
//
// Usage: node verify.mjs [base_url]   (default http://127.0.0.1:8310)
// Exit 0 = pass, 1 = fail. Prints a short PASS/FAIL report.
import { JSDOM, VirtualConsole } from "jsdom";

const BASE = process.argv[2] || "http://127.0.0.1:8310";
const started = Date.now();

const errors = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on("jsdomError", e => errors.push("jsdom: " + e.message));
virtualConsole.on("error", (...a) => errors.push("console.error: " + a.join(" ")));

const html = await (await fetch(BASE + "/")).text();

const dom = new JSDOM(html, {
  url: BASE + "/",
  runScripts: "dangerously",
  resources: "usable",
  pretendToBeVisual: true,
  virtualConsole,
  beforeParse(window) {
    window.fetch = (u, o) => fetch(new URL(u, BASE), o); // proxy to live server
    window.scrollTo = () => {};
    window.matchMedia = window.matchMedia || (() => ({ matches: false, addListener() {}, removeListener() {} }));
  },
});

const { window } = dom;

// wait for the page's async init (status, tables, stats, calls, ranking, default query)
await new Promise(r => setTimeout(r, 1000));

const doc = window.document;
const text = doc.body ? doc.body.textContent : "";
const checks = [
  ["page title", doc.querySelector("h1")?.textContent === "Hyperliquid Playground"],
  ["coin filter card", !!doc.querySelector("#rankCard")],
  ["flows section", !!doc.querySelector("#callsCard")],
  ["database card", !!doc.querySelector("#dbTable")],
  ["sql playground", !!doc.querySelector("#sqlBox")],
  ["ranking table has rows", (doc.querySelectorAll("#rankTable tr.sel").length) > 0],
  ["db summary rendered", /rows\/24h/.test(doc.querySelector("#dbSummary")?.textContent || "")],
  ["no error banner", !text.includes("class=\"error\"")],
];
const fails = checks.filter(([, ok]) => !ok);

const ms = Date.now() - started;
if (fails.length) {
  console.log(`FAIL (${ms}ms): ${fails.map(([n]) => n).join(", ")}`);
  for (const e of errors.slice(0, 5)) console.log("  " + e);
  process.exit(1);
}
console.log(`PASS (${ms}ms): ${checks.length} checks, ${errors.length} console errors`);
window.close();
