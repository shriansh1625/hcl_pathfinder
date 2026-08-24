/**
 * Lightweight accessibility audit via Playwright.
 * Usage: PF_BASE_URL=http://127.0.0.1:3002 node scripts/accessibility_audit.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.PF_BASE_URL || "http://127.0.0.1:3002";
const results = [];

async function auditPage(page, name, setup) {
  await setup();
  const issues = await page.evaluate(() => {
    const hits = [];
    const buttons = Array.from(document.querySelectorAll("button"));
    for (const btn of buttons) {
      const label = btn.getAttribute("aria-label") || btn.textContent?.trim();
      if (!label) hits.push("button without accessible name");
    }
    const dialogs = Array.from(document.querySelectorAll("[role='dialog']"));
    for (const dlg of dialogs) {
      if (!dlg.getAttribute("aria-labelledby") && !dlg.getAttribute("aria-label")) {
        hits.push("dialog without label");
      }
    }
    const h1 = document.querySelectorAll("h1").length;
    if (h1 === 0) hits.push("missing h1");
    if (h1 > 1) hits.push("multiple h1");
    return [...new Set(hits)];
  });
  results.push({ name, issues });
  console.log(issues.length ? "WARN" : "PASS", name, issues.join("; ") || "ok");
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

await auditPage(page, "onboarding", async () => {
  await page.goto(BASE);
  await page.getByRole("heading", { name: /Build the path/i }).waitFor();
});

await auditPage(page, "career explorer", async () => {
  await page.getByRole("button", { name: /Pick career manually/i }).click();
  await page.locator(".career-requirements").first().waitFor();
});

for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Continue" }).click();
await page.getByRole("button", { name: "Review profile" }).click();
await page.getByRole("button", { name: /Judge demo/i }).click();
await page.waitForURL("**/workspace**", { timeout: 180000 });

for (const [name, nav] of [
  ["dashboard", async () => page.getByRole("button", { name: "Overview" }).click()],
  ["path", async () => page.getByRole("button", { name: "My Path" }).click()],
  ["assessment", async () => { await page.getByRole("button", { name: "Assessments" }).click(); }],
  ["skill map", async () => page.getByRole("button", { name: "Skill Map" }).click()],
  ["history", async () => page.getByRole("button", { name: "History" }).click()],
]) {
  await auditPage(page, name, async () => {
    await nav();
    await page.waitForTimeout(500);
  });
}

await browser.close();
const totalIssues = results.reduce((n, r) => n + r.issues.length, 0);
console.log("SUMMARY", JSON.stringify({ pages: results.length, issues: totalIssues }));
process.exit(totalIssues > 5 ? 1 : 0);
