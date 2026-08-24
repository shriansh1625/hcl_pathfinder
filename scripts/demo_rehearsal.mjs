/**
 * 90-second demo rehearsal — measures real segment timings.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { BASE, clearSession, openAssessments, answerAssessment } from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "demo-rehearsal");
mkdirSync(OUT, { recursive: true });

const marks = [];
const t0 = Date.now();
const mark = (label) => {
  const elapsed = (Date.now() - t0) / 1000;
  marks.push({ label, elapsed });
  console.log(`${elapsed.toFixed(1)}s`, label);
};

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await clearSession(page);

await page.goto(BASE, { waitUntil: "domcontentloaded" });
await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
mark("start");

await page.locator("textarea").fill("I want to become an AI/ML engineer focused on model evaluation and deployment.");
await page.getByRole("button", { name: /Resolve goal/i }).click();
await page.locator(".goal-resolved-card").waitFor({ timeout: 60000 });
mark("career resolved");

await page.getByRole("button", { name: /Continue/i }).click();
await page.locator(".career-requirements").first().waitFor({ timeout: 30000 });
await page.getByRole("button", { name: "AI/ML Engineer" }).click();
for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Continue" }).click();
await page.getByRole("button", { name: "Review profile" }).click();
await page.getByText(/Your path configuration/i).waitFor({ timeout: 15000 });
await page.getByRole("button", { name: /Build my path/i }).click();
await page.waitForURL("**/workspace**", { timeout: 180000 });
await page.getByRole("heading", { name: /AI\/ML Engineer/i }).first().waitFor({ timeout: 60000 });
mark("dashboard / gaps / blockers");

await page.getByRole("button", { name: "My Path" }).click();
await page.waitForSelector(".path-row", { timeout: 60000 });
await page.getByRole("button", { name: /Why this path/i }).click().catch(() => {});
await page.getByTestId("why-score-breakdown").waitFor({ timeout: 15000 }).catch(() => {});
mark("path v1 + why");

await openAssessments(page);
const submit = await answerAssessment(page);
await submit.click();
await page.getByTestId("result-hero").waitFor({ timeout: 120000 });
mark("prove it / assessment result");

await page.getByText(/NEW EVIDENCE/i).first().waitFor({ timeout: 15000 }).catch(() => {});
mark("new evidence diagnosis");

await page.getByTestId("see-what-changed").click();
await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
await page.getByText("FROZEN WORK").first().waitFor({ timeout: 15000 }).catch(() => {});
mark("v1 to v2 / frozen work");

await page.getByRole("button", { name: /Why this changed/i }).click();
await page.getByTestId("why-changed").waitFor({ timeout: 30000 });
await page.getByTestId("what-changed-path").click().catch(() => {});
mark("why + grounded ai");

const total = (Date.now() - t0) / 1000;
const summary = { marks, totalSeconds: total, targetSeconds: 90 };
writeFileSync(join(OUT, "timing.json"), JSON.stringify(summary, null, 2));
await browser.close();
console.log("Demo rehearsal total", total.toFixed(1), "seconds");