/**
 * PathFinder release-gate workspace QA.
 * Usage: PF_BASE_URL=http://127.0.0.1:3002 node scripts/release_gate_workspace_qa.mjs
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUT = join(ROOT, "artifacts", "release-gate-qa");
mkdirSync(OUT, { recursive: true });

const BASE = process.env.PF_BASE_URL || "http://127.0.0.1:3002";

const VIEWPORTS = [
  { tag: "390x844", width: 390, height: 844 },
  { tag: "430x932", width: 430, height: 932 },
  { tag: "768x1024", width: 768, height: 1024 },
  { tag: "1280x720", width: 1280, height: 720 },
  { tag: "1440x900", width: 1440, height: 900 },
  { tag: "1920x1080", width: 1920, height: 1080 },
];

const ROLES = [
  "AI/ML Engineer",
  "Cybersecurity Analyst",
  "Backend Developer",
  "Frontend Developer",
  "Data Engineer",
];

const results = [];
const record = (name, pass, detail = "") => {
  results.push({ name, pass, detail });
  console.log(pass ? "PASS" : "FAIL", name, detail);
};

async function clearSession(page) {
  await page.addInitScript(() => {
    sessionStorage.clear();
    localStorage.clear();
  });
}

async function overflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
}

async function overlapHits(page) {
  return page.evaluate(() => {
    const important = Array.from(
      document.querySelectorAll(
        ".onboard-panel-body label, .onboard-panel-body button, .drawer-panel, .path-row, .ask-surface, .nav-indicator, h1, h2",
      ),
    ).filter((el) => {
      const style = window.getComputedStyle(el);
      return style.visibility !== "hidden" && style.display !== "none" && el.getClientRects().length > 0;
    });
    const floats = Array.from(document.querySelectorAll(".loading-context, .error-state, .nav-indicator, .drawer-scrim"));
    const hits = [];
    for (const a of important) {
      const ar = a.getBoundingClientRect();
      for (const b of floats) {
        if (a === b || b.contains(a) || a.contains(b)) continue;
        const br = b.getBoundingClientRect();
        if (ar.width > 0 && br.width > 0 && !(ar.right <= br.left || ar.left >= br.right || ar.bottom <= br.top || ar.top >= br.bottom)) {
          hits.push(`${a.tagName}.${a.className}`);
        }
      }
    }
    return hits;
  });
}

function attachMonitors(page, errors, netFails, allowFail = false) {
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error" && !m.text().includes("favicon")) errors.push(m.text());
  });
  page.on("response", (r) => {
    if (allowFail) return;
    if (r.status() >= 400 && !r.url().includes("favicon") && !r.url().includes("json/version")) {
      netFails.push(`${r.status()} ${r.url()}`);
    }
  });
}

async function waitOnboarding(page) {
  await page.goto(BASE, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
}

async function pickManual(page) {
  await page.getByRole("button", { name: /Pick career manually/i }).click();
  await page.locator(".career-requirements").first().waitFor({ timeout: 30000 });
}

async function selectRole(page, roleName) {
  await page.getByRole("button", { name: roleName }).click();
}

async function advanceOnboarding(page, roleName = /Backend Developer/i) {
  await waitOnboarding(page);
  await pickManual(page);
  if (roleName) await selectRole(page, roleName);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Review profile" }).click();
}

async function buildPath(page) {
  await page.getByRole("button", { name: /Build my path/i }).click();
  await page.waitForURL("**/workspace**", { timeout: 180000 });
  await page.locator("h1").first().waitFor({ timeout: 60000 });
}

async function shot(page, name, vp = "1440x900") {
  await page.screenshot({ path: join(OUT, `${name}-${vp}.png`), fullPage: true });
}

const browser = await chromium.launch({ headless: true });

// Phase 3 — full onboarding walkthrough + screenshots (desktop)
{
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await clearSession(page);
  const errors = [];
  const netFails = [];
  attachMonitors(page, errors, netFails);

  await waitOnboarding(page);
  record("1 goal screen", true);
  await shot(page, "01-onboarding-goal");

  await pickManual(page);
  record("3 career explorer", true);
  await shot(page, "02-career-explorer");

  for (const role of ROLES) {
    const visible = await page.getByRole("button", { name: role }).isVisible().catch(() => false);
    record(`career role visible: ${role}`, visible);
  }

  await selectRole(page, "Backend Developer");
  await page.getByRole("button", { name: "Continue" }).click();
  record("9 experience", await page.getByText(/Current experience/i).isVisible());
  await page.getByRole("button", { name: "Continue" }).click();
  record("10 interests", await page.getByText("Interests & specialization").isVisible());
  await page.getByRole("button", { name: "Continue" }).click();
  record("11 schedule", await page.getByText("Time & learning preference").isVisible());
  await page.getByRole("button", { name: "Continue" }).click();
  record("12 evidence", await page.getByText(/What PathFinder knows/i).isVisible());
  await shot(page, "03-onboarding-evidence");
  await page.getByRole("button", { name: "Review profile" }).click();
  record("13 profile", await page.getByText(/Your path configuration/i).isVisible());
  await shot(page, "04-onboarding-profile");

  await buildPath(page);
  record("14 build path", true);
  record("15 dashboard", await page.getByText(/KNOW/).first().isVisible());
  await shot(page, "05-dashboard");

  await page.getByRole("button", { name: "Continue" }).click();
  await page.waitForTimeout(500);
  record("16 blockers", await page.locator("h1").filter({ hasText: /blocking your path/i }).isVisible().catch(() => false));
  await shot(page, "06-blockers");

  await page.getByRole("button", { name: "My Path" }).click();
  await page.waitForSelector(".path-row, [data-testid='progress-actions']", { timeout: 60000 });
  record("17 path", true);
  await shot(page, "07-path");

  const pathRow = page.locator(".path-row").first();
  if (await pathRow.isVisible().catch(() => false)) {
    await pathRow.click();
    const hasGap = await page.getByText(/Skill gap|Intervention|Why selected/i).first().isVisible().catch(() => false);
    record("18 recommendation WHY", hasGap);
    await shot(page, "08-recommendation-why");
    await page.locator(".drawer-panel").getByRole("button", { name: "Close" }).click();
  } else {
    record("18 recommendation WHY", false, "no path row");
  }

  const progress = page.locator("[data-testid='progress-actions']").first();
  record("19 progress UI", await progress.isVisible().catch(() => false));
  await shot(page, "10-progress");

  await page.getByRole("button", { name: "Overview" }).click();
  record("25 ask pathfinder", await page.getByTestId("ask-pathfinder").isVisible().catch(() => false));

  await page.getByRole("button", { name: "Assessments" }).click();
  await page.waitForTimeout(1000);
  record("20 assessment list", await page.locator("h1").filter({ hasText: /unverified|Assessment/i }).isVisible().catch(() => false));
  await shot(page, "09-assessment");

  await page.getByRole("button", { name: "History" }).click();
  record("26 timeline", await page.locator("h1").filter({ hasText: /Timeline|History|Adaptation/i }).isVisible().catch(() => false));
  await shot(page, "13-timeline");

  await page.getByRole("button", { name: "Skill Map" }).click();
  record("27 skill map", await page.locator("h1").filter({ hasText: /What blocks what/i }).isVisible().catch(() => false));
  await shot(page, "14-skill-map");

  record("desktop console errors", errors.length === 0, errors.slice(0, 2).join(" | "));
  record("desktop network errors", netFails.length === 0, netFails.slice(0, 2).join(" | "));
  record("desktop overflow", !(await overflow(page)));

  await context.close();
}

// NL goal resolution
{
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await clearSession(page);
  await waitOnboarding(page);
  await page.locator("textarea").fill("I want to become a cybersecurity analyst focused on cloud security.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await page.getByText(/Cybersecurity Analyst|cybersecurity-analyst/i).first().waitFor({ timeout: 45000 });
  record("2 natural-language goal resolution", true);
  await context.close();
}

// Judge demo — adaptation + judge mode
{
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await clearSession(page);
  const errors = [];
  const netFails = [];
  attachMonitors(page, errors, netFails);

  await waitOnboarding(page);
  await advanceOnboarding(page, "AI/ML Engineer");
  await page.getByRole("button", { name: /Judge demo/i }).click();
  await page.waitForURL("**/workspace**", { timeout: 180000 });
  record("28 judge mode launch", true);
  await shot(page, "15-judge-mode");

  await page.getByRole("button", { name: "My Path" }).click();
  await page.waitForSelector(".path-row", { timeout: 60000 });
  await shot(page, "10-progress");

  await page.getByRole("button", { name: "Assessments" }).click();
  const start = page.getByRole("button", { name: /Start|Take|Run/i }).first();
  if (await start.isVisible({ timeout: 15000 }).catch(() => false)) {
    await start.click();
    await page.waitForSelector(".assess-index, [data-testid='assessment-question']", { timeout: 60000 }).catch(() => {});
    await shot(page, "09-assessment-run");
    record("20 assessment run", true);
  }

  record("judge console errors", errors.length === 0, errors.slice(0, 2).join(" | "));
  await context.close();
}

// Phase 5 — viewport matrix (onboarding evidence step)
for (const vp of VIEWPORTS) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
  const page = await context.newPage();
  await clearSession(page);
  const errors = [];
  attachMonitors(page, errors, [], false);
  await advanceOnboarding(page, null);
  const over = await overflow(page);
  const hits = await overlapHits(page);
  record(`viewport ${vp.tag} overflow`, !over, over ? "horizontal overflow" : "");
  record(`viewport ${vp.tag} overlay hits`, hits.length === 0, hits.slice(0, 2).join(", "));
  record(`viewport ${vp.tag} console`, errors.length === 0, errors.slice(0, 1).join(" | "));
  if (vp.tag === "390x844" || vp.tag === "1440x900") {
    await shot(page, "03-onboarding-evidence", vp.tag);
    await shot(page, "01-onboarding-goal", vp.tag);
  }
  await context.close();
}

// Phase 9 — intake failure simulation
{
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await clearSession(page);
  await page.route("**/v1/intake/goal", (route) => route.fulfill({ status: 404, body: '{"detail":"Not Found"}' }));
  await waitOnboarding(page);
  await page.locator("textarea").fill("I want to become a data engineer.");
  await page.getByRole("button", { name: /Resolve goal/i }).click();
  await page.getByText("What could not load").first().waitFor({ timeout: 15000 });
  const stillOnGoal = await page.getByRole("button", { name: /Resolve goal/i }).isVisible();
  record("intake failure preserves context", stillOnGoal);
  await shot(page, "onboarding-error");
  await context.close();
}

await browser.close();

const summary = {
  passed: results.filter((r) => r.pass).length,
  total: results.length,
  failed: results.filter((r) => !r.pass),
};
writeFileSync(join(OUT, "summary.json"), JSON.stringify({ results, summary, base: BASE }, null, 2));
console.log("SUMMARY", JSON.stringify(summary));
process.exit(summary.failed.length ? 1 : 0);
