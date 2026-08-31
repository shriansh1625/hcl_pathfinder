/**
 * Shared Playwright navigation helpers for PathFinder QA scripts.
 */
export const BASE = process.env.PF_BASE_URL || "http://127.0.0.1:3002";
export const API = process.env.PF_API_URL || "http://127.0.0.1:8000";
const SESSION_KEY = "pathfinder.session.v1";

import { fileURLToPath, pathToFileURL } from "url";
import { dirname, join } from "path";

const __helpersDir = dirname(fileURLToPath(import.meta.url));

export async function launchBrowser() {
  const candidates = [
    "playwright",
    join(__helpersDir, "..", ".tmp-pw", "node_modules", "playwright", "index.mjs"),
    join(__helpersDir, "..", ".tmp-pw", "node_modules", "playwright", "index.js"),
  ];
  let chromium;
  for (const target of candidates) {
    try {
      const spec = target.startsWith(".") || target.includes("\\") || target.includes("/")
        ? pathToFileURL(target).href
        : target;
      ({ chromium } = await import(spec));
      break;
    } catch {
      /* try next */
    }
  }
  if (!chromium) throw new Error("playwright is not installed (.tmp-pw npm install)");
  for (const channel of ["msedge", "chrome"]) {
    try {
      return await chromium.launch({ headless: true, channel });
    } catch {
      /* try next */
    }
  }
  return chromium.launch({ headless: true });
}

export function attachMonitors(page, log = { console: [], network: [] }) {
  page.on("console", (msg) => {
    if (msg.type() === "error") log.console.push(msg.text());
  });
  page.on("response", (resp) => {
    if (resp.status() >= 400 && !resp.url().includes("favicon") && !resp.url().includes("icon.svg")) {
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

export function primaryNav(page) {
  return page.getByLabel("Primary");
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
    await page.locator(".career-card-active").waitFor({ timeout: 10000 });
  }
}

export async function advanceToEvidenceStep(page, roleName = "Backend Developer", withDemoEvidence = true) {
  await advanceToCareerStep(page, roleName);
  for (let i = 0; i < 4; i++) {
    await page.getByRole("button", { name: "Continue" }).click();
  }
  await page.getByText(/Your starting evidence/i).waitFor({ timeout: 15000 });
  const toggle = page.locator(".evidence-toggle input[type='checkbox']");
  if (await toggle.isVisible().catch(() => false)) {
    const checked = await toggle.isChecked();
    if (checked !== withDemoEvidence) {
      await toggle.click();
    }
  }
  await page.getByRole("button", { name: "Review profile" }).click();
  await page.getByText(/Ready to build your path/i).waitFor({ timeout: 15000 });
}

export async function advanceToProfile(page, roleName = "Backend Developer") {
  await advanceToEvidenceStep(page, roleName, true);
}

export async function buildPathToWorkspace(page, roleName = "Backend Developer") {
  await advanceToProfile(page, roleName);
  await page.getByRole("button", { name: /Build my path/i }).click();
  await page.waitForURL("**/workspace**", { timeout: 180000 });
  await page.locator("h1").first().waitFor({ timeout: 60000 });
}

export async function buildPathWithoutEvidence(page, roleName = "Backend Developer") {
  await advanceToEvidenceStep(page, roleName, false);
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
  await primaryNav(page).getByRole("button", { name: "My Path" }).click();
  await page.getByTestId("path-canvas").waitFor({ timeout: 60000 });
  await page.waitForSelector(".path-row", { timeout: 60000 });
}

export async function openAssessments(page) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await primaryNav(page).getByRole("button", { name: "Skill Checks" }).click();
  await page.getByRole("button", { name: /Prove this skill/i }).waitFor({ timeout: 60000 });
  await page.getByRole("button", { name: /Prove this skill/i }).click();
  await page.waitForSelector(".assess-index", { timeout: 60000 });
}

export async function answerAssessment(page) {
  for (let guard = 0; guard < 12; guard++) {
    await page.locator(".assess-answer").first().click();
    const action = page.getByTestId("assessment-submit");
    const label = ((await action.innerText().catch(() => "")) || "").trim();
    if (label === "Submit") {
      return action;
    }
    await action.click();
  }
  return page.getByTestId("assessment-submit");
}

export async function submitAssessmentAndWaitForResult(page, timeoutMs = 180000) {
  const submit = await answerAssessment(page);
  await submit.click();
  await page.getByText(/Updating your competency model/i).waitFor({ timeout: 15000 }).catch(() => undefined);
  await page.getByTestId("result-hero").waitFor({ timeout: timeoutMs });
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

async function apiJson(request, path, init = {}) {
  const response = await request.fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (!response.ok()) {
    const text = await response.text();
    throw new Error(`${response.status()} ${path}: ${text}`);
  }
  if (response.status() === 204) return null;
  return response.json();
}

export async function createLearnerWithPath(request, {
  role = "ai-ml-engineer",
  roleName = "AI/ML Engineer",
  evidence = [],
  weeklyHours = 8,
  learningStyle = "MIXED",
}) {
  const learner = await apiJson(request, "/v1/learners", {
    method: "POST",
    data: {
      display_name: `proof-${globalThis.crypto?.randomUUID?.().slice(0, 8) ?? Date.now()}`,
      experience_level: "INTERMEDIATE",
      weekly_hours: weeklyHours,
      learning_style: learningStyle,
      interests: ["ml"],
      goal_text: `Become a ${roleName}`,
      target_role: role,
    },
  });
  for (const row of evidence) {
    await apiJson(request, `/v1/learners/${learner.id}/evidence`, {
      method: "POST",
      data: {
        skill: row.skill,
        source: row.source ?? "ASSESSMENT",
        observed_level: row.observed_level,
        confidence: row.confidence ?? 0.85,
      },
    });
  }
  const path = await apiJson(request, `/v1/learners/${learner.id}/paths`, {
    method: "POST",
    data: { role, weekly_hours: weeklyHours, learning_style: learningStyle },
  });
  const gaps = await apiJson(request, `/v1/learners/${learner.id}/roles/${role}/gaps`);
  return { learner, path, gaps, roleName };
}

export async function injectWorkspaceSession(page, snapshot) {
  await page.addInitScript(
    ([key, snap]) => {
      sessionStorage.setItem(key, JSON.stringify(snap));
    },
    [SESSION_KEY, snapshot],
  );
  await page.goto(`${BASE}/workspace`, { waitUntil: "domcontentloaded" });
  await page.locator("h1").first().waitFor({ timeout: 60000 });
}

export function pathSignature(path) {
  return (path.items ?? [])
    .filter((item) => item.kind === "EXECUTABLE")
    .slice(0, 12)
    .map((item) => `${item.position}:${item.resource || item.title}:${item.target_skill}`)
    .join("|");
}

export function topGapSkills(gaps, limit = 5) {
  return (gaps.items ?? gaps ?? [])
    .filter((item) => item.gap_status !== "MET" && item.attainment !== "TARGET_MET")
    .slice(0, limit)
    .map((item) => item.skill);
}
