"""Deterministic natural-language explanations. Used when the LLM is absent or invalid."""

from __future__ import annotations

from app.services.explanation.schema import AIContext, Claim, GroundedAnswer


def _fact(context: AIContext, fact_id: str) -> str:
    for item in context.facts:
        if item.id == fact_id:
            return item.value
    return "—"


def _ids(*ids: str) -> list[str]:
    return list(ids)


def explain_deterministic(context: AIContext, query: str | None = None) -> GroundedAnswer:
    asked = (query or "").lower()
    if _is_injection(asked):
        return _injection_refusal(context)
    if context.intent == "WHY_GAP":
        return _why_gap(context)
    if context.intent == "WHY_RESOURCE":
        return _why_resource(context)
    if context.intent == "WHAT_CHANGED":
        return _what_changed(context)
    if context.intent == "NEXT_ACTION":
        return _next_action(context)
    if context.intent == "COACH":
        return _coach(context)
    return _query(context, asked)


def _is_injection(asked: str) -> bool:
    needles = (
        "ignore your rules",
        "ignore previous",
        "tell me i'm already an expert",
        "tell me i am already an expert",
        "change my proficiency",
        "set my proficiency",
        "add a course that isn't",
        "add a course that is not",
        "invent a course",
        "not in the catalog",
    )
    return any(item in asked for item in needles)


def _injection_refusal(context: AIContext) -> GroundedAnswer:
    answer = (
        "PathFinder cannot change proficiency, invent courses, or override diagnosis "
        "through this interface. Proficiency comes from stored evidence. Resources must "
        "exist in the verified catalog. The current facts still stand."
    )
    ids = ["role.name"]
    if context.skill:
        ids.extend(["skill.slug", "skill.attainment"])
    cited = [item for item in ids if item in context.fact_ids()] or list(context.fact_ids())[:1] or ["role.name"]
    return GroundedAnswer(
        answer=answer,
        claims=[Claim(text=answer, fact_ids=cited)],
        source="deterministic",
        facts=context.facts,
        intent=context.intent,
    )


def _why_gap(context: AIContext) -> GroundedAnswer:
    name = _fact(context, "skill.name")
    role = _fact(context, "role.name")
    attainment = _fact(context, "skill.attainment")
    action = _fact(context, "skill.action")
    target = _fact(context, "skill.target")
    proficiency = _fact(context, "skill.proficiency")
    downstream = _fact(context, "skill.downstream")
    if attainment == "UNKNOWN":
        answer = (
            f"{name} is UNKNOWN for {role} — PathFinder has no evidence yet, so it does not "
            f"treat this as 0% mastery. Immediate action is {action}."
        )
        ids = _ids("skill.name", "role.name", "skill.attainment", "skill.action")
    elif attainment == "TARGET_MET":
        answer = (
            f"Your {name.lower()} evidence ({proficiency}) meets the {role} target of {target}. "
            f"Current action is {action}."
        )
        ids = _ids("skill.name", "skill.proficiency", "skill.target", "role.name", "skill.attainment", "skill.action")
    else:
        extra = f" It supports downstream work in {downstream}." if downstream and downstream != "—" else ""
        answer = (
            f"Your {name.lower()} evidence ({proficiency}) is below the {role} target of {target} "
            f"({attainment}). PathFinder is prioritizing {action}.{extra}"
        )
        ids = _ids(
            "skill.name",
            "skill.proficiency",
            "skill.target",
            "role.name",
            "skill.attainment",
            "skill.action",
        )
        if downstream and downstream != "—":
            ids.append("skill.downstream")
    return GroundedAnswer(
        answer=answer,
        claims=[Claim(text=answer, fact_ids=ids)],
        source="deterministic",
        facts=context.facts,
        intent=context.intent,
    )


def _why_resource(context: AIContext) -> GroundedAnswer:
    title = _fact(context, "resource.title")
    skill = _fact(context, "skill.name")
    why_skill = _fact(context, "causality.why_this_skill")
    why_pos = _fact(context, "causality.why_this_position")
    eligibility = _fact(context, "path_item.eligibility")
    intervention = _fact(context, "path_item.intervention")
    answer = (
        f"{title} is on your path because {skill} is a diagnosed need. {why_skill} "
        f"Intervention is {intervention}. {why_pos}"
    )
    if eligibility and eligibility not in {"ELIGIBLE", "GATE", "—"}:
        answer += f" Current eligibility is {eligibility}."
    ids = [
        item
        for item in (
            "resource.title",
            "skill.name",
            "causality.why_this_skill",
            "path_item.intervention",
            "causality.why_this_position",
            "path_item.eligibility",
        )
        if item in context.fact_ids()
    ]
    return GroundedAnswer(
        answer=answer.strip(),
        claims=[Claim(text=answer.strip(), fact_ids=ids or _ids("skill.name"))],
        source="deterministic",
        facts=context.facts,
        intent=context.intent,
    )


def _what_changed(context: AIContext) -> GroundedAnswer:
    skill = _fact(context, "skill.name")
    before = _fact(context, "adaptation.before_state")
    after = _fact(context, "adaptation.after_state")
    observed = _fact(context, "adaptation.observed")
    action = _fact(context, "skill.action")
    added = _fact(context, "adaptation.added")
    moved = _fact(context, "adaptation.moved")
    answer = (
        f"Your assessment produced new evidence for {skill} (observed {observed}). "
        f"That moved the skill from {before} to {after}, so the action is {action}."
    )
    if added and added != "—":
        answer += f" Path change: {added}."
    if moved and moved != "—":
        answer += f" {moved}."
    ids = [
        item
        for item in (
            "skill.name",
            "adaptation.observed",
            "adaptation.before_state",
            "adaptation.after_state",
            "skill.action",
            "adaptation.added",
            "adaptation.moved",
        )
        if item in context.fact_ids()
    ]
    return GroundedAnswer(
        answer=answer,
        claims=[Claim(text=answer, fact_ids=ids or _ids("skill.name"))],
        source="deterministic",
        facts=context.facts,
        intent=context.intent,
    )


def _next_action(context: AIContext) -> GroundedAnswer:
    title = _fact(context, "next_action.title")
    skill = _fact(context, "next_action.skill")
    week = _fact(context, "next_action.week")
    action = _fact(context, "next_action.action")
    hours = _fact(context, "learner.weekly_hours")
    answer = (
        f"This week, {action} {skill} using {title}"
        f"{f' (week {week})' if week and week != '—' else ''}. "
        f"Your weekly budget is {hours} hours. PathFinder selected this item; this layer cannot pick another resource."
    )
    ids = [
        item
        for item in (
            "next_action.action",
            "next_action.skill",
            "next_action.title",
            "next_action.week",
            "learner.weekly_hours",
        )
        if item in context.fact_ids()
    ]
    return GroundedAnswer(
        answer=answer,
        claims=[Claim(text=answer, fact_ids=ids or _ids("learner.weekly_hours"))],
        source="deterministic",
        facts=context.facts,
        intent=context.intent,
    )


def _coach(context: AIContext) -> GroundedAnswer:
    changed = _what_changed(context).answer
    nxt = _next_action(context).answer
    answer = f"{changed} Next: {nxt}"
    ids = list(context.fact_ids())[:8] or ["role.name"]
    return GroundedAnswer(
        answer=answer,
        claims=[
            Claim(text=changed, fact_ids=[i for i in ids if i.startswith("adaptation") or i.startswith("skill")] or ids[:2]),
            Claim(text=nxt, fact_ids=[i for i in ids if i.startswith("next_action")] or ids[:2]),
        ],
        source="deterministic",
        facts=context.facts,
        intent=context.intent,
    )


def _query(context: AIContext, asked: str) -> GroundedAnswer:
    if "can't start" in asked or "cannot start" in asked or "blocked" in asked:
        if context.resource or context.path_item:
            return _why_resource(context)
    if "changed" in asked or "assessment" in asked:
        if context.adaptation:
            return _what_changed(context)
    if "this week" in asked or "do next" in asked or "should i" in asked:
        if context.next_action:
            return _next_action(context)
    if "prove" in asked:
        skill = _fact(context, "skill.name")
        action = _fact(context, "skill.action")
        waiting = _fact(context, "waiting.resources")
        answer = (
            f"If you prove {skill}, PathFinder stores assessment evidence and re-runs fusion. "
            f"It does not invent a new diagnosis in this chat. Current action is {action}."
        )
        if waiting and waiting != "—":
            answer += f" Resources currently waiting on this skill: {waiting}."
        ids = [i for i in ("skill.name", "skill.action", "waiting.resources") if i in context.fact_ids()]
        return GroundedAnswer(
            answer=answer,
            claims=[Claim(text=answer, fact_ids=ids or _ids("skill.name"))],
            source="deterministic",
            facts=context.facts,
            intent=context.intent,
        )
    if context.skill:
        return _why_gap(context)
    if context.next_action:
        return _next_action(context)
    role = _fact(context, "role.name")
    answer = f"PathFinder is diagnosing your path toward {role} from stored evidence only."
    return GroundedAnswer(
        answer=answer,
        claims=[Claim(text=answer, fact_ids=_ids("role.name"))],
        source="deterministic",
        facts=context.facts,
        intent=context.intent,
    )
