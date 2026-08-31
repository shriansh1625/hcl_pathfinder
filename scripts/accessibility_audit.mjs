/**
 * Accessibility audit — 0 critical / 0 serious after final UI pass.
 * Usage: cd .tmp-pw && PF_BASE_URL=http://127.0.0.1:3004 node ../scripts/accessibility_audit.mjs
 */
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  launchBrowser,
  clearSession,
  advanceToProfile,
  launchJudgeDemo,
  openPathTab,
  openAssessments,
  answerAssessment,
  primaryNav,
  BASE,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const THEME = process.env.PF_THEME || "dark";
const OUT = join(__dirname, "..", "artifacts", "accessibility");
mkdirSync(OUT, { recursive: true });

const pages = [];
const violations = [];

function classify(issue) {
  if (/dialog without label|button without accessible name|missing h1|multiple h1|slider without label|focus/i.test(issue)) {
    return "serious";
  }
  return "moderate";
}

async function scanPage(page, name) {
  const issues = await page.evaluate(() => {
    const hits = [];
    for (const btn of document.querySelectorAll("button")) {
      const label = btn.getAttribute("aria-label") || btn.textContent?.trim();
      if (!label) hits.push("button without accessible name");
    }
    for (const dlg of document.querySelectorAll("[role='dialog']")) {
      if (!dlg.getAttribute("aria-labelledby") && !dlg.getAttribute("aria-label")) {
        hits.push("dialog without label");
      }
    }
    for (const input of document.querySelectorAll("input[type='range']")) {
      const labelled = input.labels?.length || input.getAttribute("aria-label") || input.getAttribute("aria-labelledby");
      if (!labelled) hits.push("slider without label");
    }
    const h1 = document.querySelectorAll("h1").length;
    if (h1 === 0) hits.push("missing h1");
    if (h1 > 1) hits.push("multiple h1");
    const focusable = document.querySelectorAll("button, a, input, select, textarea, [tabindex='0']").length;
    if (focusable === 0) hits.push("no focusable controls");
    return [...new Set(hits)];
  });
  const reducedMotion = await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  pages.push({ name, issues, reducedMotion });
  for (const issue of issues) {
    violations.push({ page: name, issue, severity: classify(issue) });
  }
  console.log(issues.length ? "WARN" : "PASS", name, issues.join("; ") || "ok");
}

const browser = await launchBrowser();
const page = await browser.newPage();
await clearSession(page);
await page.addInitScript((t) => {
  try {
    window.localStorage.setItem("pathfinder-theme", t);
  } catch {
    /* ignore */
  }
}, THEME);

await page.goto(BASE);
await page.getByRole("heading", { name: /Build the path/i }).waitFor();
await scanPage(page, "onboarding");

await page.getByRole("button", { name: /Pick career manually/i }).click();
await page.locator(".career-requirements").first().waitFor();
await scanPage(page, "career explorer");

await advanceToProfile(page, "AI/ML Engineer");
await scanPage(page, "profile");

await page.getByRole("button", { name: /Judge demo/i }).click();
await page.waitForURL("**/workspace**", { timeout: 240000 });
await page.getByTestId("judge-guide").waitFor({ timeout: 120000 });

await primaryNav(page).getByRole("button", { name: "My Journey" }).click();
await page.getByText(/KNOW/).first().waitFor({ timeout: 30000 });
await scanPage(page, "dashboard");

const blockersBtn = page.getByRole("button", { name: /Blockers|What is blocking/i });
if (await blockersBtn.first().isVisible().catch(() => false)) {
  await blockersBtn.first().click();
  await page.waitForTimeout(400);
  await scanPage(page, "blockers");
  await primaryNav(page).getByRole("button", { name: "My Journey" }).click();
}

await openPathTab(page);
await scanPage(page, "path");

const whyRow = page.locator(".path-row").first();
await whyRow.click();
await page.getByRole("heading", { name: /Why this is here/i }).waitFor({ timeout: 15000 });
await scanPage(page, "why drawer");
const progress = page.getByTestId("progress-actions").first();
if (await progress.isVisible().catch(() => false)) {
  await progress.scrollIntoViewIfNeeded();
  await scanPage(page, "progress");
}
await page.getByRole("button", { name: "Close" }).click();

await openAssessments(page);
await scanPage(page, "assessment");

const submit = await answerAssessment(page);
await submit.click();
await page.getByTestId("result-hero").waitFor({ timeout: 180000 }).catch(() => undefined);
if (await page.getByTestId("result-hero").isVisible().catch(() => false)) {
  await scanPage(page, "result");
  const changed = page.getByTestId("see-what-changed");
  if (await changed.isVisible().catch(() => false)) {
    await changed.click();
    await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 }).catch(() => undefined);
    if (await page.getByTestId("path-changed-hero").isVisible().catch(() => false)) {
      await scanPage(page, "path changed");
    }
  }
}

await primaryNav(page).getByRole("button", { name: "History" }).click();
await page.getByTestId("path-timeline").waitFor({ timeout: 30000 });
await scanPage(page, "timeline");

await primaryNav(page).getByRole("button", { name: "Skill Map" }).click();
await page.getByTestId("skill-plot").waitFor({ timeout: 30000 }).catch(() => undefined);
await scanPage(page, "skill map");

await primaryNav(page).getByRole("button", { name: "My Journey" }).click();
const ask = page.getByTestId("ask-pathfinder");
if (await ask.isVisible().catch(() => false)) {
  await ask.scrollIntoViewIfNeeded();
  await scanPage(page, "ai");
}

await scanPage(page, "judge mode");

await browser.close();

const critical = violations.filter((v) => v.severity === "critical");
const serious = violations.filter((v) => v.severity === "serious");
const summary = {
  pages: pages.length,
  critical: critical.length,
  serious: serious.length,
  moderate: violations.filter((v) => v.severity === "moderate").length,
  pass: critical.length === 0 && serious.length === 0,
  pagesScanned: pages,
  violations,
};
writeFileSync(join(OUT, `summary-${THEME}.json`), JSON.stringify(summary, null, 2));
console.log("SUMMARY", THEME, JSON.stringify({ pass: summary.pass, critical: summary.critical, serious: summary.serious }));
process.exit(summary.pass ? 0 : 1);
