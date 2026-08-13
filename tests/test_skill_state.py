from app.core.enums import SkillStatus
from app.core.skill_state import resolve_skill_status


def test_no_evidence_is_unknown_not_zero():
    status = resolve_skill_status(has_evidence=False, proficiency=None, target_level=0.8)
    assert status is SkillStatus.UNKNOWN


def test_null_proficiency_is_unknown_even_if_flag_true():
    status = resolve_skill_status(has_evidence=True, proficiency=None, target_level=0.8)
    assert status is SkillStatus.UNKNOWN


def test_zero_with_evidence_is_not_unknown():
    status = resolve_skill_status(has_evidence=True, proficiency=0.0, target_level=0.8)
    assert status is SkillStatus.GAP
    assert status is not SkillStatus.UNKNOWN


def test_strong_when_near_target():
    status = resolve_skill_status(has_evidence=True, proficiency=0.82, target_level=0.80)
    assert status is SkillStatus.STRONG


def test_developing_when_moderate_gap():
    status = resolve_skill_status(has_evidence=True, proficiency=0.55, target_level=0.80)
    assert status is SkillStatus.DEVELOPING
