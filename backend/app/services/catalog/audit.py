"""Static catalog forensics. Does not invent metadata or fetch the network."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.enums import ResourceType, UrlStatus
from app.ontology.load import OntologyBundle, ResourceSpec


ALLOWED_MODES = {"reading", "video", "project", "lab"}


@dataclass(frozen=True)
class UrlClass:
    slug: str
    format_valid: bool
    claimed_verified: bool
    classification: str


@dataclass(frozen=True)
class CatalogAudit:
    resource_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    url_classes: tuple[UrlClass, ...]


def classify_url(resource: ResourceSpec) -> UrlClass:
    """FORMAT vs claimed verification. Accessibility is a live check, not this function."""
    if resource.url_status == UrlStatus.UNAVAILABLE.value:
        return UrlClass(
            slug=resource.slug,
            format_valid=resource.url is None,
            claimed_verified=False,
            classification="UNAVAILABLE",
        )
    url = resource.url or ""
    parsed = urlparse(url)
    format_valid = parsed.scheme == "https" and bool(parsed.netloc)
    if not format_valid:
        classification = "URL_FORMAT_INVALID"
    elif resource.url_status == UrlStatus.VERIFIED.value:
        classification = "VERIFIED_RESOURCE"
    elif resource.url_status == UrlStatus.CLAIMED.value:
        classification = "CLAIMED_RESOURCE"
    else:
        classification = "URL_FORMAT_VALID"
    return UrlClass(
        slug=resource.slug,
        format_valid=format_valid,
        claimed_verified=resource.url_status == UrlStatus.CLAIMED.value,
        classification=classification,
    )


def audit_catalog(bundle: OntologyBundle) -> CatalogAudit:
    skills = {item.slug for item in bundle.skills}
    role_skills = {rs.slug for role in bundle.roles for rs in role.skills}
    errors: list[str] = []
    warnings: list[str] = []
    url_classes: list[UrlClass] = []
    seen: dict[tuple[str, str], str] = {}

    for resource in bundle.resources:
        url_classes.append(classify_url(resource))
        if resource.type not in {item.value for item in ResourceType}:
            errors.append(f"{resource.slug}: invalid type {resource.type}")
        if not 1 <= resource.difficulty <= 5:
            errors.append(f"{resource.slug}: indefensible difficulty {resource.difficulty}")
        if resource.duration_hours <= 0:
            errors.append(f"{resource.slug}: implausible duration")
        if resource.duration_hours > 40:
            warnings.append(f"{resource.slug}: duration {resource.duration_hours}h is unusually long")
        for mode in resource.learning_modes:
            if mode not in ALLOWED_MODES:
                errors.append(f"{resource.slug}: invalid learning mode {mode}")
        if not resource.skills:
            errors.append(f"{resource.slug}: no skill coverage")
        primary = [row for row in resource.skills if row.is_primary]
        if not primary:
            warnings.append(f"{resource.slug}: no primary skill")
        for row in resource.skills:
            if row.slug not in skills:
                errors.append(f"{resource.slug}: unknown skill {row.slug}")
            if row.is_primary and row.coverage_strength < 0.35:
                warnings.append(
                    f"{resource.slug}: weak primary coverage {row.slug}={row.coverage_strength}"
                )
        if not any(row.slug in role_skills for row in resource.skills):
            warnings.append(f"{resource.slug}: not derivable from any role_skills")
        for prereq in resource.prerequisites:
            if prereq.slug not in skills:
                errors.append(f"{resource.slug}: unknown prerequisite {prereq.slug}")
        key = (resource.type, next((row.slug for row in primary), ""))
        title_key = (key[0], key[1], round(next((row.coverage_strength for row in primary), 0), 1))
        prior = seen.get(title_key)
        if prior and key[1]:
            warnings.append(f"{resource.slug}: possible duplicate of {prior} for {key}")
        elif key[1]:
            seen[title_key] = resource.slug
        if resource.url_status == UrlStatus.VERIFIED.value:
            if not resource.url or not resource.url.startswith("https://"):
                errors.append(f"{resource.slug}: verified claim without https URL")
        if resource.url_status == UrlStatus.CLAIMED.value:
            if not resource.url or not resource.url.startswith("https://"):
                errors.append(f"{resource.slug}: claimed resource without https URL")
        if resource.url_status == UrlStatus.UNAVAILABLE.value and resource.url:
            errors.append(f"{resource.slug}: unavailable resource still has a URL")

    return CatalogAudit(
        resource_count=len(bundle.resources),
        errors=tuple(errors),
        warnings=tuple(warnings),
        url_classes=tuple(url_classes),
    )
