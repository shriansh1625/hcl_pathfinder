/**
 * Multi-career proof — same learner, different roles produce different paths.
 */
import { writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { launchBrowser, clearSession, advanceToProfile } from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "multi-career-proof");
mkdirSync(OUT, { recursive: true });

const ROLES = ["AI/ML Engineer", "Cybersecurity Analyst", "Backend Developer"];
const paths = {};

const browser = await launchBrowser();
const page = await browser.newPage();

for (const role of ROLES) {
  await clearSession(page);
  await advanceToProfile(page, role);
  await page.getByRole("button", { name: /Build my path/i }).click();
  await page.waitForURL("**/workspace**", { timeout: 240000 });
  await page.getByRole("button", { name: "My Path" }).click();
  await page.waitForSelector(".path-row", { timeout: 60000 });
  const titles = await page.locator(".path-node-title").allTextContents();
  const version = await page.locator(".path-canvas-head .type-data").innerText().catch(() => "");
  paths[role] = { titles: titles.slice(0, 8), version };
  await page.screenshot({ path: join(OUT, `path-${role.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.png`), fullPage: true });
}

await browser.close();

const unique = new Set(Object.values(paths).map((p) => p.titles.join("|")));
const pass = unique.size === ROLES.length;
const report = { pass, roles: ROLES.length, uniquePathSignatures: unique.size, paths };
writeFileSync(join(OUT, "proof.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
process.exit(pass ? 0 : 1);
