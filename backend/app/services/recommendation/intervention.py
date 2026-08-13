"""Map gap action + resource type onto an intervention. Not a roadmap."""

from __future__ import annotations

from app.core.enums import ActionClass, InterventionType, ResourceType
from app.ontology.load import ResourceSpec
from app.services.gap_engine.profile import ExplainedGap


def infer_intervention(resource: ResourceSpec, gap_item: ExplainedGap | None) -> InterventionType:
    if resource.type == ResourceType.ASSESSMENT.value:
        return InterventionType.ASSESSMENT
    if gap_item is None:
        return InterventionType.FOUNDATION
    action = gap_item.action
    if action is ActionClass.VERIFY:
        return InterventionType.VERIFY
    if action is ActionClass.ADVANCE:
        return InterventionType.ADVANCEMENT
    if action is ActionClass.REINFORCE:
        return InterventionType.PRACTICE
    if resource.type == ResourceType.PROJECT.value:
        return InterventionType.APPLICATION
    if resource.type == ResourceType.LAB.value:
        return InterventionType.PRACTICE
    if action is ActionClass.REMEDIATE and resource.type == ResourceType.COURSE.value and resource.difficulty <= 2:
        return InterventionType.FOUNDATION
    if action is ActionClass.REMEDIATE_BLOCKER:
        return InterventionType.REMEDIATION
    return InterventionType.REMEDIATION
