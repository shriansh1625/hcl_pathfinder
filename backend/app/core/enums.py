from enum import StrEnum


class RelationshipType(StrEnum):
    HARD_PREREQUISITE = "HARD_PREREQUISITE"
    SOFT_PREREQUISITE = "SOFT_PREREQUISITE"
    RELATED = "RELATED"


class RequiredStatus(StrEnum):
    CORE = "CORE"
    ELECTIVE = "ELECTIVE"
    OPTIONAL = "OPTIONAL"


class ResourceType(StrEnum):
    COURSE = "course"
    PROJECT = "project"
    LAB = "lab"
    ASSESSMENT = "assessment"


class UrlStatus(StrEnum):
    VERIFIED = "verified"
    PENDING = "pending"
    UNAVAILABLE = "unavailable"


class EvidenceSource(StrEnum):
    SELF_REPORT = "SELF_REPORT"
    RESUME = "RESUME"
    PROJECT = "PROJECT"
    ASSESSMENT = "ASSESSMENT"
    PROGRESS = "PROGRESS"
    FEEDBACK = "FEEDBACK"


class SkillStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    DEVELOPING = "DEVELOPING"
    STRONG = "STRONG"
    GAP = "GAP"


class GapStatus(StrEnum):
    """Legacy role-relative status. SATISFIED means target_met, not 'close enough'."""

    UNKNOWN = "UNKNOWN"
    SATISFIED = "SATISFIED"
    DEVELOPING = "DEVELOPING"
    GAP = "GAP"


class EvidenceState(StrEnum):
    UNKNOWN = "UNKNOWN"
    KNOWN = "KNOWN"


class AttainmentStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    GAP = "GAP"
    NEAR_TARGET = "NEAR_TARGET"
    TARGET_MET = "TARGET_MET"


class ActionClass(StrEnum):
    VERIFY = "VERIFY"
    REMEDIATE = "REMEDIATE"
    REINFORCE = "REINFORCE"
    ADVANCE = "ADVANCE"
    REMEDIATE_BLOCKER = "REMEDIATE_BLOCKER"


class GapSeverity(StrEnum):
    NONE = "none"
    UNKNOWN = "unknown"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class PathStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class PathItemStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    INSERTED = "INSERTED"
    REMOVED = "REMOVED"


class PathItemType(StrEnum):
    RESOURCE = "RESOURCE"
    ASSESSMENT = "ASSESSMENT"
    MILESTONE = "MILESTONE"
    PROJECT = "PROJECT"


class AdaptationEventType(StrEnum):
    ASSESSMENT_FAILURE = "ASSESSMENT_FAILURE"
    ASSESSMENT_SUCCESS = "ASSESSMENT_SUCCESS"
    FEEDBACK = "FEEDBACK"
    TIME_CHANGE = "TIME_CHANGE"
    DIFFICULTY_CHANGE = "DIFFICULTY_CHANGE"
    MASTERY = "MASTERY"
    REMEDIATION_INSERTED = "REMEDIATION_INSERTED"
    RESOURCE_REPLACED = "RESOURCE_REPLACED"
    PATH_REORDERED = "PATH_REORDERED"
