/**
 * Second-learner browser proof — same role, different evidence → different path.
 * Usage: cd .tmp-pw && PF_BASE_URL=http://127.0.0.1:3004 node ../scripts/second_learner_proof.mjs
 */
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  launchBrowser,
  clearSession,
  createLearnerWithPath,
  injectWorkspaceSession,
  openPathTab,
  pathSignature,
  topGapSkills,
  shot,
} from "./qa_helpers.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "artifacts", "second-learner-proof");
mkdirSync(OUT, { recursive: true });

const ROLE = "ai-ml-engineer";
const ROLE_NAME = "AI/ML Engineer";

const PROFILE_A = [
  { skill: "python", observed_level: 0.9 },
  { skill: "statistics", observed_level: 0.35 },
  { skill: "ml_fundamentals", observed_level: 0.55 },
  { skill: "supervised_learning", observed_level: 0.85 },
];

const PROFILE_B = [
  { skill: "python", observed_level: 0.45 },
  { skill: "statistics", observed_level: 0.9 },
  { skill: "ml_fundamentals", observed_level: 0.3 },
];

const browser = await launchBrowser();
const page = await browser.newPage();
const request = page.request;

const learnerA = await createLearnerWithPath(request, {
  role: ROLE,
  roleName: ROLE_NAME,
  evidence: PROFILE_A,
});
const learnerB = await createLearnerWithPath(request, {
  role: ROLE,
  roleName: ROLE_NAME,
  evidence: PROFILE_B,
});

const sigA = pathSignature(learnerA.path);
const sigB = pathSignature(learnerB.path);
const gapsA = topGapSkills(learnerA.gaps);
const gapsB = topGapSkills(learnerB.gaps);

async function captureLearner(label, learner, path, gaps, file) {
  await clearSession(page);
  await injectWorkspaceSession(page, {
    learnerId: learner.id,
    displayName: learner.display_name,
    role: ROLE,
    roleName: ROLE_NAME,
    weeklyHours: 8,
    learningStyle: "MIXED",
    v1PathId: path.id,
    view: "overview",
  });
  await openPathTab(page);
  await shot(page, OUT, file, { width: 1440, height: 900 });
  return {
    learnerId: learner.id,
    pathSignature: pathSignature(path),
    topGaps: gaps,
    resources: (path.items ?? [])
      .filter((item) => item.kind === "EXECUTABLE")
      .slice(0, 5)
      .map((item) => item.resource || item.title),
  };
}

const captureA = await captureLearner("A", learnerA.learner, learnerA.path, gapsA, "learner-a.png");
const captureB = await captureLearner("B", learnerB.learner, learnerB.path, gapsB, "learner-b.png");

await browser.close();

const sameRole = ROLE === ROLE;
const differentEvidence = JSON.stringify(PROFILE_A) !== JSON.stringify(PROFILE_B);
const differentGaps = JSON.stringify(gapsA) !== JSON.stringify(gapsB);
const differentPath = sigA !== sigB;

const proof = {
  pass: sameRole && differentEvidence && differentGaps && differentPath,
  same_role: sameRole,
  different_evidence: differentEvidence,
  different_path: differentPath,
  different_gaps: differentGaps,
  path_signature_a: sigA,
  path_signature_b: sigB,
  top_gaps_a: gapsA,
  top_gaps_b: gapsB,
  learner_a: captureA,
  learner_b: captureB,
};

writeFileSync(join(OUT, "proof.json"), JSON.stringify(proof, null, 2));
console.log(JSON.stringify(proof, null, 2));
process.exit(proof.pass ? 0 : 1);
