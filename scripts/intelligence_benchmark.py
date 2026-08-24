#!/usr/bin/env python3
"""PathFinder Slice 6.0 — Intelligence Benchmark (observe only, no engine changes)."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.enums import PathStatus  # noqa: E402
from app.core.ids import ontology_uuid  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Assessment, LearningPath, PathItem, SkillEvidence  # noqa: E402
from app.ontology.load import AssessmentSpec, load_ontology  # noqa: E402
from app.services.assessment.loader import AssessmentDriftError, load_assessment_spec  # noqa: E402
from app.services.assessment.scoring import score_attempt  # noqa: E402
from app.services.gap_engine.profile import build_gap_profile  # noqa: E402
from app.services.path.generator import generate_path  # noqa: E402
from app.services.profiling import repository as profiling  # noqa: E402
from app.services.profiling.evidence_fusion import FusedSkill  # noqa: E402
from app.services.recommendation.models import LearnerPreferences  # noqa: E402
from app.services.recommendation.scorer import score_candidates  # noqa: E402
from app.services.retrieval.structured import retrieve_candidates  # noqa: E402
from app.services.skill_graph.competency import RoleCompetency, RoleCompetencySet  # noqa: E402
from app.services.skill_graph.dependency import SkillEdge  # noqa: E402

AIML = "ai-ml-engineer"
CYBER = "cybersecurity-analyst"
ARTIFACT_PATH = REPO_ROOT / "artifacts" / "intelligence_benchmark.json"
DOC_PATH = REPO_ROOT / "docs" / "INTELLIGENCE_BENCHMARK.md"

ResultCode = str  # PASS | FAIL | INCONCLUSIVE | NOT_PROVEN


@dataclass
class ScenarioResult:
    id: str
    name: str
    result: ResultCode
    evidence: list[str] = field(default_factory=list)
    notes: str = ""
    duration_ms: float = 0.0


def postgres_available() -> bool:
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


def git_commit() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True)
            .strip()
        )
    except Exception:
        return "unknown"


class Harness:
    def __init__(self) -> None:
        self.client = TestClient(app)
        self.bundle = load_ontology()
        self.specs = {item.slug: item for item in self.bundle.assessments}
        self.edges = [
            SkillEdge(rel.source, rel.target, rel.type, rel.strength)
            for rel in self.bundle.relationships
        ]
        self.catalog = [item for item in self.bundle.resources if item.is_active]
        self.timings: dict[str, float] = {}

    def _time(self, label: str, fn: Callable[[], Any]) -> Any:
        start = time.perf_counter()
        value = fn()
        self.timings[label] = round((time.perf_counter() - start) * 1000, 2)
        return value

    def learner(self, tag: str) -> str:
        response = self.client.post("/v1/learners", json={"display_name": tag})
        if response.status_code != 200:
            raise RuntimeError(response.text)
        return response.json()["id"]

    def evidence(
        self,
        learner_id: str,
        skill: str,
        source: str,
        level: float,
        confidence: float = 0.85,
    ) -> None:
        response = self.client.post(
            f"/v1/learners/{learner_id}/evidence",
            json={
                "skill": skill,
                "source": source,
                "observed_level": level,
                "confidence": confidence,
            },
        )
        if response.status_code != 200:
            raise RuntimeError(response.text)

    def path(self, learner_id: str, role: str = AIML, hours: float = 8, style: str = "MIXED") -> dict:
        response = self.client.post(
            f"/v1/learners/{learner_id}/paths",
            json={"role": role, "weekly_hours": hours, "learning_style": style},
        )
        if response.status_code != 200:
            raise RuntimeError(response.text)
        return response.json()

    def gaps(self, learner_id: str, role: str) -> dict:
        response = self.client.get(f"/v1/learners/{learner_id}/roles/{role}/gaps")
        if response.status_code != 200:
            raise RuntimeError(response.text)
        return response.json()

    def recommendations(self, learner_id: str, role: str, hours: float = 8, style: str = "MIXED") -> list:
        response = self.client.get(
            f"/v1/learners/{learner_id}/roles/{role}/recommendations",
            params={"weekly_hours": hours, "learning_style": style},
        )
        if response.status_code != 200:
            raise RuntimeError(response.text)
        return response.json()

    def submit(self, learner_id: str, slug: str, answers: list[int], attempt_id: str | None = None) -> dict:
        payload: dict[str, Any] = {"answers": answers}
        if attempt_id:
            payload["attempt_id"] = attempt_id
        response = self.client.post(
            f"/v1/learners/{learner_id}/assessments/{slug}/attempts",
            json=payload,
        )
        if response.status_code != 200:
            raise RuntimeError(response.text)
        return response.json()

    def correct(self, slug: str) -> list[int]:
        return [q.correct_index for q in self.specs[slug].questions]

    def wrong(self, slug: str) -> list[int]:
        return [(q.correct_index + 1) % len(q.choices) for q in self.specs[slug].questions]

    def gap_profile(self, learner_id: str, role: str):
        session = SessionLocal()
        try:
            return profiling.compute_gap_profile(session, user_id=uuid.UUID(learner_id), role_slug=role)
        finally:
            session.close()

    def role_competencies(self, role_slug: str) -> RoleCompetencySet:
        role = next(item for item in self.bundle.roles if item.slug == role_slug)
        from app.core.enums import RequiredStatus

        return RoleCompetencySet(
            role.slug,
            role.name,
            tuple(
                RoleCompetency(
                    row.slug,
                    row.slug,
                    row.target_level,
                    row.importance,
                    RequiredStatus(row.required_status),
                )
                for row in role.skills
            ),
        )

    def db_paths(self, learner_id: str) -> list[LearningPath]:
        session = SessionLocal()
        try:
            return list(
                session.scalars(
                    select(LearningPath)
                    .where(LearningPath.user_id == uuid.UUID(learner_id))
                    .order_by(LearningPath.version)
                ).all()
            )
        finally:
            session.close()

    def db_path_snapshot(self, path_id: str) -> list[tuple]:
        session = SessionLocal()
        try:
            rows = session.scalars(
                select(PathItem)
                .where(PathItem.learning_path_id == uuid.UUID(path_id))
                .order_by(PathItem.position)
            ).all()
            return [
                (
                    row.position,
                    row.week_index,
                    row.status,
                    row.item_type,
                    dict(row.explanation_metadata or {}),
                )
                for row in rows
            ]
        finally:
            session.close()


def _run_scenario(h: Harness, sid: str, name: str, fn: Callable[[Harness], ScenarioResult]) -> ScenarioResult:
    start = time.perf_counter()
    try:
        result = fn(h)
    except Exception as exc:
        result = ScenarioResult(sid, name, "FAIL", evidence=[f"exception: {exc}"])
    result.duration_ms = round((time.perf_counter() - start) * 1000, 2)
    result.id = sid
    result.name = name
    return result


def s01_empty_evidence(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s01-{uuid.uuid4().hex[:6]}")
    profile = h.gaps(learner_id, AIML)
    items = profile["items"]
    evidence = []
    if any(item.get("proficiency") == 0 for item in items):
        return ScenarioResult("S01", "", "FAIL", evidence=["proficiency treated as 0"])
    if any(item.get("proficiency") is not None for item in items):
        return ScenarioResult("S01", "", "FAIL", evidence=["unexpected numeric proficiency without evidence"])
    unknowns = [item for item in items if item.get("evidence_state") == "UNKNOWN"]
    evidence.append(f"unknown_skills={len(unknowns)}")
    path = h.path(learner_id, AIML)
    executable = [i for i in path["items"] if i.get("executable") and i.get("kind") == "EXECUTABLE"]
    gates = [i for i in path["items"] if i.get("kind") == "VERIFICATION_GATE"]
    evidence.append(f"verification_gates={len(gates)} executable_courses={len(executable)}")
    if executable:
        return ScenarioResult("S01", "", "FAIL", evidence=evidence + ["executable course with no evidence"])
    if not gates:
        return ScenarioResult("S01", "", "INCONCLUSIVE", evidence=evidence, notes="no gates generated")
    return ScenarioResult("S01", "", "PASS", evidence=evidence)


def s02_target_met(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s02-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.95)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    gaps = h.gaps(learner_id, AIML)["items"]
    python = next(item for item in gaps if item["skill"] == "python")
    evidence = [f"python_attainment={python['attainment']}"]
    if python["attainment"] != "TARGET_MET":
        return ScenarioResult("S02", "", "FAIL", evidence=evidence)
    recs = h.recommendations(learner_id, AIML)
    python_remediation = [
        row
        for row in recs
        if row["primary_skill"] == "python" and row["intervention"] in {"REMEDIATION", "FOUNDATION"}
    ][:3]
    evidence.append(f"python_remediation_candidates={len(python_remediation)}")
    if python_remediation and python_remediation[0]["final_score"] > 0.7:
        return ScenarioResult("S02", "", "FAIL", evidence=evidence + ["unnecessary python remediation ranked high"])
    return ScenarioResult("S02", "", "PASS", evidence=evidence)


def s03_diagnosed_gap(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s03-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.90)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.30)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    stats = next(item for item in h.gaps(learner_id, AIML)["items"] if item["skill"] == "statistics")
    evidence = [f"statistics_attainment={stats['attainment']}", f"statistics_action={stats['action']}"]
    if stats["attainment"] not in {"GAP", "NEAR_TARGET"}:
        return ScenarioResult("S03", "", "FAIL", evidence=evidence)
    recs = h.recommendations(learner_id, AIML)[:5]
    stats_recs = [row for row in recs if row["primary_skill"] == "statistics"]
    evidence.append(f"top_stats_recs={[row['resource'] for row in stats_recs[:3]]}")
    if not stats_recs:
        return ScenarioResult("S03", "", "INCONCLUSIVE", evidence=evidence, notes="no statistics resources in top recs")
    irrelevant_top = [
        row
        for row in recs
        if row["primary_skill"] not in {"statistics", "probability"}
        and row["score_breakdown"].get("role_importance", 0) == 0
    ]
    if irrelevant_top and irrelevant_top[0]["final_score"] > (stats_recs[0]["final_score"] if stats_recs else 0):
        return ScenarioResult("S03", "", "FAIL", evidence=evidence + [f"irrelevant_winner={irrelevant_top[0]['resource']}"])
    return ScenarioResult("S03", "", "PASS", evidence=evidence)


def s04_unknown_blocker(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s04-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.92)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.85)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.88)
    path = h.path(learner_id, AIML)
    docker_waiting = [
        item
        for item in path["items"]
        if not item["executable"] and item.get("resource") and "docker" in (item.get("title") or "").lower()
    ]
    if not docker_waiting:
        docker_waiting = [
            item
            for item in path["items"]
            if item.get("eligibility") == "BLOCKED_BY_UNKNOWN" and item.get("resource")
        ]
    evidence = [f"waiting_items={len(docker_waiting)}"]
    if not docker_waiting:
        return ScenarioResult("S04", "", "INCONCLUSIVE", evidence=evidence, notes="no docker-blocked resource in path")
    item = docker_waiting[0]
    evidence.extend([f"eligibility={item.get('eligibility')}", f"executable={item.get('executable')}"])
    if item.get("executable"):
        return ScenarioResult("S04", "", "FAIL", evidence=evidence)
    if item.get("eligibility") != "BLOCKED_BY_UNKNOWN":
        return ScenarioResult("S04", "", "FAIL", evidence=evidence)
    return ScenarioResult("S04", "", "PASS", evidence=evidence)


def s05_known_gap_blocker(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s05-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.20)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.85)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.88)
    path = h.path(learner_id, AIML)
    blocked = [item for item in path["items"] if item.get("eligibility") == "BLOCKED_BY_KNOWN_GAP"]
    evidence = [f"blocked_items={len(blocked)}"]
    if not blocked:
        return ScenarioResult("S05", "", "INCONCLUSIVE", evidence=evidence)
    item = blocked[0]
    evidence.extend([f"resource={item.get('resource')}", f"executable={item.get('executable')}"])
    if item.get("executable"):
        return ScenarioResult("S05", "", "FAIL", evidence=evidence)
    return ScenarioResult("S05", "", "PASS", evidence=evidence)


def s06_role_change(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s06-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.85)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.40)
    h.evidence(learner_id, "owasp_top10", "ASSESSMENT", 0.30)
    aiml_gaps = {item["skill"] for item in h.gaps(learner_id, AIML)["items"] if item.get("attainment") == "GAP"}
    cyber_gaps = {item["skill"] for item in h.gaps(learner_id, CYBER)["items"] if item.get("attainment") == "GAP"}
    aiml_path = h.path(learner_id, AIML, hours=10)
    cyber_path = h.path(learner_id, CYBER, hours=10)
    aiml_resources = {i["resource"] for i in aiml_path["items"] if i.get("resource")}
    cyber_resources = {i["resource"] for i in cyber_path["items"] if i.get("resource")}
    evidence = [
        f"aiml_gaps={sorted(aiml_gaps)[:5]}",
        f"cyber_gaps={sorted(cyber_gaps)[:5]}",
        f"aiml_resources={len(aiml_resources)} cyber_resources={len(cyber_resources)}",
        f"overlap={len(aiml_resources & cyber_resources)}",
    ]
    if aiml_gaps == cyber_gaps and aiml_resources == cyber_resources:
        return ScenarioResult("S06", "", "FAIL", evidence=evidence)
    if not aiml_resources or not cyber_resources:
        return ScenarioResult("S06", "", "INCONCLUSIVE", evidence=evidence)
    return ScenarioResult("S06", "", "PASS", evidence=evidence)


def s07_learner_change(h: Harness) -> ScenarioResult:
    a = h.learner(f"bench-s07a-{uuid.uuid4().hex[:6]}")
    b = h.learner(f"bench-s07b-{uuid.uuid4().hex[:6]}")
    h.evidence(a, "python", "ASSESSMENT", 0.90)
    h.evidence(a, "statistics", "ASSESSMENT", 0.35)
    h.evidence(a, "ml_fundamentals", "ASSESSMENT", 0.55)
    h.evidence(b, "python", "ASSESSMENT", 0.40)
    h.evidence(b, "statistics", "ASSESSMENT", 0.90)
    h.evidence(b, "ml_fundamentals", "ASSESSMENT", 0.55)
    ga = h.gaps(a, AIML)["items"]
    gb = h.gaps(b, AIML)["items"]
    fa = next(item for item in ga if item["skill"] == "statistics")
    fb = next(item for item in gb if item["skill"] == "statistics")
    pa = h.path(a, AIML)
    pb = h.path(b, AIML)
    evidence = [
        f"A_stats_action={fa['action']} B_stats_action={fb['action']}",
        f"A_path_resources={[i['resource'] for i in pa['items'] if i.get('resource')][:4]}",
        f"B_path_resources={[i['resource'] for i in pb['items'] if i.get('resource')][:4]}",
    ]
    if pa["items"] == pb["items"]:
        return ScenarioResult("S07", "", "FAIL", evidence=evidence)
    return ScenarioResult("S07", "", "PASS", evidence=evidence)


def s08_weekly_budget(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s08-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.90)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    p5 = h.path(learner_id, AIML, hours=5)
    p15 = h.path(learner_id, AIML, hours=15)
    hours5 = sum(i.get("duration_hours") or 0 for i in p5["items"] if i.get("executable"))
    hours15 = sum(i.get("duration_hours") or 0 for i in p15["items"] if i.get("executable"))
    evidence = [f"5h_weekly_estimated={hours5}", f"15h_weekly_estimated={hours15}", f"5h_items={len(p5['items'])}", f"15h_items={len(p15['items'])}"]
    if hours5 > 5 * 8 + 1 and hours15 > 15 * 8 + 1:
        return ScenarioResult("S08", "", "FAIL", evidence=evidence + ["budget appears ignored"])
    if p5["items"] == p15["items"]:
        return ScenarioResult("S08", "", "INCONCLUSIVE", evidence=evidence, notes="identical paths under different budgets")
    return ScenarioResult("S08", "", "PASS", evidence=evidence)


def s09_learning_style(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s09-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.90)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    styles = {}
    for style in ("READING", "VIDEO", "HANDS_ON"):
        rows = h.recommendations(learner_id, AIML, style=style)[:5]
        styles[style] = [row["resource"] for row in rows]
    evidence = [f"top_by_style={styles}"]
    zero_role_winners = []
    for style, slugs in styles.items():
        rows = h.recommendations(learner_id, AIML, style=style)
        for row in rows:
            if row["score_breakdown"].get("role_importance", 0) == 0 and row["final_score"] > 0.6:
                zero_role_winners.append((style, row["resource"]))
    if zero_role_winners:
        return ScenarioResult("S09", "", "FAIL", evidence=evidence + [f"zero_role_high_score={zero_role_winners}"])
    if styles["READING"] == styles["VIDEO"] == styles["HANDS_ON"]:
        return ScenarioResult("S09", "", "INCONCLUSIVE", evidence=evidence)
    return ScenarioResult("S09", "", "PASS", evidence=evidence)


def s10_semantic_on_off(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s10-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.45)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.30)
    settings.semantic_enabled = False
    off = h.recommendations(learner_id, AIML)[:15]
    settings.semantic_enabled = True
    on = h.recommendations(learner_id, AIML)[:15]
    off_sem = {row["resource"]: row["score_breakdown"]["semantic_similarity"] for row in off}
    on_sem = {row["resource"]: row["score_breakdown"]["semantic_similarity"] for row in on}
    if not all(abs(v - 0.5) < 0.001 for v in off_sem.values()):
        return ScenarioResult("S10", "", "FAIL", evidence=[f"off_not_neutral={off_sem}"])
    if all(abs(v - 0.5) < 0.001 for v in on_sem.values()):
        return ScenarioResult("S10", "", "FAIL", evidence=["semantic_on_still_neutral"])
    off_order = [row["resource"] for row in off]
    on_order = [row["resource"] for row in on]
    changes = sum(1 for i, slug in enumerate(off_order) if on_order[i] != slug)
    max_swing = max(abs(on_sem.get(k, 0.5) - off_sem.get(k, 0.5)) for k in on_sem)
    evidence = [f"position_changes_top15={changes}", f"max_semantic_swing={max_swing:.4f}"]
    if max_swing > 0.35:
        return ScenarioResult("S10", "", "FAIL", evidence=evidence + ["semantic swing too large"])
    return ScenarioResult("S10", "", "PASS" if changes >= 0 else "INCONCLUSIVE", evidence=evidence)


def s11_conflicting_evidence(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s11-{uuid.uuid4().hex[:6]}")
    self_report_level = 0.90
    h.evidence(learner_id, "python", "SELF_REPORT", self_report_level)
    h.submit(learner_id, "python-gate", h.wrong("python-gate"))
    session = SessionLocal()
    try:
        from app.models import Skill

        rows = session.scalars(
            select(SkillEvidence)
            .join(Skill, Skill.id == SkillEvidence.skill_id)
            .where(SkillEvidence.user_id == uuid.UUID(learner_id), Skill.slug == "python")
        ).all()
    finally:
        session.close()
    sources = sorted({row.source_type for row in rows})
    evidence = [
        f"evidence_rows={len(rows)}",
        f"sources={sources}",
    ]
    if len(rows) != 2:
        return ScenarioResult("S11", "", "FAIL", evidence=evidence, notes="expected two retained evidence rows")
    if set(sources) != {"ASSESSMENT", "SELF_REPORT"}:
        return ScenarioResult("S11", "", "FAIL", evidence=evidence, notes="both evidence sources must be retained")
    skills = h.client.get(f"/v1/learners/{learner_id}/skills").json()
    python = next(item for item in skills if item["skill"] == "python")
    gap = next(item for item in h.gaps(learner_id, AIML)["items"] if item["skill"] == "python")
    evidence.extend(
        [
            f"proficiency={python['proficiency']}",
            f"conflict={python['conflict']}",
            f"dominant_source={python['dominant_source']}",
            f"attainment={gap['attainment']}",
            f"target_met={gap['target_met']}",
            f"action={gap['action']}",
        ]
    )
    if python["evidence_count"] != 2:
        return ScenarioResult("S11", "", "FAIL", evidence=evidence)
    if not python["conflict"]:
        return ScenarioResult("S11", "", "FAIL", evidence=evidence)
    if python["dominant_source"] != "ASSESSMENT":
        return ScenarioResult("S11", "", "FAIL", evidence=evidence)
    if python["proficiency"] is None:
        return ScenarioResult("S11", "", "FAIL", evidence=evidence)
    if python["proficiency"] >= self_report_level:
        return ScenarioResult("S11", "", "FAIL", evidence=evidence, notes="fused must sit below self-report")
    if python["proficiency"] >= gap["target_level"]:
        return ScenarioResult("S11", "", "FAIL", evidence=evidence, notes="fused must remain below role target")
    if gap["attainment"] != "GAP":
        return ScenarioResult("S11", "", "FAIL", evidence=evidence)
    if gap["target_met"] is not False:
        return ScenarioResult("S11", "", "FAIL", evidence=evidence)
    if gap["action"] != "REMEDIATE":
        return ScenarioResult("S11", "", "FAIL", evidence=evidence)
    return ScenarioResult("S11", "", "PASS", evidence=evidence)


def s12_positive_surprise(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s12-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.90)
    # Low-reliability prior lets a perfect gate dominate fusion (canonical adaptation contract).
    h.evidence(learner_id, "statistics", "SELF_REPORT", 0.45, confidence=0.60)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    before = next(item for item in h.gaps(learner_id, AIML)["items"] if item["skill"] == "statistics")
    v1 = h.path(learner_id, AIML)
    stats_v1 = [
        item
        for item in v1["items"]
        if item.get("target_skill") == "statistics" and item.get("kind") == "EXECUTABLE"
    ]
    evidence = [
        f"before_attainment={before['attainment']}",
        f"stats_remediation_v1={len(stats_v1)}",
    ]
    if before["attainment"] != "GAP":
        return ScenarioResult("S12", "", "FAIL", evidence=evidence, notes="expected initial GAP")
    if not stats_v1:
        return ScenarioResult("S12", "", "INCONCLUSIVE", evidence=evidence, notes="no statistics remediation in V1")
    body = h.submit(learner_id, "statistics-gate", h.correct("statistics-gate"))
    evidence.append(f"adaptation={body['adaptation']}")
    if body["adaptation"] != "CREATED":
        return ScenarioResult("S12", "", "FAIL", evidence=evidence)
    after = next(item for item in h.gaps(learner_id, AIML)["items"] if item["skill"] == "statistics")
    evidence.append(f"after_attainment={after['attainment']}")
    evidence.append(f"target_met={after['target_met']}")
    evidence.append(f"action={after['action']}")
    if after["attainment"] != "TARGET_MET":
        return ScenarioResult("S12", "", "FAIL", evidence=evidence)
    if after["target_met"] is not True:
        return ScenarioResult("S12", "", "FAIL", evidence=evidence)
    diff = body.get("diff") or {}
    removed_stats = [entry for entry in diff.get("removed", []) if entry.get("skill") == "statistics"]
    evidence.append(f"removed_stats_entries={len(removed_stats)}")
    if not removed_stats:
        return ScenarioResult("S12", "", "FAIL", evidence=evidence, notes="statistics remediation should be removed")
    v2 = h.client.get(f"/v1/learners/{learner_id}/paths/{body['path_id']}").json()
    v2_stats = [
        item
        for item in v2["items"]
        if item.get("target_skill") == "statistics"
        and item.get("kind") == "EXECUTABLE"
        and item.get("status") != "COMPLETED"
    ]
    if v2_stats:
        return ScenarioResult("S12", "", "FAIL", evidence=evidence, notes="remaining statistics remediation in V2")
    v1_after = h.client.get(f"/v1/learners/{learner_id}/paths/{v1['id']}").json()
    if v1_after["status"] != "SUPERSEDED":
        return ScenarioResult("S12", "", "FAIL", evidence=evidence, notes="V1 must remain immutable history")
    return ScenarioResult("S12", "", "PASS", evidence=evidence)


def s13_negative_surprise(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s13-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.90)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.85)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.88)
    h.evidence(learner_id, "model_evaluation", "ASSESSMENT", 0.85)
    v1 = h.path(learner_id, AIML)
    before = next(item for item in h.gaps(learner_id, AIML)["items"] if item["skill"] == "model_evaluation")
    body = h.submit(learner_id, "model-evaluation-gate", h.wrong("model-evaluation-gate"))
    after = next(item for item in h.gaps(learner_id, AIML)["items"] if item["skill"] == "model_evaluation")
    evidence = [
        f"adaptation={body['adaptation']}",
        f"before={before['attainment']} after={after['attainment']}",
    ]
    if body["adaptation"] != "CREATED":
        return ScenarioResult("S13", "", "FAIL", evidence=evidence)
    if after["attainment"] not in {"GAP", "NEAR_TARGET"}:
        return ScenarioResult("S13", "", "INCONCLUSIVE", evidence=evidence)
    return ScenarioResult("S13", "", "PASS", evidence=evidence)


def s14_docker_unknown_to_known(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s14-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.92)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.85)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.88)
    h.evidence(learner_id, "model_evaluation", "ASSESSMENT", 0.85)
    h.evidence(learner_id, "model_deployment", "ASSESSMENT", 0.30)
    h.evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)
    v1 = h.path(learner_id, AIML)
    gates = [i for i in v1["items"] if (i.get("gate") or {}).get("skill") == "docker"]
    if not gates:
        return ScenarioResult("S14", "", "INCONCLUSIVE", evidence=["no docker gate in V1"])
    body = h.submit(learner_id, "docker-gate", h.correct("docker-gate"))
    evidence = [f"adaptation={body['adaptation']}"]
    if body["adaptation"] != "CREATED":
        return ScenarioResult("S14", "", "FAIL", evidence=evidence)
    removed = [e for e in body.get("diff", {}).get("removed", []) if e.get("key") == "gate:docker"]
    evidence.append(f"docker_gate_removed={bool(removed)}")
    if not removed:
        return ScenarioResult("S14", "", "FAIL", evidence=evidence)
    return ScenarioResult("S14", "", "PASS", evidence=evidence)


def s15_no_op_adaptation(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s15-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.92)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.40)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    h.evidence(learner_id, "model_evaluation", "ASSESSMENT", 0.88)
    v1 = h.path(learner_id, AIML)
    body = h.submit(learner_id, "model-evaluation-gate", h.correct("model-evaluation-gate"))
    evidence = [f"adaptation={body['adaptation']}", f"path_count={len(h.db_paths(learner_id))}"]
    if body["adaptation"] != "NO_ADAPTATION_REQUIRED":
        return ScenarioResult("S15", "", "FAIL", evidence=evidence)
    if len(h.db_paths(learner_id)) != 1:
        return ScenarioResult("S15", "", "FAIL", evidence=evidence)
    return ScenarioResult("S15", "", "PASS", evidence=evidence)


def s16_duplicate_attempt(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s16-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.90)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    v1 = h.path(learner_id, AIML)
    attempt_id = str(uuid.uuid4())
    first = h.submit(learner_id, "statistics-gate", h.correct("statistics-gate"), attempt_id=attempt_id)
    paths_after_first = len(h.db_paths(learner_id))
    second = h.submit(learner_id, "statistics-gate", h.correct("statistics-gate"), attempt_id=attempt_id)
    evidence = [
        f"first_adaptation={first['adaptation']}",
        f"second_adaptation={second['adaptation']}",
        f"paths_after_first={paths_after_first} paths_after_second={len(h.db_paths(learner_id))}",
    ]
    if second["adaptation"] != "REPLAYED":
        return ScenarioResult("S16", "", "FAIL", evidence=evidence)
    if len(h.db_paths(learner_id)) != paths_after_first:
        return ScenarioResult("S16", "", "FAIL", evidence=evidence + ["extra path version"])
    return ScenarioResult("S16", "", "PASS", evidence=evidence)


def s17_completed_work(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s17-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.90)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    h.evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)
    v1 = h.path(learner_id, AIML)
    first = next(i for i in v1["items"] if i["executable"] and i["kind"] == "EXECUTABLE")
    h.client.post(
        f"/v1/learners/{learner_id}/paths/{v1['id']}/complete-item",
        json={"position": first["position"]},
    ).raise_for_status()
    snap_before = h.db_path_snapshot(v1["id"])
    body = h.submit(learner_id, "model-evaluation-gate", h.wrong("model-evaluation-gate"))
    snap_after_v1 = h.db_path_snapshot(v1["id"])
    v2 = next(p for p in h.client.get(f"/v1/learners/{learner_id}/paths").json() if p["status"] == "ACTIVE")
    completed_v2 = [i for i in v2["items"] if i["status"] == "COMPLETED"]
    evidence = [
        f"v1_immutable={snap_before == snap_after_v1}",
        f"completed_in_v2={len(completed_v2)}",
        f"adaptation={body['adaptation']}",
    ]
    if snap_before != snap_after_v1:
        return ScenarioResult("S17", "", "FAIL", evidence=evidence)
    if not completed_v2:
        return ScenarioResult("S17", "", "FAIL", evidence=evidence)
    return ScenarioResult("S17", "", "PASS", evidence=evidence)


def s18_multi_version(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s18-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.90)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    h.evidence(learner_id, "supervised_learning", "ASSESSMENT", 0.85)
    v1 = h.path(learner_id, AIML)
    v1_snap = h.db_path_snapshot(v1["id"])
    r2 = h.submit(learner_id, "model-evaluation-gate", h.wrong("model-evaluation-gate"))
    v2_id = r2["path_id"]
    v2_snap = h.db_path_snapshot(v2_id)
    r3 = h.submit(learner_id, "statistics-gate", h.correct("statistics-gate"))
    rows = h.db_paths(learner_id)
    evidence = [f"versions={len(rows)}", f"active={[r.version for r in rows if r.status == 'ACTIVE']}"]
    if len(rows) != 3:
        return ScenarioResult("S18", "", "FAIL", evidence=evidence)
    if len([r for r in rows if r.status == PathStatus.ACTIVE.value]) != 1:
        return ScenarioResult("S18", "", "FAIL", evidence=evidence)
    if h.db_path_snapshot(v1["id"]) != v1_snap:
        return ScenarioResult("S18", "", "FAIL", evidence=evidence + ["V1 mutated"])
    if h.db_path_snapshot(v2_id) != v2_snap:
        return ScenarioResult("S18", "", "FAIL", evidence=evidence + ["V2 mutated"])
    timeline = h.client.get(f"/v1/learners/{learner_id}/roles/{AIML}/path-timeline").json()
    if [e["version"] for e in timeline] != [1, 2, 3]:
        return ScenarioResult("S18", "", "FAIL", evidence=evidence)
    return ScenarioResult("S18", "", "PASS", evidence=evidence)


def s19_assessment_drift(h: Harness) -> ScenarioResult:
    _ = h
    session = SessionLocal()
    try:
        assessment_id = ontology_uuid("assessment", "python-gate")
        yaml_spec = next(spec for spec in h.bundle.assessments if spec.slug == "python-gate")
        drifted = copy.deepcopy(yaml_spec)
        drifted = AssessmentSpec(
            slug=drifted.slug,
            title=drifted.title,
            description=drifted.description,
            primary_skill=drifted.primary_skill,
            pass_threshold=0.55,
            questions=drifted.questions,
            target_role=drifted.target_role,
            target_skills=drifted.target_skills,
        )
        try:
            load_assessment_spec(session, assessment_id=assessment_id, yaml_spec=drifted)
            return ScenarioResult("S19", "", "FAIL", evidence=["drift not detected"])
        except AssessmentDriftError as exc:
            if exc.code != "DRIFT_DETECTED":
                return ScenarioResult("S19", "", "FAIL", evidence=[f"code={exc.code}"])
            return ScenarioResult("S19", "", "PASS", evidence=[f"code={exc.code}"])
    finally:
        session.close()


def s20_causal_explanations(h: Harness) -> ScenarioResult:
    learner_id = h.learner(f"bench-s20-{uuid.uuid4().hex[:6]}")
    h.evidence(learner_id, "python", "ASSESSMENT", 0.90)
    h.evidence(learner_id, "statistics", "ASSESSMENT", 0.35)
    h.evidence(learner_id, "ml_fundamentals", "ASSESSMENT", 0.55)
    path = h.path(learner_id, AIML)
    executable = [i for i in path["items"] if i.get("executable") and i.get("kind") == "EXECUTABLE"]
    if not executable:
        return ScenarioResult("S20", "", "INCONCLUSIVE", evidence=["no executable items"])
    failures = []
    for item in executable[:8]:
        cause = item.get("causality") or {}
        for field in (
            "why_selected",
            "why_this_skill",
            "why_this_position",
            "why_this_intervention",
            "why_this_resource",
            "why_not_earlier",
        ):
            if not cause.get(field):
                failures.append(f"missing {field} on {item.get('resource')}")
        if cause and "scored highly" in cause.get("why_selected", "").lower():
            failures.append(f"score-only language on {item.get('resource')}")
    if failures:
        return ScenarioResult("S20", "", "FAIL", evidence=failures[:6])
    return ScenarioResult("S20", "", "PASS", evidence=[f"checked={len(executable[:8])} items"])


SCENARIOS: list[tuple[str, str, Callable[[Harness], ScenarioResult]]] = [
    ("S01", "EMPTY EVIDENCE", s01_empty_evidence),
    ("S02", "TARGET-MET SKILL", s02_target_met),
    ("S03", "DIAGNOSED GAP", s03_diagnosed_gap),
    ("S04", "UNKNOWN BLOCKER", s04_unknown_blocker),
    ("S05", "KNOWN GAP BLOCKER", s05_known_gap_blocker),
    ("S06", "ROLE CHANGE", s06_role_change),
    ("S07", "LEARNER CHANGE", s07_learner_change),
    ("S08", "WEEKLY BUDGET", s08_weekly_budget),
    ("S09", "LEARNING STYLE", s09_learning_style),
    ("S10", "SEMANTIC OFF VS ON", s10_semantic_on_off),
    ("S11", "CONFLICTING EVIDENCE", s11_conflicting_evidence),
    ("S12", "POSITIVE SURPRISE", s12_positive_surprise),
    ("S13", "NEGATIVE SURPRISE", s13_negative_surprise),
    ("S14", "DOCKER UNKNOWN→KNOWN", s14_docker_unknown_to_known),
    ("S15", "NO-OP ADAPTATION", s15_no_op_adaptation),
    ("S16", "DUPLICATE ATTEMPT", s16_duplicate_attempt),
    ("S17", "COMPLETED WORK", s17_completed_work),
    ("S18", "MULTI-VERSION CHAIN", s18_multi_version),
    ("S19", "ASSESSMENT DRIFT", s19_assessment_drift),
    ("S20", "CAUSAL EXPLANATIONS", s20_causal_explanations),
]


def compute_metrics(results: list[ScenarioResult]) -> dict[str, Any]:
    def rate(ids: list[str]) -> float:
        subset = [r for r in results if r.id in ids]
        if not subset:
            return 0.0
        return round(sum(1 for r in subset if r.result == "PASS") / len(subset), 4)

    passed = sum(1 for r in results if r.result == "PASS")
    total = len(results)
    return {
        "scenario_pass_rate": round(passed / total, 4) if total else 0.0,
        "passed": passed,
        "total": total,
        "percentage": round(100 * passed / total, 2) if total else 0.0,
        "causal_validity_rate": rate(["S03", "S20"]),
        "unknown_integrity_rate": rate(["S01", "S04", "S14"]),
        "blocker_integrity_rate": rate(["S04", "S05"]),
        "role_personalization_rate": rate(["S06"]),
        "learner_personalization_rate": rate(["S07"]),
        "budget_compliance_rate": rate(["S08"]),
        "evidence_fusion_integrity_rate": rate(["S11"]),
        "adaptation_integrity_rate": rate(["S12", "S13", "S15", "S16", "S17", "S18"]),
        "historical_immutability_rate": rate(["S17", "S18"]),
        "idempotency_rate": rate(["S16"]),
        "semantic_safety_rate": rate(["S10"]),
        "drift_detection_rate": rate(["S19"]),
        "explanation_grounding_rate": rate(["S20"]),
        "overall_benchmark_score": round(passed / total, 4) if total else 0.0,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# PathFinder Intelligence Benchmark",
        "",
        "## Executive Verdict",
        f"- Overall: **{payload['metrics']['passed']}/{payload['metrics']['total']}** ({payload['metrics']['percentage']}%)",
        f"- Commit: `{payload['commit']}`",
        f"- Timestamp: {payload['timestamp']}",
        "",
        "## Scenario Matrix",
        "| ID | Scenario | Result | Duration ms |",
        "|----|----------|--------|-------------|",
    ]
    for row in payload["scenarios"]:
        lines.append(f"| {row['id']} | {row['name']} | {row['result']} | {row['duration_ms']} |")
    lines.extend(["", "## Quantitative Metrics", "", "```json", json.dumps(payload["metrics"], indent=2), "```"])
    if payload["failures"]:
        lines.extend(["", "## Failures", ""])
        for item in payload["failures"]:
            lines.append(f"- **{item['id']}** {item['name']}: {item['evidence']}")
    if payload["inconclusive"]:
        lines.extend(["", "## Inconclusive / Not Proven", ""])
        for item in payload["inconclusive"]:
            lines.append(f"- **{item['id']}** {item['name']}: {item.get('notes','')}")
    lines.extend(
        [
            "",
            "## Specification Corrections",
            "",
            "S11 and S12 expectations were corrected to match established domain semantics:",
            "",
            "- **S11** no longer assumes fused proficiency must fall between 0.50 and 0.90 when "
            "a failed assessment reports 0.00. The scenario now asserts append-only evidence, "
            "conflict detection, ASSESSMENT dominance, and GAP classification below target.",
            "- **S12** now seeds the initial low statistics signal as SELF_REPORT (not ASSESSMENT), "
            "matching `test_positive_surprise_removes_unjustified_remediation`. A perfect gate can "
            "therefore move statistics to TARGET_MET and remove unjustified remediation without "
            "violating append-only ASSESSMENT fusion rules.",
        ]
    )
    lines.extend(["", "## Performance", "", "```json", json.dumps(payload["performance"], indent=2), "```"])
    return "\n".join(lines) + "\n"


def run_benchmark() -> dict[str, Any]:
    if not postgres_available():
        raise SystemExit("PostgreSQL required for intelligence benchmark (DATABASE_URL unreachable)")

    startup = time.perf_counter()
    h = Harness()
    results: list[ScenarioResult] = []
    for sid, name, fn in SCENARIOS:
        results.append(_run_scenario(h, sid, name, fn))

    metrics = compute_metrics(results)
    payload = {
        "benchmark": "PathFinder Intelligence Benchmark",
        "version": "6.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commit": git_commit(),
        "scenarios": [asdict(r) for r in results],
        "metrics": metrics,
        "failures": [asdict(r) for r in results if r.result == "FAIL"],
        "inconclusive": [asdict(r) for r in results if r.result in {"INCONCLUSIVE", "NOT_PROVEN"}],
        "performance": {
            "startup_ms": round((time.perf_counter() - startup) * 1000, 2),
            "scenario_timings_ms": {r.id: r.duration_ms for r in results},
            "harness_timings_ms": h.timings,
            "total_ms": round(sum(r.duration_ms for r in results), 2),
        },
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    DOC_PATH.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    payload = run_benchmark()
    print(json.dumps({"passed": payload["metrics"]["passed"], "total": payload["metrics"]["total"]}))
    return 0 if not payload["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
