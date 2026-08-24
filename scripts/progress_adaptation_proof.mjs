/**
 * Progress adaptation browser proof — real live flow screenshots.
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { buildPathToWorkspace, clearSession, openPathTab, shot, submitProgressStruggle } from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "adaptation-proof");
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await clearSession(page);

await buildPathToWorkspace(page, "Backend Developer");
await openPathTab(page);
await shot(page, OUT, "progress-adaptation-v1.png");

await submitProgressStruggle(page, 15);
await page.getByTestId("progress-result-created").waitFor({ timeout: 120000 });
await page.getByText("Progress recorded").waitFor();
await page.getByText("Competency updated").waitFor();
await page.getByText("Path changed").waitFor();
await shot(page, OUT, "progress-adaptation-result.png");

await page.getByRole("button", { name: "See what changed" }).click();
await page.getByTestId("path-changed-hero").waitFor({ timeout: 60000 });
await page.waitForTimeout(400);
await shot(page, OUT, "progress-adaptation-v2.png");

await page.getByRole("button", { name: /Why this changed/i }).click();
await page.getByTestId("why-changed").waitFor({ timeout: 30000 });
await shot(page, OUT, "progress-adaptation-why.png");

await page.getByRole("button", { name: "History" }).click();
await page.getByTestId("path-timeline").waitFor({ timeout: 30000 });
await shot(page, OUT, "progress-adaptation-history.png");

await browser.close();
console.log("Progress adaptation proof written to", OUT);