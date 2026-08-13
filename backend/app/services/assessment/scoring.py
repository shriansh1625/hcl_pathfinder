"""Deterministic assessment scoring. Not a second learner model.

Scoring produces observations per canonical skill. The evidence system
remains authoritative; nothing here writes learner state.

Skill score:
    correct_weighted = Σ(difficulty_i × correctness_i)
    max_weighted     = Σ(difficulty_i)
    observed_level   = correct_weighted / max_weighted

Confidence (documented deterministic rule, clamped to [0.30, 0.95]):
    base 0.50
    + 0.05 × question_count (capped at 10)
    + 0.05 × average_difficulty
    + 0.10 if all of the skill's questions agree (all correct or all wrong)
    − 0.10 if mixed results on a skill with ≥ 3 questions
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ontology.load import AssessmentSpec

CONFIDENCE_BASE = 0.50
CONFIDENCE_PER_QUESTION = 0.05
CONFIDENCE_QUESTION_CAP = 10
CONFIDENCE_PER_DIFFICULTY = 0.05
CONFIDENCE_AGREEMENT_BONUS = 0.10
CONFIDENCE_MIXED_PENALTY = 0.10
CONFIDENCE_MIN = 0.30
CONFIDENCE_MAX = 0.95


@dataclass(frozen=True)
class SkillScore:
    skill_slug: str
    question_count: int
    correct_count: int
    observed_level: float
    confidence: float
    difficulty_avg: float
    consistency: str  # "AGREE" | "MIXED"

    def as_dict(self) -> dict:
        return {
            "skill": self.skill_slug,
            "question_count": self.question_count,
            "correct_count": self.correct_count,
            "observed_level": round(self.observed_level, 6),
            "confidence": round(self.confidence, 6),
            "difficulty_avg": round(self.difficulty_avg, 6),
            "consistency": self.consistency,
        }


@dataclass(frozen=True)
class AssessmentScore:
    assessment_slug: str
    overall_score: float
    passed: bool
    skill_results: tuple[SkillScore, ...]

    def as_dict(self) -> dict:
        return {
            "assessment": self.assessment_slug,
            "overall_score": round(self.overall_score, 6),
            "passed": self.passed,
            "skill_results": [item.as_dict() for item in self.skill_results],
        }


def skill_confidence(
    *,
    question_count: int,
    difficulty_avg: float,
    all_agree: bool,
) -> float:
    """Transparent deterministic confidence. Never invented per-assessment."""
    value = CONFIDENCE_BASE
    value += CONFIDENCE_PER_QUESTION * min(question_count, CONFIDENCE_QUESTION_CAP)
    value += CONFIDENCE_PER_DIFFICULTY * difficulty_avg
    if all_agree:
        value += CONFIDENCE_AGREEMENT_BONUS
    elif question_count >= 3:
        value -= CONFIDENCE_MIXED_PENALTY
    return min(CONFIDENCE_MAX, max(CONFIDENCE_MIN, value))


def score_attempt(spec: AssessmentSpec, answers: list[int]) -> AssessmentScore:
    """Score submitted answers against the canonical question spec.

    answers[i] is the selected choice index for the question at position i.
    Correctness is binary; difficulty weights preserve skill resolution.
    """
    questions = sorted(spec.questions, key=lambda q: spec.questions.index(q))
    if len(answers) != len(questions):
        raise ValueError(
            f"Expected {len(questions)} answers, got {len(answers)}"
        )
    for idx, answer in enumerate(answers):
        if not isinstance(answer, int) or answer < 0 or answer >= len(questions[idx].choices):
            raise ValueError(f"Answer {idx} is not a valid choice index")

    per_skill: dict[str, list[tuple[int, bool]]] = {}
    for question, answer in zip(questions, answers, strict=True):
        per_skill.setdefault(question.skill, []).append(
            (question.difficulty, answer == question.correct_index)
        )

    skill_results: list[SkillScore] = []
    total_correct_weighted = 0.0
    total_max_weighted = 0.0
    for slug in sorted(per_skill):
        rows = per_skill[slug]
        correct_weighted = sum(diff for diff, correct in rows if correct)
        max_weighted = sum(diff for diff, _ in rows)
        total_correct_weighted += correct_weighted
        total_max_weighted += max_weighted
        observed = correct_weighted / max_weighted if max_weighted else 0.0
        correctness = [correct for _, correct in rows]
        all_agree = all(correctness) or not any(correctness)
        difficulty_avg = sum(diff for diff, _ in rows) / len(rows)
        skill_results.append(
            SkillScore(
                skill_slug=slug,
                question_count=len(rows),
                correct_count=sum(1 for correct in correctness if correct),
                observed_level=observed,
                confidence=skill_confidence(
                    question_count=len(rows),
                    difficulty_avg=difficulty_avg,
                    all_agree=all_agree,
                ),
                difficulty_avg=difficulty_avg,
                consistency="AGREE" if all_agree else "MIXED",
            )
        )

    overall = (
        total_correct_weighted / total_max_weighted if total_max_weighted else 0.0
    )
    return AssessmentScore(
        assessment_slug=spec.slug,
        overall_score=overall,
        passed=overall + 1e-9 >= spec.pass_threshold,
        skill_results=tuple(skill_results),
    )
