/**
 * Failure evidence screenshots — one per safe failure state.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  BASE,
  attachMonitors,
  buildPathToWorkspace,
  clearSession,
  launchJudgeDemo,
  openAssessments,
  answerAssessment,
  openPathTab,
  submitProgressStruggle,
  shot,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "failure-evidence");
mkdirSync(OUT, { recursive: true });
const meta = [];

async function capture(name, fn) {
  const page = await browser.newPage();
  const log = attachMonitors(page);
  await clearSession(page);
  try {
    await fn(page);
    await shot(page, OUT, `${name}.png`);
    meta.push({ name, ok: true, ...log });
  } catch (err) {
    meta.push({ name, ok: false, error: String(err), ...log });
    throw err;
  } finally {
    await page.close();
  }
}

const browser = await chromium.launch({ headless: true });

await capture("backend-unavailable", async (page) => {
  await page.route("**/v1/intake/goal", (route) => route.abort("failed"));
  await page.goto(BASE);
  await page.locator("textarea").fill("I want to become a backend engineer.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await page.getByText("What could not load").first().waitFor({ timeout: 15000 });
  await page.unroute("**/v1/intake/goal");
});

await capture("progress-failure", async (page) => {
  await buildPathToWorkspace(page, "Backend Developer");
  await openPathTab(page);
  await page.locator("[data-testid='progress-actions']").first().waitFor({ timeout: 30000 });
  await page.route("**/learners/**/progress", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"progress failed"}' });
    }
    return route.continue();
  });
  await submitProgressStruggle(page);
  await page.getByTestId("progress-error").waitFor({ timeout: 20000 });
  await page.unroute("**/learners/**/progress");
});

await capture("assessment-failure", async (page) => {
  await buildPathToWorkspace(page, "Backend Developer");
  await page.route("**/assessments/**/attempts", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"assessment failed"}' });
    }
    return route.continue();
  });
  await openAssessments(page);
  const submit = await answerAssessment(page);
  await submit.click();
  await page.locator(".error-state").filter({ hasText: /assessment failed/i }).first().waitFor({ timeout: 30000 });
  await page.unroute("**/assessments/**/attempts");
});

await capture("ai-unavailable", async (page) => {
  await buildPathToWorkspace(page, "Backend Developer");
  await page.route("**/ai/explain", (route) =>
    route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"AI unavailable"}' }),
  );
  await page.getByTestId("ask-pathfinder").waitFor({ timeout: 15000 });
  await page.getByRole("button", { name: "Why am I learning statistics?" }).click();
  await page.getByText(/Explanation is unavailable/i).waitFor({ timeout: 15000 });
  await page.unroute("**/ai/explain");
});

await capture("malformed-ai-response", async (page) => {
  await buildPathToWorkspace(page, "Backend Developer");
  await page.route("**/ai/explain", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "not-json" }),
  );
  await page.getByTestId("ask-pathfinder").waitFor({ timeout: 15000 });
  await page.getByRole("button", { name: "What should I do this week?" }).click();
  await page.getByText(/Explanation is unavailable/i).waitFor({ timeout: 15000 });
  await page.unroute("**/ai/explain");
});

await browser.close();
writeFileSync(join(OUT, "summary.json"), JSON.stringify(meta, null, 2));
console.log("Failure evidence screenshots written to", OUT);