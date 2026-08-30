/**
 * Forensic dual-theme browser gate — fresh production QA.
 * Usage: cd .tmp-pw && PF_BASE_URL=http://127.0.0.1:3004 node ../scripts/theme_forensic_browser_qa.mjs
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
  launchBrowser,
  primaryNav,
  BASE,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "forensic-theme-qa");
mkdirSync(OUT, { recursive: true });

const VIEWPORTS = [
  { name: "390x844", width: 390, height: 844 },
  { name: "430x932", width: 430, height: 932 },
  { name: "768x1024", width: 768, height: 1024 },
  { name: "1280x720", width: 1280, height: 720 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1920x1080", width: 1920, height: 1080 },
];

const SCREENS = [
  "onboarding",
  "career-explorer",
  "dashboard",
  "path",
  "progress",
  "assessment",
  "result",
  "path-v2",
  "timeline",
  "skill-map",
  "ai",
  "judge-mode",
];

const report = {
  console: [],
  network: [],
  hydration: [],
  overflow: [],
  occlusion: [],
  themeFlash: [],
  themePersistence: [],
  screens: [],
  pass: false,
};

function record(type, entry) {
  report[type].push(entry);
}

async function setTheme(page, theme) {
  await page.addInitScript((t) => {
    try {
      window.localStorage.setItem("pathfinder-theme", t);
    } catch {
      /* ignore */
    }
  }, theme);
}

async function checkOverflow(page, theme, screen, viewport) {
  const issues = await page.evaluate(() => {
    const hits = [];
    const vw = document.documentElement.clientWidth;
    const vh = document.documentElement.clientHeight;
    const els = document.querySelectorAll("body *");
    for (const el of els) {
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") continue;
      const rect = el.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) continue;
      if (rect.right > vw + 2 || rect.left < -2) {
        const tag = `${el.tagName}.${(el.className || "").toString().slice(0, 40)}`;
        hits.push(`h-overflow:${tag}:${Math.round(rect.right - vw)}px`);
      }
      if (rect.bottom > vh + 2) {
        const tag = `${el.tagName}.${(el.className || "").toString().slice(0, 40)}`;
        hits.push(`v-overflow:${tag}:${Math.round(rect.bottom - vh)}px`);
      }
    }
    return [...new Set(hits)].slice(0, 8);
  });
  for (const issue of issues) {
    record("overflow", { theme, screen, viewport, issue });
  }
  return issues.length === 0;
}

async function captureAtViewports(page, theme, screen, shotDir) {
  const results = [];
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.waitForTimeout(250);
    const ok = await checkOverflow(page, theme, screen, vp.name);
    await page.screenshot({
      path: join(shotDir, `${theme}-${screen}-${vp.name}.png`),
      fullPage: false,
    });
    results.push({ viewport: vp.name, overflowOk: ok });
  }
  report.screens.push({ theme, screen, viewports: results });
}

async function verifyThemePersistence(page, theme) {
  const before = await page.evaluate(() => document.documentElement.dataset.theme);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForTimeout(200);
  const after = await page.evaluate(() => document.documentElement.dataset.theme);
  const stored = await page.evaluate(() => window.localStorage.getItem("pathfinder-theme"));
  const ok = before === theme && after === theme && stored === theme;
  record("themePersistence", { theme, before, after, stored, ok });
  return ok;
}

async function verifyNoFlash(page, theme) {
  await page.addInitScript((t) => {
    window.localStorage.setItem("pathfinder-theme", t);
  }, theme);
  const html = await page.goto(BASE, { waitUntil: "commit" }).then(() =>
    page.evaluate(() => document.documentElement.outerHTML.slice(0, 8000)),
  );
  const hasScript = html.includes("pathfinder-theme");
  await page.waitForTimeout(300);
  const atDom = await page.evaluate(() => document.documentElement.dataset.theme);
  const ok = hasScript && atDom === theme;
  record("themeFlash", { theme, hasScript, atDom, ok });
  return ok;
}

async function runTheme(theme) {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  const log = { console: [], network: [] };
  attachMonitors(page, log);
  page.on("pageerror", (err) => record("hydration", { theme, error: String(err) }));

  await setTheme(page, theme);
  const shotDir = join(OUT, "screenshots");
  mkdirSync(shotDir, { recursive: true });

  // Theme flash + persistence checks
  await verifyNoFlash(page, theme);

  // Onboarding
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
  await verifyThemePersistence(page, theme);
  const activeTheme = await page.evaluate(() => document.documentElement.dataset.theme);
  if (activeTheme !== theme) {
    record("themeFlash", { theme, screen: "onboarding", activeTheme, ok: false });
  }
  await captureAtViewports(page, theme, "onboarding", shotDir);

  // Career explorer
  const pick = page.getByRole("button", { name: /Pick career manually/i });
  if (await pick.isVisible().catch(() => false)) {
    await pick.click();
    try {
      await page.locator(".career-requirements").first().waitFor({ timeout: 60000 });
      await captureAtViewports(page, theme, "career-explorer", shotDir);
    } catch (err) {
      record("hydration", { theme, screen: "career-explorer", error: String(err) });
    }
  }

  // Workspace via judge demo
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
  try {
    await advanceToProfile(page, "AI/ML Engineer");
    await page.getByRole("button", { name: /Judge demo/i }).click();
    await page.waitForURL(/workspace/, { timeout: 240000, waitUntil: "domcontentloaded" });
    await page.getByTestId("judge-guide").waitFor({ timeout: 120000 });
  } catch (err) {
    record("hydration", { theme, screen: "judge-demo", error: String(err) });
    report.console.push(...log.console.map((m) => ({ theme, msg: m })));
    report.network.push(...log.network.map((m) => ({ theme, msg: m })));
    await browser.close();
    return;
  }

  await page.waitForTimeout(400);
  await captureAtViewports(page, theme, "dashboard", shotDir);
  await captureAtViewports(page, theme, "judge-mode", shotDir);

  try {
    await openPathTab(page);
    await captureAtViewports(page, theme, "path", shotDir);

    const whyRow = page.locator(".path-row").first();
    await whyRow.click();
    await page.getByRole("heading", { name: /Why this is here/i }).waitFor({ timeout: 15000 });
    const progress = page.getByTestId("progress-actions").first();
    if (await progress.isVisible().catch(() => false)) {
      await progress.scrollIntoViewIfNeeded();
      await captureAtViewports(page, theme, "progress", shotDir);
    }
    await page.getByRole("button", { name: "Close" }).click().catch(() => undefined);

    await primaryNav(page).getByRole("button", { name: "History" }).click();
    await page.getByTestId("path-timeline").waitFor({ timeout: 30000 });
    await captureAtViewports(page, theme, "timeline", shotDir);

    await primaryNav(page).getByRole("button", { name: "Skill Map" }).click();
    await page.getByTestId("skill-plot").waitFor({ timeout: 15000 }).catch(() => undefined);
    await captureAtViewports(page, theme, "skill-map", shotDir);

    await openAssessments(page);
    await captureAtViewports(page, theme, "assessment", shotDir);

    try {
      await submitAssessmentAndWaitForResult(page);
      await captureAtViewports(page, theme, "result", shotDir);

      const changed = page.getByTestId("see-what-changed");
      if (await changed.isVisible().catch(() => false)) {
        await changed.click();
        await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
        await captureAtViewports(page, theme, "path-v2", shotDir);
      }
    } catch (err) {
      record("hydration", { theme, screen: "result-v2", error: String(err) });
    }

    await primaryNav(page).getByRole("button", { name: "Overview" }).click().catch(() => undefined);
    const ask = page.getByTestId("ask-pathfinder");
    if (await ask.isVisible().catch(() => false)) {
      await ask.scrollIntoViewIfNeeded();
      await captureAtViewports(page, theme, "ai", shotDir);
    }
  } catch (err) {
    record("hydration", { theme, screen: "workspace", error: String(err) });
  }

  report.console.push(...log.console.map((m) => ({ theme, msg: m })));
  report.network.push(...log.network.map((m) => ({ theme, msg: m })));
  await browser.close();
}

await runTheme("dark");
await runTheme("light");

report.pass =
  report.console.length === 0 &&
  report.network.length === 0 &&
  report.hydration.length === 0 &&
  report.overflow.length === 0 &&
  report.occlusion.length === 0 &&
  report.themeFlash.every((t) => t.ok) &&
  report.themePersistence.every((t) => t.ok);

writeFileSync(join(OUT, "report.json"), JSON.stringify(report, null, 2));
console.log(
  JSON.stringify(
    {
      pass: report.pass,
      console: report.console.length,
      network: report.network.length,
      hydration: report.hydration.length,
      overflow: report.overflow.length,
      themeFlash: report.themeFlash.filter((t) => !t.ok).length,
      themePersistence: report.themePersistence.filter((t) => !t.ok).length,
      screensCaptured: report.screens.length,
    },
    null,
    2,
  ),
);
process.exit(report.pass ? 0 : 1);
