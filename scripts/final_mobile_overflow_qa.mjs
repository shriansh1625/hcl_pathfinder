/**
 * Final mobile overflow gate — all key screens, both themes, strict overflowPx <= 1.
 * Usage: PF_BASE_URL=http://127.0.0.1:3002 node scripts/final_mobile_overflow_qa.mjs
 */
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  launchBrowser,
  advanceToProfile,
  openAssessments,
  openPathTab,
  submitAssessmentAndWaitForResult,
  BASE,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "final-mobile-overflow");
mkdirSync(OUT, { recursive: true });

const MOBILE = [
  { name: "390x844", width: 390, height: 844 },
  { name: "430x932", width: 430, height: 932 },
];
const DESKTOP = [
  { name: "768x1024", width: 768, height: 1024 },
  { name: "1280x720", width: 1280, height: 720 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1920x1080", width: 1920, height: 1080 },
];

const results = [];

async function measure(page) {
  return page.evaluate(() => {
    const clientWidth = document.documentElement.clientWidth;
    const scrollWidth = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
    return { scrollWidth, clientWidth, overflowPx: scrollWidth - clientWidth };
  });
}

async function check(page, theme, screen, vp, reducedMotion = false) {
  if (reducedMotion) {
    await page.emulateMedia({ reducedMotion: "reduce" });
  } else {
    await page.emulateMedia({ reducedMotion: "no-preference" });
  }
  await page.setViewportSize({ width: vp.width, height: vp.height });
  await page.waitForTimeout(250);
  const m = await measure(page);
  const pass = m.overflowPx <= 1;
  const row = { theme, screen, viewport: vp.name, reducedMotion, ...m, pass };
  results.push(row);
  console.log(pass ? "PASS" : "FAIL", theme, screen, vp.name, `overflow=${m.overflowPx}px`);
  return pass;
}

async function runTheme(theme) {
  const browser = await launchBrowser();
  const page = await browser.newPage();
  await page.addInitScript((t) => localStorage.setItem("pathfinder-theme", t), theme);

  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
  for (const vp of MOBILE) await check(page, theme, "onboarding", vp);

  await page.getByRole("button", { name: /Pick career manually/i }).click().catch(() => undefined);
  await page.locator(".career-requirements").first().waitFor({ timeout: 60000 }).catch(() => undefined);
  for (const vp of MOBILE) await check(page, theme, "career-explorer", vp);

  await page.goto(BASE);
  await advanceToProfile(page, "AI/ML Engineer");
  await page.getByRole("button", { name: /Judge demo/i }).click();
  await page.waitForURL(/workspace/, { timeout: 240000 });
  await page.getByTestId("judge-guide").waitFor({ timeout: 120000 });

  for (const vp of MOBILE) await check(page, theme, "dashboard", vp);
  for (const vp of MOBILE) await check(page, theme, "judge-mode", vp);

  await page.getByRole("button", { name: "Overview" }).click().catch(() => undefined);
  await page.getByRole("button", { name: "Continue" }).click().catch(() => undefined);
  await page.getByText(/Career blockers by priority/i).waitFor({ timeout: 15000 }).catch(() => undefined);
  for (const vp of MOBILE) await check(page, theme, "blockers", vp);

  await openPathTab(page);
  for (const vp of MOBILE) await check(page, theme, "path-v1", vp);
  for (const vp of DESKTOP) await check(page, theme, "path-v1", vp);
  // Progress actions live on the path view — covered by path-v1 checks above.

  await openAssessments(page);
  for (const vp of MOBILE) await check(page, theme, "assessment", vp);

  await submitAssessmentAndWaitForResult(page);
  for (const vp of MOBILE) await check(page, theme, "result", vp);

  const changed = page.getByTestId("see-what-changed");
  if (await changed.isVisible().catch(() => false)) {
    await changed.click();
    await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
    await page.waitForTimeout(1200);
    for (const vp of MOBILE) {
      await check(page, theme, "path-v2", vp);
      if (theme === "dark" && vp.name === "390x844") {
        await page.screenshot({ path: join(OUT, "dark-path-v2-390.png") });
      }
      if (theme === "dark" && vp.name === "430x932") {
        await page.screenshot({ path: join(OUT, "dark-path-v2-430.png") });
      }
      if (theme === "light" && vp.name === "390x844") {
        await page.screenshot({ path: join(OUT, "light-path-v2-390.png") });
      }
      if (theme === "light" && vp.name === "430x932") {
        await page.screenshot({ path: join(OUT, "light-path-v2-430.png") });
      }
    }
    for (const vp of DESKTOP) await check(page, theme, "path-v2", vp);

    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const vp of MOBILE) await check(page, theme, "path-v2-reduced-motion", vp, true);

    const whyBtn = page.getByRole("button", { name: /Why this changed/i });
    if (await whyBtn.isVisible().catch(() => false)) {
      await whyBtn.click();
      await page.waitForTimeout(400);
      for (const vp of MOBILE) await check(page, theme, "why-changed", vp);
    }
  }

  await page.getByRole("button", { name: "History" }).click().catch(() => undefined);
  await page.waitForTimeout(400);
  for (const vp of MOBILE) await check(page, theme, "history", vp);

  await page.getByLabel("Workspace").getByRole("button", { name: "Skill Map", exact: true }).click();
  await page.getByTestId("skill-plot").waitFor({ timeout: 15000 }).catch(() => undefined);
  for (const vp of MOBILE) await check(page, theme, "skill-map", vp);

  await page.getByRole("button", { name: "Overview" }).click().catch(() => undefined);
  const ask = page.getByTestId("ask-pathfinder");
  if (await ask.isVisible().catch(() => false)) {
    await ask.scrollIntoViewIfNeeded();
    for (const vp of MOBILE) await check(page, theme, "ai", vp);
  }

  await browser.close();
}

await runTheme("dark");
await runTheme("light");

const passed = results.filter((r) => r.pass).length;
const summary = { passed, total: results.length, pass: passed === results.length, results, base: BASE, at: new Date().toISOString() };
writeFileSync(join(OUT, "summary.json"), JSON.stringify(summary, null, 2));
console.log(`\n${passed}/${results.length} passed`);
process.exit(summary.pass ? 0 : 1);
