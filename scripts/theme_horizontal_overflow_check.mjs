/**
 * Horizontal overflow gate — flags body-level horizontal scroll only.
 * Usage: cd .tmp-pw && PF_BASE_URL=http://127.0.0.1:3004 node ../scripts/theme_horizontal_overflow_check.mjs
 */
import { writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { launchBrowser, advanceToProfile, openPathTab, primaryNav, BASE } from "./qa_helpers.mjs";

const VIEWPORTS = [
  [390, 844], [430, 932], [768, 1024], [1280, 720], [1440, 900], [1920, 1080],
];
const issues = [];

async function check(page, theme, screen, w, h) {
  await page.setViewportSize({ width: w, height: h });
  await page.waitForTimeout(200);
  const r = await page.evaluate(() => ({
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
    bodyScrollW: document.body.scrollWidth,
  }));
  const overflow = Math.max(r.scrollW, r.bodyScrollW) - r.clientW;
  if (overflow > 2) {
    issues.push({ theme, screen, viewport: `${w}x${h}`, overflowPx: overflow });
  }
}

async function runTheme(theme) {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.addInitScript((t) => localStorage.setItem("pathfinder-theme", t), theme);

  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
  for (const [w, h] of VIEWPORTS) await check(page, theme, "onboarding", w, h);

  await page.getByRole("button", { name: /Pick career manually/i }).click().catch(() => undefined);
  await page.locator(".career-requirements").first().waitFor({ timeout: 60000 }).catch(() => undefined);
  for (const [w, h] of VIEWPORTS) await check(page, theme, "career-explorer", w, h);

  await page.goto(BASE);
  await advanceToProfile(page, "AI/ML Engineer");
  await page.getByRole("button", { name: /Judge demo/i }).click();
  await page.waitForURL(/workspace/, { timeout: 240000 });
  await page.getByTestId("judge-guide").waitFor({ timeout: 120000 });

  for (const [w, h] of VIEWPORTS) await check(page, theme, "dashboard", w, h);
  await openPathTab(page);
  for (const [w, h] of VIEWPORTS) await check(page, theme, "path", w, h);
  await primaryNav(page).getByRole("button", { name: "Skill Map" }).click();
  await page.getByTestId("skill-plot").waitFor({ timeout: 15000 }).catch(() => undefined);
  for (const [w, h] of VIEWPORTS) await check(page, theme, "skill-map", w, h);

  await browser.close();
}

await runTheme("dark");
await runTheme("light");

const out = join(dirname(fileURLToPath(import.meta.url)), "..", "artifacts", "forensic-horizontal-overflow.json");
writeFileSync(out, JSON.stringify({ pass: issues.length === 0, issues }, null, 2));
console.log(JSON.stringify({ pass: issues.length === 0, issues: issues.length }, null, 2));
process.exit(issues.length === 0 ? 0 : 1);
