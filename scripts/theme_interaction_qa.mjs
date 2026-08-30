/**
 * Theme switch interaction QA — toggle, persistence, system preference, no-flash.
 * Usage: cd .tmp-pw && PF_BASE_URL=http://127.0.0.1:3004 node ../scripts/theme_interaction_qa.mjs
 */
import { launchBrowser, BASE } from "./qa_helpers.mjs";

const results = [];
const check = (name, ok, detail = "") => {
  results.push({ name, ok, detail });
  console.log(ok ? "PASS" : "FAIL", name, detail);
};

const browser = await launchBrowser();

// 1. Default (no stored pref, dark system) → dark
let ctx = await browser.newContext({ colorScheme: "dark" });
let page = await ctx.newPage();
await page.goto(BASE, { waitUntil: "domcontentloaded" });
await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
let theme = await page.evaluate(() => document.documentElement.dataset.theme);
check("default dark system → dark", theme === "dark", `got ${theme}`);
await ctx.close();

// 2. Light system preference → light (no stored pref)
ctx = await browser.newContext({ colorScheme: "light" });
page = await ctx.newPage();
await page.goto(BASE, { waitUntil: "domcontentloaded" });
await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
theme = await page.evaluate(() => document.documentElement.dataset.theme);
check("light system → light (no stored)", theme === "light", `got ${theme}`);

// 3. Toggle switches theme + persists to localStorage
const switchBtn = page.getByTestId("theme-switch");
await switchBtn.waitFor({ timeout: 10000 });
const before = await page.evaluate(() => document.documentElement.dataset.theme);
await switchBtn.click();
await page.waitForTimeout(150);
const after = await page.evaluate(() => document.documentElement.dataset.theme);
const stored = await page.evaluate(() => window.localStorage.getItem("pathfinder-theme"));
check("toggle flips theme", before !== after, `${before} → ${after}`);
check("toggle persists to localStorage", stored === after, `stored=${stored}`);

// 4. aria-label reflects next theme
const aria = await switchBtn.getAttribute("aria-label");
check("aria-label present + descriptive", /Switch to (dark|light) theme/i.test(aria ?? ""), aria);

// 5. Persistence across reload (stored pref wins over system)
await page.reload({ waitUntil: "domcontentloaded" });
await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
const reloaded = await page.evaluate(() => document.documentElement.dataset.theme);
check("stored pref survives reload", reloaded === after, `got ${reloaded}`);
await ctx.close();

// 6. No-flash: inline <head> script applies theme before hydration/paint.
ctx = await browser.newContext({ colorScheme: "dark" });
page = await ctx.newPage();
await page.addInitScript(() => {
  window.localStorage.setItem("pathfinder-theme", "light");
});
// Read theme at the earliest navigation commit (before app hydration).
const nav = await page.goto(BASE, { waitUntil: "commit" });
const html = await page.evaluate(() => document.documentElement.outerHTML).catch(() => "");
const headHasInline = html.includes("pathfinder-theme") && html.indexOf("pathfinder-theme") < html.indexOf("<body");
await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
const themeAtDom = await page.evaluate(() => document.documentElement.dataset.theme);
check("no-flash: inline script in <head>", headHasInline, headHasInline ? "found before <body>" : "missing");
check("no-flash: correct theme at DOMContentLoaded", themeAtDom === "light", `got ${themeAtDom}`);
await ctx.close();

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n${failed.length === 0 ? "ALL PASS" : "FAILURES"}: ${results.length - failed.length}/${results.length}`);
process.exit(failed.length === 0 ? 0 : 1);
