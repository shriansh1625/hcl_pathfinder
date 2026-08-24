/**
 * PathFinder submission screenshot package.
 * Usage: PF_BASE_URL=http://127.0.0.1:3002 node scripts/capture_submission_screenshots.mjs
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUT = join(ROOT, "artifacts", "submission-screenshots");
mkdirSync(OUT, { recursive: true });
const BASE = process.env.PF_BASE_URL || "http://127.0.0.1:3002";

async function clearSession(page) {
  await page.addInitScript(() => {
    sessionStorage.clear();
    localStorage.clear();
  });
}

async function shot(page, name, viewport = { width: 1440, height: 900 }) {
  await page.setViewportSize(viewport);
  await page.screenshot({ path: join(OUT, name), fullPage: true });
}

async function advanceOnboarding(page, roleName = "Backend Developer") {
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
  await shot(page, "01-onboarding.png");
  await shot(page, "01-onboarding-mobile.png", { width: 390, height: 844 });

  await page.locator("textarea").fill("I want to become a backend engineer focused on APIs and distributed systems.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await page.getByText(/Backend Developer|backend-developer/i).first().waitFor({ timeout: 45000 });
  await shot(page, "02-goal-resolved.png");

  const resolvedContinue = page.locator(".goal-resolved-card").getByRole("button", { name: "Continue" });
  if (await resolvedContinue.isVisible().catch(() => false)) {
    await resolvedContinue.click();
  } else {
    await page.getByRole("button", { name: /Pick career manually/i }).click();
  }
  await page.locator(".career-requirements").first().waitFor({ timeout: 30000 });
  await shot(page, "03-career-explorer.png");
  await page.getByRole("button", { name: roleName }).click();

  for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Review profile" }).click();
  await shot(page, "04-profile.png");
}

async function runAssessmentFlow(page) {
  await page.getByRole("button", { name: "Assessments" }).click();
  await page.getByRole("button", { name: /Prove this skill/i }).click();
  await page.waitForSelector(".assess-index, [data-testid='assessment-question']", { timeout: 60000 });
  await shot(page, "10-assessment.png");

  for (let guard = 0; guard < 12; guard++) {
    await page.locator(".assess-answer").first().click();
    const submit = page.getByRole("button", { name: "Submit" });
    if (await submit.isVisible().catch(() => false)) {
      await submit.click();
      break;
    }
    await page.getByRole("button", { name: "Next" }).click();
  }
  await page.getByTestId("result-hero").waitFor({ timeout: 120000 });
  await shot(page, "11-result.png");
  await shot(page, "11-result-mobile.png", { width: 390, height: 844 });

  await page.getByTestId("see-what-changed").click();
  await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
  await page.waitForTimeout(1100);
  await shot(page, "12-path-v1.png");
  await page.waitForTimeout(400);
  await shot(page, "13-path-v2.png");
  await shot(page, "13-path-v2-mobile.png", { width: 390, height: 844 });

  await page.getByRole("button", { name: /Why this changed/i }).click();
  await page.getByTestId("why-changed").waitFor({ timeout: 30000 });
  await shot(page, "14-why-changed.png");

  await page.getByRole("button", { name: "History" }).click();
  await page.getByTestId("path-timeline").waitFor({ timeout: 30000 });
  await shot(page, "15-history.png");
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
await clearSession(page);

await advanceOnboarding(page, "Backend Developer");
await page.getByRole("button", { name: /Build my path/i }).click();
await page.waitForURL("**/workspace**", { timeout: 180000 });
await page.locator("h1").first().waitFor({ timeout: 60000 });
await shot(page, "05-dashboard.png");
await shot(page, "05-dashboard-mobile.png", { width: 390, height: 844 });

await page.getByRole("button", { name: "Continue" }).click();
await page.waitForTimeout(400);
await shot(page, "06-blockers.png");

await page.getByRole("button", { name: "My Path" }).click();
await page.waitForSelector(".path-row", { timeout: 60000 });
await shot(page, "07-path.png");
await shot(page, "07-path-mobile.png", { width: 390, height: 844 });

const row = page.locator(".path-row").first();
if (await row.isVisible()) {
  await row.click();
  await page.locator(".drawer-panel").waitFor({ timeout: 15000 });
  await shot(page, "08-why-resource.png");
  await page.locator(".drawer-panel").getByRole("button", { name: "Close" }).click();
}

await page.locator("[data-testid='progress-actions']").first().scrollIntoViewIfNeeded();
await shot(page, "09-progress.png");
await shot(page, "09-progress-mobile.png", { width: 390, height: 844 });

await page.setViewportSize({ width: 1440, height: 900 });
await runAssessmentFlow(page);

await page.getByRole("button", { name: "Skill Map" }).click();
await page.locator("h1").filter({ hasText: /What blocks what/i }).waitFor({ timeout: 30000 });
await shot(page, "16-skill-map.png");

await page.getByRole("button", { name: "Overview" }).click();
await page.getByTestId("ask-pathfinder").waitFor({ timeout: 15000 });
await shot(page, "17-ai.png");

await page.goto(BASE);
await clearSession(page);
await page.goto(BASE);
await advanceOnboarding(page, "AI/ML Engineer");
await page.getByRole("button", { name: /Judge demo/i }).click();
await page.waitForURL("**/workspace**", { timeout: 180000 });
await page.getByTestId("judge-guide").waitFor({ timeout: 60000 });
await shot(page, "18-judge-mode.png");

await browser.close();
console.log("Screenshots written to", OUT);
