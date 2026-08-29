import { mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { launchBrowser, clearSession, launchJudgeDemo, openPathTab } from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "mobile-path-verify");
mkdirSync(OUT, { recursive: true });

const browser = await launchBrowser();
const page = await browser.newPage();
await clearSession(page);
await launchJudgeDemo(page, "AI/ML Engineer");
await openPathTab(page);

const checks = [];
for (const viewport of [
  { width: 390, height: 844 },
  { width: 430, height: 932 },
]) {
  await page.setViewportSize(viewport);
  const rail = await page.getByTestId("path-mobile-rail").isVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  checks.push({ viewport, rail, overflow });
  await page.screenshot({ path: join(OUT, `path-${viewport.width}x${viewport.height}.png`), fullPage: true });
}

await browser.close();
const pass = checks.every((row) => row.rail && !row.overflow);
console.log(JSON.stringify({ pass, checks }, null, 2));
process.exit(pass ? 0 : 1);
