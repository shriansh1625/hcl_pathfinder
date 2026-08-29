/**
 * Production-browser screenshot capture for the final spatial UX pass.
 * Usage: PF_BASE_URL=http://127.0.0.1:3002 node scripts/ui_final_capture.mjs [after|before]
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  attachMonitors,
  buildPathToWorkspace,
  clearSession,
  launchJudgeDemo,
  openAssessments,
  openPathTab,
  answerAssessment,
  shot,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const phase = process.argv[2] === "before" ? "before" : "after";
const OUT = join(__dirname, "..", "artifacts", "ui-final", phase);
mkdirSync(OUT, { recursive: true });

const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 390, height: 844 };

const log = { console: [], network: [], hydration: [] };

async function capture(page, name) {
  await shot(page, OUT, `${name}-1440.png`, DESKTOP);
  await shot(page, OUT, `${name}-390.png`, MOBILE);
  await page.setViewportSize(DESKTOP);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
attachMonitors(page, log);
page.on("pageerror", (err) => log.hydration.push(String(err)));
await clearSession(page);

await page.goto(process.env.PF_BASE_URL || "http://127.0.0.1:3002", { waitUntil: "domcontentloaded" });
await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
await capture(page, "onboarding");

await page.getByRole("button", { name: /Pick career manually/i }).click();
await page.locator(".career-requirements").first().waitFor({ timeout: 30000 });
await capture(page, "career-explorer");

await launchJudgeDemo(page, "AI/ML Engineer");
await capture(page, "dashboard");
await capture(page, "judge-mode");

await page.getByRole("button", { name: "Overview" }).click();
const blockersBtn = page.getByRole("button", { name: /Blockers|What is blocking/i });
if (await blockersBtn.first().isVisible().catch(() => false)) {
  await blockersBtn.first().click().catch(() => undefined);
}
await page.getByRole("button", { name: "Overview" }).click();

await openPathTab(page);
await capture(page, "path");
const whyBtn = page.locator(".path-row").first();
await whyBtn.click();
await page.getByRole("heading", { name: /Why this is here/i }).waitFor({ timeout: 15000 });
await capture(page, "path-why");
await page.getByRole("button", { name: "Close" }).click();

await page.getByRole("button", { name: "Skill Map" }).click();
await page.waitForTimeout(400);
await capture(page, "skill-map");

await page.getByRole("button", { name: "History" }).click();
await page.getByTestId("path-timeline").waitFor({ timeout: 30000 });
await capture(page, "timeline");

await openAssessments(page);
await capture(page, "assessment");

const submit = await answerAssessment(page);
await submit.click();
await page.getByTestId("result-hero").waitFor({ timeout: 120000 });
await capture(page, "result");

await page.getByTestId("see-what-changed").click();
await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
await page.waitForTimeout(200);
await capture(page, "v1");
await page.waitForTimeout(1000);
await capture(page, "v2");

await page.getByRole("button", { name: /Why this changed/i }).click();
await page.getByTestId("why-changed").waitFor({ timeout: 30000 });
await capture(page, "why-changed");

await page.getByRole("button", { name: "Overview" }).click();
const ask = page.getByTestId("ask-pathfinder");
if (await ask.isVisible().catch(() => false)) {
  await ask.scrollIntoViewIfNeeded();
  await capture(page, "ask-pathfinder");
}

const grounded = page.getByTestId("why-gap-statistics").or(page.locator("[data-testid^='why-gap-']").first());
if (await grounded.isVisible().catch(() => false)) {
  await grounded.locator("button").first().click();
  await page.waitForTimeout(800);
  await capture(page, "grounded-ai");
}

await browser.close();
console.log(
  JSON.stringify(
    {
      phase,
      out: OUT,
      consoleErrors: log.console,
      networkErrors: log.network,
      pageErrors: log.hydration,
    },
    null,
    2,
  ),
);
