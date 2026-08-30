/**
 * Goal intake hardening — browser verification for RESOLVED / AMBIGUOUS / UNSUPPORTED.
 * Usage: PF_BASE_URL=http://127.0.0.1:3002 node scripts/goal_intake_browser_qa.mjs
 */
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { BASE, attachMonitors, clearSession, launchBrowser } from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "goal-intake-qa");
mkdirSync(OUT, { recursive: true });

const CASES = [
  {
    goal: "I want to become a machine learning engineer focused on computer vision.",
    expect: "resolved",
    label: "Goal understood",
  },
  {
    goal: "I want to be a pen tester.",
    expect: "resolved",
    label: "Goal understood",
  },
  {
    goal: "I want to work in cloud security.",
    expect: "ambiguous",
    label: "Which route fits your goal?",
  },
  {
    goal: "I want to become an MLOps engineer.",
    expect: "resolved",
    label: "Goal understood",
  },
  {
    goal: "I want a career in data.",
    expect: "ambiguous",
    label: "Which route fits your goal?",
  },
  {
    goal: "I want to be a marine biologist.",
    expect: "unsupported",
    label: "Goal not mapped yet",
  },
  {
    goal: "quantum potato infrastructure architect",
    expect: "unsupported",
    label: "Goal not mapped yet",
  },
];

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

const results = [];

function record(name, pass, detail = "", meta = {}) {
  results.push({ name, pass, detail, ...meta });
  console.log(pass ? "PASS" : "FAIL", name, detail);
}

const browser = await launchBrowser();

for (const viewport of VIEWPORTS) {
  for (const testCase of CASES) {
    const page = await browser.newPage();
    const log = attachMonitors(page);
    const caseName = `${viewport.name}: ${testCase.goal.slice(0, 48)}`;
    try {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await clearSession(page);
      await page.goto(BASE, { waitUntil: "networkidle" });
      await page.locator("textarea").fill(testCase.goal);
      const resolveBtn = page.getByRole("button", { name: /Resolve goal/i });
      await resolveBtn.scrollIntoViewIfNeeded();
      await resolveBtn.click({ timeout: 45000 });
      await page.getByText(testCase.label).first().waitFor({ timeout: 20000 });

      let pass = false;
      if (testCase.expect === "resolved") {
        pass =
          (await page.getByText("Goal understood").isVisible()) &&
          (await page.getByRole("button", { name: /^Continue$/i }).isVisible());
      } else if (testCase.expect === "ambiguous") {
        pass =
          (await page.getByText("Which route fits your goal?").isVisible()) &&
          (await page.getByRole("button", { name: /Pick career manually/i }).isVisible());
      } else {
        pass =
          (await page.getByText("Goal not mapped yet").isVisible()) &&
          (await page.getByRole("button", { name: /See supported careers/i }).isVisible());
      }

      const stuck = await page.getByRole("button", { name: /^Resolving/i }).isVisible().catch(() => false);
      pass = pass && !stuck;

      record(caseName, pass, pass ? testCase.expect : "stuck or missing fallback", {
        expect: testCase.expect,
        console: log.console,
        network: log.network,
      });
    } catch (err) {
      record(caseName, false, String(err), { console: log.console, network: log.network });
    } finally {
      await page.close();
    }
  }
}

// Provider failure recovery — deterministic fallback still offers manual path
{
  const page = await browser.newPage();
  const log = attachMonitors(page);
  try {
    await page.route("**/v1/intake/goal", (route) => route.abort("failed"));
    await clearSession(page);
    await page.goto(BASE);
    await page.locator("textarea").fill("I want to be a penetration tester.");
    await page.getByRole("button", { name: /Resolve goal/i }).click();
    await page.getByText(/Goal interpretation did not complete/i).waitFor({ timeout: 15000 });
    const manual = await page.getByRole("button", { name: /Pick career manually/i }).isVisible();
    const preserved = (await page.locator("textarea").inputValue()) === "I want to be a penetration tester.";
    record("provider failure recovery", manual && preserved, manual ? "manual fallback visible" : "no fallback", log);
  } catch (err) {
    record("provider failure recovery", false, String(err), log);
  } finally {
    await page.unroute("**/v1/intake/goal");
    await page.close();
  }
}

await browser.close();

const passed = results.filter((r) => r.pass).length;
const summary = { passed, total: results.length, results, base: BASE, at: new Date().toISOString() };
writeFileSync(join(OUT, "summary.json"), JSON.stringify(summary, null, 2));
console.log(`\n${passed}/${results.length} passed`);
process.exit(passed === results.length ? 0 : 1);
