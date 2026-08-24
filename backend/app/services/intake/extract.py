"""Natural-language goal intake.

The learner types a paragraph. An LLM proposes structure; the ontology
resolver decides what is real. Every mention must resolve to a canonical slug
or it is reported back as unresolved ΓÇö the model cannot introduce a skill, a
role, or a proficiency the ontology does not define.

Without an API key the rule-based extractor runs instead, so the intake screen
works offline. Both paths go through the same resolver and produce the same
shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.enums import LearningStyle
from app.ontology.load import load_ontology
from app.services.llm.provider import LLMProvider, LLMUnavailable, get_llm_provider
from app.services.intake import resolver as res

MAX_TOKENS = 2000
MAX_SKILLS = 12

EXTRACTION_SYSTEM = """
You extract structure from a learner's description of their career goal.

Return only what the learner actually said. Do not infer a target role they
did not name, do not add skills they did not mention, and do not guess a
proficiency they did not describe.

For each skill or technology they mention, copy their exact wording into
`mention`, and copy the words describing their experience level into
`level_phrase` (for example "pretty good at", "no experience with",
"beginner"). Leave `level_phrase` empty if they gave no indication.

`goal_role` is the job or career they want, in their words. Leave it empty if
they did not name one.

Do not normalise, translate, or correct spellings ΓÇö downstream code resolves
the wording against a fixed catalog, and it needs the original text.
""".strip()

EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "goal_role": {"type": "string"},
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "mention": {"type": "string"},
                    "level_phrase": {"type": "string"},
                },
                "required": ["mention", "level_phrase"],
                "additionalProperties": False,
            },
        },
        "weekly_hours_phrase": {"type": "string"},
        "timeframe_phrase": {"type": "string"},
        "learning_style_phrase": {"type": "string"},
    },
    "required": [
        "goal_role",
        "skills",
        "weekly_hours_phrase",
        "timeframe_phrase",
        "learning_style_phrase",
    ],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class SkillClaim:
    skill: str
    name: str
    observed_level: float
    mention: str
    level_phrase: str
    how: str
    level_stated: bool


@dataclass(frozen=True)
class GoalIntake:
    """What the learner said, resolved against the ontology.

    `skills` carries only claims where the learner actually described a level.
    A skill they named without saying how well they know it lands in
    `ungraded`: the engine asks rather than inventing a proficiency, because a
    fabricated number would enter evidence fusion as if it were observed.
    """

    goal_text: str
    role: res.ResolvedEntity | None
    role_alternatives: tuple[res.ResolvedEntity, ...]
    skills: tuple[SkillClaim, ...]
    ungraded: tuple[SkillClaim, ...]
    weekly_hours: float | None
    timeframe_weeks: int | None
    learning_style: str | None
    unresolved: tuple[str, ...]
    source: str
    provider: str
    model: str
    notes: tuple[str, ...] = field(default_factory=tuple)


def _split(
    claims: list[SkillClaim],
) -> tuple[tuple[SkillClaim, ...], tuple[SkillClaim, ...]]:
    """One claim per skill, partitioned by whether a level was stated."""
    best: dict[str, SkillClaim] = {}
    for claim in claims:
        current = best.get(claim.skill)
        if current is None or (claim.level_stated and not current.level_stated):
            best[claim.skill] = claim
    graded = [claim for claim in best.values() if claim.level_stated]
    ungraded = [claim for claim in best.values() if not claim.level_stated]
    return tuple(graded[:MAX_SKILLS]), tuple(ungraded[:MAX_SKILLS])


def _role_alternatives(
    text: str, vocab: res.Vocabulary, chosen: res.ResolvedEntity | None
) -> tuple[res.ResolvedEntity, ...]:
    """Other roles the text also gestures at, offered as corrections."""
    found: dict[str, res.ResolvedEntity] = {}
    haystack = f" {res._normalise(text)} "
    for key, slug in vocab.role_by_key.items():
        if chosen is not None and slug == chosen.slug:
            continue
        if len(key) < 3:
            continue
        if re.search(rf"\b{re.escape(key)}\b", haystack):
            found.setdefault(
                slug,
                res.ResolvedEntity(
                    slug=slug, name=vocab.role_names[slug], mention=key, how="ALIAS"
                ),
            )
    return tuple(found.values())[:3]


def _vocabulary_words(vocab: res.Vocabulary) -> set[str]:
    """Every word that appears in any resolvable name or alias.

    "Data Analyst" resolves as a role, but "Data" on its own resolves to
    nothing ΓÇö so a token-by-token check would report it as unknown. Matching
    against the constituent words prevents that.
    """
    words: set[str] = set()
    for key in (*vocab.skill_by_key, *vocab.role_by_key):
        words.update(key.split())
    return words


def _capitalised_unknowns(text: str, vocab: res.Vocabulary) -> list[str]:
    """Proper-noun technologies the ontology does not carry.

    Learners capitalise product names ("Kubernetes", "Rust", "Figma"), so a
    capitalised mid-sentence token that resolves to nothing is a reliable
    signal of an out-of-catalog request worth telling them about.
    """
    known_words = _vocabulary_words(vocab)
    unknown: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.]*\b", sentence)
        for index, token in enumerate(tokens):
            if index == 0 or not token[0].isupper() or token.isupper() and len(token) <= 2:
                continue
            lowered = token.lower()
            if lowered in known_words or lowered in _PROSE_CAPITALS:
                continue
            if vocab.resolve_skill(token) or vocab.resolve_role(token):
                continue
            if token not in unknown:
                unknown.append(token)
    return unknown


_PROSE_CAPITALS = frozenset(
    """
    i i'm im ive id ill monday tuesday wednesday thursday friday saturday
    sunday january february march april may june july august september october
    november december
    """.split()
)


_CLAUSE_BREAK = re.compile(r"[,.;:]| and | but | or | with ")
_SENTENCE_END = re.compile(r"[.;!?]")

LOOKBACK = 45


def _sentence_before(padded: str, start: int) -> str:
    """Text preceding a mention, clipped at the last sentence boundary.

    An experience claim does not carry across sentences. Without this,
    "no Python at all. 2 hours a day. I also use Tableau" let the Python
    denial fall inside Tableau's lookback window and silently drop Tableau.
    """
    window = padded[max(0, start - LOOKBACK) : start]
    breaks = list(_SENTENCE_END.finditer(window))
    return window[breaks[-1].end() :] if breaks else window


def _clause(text: str) -> str:
    """Trim a forward window at the first clause break.

    In "React well and some Node", the level for React is "well"; "some"
    belongs to Node and must not bleed backwards.
    """
    match = _CLAUSE_BREAK.search(text)
    return text[: match.start()] if match else text


# --- rule-based path -------------------------------------------------------


def _rule_based(text: str, vocab: res.Vocabulary) -> GoalIntake:
    normalised = res._normalise(text)
    padded = f" {normalised} "

    role: res.ResolvedEntity | None = None
    # Spans covered by the goal statement itself. "I want to be an AI/ML
    # engineer" names a target, not a skill the learner already holds.
    reserved: list[tuple[int, int]] = []
    for key in sorted(vocab.role_by_key, key=len, reverse=True):
        if len(key) < 3:
            continue
        match = re.search(rf"\b{re.escape(key)}\b", padded)
        if match is None:
            continue
        if role is None:
            role = vocab.resolve_role(key)
        reserved.append((match.start(), match.end()))

    claims: list[SkillClaim] = []
    consumed: list[tuple[int, int]] = list(reserved)
    for key in sorted(vocab.skill_by_key, key=len, reverse=True):
        if len(key) < 2:
            continue
        for match in re.finditer(rf"\b{re.escape(key)}\b", padded):
            span = (match.start(), match.end())
            if any(start < span[1] and span[0] < end for start, end in consumed):
                continue
            entity = vocab.resolve_skill(key)
            if entity is None:
                continue
            consumed.append(span)
            before = _sentence_before(padded, span[0])
            after = _clause(padded[span[1] : span[1] + 30])
            reading = res.read_experience(before, after)
            if reading.denied:
                # An explicit absence of experience: record nothing, so the
                # gap engine treats the skill as UNKNOWN rather than as 0.
                break
            level = reading.level
            claims.append(
                SkillClaim(
                    skill=entity.slug,
                    name=entity.name,
                    observed_level=level if level is not None else res.DEFAULT_LEVEL,
                    mention=key,
                    level_phrase=before.strip(),
                    how=entity.how,
                    level_stated=level is not None,
                )
            )
            break

    graded, ungraded = _split(claims)
    return GoalIntake(
        goal_text=text,
        role=role,
        role_alternatives=_role_alternatives(text, vocab, role),
        skills=graded,
        ungraded=ungraded,
        weekly_hours=res.weekly_hours_from_text(text),
        timeframe_weeks=res.timeframe_weeks_from_text(text),
        learning_style=res.learning_style_from_text(text),
        unresolved=tuple(_capitalised_unknowns(text, vocab)),
        source="DETERMINISTIC",
        provider="rules",
        model="keyword-resolver",
    )


# --- LLM path --------------------------------------------------------------


def _from_payload(
    text: str, payload: dict, vocab: res.Vocabulary, provider: LLMProvider
) -> GoalIntake:
    unresolved: list[str] = []

    role_mention = str(payload.get("goal_role") or "").strip()
    role = vocab.resolve_role(role_mention) if role_mention else None
    if role is None and role_mention:
        # The model may return a description rather than a title.
        for key in sorted(vocab.role_by_key, key=len, reverse=True):
            if len(key) >= 3 and re.search(
                rf"\b{re.escape(key)}\b", res._normalise(role_mention)
            ):
                role = vocab.resolve_role(key)
                break
    if role is None and role_mention:
        unresolved.append(role_mention)

    claims: list[SkillClaim] = []
    raw_skills = payload.get("skills")
    for row in raw_skills if isinstance(raw_skills, list) else []:
        if not isinstance(row, dict):
            continue
        mention = str(row.get("mention") or "").strip()
        phrase = str(row.get("level_phrase") or "").strip()
        if not mention:
            continue
        entity = vocab.resolve_skill(mention)
        if entity is None:
            if mention not in unresolved:
                unresolved.append(mention)
            continue
        reading = res.read_experience(phrase) if phrase else res.ExperienceReading(None, False)
        if reading.denied:
            continue  # stated absence of experience -> UNKNOWN, not 0
        level = reading.level
        claims.append(
            SkillClaim(
                skill=entity.slug,
                name=entity.name,
                observed_level=level if level is not None else res.DEFAULT_LEVEL,
                mention=mention,
                level_phrase=phrase,
                how=entity.how,
                level_stated=level is not None,
            )
        )

    for token in _capitalised_unknowns(text, vocab):
        if token not in unresolved:
            unresolved.append(token)

    hours_phrase = str(payload.get("weekly_hours_phrase") or "")
    style_phrase = str(payload.get("learning_style_phrase") or "")
    time_phrase = str(payload.get("timeframe_phrase") or "")

    style = res.learning_style_from_text(style_phrase or text)
    if style is not None and style not in {item.value for item in LearningStyle}:
        style = None

    graded, ungraded = _split(claims)
    return GoalIntake(
        goal_text=text,
        role=role,
        role_alternatives=_role_alternatives(text, vocab, role),
        skills=graded,
        ungraded=ungraded,
        weekly_hours=res.weekly_hours_from_text(hours_phrase)
        or res.weekly_hours_from_text(text),
        timeframe_weeks=res.timeframe_weeks_from_text(time_phrase)
        or res.timeframe_weeks_from_text(text),
        learning_style=style,
        unresolved=tuple(unresolved),
        source="LLM",
        provider=provider.name,
        model=provider.model,
    )


def parse_goal(text: str, *, provider: LLMProvider | None = None) -> GoalIntake:
    """Turn a free-text goal into resolved, ontology-backed structure."""
    vocab = res.build_vocabulary(load_ontology())
    engine = provider or get_llm_provider()
    try:
        payload = engine.complete_json(
            system=EXTRACTION_SYSTEM,
            user=text,
            schema=EXTRACTION_SCHEMA,
            max_tokens=MAX_TOKENS,
        )
    except LLMUnavailable:
        return _rule_based(text, vocab)

    result = _from_payload(text, payload, vocab, engine)
    if result.role is None and not result.skills and not result.ungraded:
        # Extraction produced nothing usable; the rule-based scan may still hit.
        fallback = _rule_based(text, vocab)
        if fallback.role is not None or fallback.skills or fallback.ungraded:
            return fallback
    return result
