/**
 * Production screenshot capture — final proof package.
 * Usage: cd .tmp-pw && PF_BASE_URL=http://127.0.0.1:3004 node ../scripts/grok_final_capture.mjs
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
  clearSession,
  launchBrowser,
  primaryNav,
  BASE,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "ui-grok-final");
mkdirSync(OUT, { recursive: true });

const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 390, height: 844 };
const log = { console: [], network: [], hydration: [], misses: [] };

async function capture(page, name, alsoMobile = false) {
  await shot(page, OUT, `${name}.png`, DESKTOP);
  if (alsoMobile) {
    await shot(page, OUT, `${name}-mobile.png`, MOBILE);
    await page.setViewportSize(DESKTOP);
  }
}

const browser = await launchBrowser();
const page = await browser.newPage();
attachMonitors(page, log);
page.on("pageerror", (err) => log.hydration.push(String(err)));
await clearSession(page);

await page.goto(BASE, { waitUntil: "domcontentloaded" });
await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
await capture(page, "01-onboarding", true);

const resolve = page.getByRole("button", { name: /Resolve goal/i });
if (await resolve.isVisible().catch(() => false)) {
  await page.locator(".goal-intel-input").fill(
    "I want to become a machine learning engineer focused on computer vision and production systems.",
  );
  await resolve.click();
  await page.getByText(/Matching your goal|Inferred|Continue/i).first().waitFor({ timeout: 20000 }).catch(() => undefined);
  await page.waitForTimeout(800);
  await capture(page, "02-goal-resolved");
}

const pick = page.getByRole("button", { name: /Pick career manually/i });
const fromResolved = page.getByRole("button", { name: /^Continue$/ }).first();
if (await pick.isVisible().catch(() => false)) {
  await pick.click();
} else if (await fromResolved.isVisible().catch(() => false)) {
  await fromResolved.click();
}
await page.locator(".career-requirements").first().waitFor({ timeout: 30000 });
await capture(page, "03-career-explorer");

const compareBtn = page.getByRole("button", { name: /Compare two careers/i });
if (await compareBtn.isVisible().catch(() => false)) {
  await compareBtn.click().catch(() => undefined);
  const roleB = page.locator("select").nth(1);
  if (await roleB.isVisible().catch(() => false)) {
    await roleB.selectOption({ label: "Backend Developer" }).catch(() => undefined);
    await page.waitForTimeout(600);
  }
  await capture(page, "04-career-compare");
}

await page.goto(BASE, { waitUntil: "domcontentloaded" });
await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });

try {
  await advanceToProfile(page, "AI/ML Engineer");
  await capture(page, "05-profile");
  await page.getByRole("button", { name: /Judge demo/i }).click();
  await page.waitForURL(/workspace/, { timeout: 240000, waitUntil: "domcontentloaded" });
  await page.getByTestId("judge-guide").waitFor({ timeout: 120000 });
} catch (err) {
  log.misses.push(`judge-demo: ${err}`);
}

await capture(page, "06-dashboard", true);
await capture(page, "19-judge-mode");

try {
  await primaryNav(page).getByRole("button", { name: "Overview" }).click().catch(() => undefined);
  const blockersLink = page.getByRole("button", { name: /Blockers|What is blocking/i });
  if (await blockersLink.first().isVisible().catch(() => false)) {
    await blockersLink.first().click();
    await page.waitForTimeout(300);
    await capture(page, "07-blockers");
    await primaryNav(page).getByRole("button", { name: "Overview" }).click();
  }

  await openPathTab(page);
  await capture(page, "08-path", true);
  await capture(page, "13-path-v1");

  const whyBtn = page.locator(".path-row").first();
  await whyBtn.click();
  await page.getByRole("heading", { name: /Why this is here/i }).waitFor({ timeout: 15000 });
  await capture(page, "09-why-resource");
  const progress = page.getByTestId("progress-actions").first();
  if (await progress.isVisible().catch(() => false)) {
    await progress.scrollIntoViewIfNeeded();
    await capture(page, "10-progress", true);
  }
  await page.getByRole("button", { name: "Close" }).click().catch(() => undefined);

  await primaryNav(page).getByRole("button", { name: "Skill Map" }).click();
  await page.getByTestId("skill-plot").waitFor({ timeout: 15000 }).catch(() => log.misses.push("skill-plot"));
  await capture(page, "17-skill-map");

  await primaryNav(page).getByRole("button", { name: "History" }).click();
  await page.getByTestId("path-timeline").waitFor({ timeout: 30000 });
  await capture(page, "16-history");

  try {
    await openAssessments(page);
    await capture(page, "11-assessment");

    try {
      await submitAssessmentAndWaitForResult(page);
      await capture(page, "12-result", true);
      await capture(page, "assessment-result");

      await page.getByTestId("see-what-changed").click();
      await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
      await page.waitForTimeout(200);
      await capture(page, "14-path-v2", true);
      await page.getByTestId("path-changed-hero").getByRole("button", { name: "Why this changed", exact: true }).click();
      await page.getByTestId("why-changed").waitFor({ timeout: 30000 });
      await capture(page, "15-why-changed");

      await primaryNav(page).getByRole("button", { name: "History" }).click();
      await page.getByTestId("path-timeline").waitFor({ timeout: 30000 });
      await capture(page, "history-after-adaptation");
    } catch (err) {
      log.misses.push(`result-adaptation: ${err}`);
    }
  } catch (err) {
    log.misses.push(`assessment: ${err}`);
  }

  await primaryNav(page).getByRole("button", { name: "Overview" }).click().catch(() => undefined);
  const ask = page.getByTestId("ask-pathfinder");
  if (await ask.isVisible().catch(() => false)) {
    await ask.scrollIntoViewIfNeeded();
    await capture(page, "18-ai");
  }
} catch (err) {
  log.misses.push(`workspace: ${err}`);
}

await browser.close();
writeFileSync(join(OUT, "capture-log.json"), JSON.stringify(log, null, 2));
const pass = log.console.length === 0 && log.network.length === 0 && log.hydration.length === 0 && log.misses.length === 0;
console.log(JSON.stringify({ out: OUT, pass, ...log }, null, 2));
process.exit(pass ? 0 : 1);
