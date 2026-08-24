/**
 * Assessment adaptation browser proof — real live flow screenshots.
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { buildPathToWorkspace, clearSession, openAssessments, answerAssessment, shot } from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "adaptation-proof");
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await clearSession(page);

await buildPathToWorkspace(page, "Backend Developer");
await openAssessments(page);
await shot(page, OUT, "assessment.png");

const submit = await answerAssessment(page);
await submit.click();
await page.getByTestId("result-hero").waitFor({ timeout: 120000 });
await shot(page, OUT, "assessment-result.png");

await page.getByTestId("see-what-changed").click();
await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
await page.waitForTimeout(400);
await shot(page, OUT, "assessment-v1.png");
await page.waitForTimeout(900);
await shot(page, OUT, "assessment-v2.png");

await page.getByRole("button", { name: /Why this changed/i }).click();
await page.getByTestId("why-changed").waitFor({ timeout: 30000 });
await shot(page, OUT, "assessment-why.png");

await page.getByRole("button", { name: "History" }).click();
await page.getByTestId("path-timeline").waitFor({ timeout: 30000 });
await shot(page, OUT, "assessment-history.png");

await browser.close();
console.log("Assessment adaptation proof written to", OUT);