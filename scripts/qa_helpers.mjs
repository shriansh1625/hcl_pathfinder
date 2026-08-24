/**
 * Shared Playwright navigation helpers for PathFinder QA scripts.
 */
export const BASE = process.env.PF_BASE_URL || "http://127.0.0.1:3002";

export function attachMonitors(page, log = { console: [], network: [] }) {
  page.on("console", (msg) => {
    if (msg.type() === "error") log.console.push(msg.text());
  });
  page.on("response", (resp) => {
    if (resp.status() >= 400 && !resp.url().includes("favicon")) {
      log.network.push(`${resp.status()} ${resp.url()}`);
    }
  });
  return log;
}

export async function clearSession(page) {
  await page.addInitScript(() => {
    sessionStorage.clear();
    localStorage.clear();
  });
}

export async function advanceToCareerStep(page, roleName = "Backend Developer") {
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /Build the path/i }).waitFor({ timeout: 30000 });
  const pickManual = page.getByRole("button", { name: /Pick career manually/i });
  if (await pickManual.isVisible().catch(() => false)) {
    await pickManual.click();
  }
  await page.locator(".career-requirements").first().waitFor({ timeout: 30000 });
  if (roleName) {
    await page.getByRole("button", { name: roleName }).click();
  }
}

export async function advanceToProfile(page, roleName = "Backend Developer") {
  await advanceToCareerStep(page, roleName);
  for (let i = 0; i < 4; i++) {
    await page.getByRole("button", { name: "Continue" }).click();
  }
  await page.getByRole("button", { name: "Review profile" }).click();
  await page.getByText(/Your path configuration/i).waitFor({ timeout: 15000 });
}

export async function buildPathToWorkspace(page, roleName = "Backend Developer") {
  await advanceToProfile(page, roleName);
  await page.getByRole("button", { name: /Build my path/i }).click();
  await page.waitForURL("**/workspace**", { timeout: 180000 });
  await page.locator("h1").first().waitFor({ timeout: 60000 });
}

export async function launchJudgeDemo(page, roleName = "AI/ML Engineer") {
  await advanceToProfile(page, roleName);
  await page.getByRole("button", { name: /Judge demo/i }).click();
  await page.waitForURL("**/workspace**", { timeout: 180000 });
  await page.getByTestId("judge-guide").waitFor({ timeout: 60000 });
}

export async function openPathTab(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("button", { name: "My Path" }).click();
  await page.waitForSelector(".path-row", { timeout: 60000 });
}

export async function openAssessments(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("button", { name: "Assessments" }).click();
  await page.getByRole("button", { name: /Prove this skill/i }).waitFor({ timeout: 60000 });
  await page.getByRole("button", { name: /Prove this skill/i }).click();
  await page.waitForSelector(".assess-index", { timeout: 60000 });
}

export async function answerAssessment(page) {
  for (let guard = 0; guard < 12; guard++) {
    await page.locator(".assess-answer").first().click();
    const submit = page.getByRole("button", { name: "Submit" });
    if (await submit.isVisible().catch(() => false)) {
      return submit;
    }
    await page.getByRole("button", { name: "Next" }).click();
  }
  return page.getByRole("button", { name: "Submit" });
}

export async function submitProgressStruggle(page, confidencePercent = 20) {
  const actions = page.locator("[data-testid='progress-actions']").first();
  await actions.scrollIntoViewIfNeeded();
  await actions.waitFor({ state: "visible", timeout: 30000 });
  await actions.getByRole("button", { name: "I struggled" }).click();
  await page.getByTestId("progress-confidence").waitFor({ timeout: 15000 });
  await page.locator(".progress-slider").evaluate((el, value) => {
    el.value = String(value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, confidencePercent);
  await page.getByRole("button", { name: "Submit progress" }).click();
}

export async function shot(page, dir, name, viewport = { width: 1440, height: 900 }) {
  await page.setViewportSize(viewport);
  await page.screenshot({ path: `${dir}/${name}`, fullPage: true });
}