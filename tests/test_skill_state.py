from app.core.enums import AttainmentStatus, SkillStatus
from app.core.skill_state import resolve_attainment, resolve_skill_status, resolve_target_met


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


def test_below_target_is_not_strong_even_when_close():
    status = resolve_skill_status(has_evidence=True, proficiency=0.65, target_level=0.75)
    assert status is SkillStatus.DEVELOPING
    assert status is not SkillStatus.STRONG


def test_exact_gap_min_delta_is_gap_not_developing():
    status = resolve_skill_status(has_evidence=True, proficiency=0.45, target_level=0.85)
    assert status is SkillStatus.GAP


def test_near_target_is_not_target_met():
    assert resolve_target_met(proficiency=0.65, target_level=0.75) is False
    assert (
        resolve_attainment(has_evidence=True, proficiency=0.65, target_level=0.75)
        is AttainmentStatus.NEAR_TARGET
    )


def test_at_or_above_target_is_target_met():
    assert resolve_target_met(proficiency=0.80, target_level=0.75) is True
    assert (
        resolve_attainment(has_evidence=True, proficiency=0.80, target_level=0.75)
        is AttainmentStatus.TARGET_MET
    )


def test_unknown_attainment_is_not_a_score():
    assert resolve_target_met(proficiency=None, target_level=0.75) is None
    assert (
        resolve_attainment(has_evidence=False, proficiency=None, target_level=0.75)
        is AttainmentStatus.UNKNOWN
    )
