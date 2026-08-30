/**
 * Dual-theme comparison capture — dark vs light, desktop + mobile.
 * Usage: cd .tmp-pw && PF_BASE_URL=http://127.0.0.1:3004 node ../scripts/theme_comparison_capture.mjs
 */
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  attachMonitors,
  advanceToProfile,
  openAssessments,
  openPathTab,
  submitAssessmentAndWaitForResult,
  shot,
  launchBrowser,
  primaryNav,
  BASE,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "theme-comparison");
mkdirSync(OUT, { recursive: true });

const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 390, height: 844 };
const log = { console: [], network: [], hydration: [], misses: [] };

async function setTheme(page, theme) {
  await page.addInitScript((t) => {
    try {
      window.localStorage.setItem("pathfinder-theme", t);
    } catch {
      /* ignore */
    }
  }, theme);
}

async function capture(page, theme, name, viewport = DESKTOP) {
  const suffix = viewport === DESKTOP ? "" : "-mobile";
  await shot(page, OUT, `${theme}-${name}${suffix}.png`, viewport);
}

async function captureFlow(theme) {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  attachMonitors(page, log);
  page.on("pageerror", (err) => log.hydration.push(`[${theme}] ${err}`));
  await setTheme(page, theme);

  // Onboarding
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
  await page.waitForTimeout(400);
  await capture(page, theme, "onboarding", DESKTOP);
  await capture(page, theme, "onboarding", MOBILE);
  await page.setViewportSize(DESKTOP);

  // Career explorer
  const pick = page.getByRole("button", { name: /Pick career manually/i });
  if (await pick.isVisible().catch(() => false)) {
    await pick.click();
    await page.locator(".career-requirements").first().waitFor({ timeout: 30000 });
    await capture(page, theme, "career-explorer", DESKTOP);
  }

  // Build to workspace via judge demo
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
  try {
    await advanceToProfile(page, "AI/ML Engineer");
    await page.getByRole("button", { name: /Judge demo/i }).click();
    await page.waitForURL(/workspace/, { timeout: 240000, waitUntil: "domcontentloaded" });
    await page.getByTestId("judge-guide").waitFor({ timeout: 120000 });
  } catch (err) {
    log.misses.push(`[${theme}] judge-demo: ${err}`);
    await browser.close();
    return;
  }

  await page.waitForTimeout(500);
  await capture(page, theme, "dashboard", DESKTOP);
  await capture(page, theme, "dashboard", MOBILE);
  await page.setViewportSize(DESKTOP);

  try {
    // Path
    await openPathTab(page);
    await page.waitForTimeout(300);
    await capture(page, theme, "path", DESKTOP);
    await capture(page, theme, "path", MOBILE);
    await page.setViewportSize(DESKTOP);
    await capture(page, theme, "path-v1", DESKTOP);

    // Skill map
    await primaryNav(page).getByRole("button", { name: "Skill Map" }).click();
    await page.getByTestId("skill-plot").waitFor({ timeout: 15000 }).catch(() => log.misses.push(`[${theme}] skill-plot`));
    await page.waitForTimeout(300);
    await capture(page, theme, "skill-map", DESKTOP);

    // Assessment → result → V2
    await openAssessments(page);
    await capture(page, theme, "assessment", DESKTOP);
    try {
      await submitAssessmentAndWaitForResult(page);
      await page.waitForTimeout(300);
      await capture(page, theme, "result", DESKTOP);

      await page.getByTestId("see-what-changed").click();
      await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
      await page.waitForTimeout(400);
      await capture(page, theme, "path-v2", DESKTOP);
      await capture(page, theme, "path-v2", MOBILE);
      await page.setViewportSize(DESKTOP);
    } catch (err) {
      log.misses.push(`[${theme}] result-v2: ${err}`);
    }
  } catch (err) {
    log.misses.push(`[${theme}] workspace: ${err}`);
  }

  await browser.close();
}

await captureFlow("dark");
await captureFlow("light");

writeFileSync(join(OUT, "capture-log.json"), JSON.stringify(log, null, 2));
const pass = log.console.length === 0 && log.hydration.length === 0;
console.log(JSON.stringify({ out: OUT, pass, ...log }, null, 2));
process.exit(pass ? 0 : 1);
