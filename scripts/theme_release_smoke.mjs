/**
 * Release smoke — dual theme, key screens, 1440x900 + 390x844.
 * Usage: cd .tmp-pw && PF_BASE_URL=http://127.0.0.1:3004 node ../scripts/theme_release_smoke.mjs
 */
import { writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  attachMonitors,
  advanceToProfile,
  openAssessments,
  openPathTab,
  submitAssessmentAndWaitForResult,
  launchBrowser,
  primaryNav,
  BASE,
} from "./qa_helpers.mjs";

const VIEWPORTS = [
  { name: "1440x900", width: 1440, height: 900 },
  { name: "390x844", width: 390, height: 844 },
];
const report = {
  console: [],
  network: [],
  hydration: [],
  themeFlash: [],
  overflow: [],
  screens: [],
  pass: false,
};

async function setTheme(page, theme) {
  await page.addInitScript((t) => localStorage.setItem("pathfinder-theme", t), theme);
}

async function hOverflow(page) {
  return page.evaluate(() => {
    const c = document.documentElement.clientWidth;
    return Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - c;
  });
}

async function shot(page, theme, screen, vp, dir) {
  await page.setViewportSize({ width: vp.width, height: vp.height });
  await page.waitForTimeout(200);
  const overflow = await hOverflow(page);
  if (overflow > 2) report.overflow.push({ theme, screen, viewport: vp.name, overflowPx: overflow });
  await page.screenshot({ path: join(dir, `${theme}-${screen}-${vp.name}.png`) });
}

async function runTheme(theme) {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  const log = { console: [], network: [] };
  attachMonitors(page, log);
  page.on("pageerror", (e) => report.hydration.push({ theme, error: String(e) }));
  await setTheme(page, theme);
  const dir = join(dirname(fileURLToPath(import.meta.url)), "..", "artifacts", "release-smoke");
  const { mkdirSync } = await import("fs");
  mkdirSync(dir, { recursive: true });

  await page.addInitScript((t) => localStorage.setItem("pathfinder-theme", t), theme);
  const html = await page.goto(BASE, { waitUntil: "commit" }).then(() =>
    page.evaluate(() => document.documentElement.outerHTML.slice(0, 6000)),
  );
  const flashOk = html.includes("pathfinder-theme");
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
  const atDom = await page.evaluate(() => document.documentElement.dataset.theme);
  report.themeFlash.push({ theme, flashOk, atDom, ok: flashOk && atDom === theme });

  for (const vp of VIEWPORTS) await shot(page, theme, "onboarding", vp, dir);

  await advanceToProfile(page, "AI/ML Engineer");
  await page.getByRole("button", { name: /Judge demo/i }).click();
  await page.waitForURL(/workspace/, { timeout: 240000 });
  await page.getByTestId("judge-guide").waitFor({ timeout: 120000 });

  for (const vp of VIEWPORTS) await shot(page, theme, "dashboard", vp, dir);

  await openPathTab(page);
  for (const vp of VIEWPORTS) await shot(page, theme, "path-v1", vp, dir);

  await openAssessments(page);
  for (const vp of VIEWPORTS) await shot(page, theme, "assessment", vp, dir);

  await submitAssessmentAndWaitForResult(page);
  for (const vp of VIEWPORTS) await shot(page, theme, "result", vp, dir);

  const changed = page.getByTestId("see-what-changed");
  if (await changed.isVisible().catch(() => false)) {
    await changed.click();
    await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
    for (const vp of VIEWPORTS) await shot(page, theme, "path-v2", vp, dir);
  }

  await primaryNav(page).getByRole("button", { name: "Overview" }).click().catch(() => undefined);
  const ask = page.getByTestId("ask-pathfinder");
  if (await ask.isVisible().catch(() => false)) {
    await ask.scrollIntoViewIfNeeded();
    for (const vp of VIEWPORTS) await shot(page, theme, "ai", vp, dir);
  }

  report.console.push(...log.console.map((m) => ({ theme, m })));
  report.network.push(...log.network.map((m) => ({ theme, m })));
  report.screens.push({ theme, captured: ["onboarding", "dashboard", "path-v1", "assessment", "result", "path-v2", "ai"] });
  await browser.close();
}

await runTheme("dark");
await runTheme("light");

report.pass =
  report.console.length === 0 &&
  report.network.length === 0 &&
  report.hydration.length === 0 &&
  report.overflow.length === 0 &&
  report.themeFlash.every((t) => t.ok);

const out = join(dirname(fileURLToPath(import.meta.url)), "..", "artifacts", "release-smoke", "report.json");
writeFileSync(out, JSON.stringify(report, null, 2));
console.log(JSON.stringify({ pass: report.pass, ...report, screens: report.screens.length }, null, 2));
process.exit(report.pass ? 0 : 1);
