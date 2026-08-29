/**
 * PathFinder failure matrix — 9/9 browser verification.
 * Usage: cd .tmp-pw && PF_BASE_URL=http://127.0.0.1:3004 node ../scripts/failure_matrix_qa.mjs
 */
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  BASE,
  attachMonitors,
  buildPathToWorkspace,
  buildPathWithoutEvidence,
  launchJudgeDemo,
  openAssessments,
  openPathTab,
  answerAssessment,
  submitProgressStruggle,
  launchBrowser,
  clearSession,
  primaryNav,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "failure-matrix");
mkdirSync(OUT, { recursive: true });

const results = [];

function record(name, pass, detail = "", meta = {}) {
  results.push({ name, pass, detail, console: meta.console ?? [], network: meta.network ?? [], expectedUi: meta.expectedUi ?? "" });
  console.log(pass ? "PASS" : "FAIL", name, detail);
}

const browser = await launchBrowser();

async function runCase(name, fn) {
  const page = await browser.newPage();
  const log = attachMonitors(page);
  try {
    await clearSession(page);
    await fn(page, log);
  } catch (err) {
    record(name, false, String(err), log);
  } finally {
    await page.close();
  }
}

// 1 — backend unavailable
await runCase("backend unavailable", async (page, log) => {
  await page.route("**/v1/intake/goal", (route) => route.abort("failed"));
  await page.goto(BASE);
  await page.locator("textarea").fill("I want to become a backend engineer.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await page.getByText("What could not load").first().waitFor({ timeout: 15000 });
  const preserved = await page.getByRole("button", { name: /Resolve goal/i }).isVisible();
  const noWorkspace = !page.url().includes("/workspace");
  await page.unroute("**/v1/intake/goal");
  record(
    "backend unavailable",
    preserved && noWorkspace,
    preserved ? "context preserved" : "lost context",
    { ...log, expectedUi: "What could not load" },
  );
});

// 2 — intake failure
await runCase("intake failure", async (page, log) => {
  await page.route("**/v1/intake/goal", (route) =>
    route.fulfill({ status: 404, contentType: "application/json", body: '{"detail":"Not Found"}' }),
  );
  await page.goto(BASE);
  await page.locator("textarea").fill("I want to become a data engineer.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await page.getByText("What could not load").first().waitFor({ timeout: 15000 });
  const preserved = await page.getByRole("button", { name: /Resolve goal/i }).isVisible();
  await page.unroute("**/v1/intake/goal");
  record("intake failure", preserved, "context preserved after 404", { ...log, expectedUi: "What could not load" });
});

// 3 — demo-evidence failure
await runCase("demo-evidence failure", async (page, log) => {
  await page.goto(BASE);
  await page.getByRole("button", { name: /Pick career manually/i }).click();
  await page.locator(".career-requirements").first().waitFor();
  for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Review profile" }).click();
  await page.route("**/demo-evidence", (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"seed error"}' }),
  );
  await page.getByRole("button", { name: /Build my path/i }).click();
  await page.getByText(/could not|failed|error/i).first().waitFor({ timeout: 30000 });
  const onWorkspace = page.url().includes("/workspace");
  await page.unroute("**/demo-evidence");
  record("demo-evidence failure", !onWorkspace, onWorkspace ? "reached workspace" : "truthful error", {
    ...log,
    expectedUi: "error banner, no workspace",
  });
});

// 4 — progress failure
await runCase("progress failure", async (page, log) => {
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
  await page.unroute("**/learners/**/progress");
  record("progress failure", Boolean(alert) && noSuccess, alert?.slice(0, 80) ?? "", {
    ...log,
    expectedUi: "progress-error visible, no progress-result-created",
  });
});

// 5 — assessment failure
await runCase("assessment failure", async (page, log) => {
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
  await page.unroute("**/assessments/**/attempts");
  record("assessment failure", !onResult, "error surfaced, no result view", {
    ...log,
    expectedUi: "error-state, no result-hero",
  });
});

// 6 — AI unavailable
await runCase("AI unavailable", async (page, log) => {
  await buildPathToWorkspace(page, "Backend Developer");
  await page.route("**/ai/explain", (route) =>
    route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"AI unavailable"}' }),
  );
  await page.getByTestId("ask-pathfinder").waitFor({ timeout: 15000 });
  await page.getByRole("button", { name: "Why am I learning this skill?" }).click();
  await page.getByText(/Explanation is unavailable/i).waitFor({ timeout: 15000 });
  const stillOnDashboard = await page.getByText(/KNOW/).first().isVisible();
  await page.unroute("**/ai/explain");
  record("AI unavailable", stillOnDashboard, "deterministic fallback shown", {
    ...log,
    expectedUi: "Explanation is unavailable",
  });
});

// 7 — malformed AI response
await runCase("malformed AI response", async (page, log) => {
  await buildPathToWorkspace(page, "Backend Developer");
  await page.route("**/ai/explain", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "not-json" }),
  );
  await page.getByTestId("ask-pathfinder").waitFor({ timeout: 15000 });
  await page.getByRole("button", { name: "What should I do this week?" }).click();
  await page.getByText(/Explanation is unavailable/i).waitFor({ timeout: 15000 });
  const noFakeAnswer = !(await page.locator(".grounded-answer").isVisible().catch(() => false));
  await page.unroute("**/ai/explain");
  record("malformed AI response", noFakeAnswer, "no fabricated answer", {
    ...log,
    expectedUi: "Explanation is unavailable, no grounded-answer",
  });
});

// 8 — blocked prerequisite
await runCase("blocked prerequisite", async (page, log) => {
  await launchJudgeDemo(page, "AI/ML Engineer");
  await openPathTab(page);
  const blocked = page.getByTestId("blocked-prerequisite").first();
  await blocked.waitFor({ timeout: 60000 });
  const exposition = blocked.getByTestId("blocker-exposition");
  await exposition.waitFor({ timeout: 15000 });
  const waitText = await exposition.locator(".blocker-expo-wait").textContent();
  const skillText = await exposition.locator(".blocker-expo-skill").textContent();
  const hasPrereq = Boolean(waitText?.trim()) && Boolean(skillText?.trim());
  const progressCreated = await blocked.getByTestId("progress-result-created").isVisible().catch(() => false);
  record("blocked prerequisite", hasPrereq && !progressCreated, `${waitText} · ${skillText}`, {
    ...log,
    expectedUi: "blocker-exposition on waiting path item",
  });
});

// 9 — UNKNOWN skill
await runCase("UNKNOWN skill", async (page, log) => {
  await buildPathWithoutEvidence(page, "Backend Developer");
  await page.getByText(/KNOW/).first().waitFor({ timeout: 30000 });
  const noEvidenceBadge = page.locator(".status-badge-unknown, .status-badge-verify").filter({ hasText: /NO EVIDENCE|VERIFY/i });
  await noEvidenceBadge.first().waitFor({ timeout: 30000 });
  const pageText = await page.locator(".command-center, .app-root").first().innerText();
  const noZeroPercent = !/\b0\s*%/.test(pageText);
  const showsNoEvidence = /NO EVIDENCE|VERIFY/i.test(pageText);
  record("UNKNOWN skill", noZeroPercent && showsNoEvidence, "UNKNOWN rendered without 0%", {
    ...log,
    expectedUi: "NO EVIDENCE badge, no 0% for unknown",
  });
});

await browser.close();

const failed = results.filter((r) => !r.pass);
const summary = {
  passed: results.length - failed.length,
  failed: failed.length,
  total: results.length,
  results,
};
writeFileSync(join(OUT, "summary.json"), JSON.stringify(summary, null, 2));
console.log("SUMMARY", JSON.stringify({ passed: summary.passed, failed: summary.failed, names: failed.map((f) => f.name) }));
process.exit(failed.length ? 1 : 0);
