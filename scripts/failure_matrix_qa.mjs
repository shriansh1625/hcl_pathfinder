/**
 * PathFinder failure matrix — 7/7 browser verification.
 * Usage: cd .tmp-pw && npm install && PF_BASE_URL=http://127.0.0.1:3002 node ../scripts/failure_matrix_qa.mjs
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
  openPathTab,
  answerAssessment,
  submitProgressStruggle,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "failure-matrix");
mkdirSync(OUT, { recursive: true });

const results = [];

function record(name, pass, detail = "", meta = {}) {
  results.push({ name, pass, detail, ...meta });
  console.log(pass ? "PASS" : "FAIL", name, detail);
}

const browser = await chromium.launch({ headless: true });

// 1 — backend unavailable at intake
{
  const page = await browser.newPage();
  const log = attachMonitors(page);
  await clearSession(page);
  await page.route("**/v1/intake/goal", (route) => route.abort("failed"));
  await page.goto(BASE);
  await page.locator("textarea").fill("I want to become a backend engineer.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await page.getByText("What could not load").first().waitFor({ timeout: 15000 });
  const preserved = await page.getByRole("button", { name: /Resolve goal/i }).isVisible();
  record("backend unavailable (intake)", preserved, preserved ? "context preserved" : "lost context", log);
  await page.unroute("**/v1/intake/goal");
  await page.close();
}

// 2 — intake 404
{
  const page = await browser.newPage();
  const log = attachMonitors(page);
  await clearSession(page);
  await page.route("**/v1/intake/goal", (route) =>
    route.fulfill({ status: 404, contentType: "application/json", body: '{"detail":"Not Found"}' }),
  );
  await page.goto(BASE);
  await page.locator("textarea").fill("I want to become a data engineer.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await page.getByText("What could not load").first().waitFor({ timeout: 15000 });
  const preserved = await page.getByRole("button", { name: /Resolve goal/i }).isVisible();
  record("intake failure preserves context", preserved, "", log);
  await page.unroute("**/v1/intake/goal");
  await page.close();
}

// 3 — demo-evidence failure during bootstrap
{
  const page = await browser.newPage();
  const log = attachMonitors(page);
  await clearSession(page);
  await page.goto(BASE);
  await page.getByRole("button", { name: /Pick career manually/i }).click();
  await page.locator(".career-requirements").first().waitFor();
  for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Review profile" }).click();
  await page.route("**/demo-evidence", (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"seed error"}' }),
  );
  await page.getByRole("button", { name: /Build my path/i }).click();
  const err = await page
    .getByText(/could not|failed|error/i)
    .first()
    .waitFor({ timeout: 30000 })
    .then(() => true)
    .catch(() => false);
  const onWorkspace = page.url().includes("/workspace");
  record("demo-evidence failure", err && !onWorkspace, err ? "truthful error, no workspace" : `workspace=${onWorkspace}`, log);
  await page.unroute("**/demo-evidence");
  await page.close();
}

// 4 — progress failure
{
  const page = await browser.newPage();
  const log = attachMonitors(page);
  await clearSession(page);
  await buildPathToWorkspace(page, "Backend Developer");
  await openPathTab(page);
  await page.locator("[data-testid='progress-actions']").first().waitFor({ timeout: 30000 });
  await page.route("**/learners/**/progress", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 500,
        contentType: "application/json",
        body: '{"detail":"progress failed"}',
      });
    }
    return route.continue();
  });
  await submitProgressStruggle(page);
  await page.getByTestId("progress-error").waitFor({ timeout: 20000 });
  const alert = await page.getByTestId("progress-error").textContent();
  const noSuccess = !(await page.getByTestId("progress-result-created").isVisible().catch(() => false));
  record("progress failure", Boolean(alert) && noSuccess, alert?.slice(0, 80) ?? "", log);
  await page.unroute("**/learners/**/progress");
  await page.close();
}

// 5 — assessment failure
{
  const page = await browser.newPage();
  const log = attachMonitors(page);
  await clearSession(page);
  await buildPathToWorkspace(page, "Backend Developer");
  await page.route("**/assessments/**/attempts", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 500,
        contentType: "application/json",
        body: '{"detail":"assessment failed"}',
      });
    }
    return route.continue();
  });
  await openAssessments(page);
  const submit = await answerAssessment(page);
  await submit.click();
  await page.locator(".error-state").filter({ hasText: /assessment failed/i }).first().waitFor({ timeout: 30000 });
  const onResult = await page.getByTestId("result-hero").isVisible().catch(() => false);
  record("assessment failure", !onResult, "error surfaced, no result view", log);
  await page.unroute("**/assessments/**/attempts");
  await page.close();
}

// 6 — AI unavailable
{
  const page = await browser.newPage();
  const log = attachMonitors(page);
  await clearSession(page);
  await buildPathToWorkspace(page, "Backend Developer");
  await page.route("**/ai/explain", (route) =>
    route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"AI unavailable"}' }),
  );
  await page.getByTestId("ask-pathfinder").waitFor({ timeout: 15000 });
  await page.getByRole("button", { name: "Why am I learning statistics?" }).click();
  await page.getByText(/Explanation is unavailable/i).waitFor({ timeout: 15000 });
  const stillOnDashboard = await page.getByText(/KNOW/).first().isVisible();
  record("AI unavailable fallback", stillOnDashboard, "deterministic fallback shown", log);
  await page.unroute("**/ai/explain");
  await page.close();
}

// 7 — malformed AI response
{
  const page = await browser.newPage();
  const log = attachMonitors(page);
  await clearSession(page);
  await buildPathToWorkspace(page, "Backend Developer");
  await page.route("**/ai/explain", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "not-json" }),
  );
  await page.getByTestId("ask-pathfinder").waitFor({ timeout: 15000 });
  await page.getByRole("button", { name: "What should I do this week?" }).click();
  await page.getByText(/Explanation is unavailable/i).waitFor({ timeout: 15000 });
  const noFakeAnswer = !(await page.locator(".grounded-answer").isVisible().catch(() => false));
  record("malformed AI response", noFakeAnswer, "no fabricated answer", log);
  await page.unroute("**/ai/explain");
  await page.close();
}

await browser.close();

const failed = results.filter((r) => !r.pass);
writeFileSync(join(OUT, "summary.json"), JSON.stringify({ results, passed: results.length - failed.length, total: results.length }, null, 2));
console.log("SUMMARY", JSON.stringify({ passed: results.length - failed.length, total: results.length, failed: failed.map((f) => f.name) }));
process.exit(failed.length ? 1 : 0);
