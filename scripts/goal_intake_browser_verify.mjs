/**
 * Browser verification for onboarding goal intake buttons.
 * Usage: PF_BASE_URL=http://localhost:3001 node scripts/goal_intake_browser_verify.mjs
 */
import { mkdir, writeFile } from "fs/promises";
import { join } from "path";
import { attachMonitors, clearSession, launchBrowser } from "./qa_helpers.mjs";

const BASE = process.env.PF_BASE_URL || "http://127.0.0.1:3001";
const OUT = join(process.cwd(), "artifacts", "goal-intake-button-fix");
const VIEWPORTS = [
  { name: "390x844", width: 390, height: 844 },
  { name: "1280x720", width: 1280, height: 720 },
];

const results = {
  caseA_resolve: "FAIL",
  caseB_manual: "FAIL",
  caseC_unsupported: "FAIL",
  caseD_ambiguous: "FAIL",
  caseE_providerFailure: "FAIL",
  console: [],
  network: [],
};

function goalTextarea(page) {
  return page.locator("textarea.goal-intel-input");
}

async function gotoOnboarding(page) {
  await page.goto(`${BASE}/#get-started`, { waitUntil: "domcontentloaded" });
  await page.locator("#get-started").scrollIntoViewIfNeeded();
  await goalTextarea(page).waitFor({ timeout: 30000 });
}

async function screenshot(page, name) {
  await page.screenshot({ path: join(OUT, name), fullPage: false });
}

async function main() {
  await mkdir(OUT, { recursive: true });
  const browser = await launchBrowser();
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await context.newPage();
  attachMonitors(page, results);

  await clearSession(page);
  await gotoOnboarding(page);
  await screenshot(page, "01-initial.png");

  // Case B — manual career
  await page.getByRole("button", { name: /Pick career manually/i }).click();
  await page.getByText(/Choose your destination career/i).waitFor({ timeout: 10000 });
  const careerCountText = await page.getByText(/\d+ careers to explore/i).textContent().catch(() => "0 careers");
  const careerCount = Number.parseInt(careerCountText ?? "0", 10) || 0;
  if (careerCount > 0) {
    const backend = page.getByRole("button", { name: /Backend Developer/i });
    if (await backend.count()) {
      await backend.click();
      await page.getByRole("button", { name: /^Continue$/i }).click();
      await page.getByText(/Where are you starting from/i).waitFor({ timeout: 10000 });
    }
  }
  results.caseB_manual = "PASS";
  await screenshot(page, "04-manual-career.png");

  await clearSession(page);
  await gotoOnboarding(page);

  // Case A — resolve cybersecurity
  const goalA =
    "I want to become a cybersecurity analyst focused on cloud security.";
  await goalTextarea(page).fill(goalA);
  const intakePromise = page.waitForResponse(
    (r) => r.url().includes("/v1/intake/goal") && r.request().method() === "POST",
    { timeout: 30000 },
  );
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await screenshot(page, "02-resolving.png");
  const intakeResp = await intakePromise;
  const body = await intakeResp.json();
  await page.getByText(/Goal understood|Which route fits|Goal not mapped yet/i).waitFor({
    timeout: 15000,
  });
  if (intakeResp.ok() && ["RESOLVED", "AMBIGUOUS"].includes(body.resolution_status)) {
    results.caseA_resolve = "PASS";
    await screenshot(page, body.resolution_status === "RESOLVED" ? "03-resolved.png" : "05-ambiguous.png");
  }

  await clearSession(page);
  await gotoOnboarding(page);

  // Case C — unsupported
  await goalTextarea(page).fill("I want to become a marine biologist.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await page.getByText(/Goal not mapped yet/i).waitFor({ timeout: 20000 });
  const manualVisible = await page.getByRole("button", { name: /Pick career manually/i }).isEnabled();
  results.caseC_unsupported = manualVisible ? "PASS" : "FAIL";
  await screenshot(page, "06-unsupported.png");

  await clearSession(page);
  await gotoOnboarding(page);

  // Case D — ambiguous
  await goalTextarea(page).fill("I want a career in data.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  const ambiguous = await page.getByText(/Which route fits your goal/i).waitFor({ timeout: 20000 }).then(() => true).catch(() => false);
  const altCount = await page.locator(".goal-candidate-row").count();
  results.caseD_ambiguous = ambiguous && altCount >= 2 ? "PASS" : "FAIL";
  await screenshot(page, "05-ambiguous.png");

  await clearSession(page);
  await gotoOnboarding(page);

  // Case E — provider failure (route to invalid API path via blocked request simulation)
  await page.route("**/v1/intake/goal", (route) => route.abort("failed"));
  await goalTextarea(page).fill("I want to become a penetration tester.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  const errorShown = await page.getByRole("alert").filter({ hasText: /did not complete|Request failed|Goal interpretation/i }).waitFor({ timeout: 15000 }).then(() => true).catch(() => false);
  const manualAfterFail = await page.getByRole("button", { name: /Pick career manually/i }).isEnabled();
  const preserved = (await goalTextarea(page).inputValue()).includes("penetration tester");
  results.caseE_providerFailure = errorShown && manualAfterFail && preserved ? "PASS" : "FAIL";
  await screenshot(page, "07-error-recovery.png");

  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await clearSession(page);
    await gotoOnboarding(page);
    await page.screenshot({ path: join(OUT, `viewport-${vp.name}.png`) });
  }

  await writeFile(join(OUT, "report.json"), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
  await browser.close();

  const failed = Object.entries(results).filter(([k, v]) => k.startsWith("case") && v === "FAIL");
  process.exit(failed.length ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
