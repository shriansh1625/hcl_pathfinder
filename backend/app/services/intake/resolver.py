"""Canonical entity resolution for free-text learner input.

Implements the resolver contract in docs/AI_ARCHITECTURE.md: a mention becomes
an ontology entity only via exact slug, canonical name, or a documented alias.
Anything else is rejected and reported back as unresolved ΓÇö the system never
invents a skill, role, or resource from learner prose or model output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ontology.load import OntologyBundle

# Documented alias table. Maps how learners actually write things to the
# canonical slug. Tools map to the skill they demonstrate, not to themselves.
SKILL_ALIASES: dict[str, str] = {
    # Programming
    "py": "python", "python3": "python",
    "js": "javascript", "es6": "javascript",
    "ts": "typescript",
    "html": "html_css", "css": "html_css", "html/css": "html_css",
    "postgres": "databases", "postgresql": "databases", "mysql": "databases",
    "mongodb": "databases", "mongo": "databases", "database": "databases",
    "nosql": "databases",
    "github": "git", "version control": "git", "gitlab": "git",
    "dsa": "data_structures", "algorithms": "data_structures",
    "leetcode": "data_structures",
    "unix": "linux", "bash": "linux", "shell": "linux",
    # Mathematics
    "stats": "statistics", "statistic": "statistics",
    "prob": "probability",
    "matrices": "linear_algebra", "matrix algebra": "linear_algebra",
    "calculus": "calculus_basics", "derivatives": "calculus_basics",
    # Data
    "pandas": "data_wrangling", "numpy": "data_wrangling",
    "data cleaning": "data_wrangling", "etl": "data_wrangling",
    "matplotlib": "data_visualization", "seaborn": "data_visualization",
    "tableau": "data_visualization", "plotly": "data_visualization",
    "charts": "data_visualization", "dashboards": "data_visualization",
    "excel": "excel_bi", "spreadsheets": "excel_bi", "bi": "excel_bi",
    "power bi": "excel_bi", "powerbi": "excel_bi", "looker": "excel_bi",
    "eda": "exploratory_data_analysis",
    # Machine learning
    "ml": "ml_fundamentals", "machine learning": "ml_fundamentals",
    "sklearn": "supervised_learning", "scikit-learn": "supervised_learning",
    "scikit learn": "supervised_learning", "regression": "supervised_learning",
    "classification": "supervised_learning", "xgboost": "supervised_learning",
    "random forest": "supervised_learning",
    "clustering": "unsupervised_learning", "kmeans": "unsupervised_learning",
    "k-means": "unsupervised_learning", "pca": "unsupervised_learning",
    "feature selection": "feature_engineering",
    "cross validation": "model_evaluation", "metrics": "model_evaluation",
    "confusion matrix": "model_evaluation", "precision": "model_evaluation",
    "recall": "model_evaluation", "auc": "model_evaluation",
    # Deep learning
    "dl": "neural_networks", "deep learning": "neural_networks",
    "pytorch": "neural_networks", "tensorflow": "neural_networks",
    "keras": "neural_networks", "torch": "neural_networks",
    "backpropagation": "neural_networks",
    "convolutional": "cnn", "convnet": "cnn", "computer vision": "cnn",
    "image classification": "cnn",
    "transformer": "transformers", "llm": "transformers", "llms": "transformers",
    "bert": "transformers", "gpt": "transformers", "attention": "transformers",
    "huggingface": "transformers", "hugging face": "transformers",
    # Engineering
    "rest": "rest_apis", "api": "rest_apis", "apis": "rest_apis",
    "graphql": "rest_apis",
    "flask": "fastapi", "django": "fastapi", "backend framework": "fastapi",
    "containers": "docker", "container": "docker", "dockerfile": "docker",
    "testing": "software_testing", "unit tests": "software_testing",
    "pytest": "software_testing", "unit testing": "software_testing",
    "jest": "software_testing", "tdd": "software_testing",
    "reactjs": "react", "react.js": "react", "nextjs": "react",
    "next.js": "react", "frontend framework": "react",
    "node": "nodejs", "node.js": "nodejs", "express": "nodejs",
    "auth": "authentication", "oauth": "authentication", "jwt": "authentication",
    "login": "authentication",
    # Security
    "networking": "networking_basics", "tcp/ip": "networking_basics",
    "dns": "networking_basics",
    "owasp": "owasp_top10", "owasp top 10": "owasp_top10",
    "web security": "owasp_top10", "xss": "owasp_top10",
    "sql injection": "owasp_top10",
    "iam": "identity_access", "identity": "identity_access",
    "access control": "identity_access", "rbac": "identity_access",
    "siem": "siem_logging", "splunk": "siem_logging", "logging": "siem_logging",
    "soc": "siem_logging",
    "ir": "incident_response", "forensics": "incident_response",
    "threat modelling": "threat_modeling", "stride": "threat_modeling",
    # Cloud / DevOps
    "cloud": "cloud_fundamentals", "gcp": "cloud_fundamentals",
    "azure": "cloud_fundamentals",
    "aws": "aws_core", "ec2": "aws_core", "s3": "aws_core", "lambda": "aws_core",
    "cicd": "ci_cd", "ci/cd": "ci_cd", "jenkins": "ci_cd",
    "github actions": "ci_cd", "pipelines": "ci_cd",
    "iac": "infrastructure_as_code", "terraform": "infrastructure_as_code",
    "cloudformation": "infrastructure_as_code", "ansible": "infrastructure_as_code",
    "monitoring": "observability", "grafana": "observability",
    "prometheus": "observability", "tracing": "observability",
    "sysadmin": "linux_admin", "linux administration": "linux_admin",
    # MLOps
    "mlflow": "experiment_tracking", "wandb": "experiment_tracking",
    "weights and biases": "experiment_tracking",
    "experiment logging": "experiment_tracking",
    "deployment": "model_deployment", "deploy": "model_deployment",
    "serving": "model_deployment", "mlops": "model_deployment",
    "inference": "model_deployment",
    "drift": "ml_monitoring", "model monitoring": "ml_monitoring",
    "data drift": "ml_monitoring",
}

ROLE_ALIASES: dict[str, str] = {
    "ai engineer": "ai-ml-engineer", "ml engineer": "ai-ml-engineer",
    "machine learning engineer": "ai-ml-engineer", "ai/ml": "ai-ml-engineer",
    "ai ml engineer": "ai-ml-engineer", "data scientist": "ai-ml-engineer",
    "ai": "ai-ml-engineer", "ml": "ai-ml-engineer",
    "deep learning engineer": "ai-ml-engineer",
    "full stack": "full-stack-developer", "fullstack": "full-stack-developer",
    "full stack developer": "full-stack-developer",
    "full-stack engineer": "full-stack-developer",
    "full stack engineer": "full-stack-developer",
    "web developer": "full-stack-developer", "web dev": "full-stack-developer",
    "software engineer": "full-stack-developer",
    # Backend and frontend are their own paths, not Full-Stack. Routing them
    # to Full-Stack gave a backend learner React work and a frontend learner
    # databases.
    "backend": "backend-developer", "back end": "backend-developer",
    "backend developer": "backend-developer",
    "backend engineer": "backend-developer",
    "back-end developer": "backend-developer",
    "server side": "backend-developer", "api developer": "backend-developer",
    "api engineer": "backend-developer",
    "frontend": "frontend-developer", "front end": "frontend-developer",
    "frontend developer": "frontend-developer",
    "frontend engineer": "frontend-developer",
    "front-end developer": "frontend-developer",
    "ui developer": "frontend-developer", "ui engineer": "frontend-developer",
    "react developer": "frontend-developer",
    "data engineer": "data-engineer", "data engineering": "data-engineer",
    "etl developer": "data-engineer", "pipeline engineer": "data-engineer",
    "analytics engineer": "data-engineer",
    "analyst": "data-analyst", "data analyst": "data-analyst",
    "bi analyst": "data-analyst", "business analyst": "data-analyst",
    "business intelligence": "data-analyst",
    "cybersecurity": "cybersecurity-analyst", "cyber security": "cybersecurity-analyst",
    "security analyst": "cybersecurity-analyst", "infosec": "cybersecurity-analyst",
    "soc analyst": "cybersecurity-analyst", "security engineer": "cybersecurity-analyst",
    "pentester": "cybersecurity-analyst",
    "pen tester": "cybersecurity-analyst",
    "penetration tester": "cybersecurity-analyst",
    "penetration testing": "cybersecurity-analyst",
    "mlops engineer": "ai-ml-engineer",
    "ml ops engineer": "ai-ml-engineer",
    "mlops": "ai-ml-engineer",
    "mobile developer": "frontend-developer",
    "mobile app developer": "frontend-developer",
    "mobile apps": "frontend-developer",
    "ios developer": "frontend-developer",
    "android developer": "frontend-developer",
    "devops": "cloud-devops-engineer", "dev ops": "cloud-devops-engineer",
    "cloud engineer": "cloud-devops-engineer", "sre": "cloud-devops-engineer",
    "platform engineer": "cloud-devops-engineer",
    "site reliability": "cloud-devops-engineer",
    "infrastructure engineer": "cloud-devops-engineer",
}

# Phrases that legitimately map to more than one canonical role — never auto-pick.
AMBIGUOUS_ROLE_PHRASES: dict[str, tuple[str, ...]] = {
    "career in data": ("data-engineer", "data-analyst"),
    "work in data": ("data-engineer", "data-analyst"),
    "data career": ("data-engineer", "data-analyst"),
    "job in data": ("data-engineer", "data-analyst"),
    "cloud security": ("cybersecurity-analyst", "cloud-devops-engineer"),
    "security in the cloud": ("cybersecurity-analyst", "cloud-devops-engineer"),
}

# Qualitative experience wording -> observed proficiency.
# "no experience" is deliberately absent: it produces UNKNOWN, never 0.0.
LEVEL_LEXICON: tuple[tuple[str, float], ...] = (
    ("expert", 0.92), ("advanced", 0.85), ("very strong", 0.88),
    ("very good", 0.85), ("professional", 0.85), ("years of", 0.85),
    ("experienced", 0.85), ("fluent", 0.85),
    ("strong", 0.80), ("proficient", 0.80), ("confident", 0.78),
    ("well", 0.78), ("great", 0.80),
    ("solid", 0.75), ("comfortable", 0.72), ("good", 0.70),
    ("intermediate", 0.65), ("decent", 0.65), ("ok", 0.55), ("okay", 0.55),
    ("some", 0.40), ("basic", 0.35), ("beginner", 0.30), ("basics", 0.35),
    ("familiar", 0.35), ("learning", 0.30), ("rusty", 0.30),
    ("little", 0.25), ("weak", 0.25), ("new to", 0.20), ("novice", 0.25),
)

DEFAULT_LEVEL = 0.60

LEARNING_STYLES: dict[str, str] = {
    "video": "VIDEO", "videos": "VIDEO", "watching": "VIDEO",
    "lecture": "VIDEO", "lectures": "VIDEO",
    "reading": "READING", "read": "READING", "book": "READING",
    "books": "READING", "docs": "READING", "articles": "READING",
    "hands on": "HANDS_ON", "hands-on": "HANDS_ON", "practical": "HANDS_ON",
    "labs": "HANDS_ON", "exercises": "HANDS_ON", "interactive": "HANDS_ON",
    "project": "PROJECT", "projects": "PROJECT", "building": "PROJECT",
    "build": "PROJECT", "portfolio": "PROJECT",
    "mixed": "MIXED", "mix": "MIXED", "anything": "MIXED",
}


@dataclass(frozen=True)
class ResolvedEntity:
    slug: str
    name: str
    mention: str
    how: str  # SLUG | NAME | ALIAS


@dataclass(frozen=True)
class Vocabulary:
    """Lookup tables built once from the ontology bundle."""

    skill_by_key: dict[str, str]
    skill_names: dict[str, str]
    role_by_key: dict[str, str]
    role_names: dict[str, str]

    def resolve_skill(self, mention: str) -> ResolvedEntity | None:
        return _resolve(mention, self.skill_by_key, self.skill_names)

    def resolve_role(self, mention: str) -> ResolvedEntity | None:
        return _resolve(mention, self.role_by_key, self.role_names)

    def role_entities(self, slugs: tuple[str, ...], mention: str, how: str = "ALIAS") -> tuple[ResolvedEntity, ...]:
        out: list[ResolvedEntity] = []
        seen: set[str] = set()
        for slug in slugs:
            if slug not in self.role_names or slug in seen:
                continue
            seen.add(slug)
            out.append(ResolvedEntity(slug=slug, name=self.role_names[slug], mention=mention, how=how))
        return tuple(out)


def _normalise(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[^a-z0-9+#./\- ]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _resolve(
    mention: str,
    by_key: dict[str, str],
    names: dict[str, str],
) -> ResolvedEntity | None:
    key = _normalise(mention)
    if not key:
        return None
    slug = by_key.get(key)
    if slug is None:
        # Tolerate underscore/space/hyphen variation in a supplied slug.
        slug = by_key.get(key.replace(" ", "_")) or by_key.get(key.replace(" ", "-"))
    if slug is None:
        return None
    how = "SLUG" if key in {slug, slug.replace("_", " "), slug.replace("-", " ")} else (
        "NAME" if key == _normalise(names.get(slug, "")) else "ALIAS"
    )
    return ResolvedEntity(slug=slug, name=names.get(slug, slug), mention=mention, how=how)


def build_vocabulary(bundle: OntologyBundle) -> Vocabulary:
    skill_names = {item.slug: item.canonical_name for item in bundle.skills}
    role_names = {item.slug: item.name for item in bundle.roles}

    skill_by_key: dict[str, str] = {}
    for slug, name in skill_names.items():
        skill_by_key[_normalise(slug)] = slug
        skill_by_key[_normalise(slug.replace("_", " "))] = slug
        skill_by_key[_normalise(name)] = slug
    for alias, slug in SKILL_ALIASES.items():
        if slug in skill_names:
            skill_by_key.setdefault(_normalise(alias), slug)

    role_by_key: dict[str, str] = {}
    for slug, name in role_names.items():
        role_by_key[_normalise(slug)] = slug
        role_by_key[_normalise(slug.replace("-", " "))] = slug
        role_by_key[_normalise(name)] = slug
    for alias, slug in ROLE_ALIASES.items():
        if slug in role_names:
            role_by_key.setdefault(_normalise(alias), slug)

    return Vocabulary(
        skill_by_key=skill_by_key,
        skill_names=skill_names,
        role_by_key=role_by_key,
        role_names=role_names,
    )


def level_from_phrase(phrase: str) -> float | None:
    """Map qualitative experience wording to a proficiency.

    Returns None when the phrase asserts an absence of experience, so the
    caller records no evidence at all rather than a proficiency of zero.
    """
    text = _normalise(phrase)
    if not text:
        return None
    if re.search(r"\b(no|never|zero|none|not?)\b.{0,20}\b(experience|idea|clue|background)\b", text):
        return None
    if re.search(r"\b(don'?t|dont|cannot|can'?t|haven'?t|havent)\b", text):
        return None
    for marker, level in LEVEL_LEXICON:
        if marker in text:
            return level
    return None


DENIAL_MARKERS: tuple[str, ...] = (
    "no experience", "no idea", "not familiar", "have not", "do not",
    "haven't", "havent", "don't", "dont", "cannot", "can't", "cant",
    "never", "zero", "none", "nothing", "without", "not", "no",
)


@dataclass(frozen=True)
class ExperienceReading:
    """What the learner said about their level with one skill."""

    level: float | None
    denied: bool

    @property
    def stated(self) -> bool:
        return self.level is not None


def _nearest(haystack: str, markers: tuple[str, ...] | tuple[tuple[str, float], ...]):
    """Rightmost marker match: the one closest to the skill mention wins."""
    best: tuple[int, int, object] | None = None
    for entry in markers:
        marker, payload = entry if isinstance(entry, tuple) else (entry, entry)
        for match in re.finditer(rf"\b{re.escape(marker)}\b", haystack):
            candidate = (match.start(), len(marker), payload)
            if best is None or candidate[:2] > best[:2]:
                best = candidate
    return best


def read_experience(before: str, after: str = "") -> ExperienceReading:
    """Read the level nearest a skill mention, honouring denials.

    Position decides, not lexicon order. In "strong Linux and networking,
    never touched SIEM" the denial sits closer to SIEM than "strong" does, so
    SIEM is recorded as no evidence rather than as strong.
    """
    haystack = _normalise(before)
    level_hit = _nearest(haystack, LEVEL_LEXICON)
    denial_hit = _nearest(haystack, DENIAL_MARKERS)

    if denial_hit is not None and (
        level_hit is None or denial_hit[0] > level_hit[0]
    ):
        return ExperienceReading(level=None, denied=True)
    if level_hit is not None:
        return ExperienceReading(level=float(level_hit[2]), denied=False)

    tail = _normalise(after)
    if _nearest(tail, DENIAL_MARKERS) is not None and _nearest(tail, LEVEL_LEXICON) is None:
        return ExperienceReading(level=None, denied=True)
    tail_level = _nearest(tail, LEVEL_LEXICON)
    if tail_level is not None:
        return ExperienceReading(level=float(tail_level[2]), denied=False)
    return ExperienceReading(level=None, denied=False)


def learning_style_from_text(text: str) -> str | None:
    normalised = _normalise(text)
    for marker, style in LEARNING_STYLES.items():
        if re.search(rf"\b{re.escape(marker)}\b", normalised):
            return style
    return None


def weekly_hours_from_text(text: str) -> float | None:
    """Read an explicit weekly time budget. Ignores unrelated numbers."""
    normalised = _normalise(text)
    patterns = (
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b",
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalised)
        if not match:
            continue
        groups = [float(value) for value in match.groups() if value]
        hours = sum(groups) / len(groups)
        if "day" in normalised[match.end() : match.end() + 12]:
            hours *= 5  # a weekday budget, stated per day
        if 0 < hours <= 80:
            return round(hours, 1)
    return None


def timeframe_weeks_from_text(text: str) -> int | None:
    normalised = _normalise(text)
    match = re.search(r"(\d+)\s*(week|month|year)s?", normalised)
    if not match:
        return None
    count = int(match.group(1))
    unit = match.group(2)
    weeks = count * {"week": 1, "month": 4, "year": 52}[unit]
    return weeks if 0 < weeks <= 260 else None


def ambiguous_phrase_match(text: str) -> tuple[str, ...] | None:
    """Return canonical role slugs when text hits a known ambiguous phrase."""
    normalised = _normalise(text)
    for phrase, slugs in AMBIGUOUS_ROLE_PHRASES.items():
        if phrase in normalised:
            return slugs
    return None


def collect_roles_from_text(text: str, vocab: Vocabulary) -> tuple[ResolvedEntity, ...]:
    """Every distinct canonical role the text mentions, longest non-overlapping matches."""
    haystack = f" {_normalise(text)} "
    found: dict[str, ResolvedEntity] = {}
    consumed: list[tuple[int, int]] = []
    for key in sorted(vocab.role_by_key, key=len, reverse=True):
        if len(key) < 3:
            continue
        for match in re.finditer(rf"\b{re.escape(key)}\b", haystack):
            span = (match.start(), match.end())
            if any(start < span[1] and span[0] < end for start, end in consumed):
                continue
            slug = vocab.role_by_key[key]
            if slug not in found:
                entity = vocab.resolve_role(key)
                if entity is not None:
                    found[slug] = entity
                    consumed.append(span)
            break
    return tuple(found.values())
